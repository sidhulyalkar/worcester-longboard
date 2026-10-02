#!/usr/bin/env python3
"""Replay validated Worcester X1 telemetry into commissioning metric evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SIGNALS = ROOT / "hardware/x1_telemetry_signal_registry_2026-10-02.json"
COMMISSIONING = ROOT / "hardware/rev_c_powered_commissioning_snapshot_2026-10-01.json"

TIME_SCALE = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9}


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _valid_fp(data: dict) -> bool:
    actual = data.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        return False
    unsigned = dict(data)
    unsigned.pop("authority_fingerprint_sha256", None)
    try:
        return actual == _digest(unsigned)
    except (TypeError, ValueError):
        return False


def _sync(item: dict) -> tuple[float, float]:
    unit = item["timestamp_unit"]
    model = item["sync_model"]
    return TIME_SCALE[unit] * float(model["scale"]), float(model["offset_s"])


def _load_stream_rows(
    manifest: dict,
    base_dir: Path,
) -> dict[str, list[dict[str, float]]]:
    by_signal: dict[str, list[dict[str, float]]] = {}
    for stream in manifest["streams"]:
        path = base_dir / stream["file"]
        if _sha256(path) != stream["file_sha256"]:
            raise ValueError(f"raw stream changed after validation: {stream['stream_id']}")
        factor, offset = _sync(stream)
        ts_col = stream["timestamp_column"]
        signal_columns = {
            decl["column"]: decl["signal_id"]
            for decl in stream["signals"]
        }
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                t = float(row[ts_col]) * factor + offset
                for column, signal_id in signal_columns.items():
                    value = row[column].strip()
                    if value == "":
                        continue
                    try:
                        parsed = float(value)
                    except ValueError:
                        # bool/int enum signals are not used for numeric metric replay.
                        continue
                    if math.isfinite(parsed):
                        by_signal.setdefault(signal_id, []).append(
                            {"t": t, "value": parsed}
                        )
    return by_signal


def _load_events(manifest: dict, base_dir: Path) -> list[dict]:
    event = manifest["event_log"]
    path = base_dir / event["file"]
    if _sha256(path) != event["file_sha256"]:
        raise ValueError("raw event log changed after validation")
    factor, offset = _sync(event)
    result: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            result.append(
                {
                    **row,
                    "session_time_s": float(row[event["timestamp_field"]])
                    * factor
                    + offset,
                }
            )
    return result


def _series_metric(
    metric_id: str,
    signal_id: str,
    unit: str,
    series: dict[str, list[dict[str, float]]],
    telemetry_fp: str,
) -> dict | None:
    values = series.get(signal_id, [])
    if not values:
        return None
    numeric = [item["value"] for item in values]
    return {
        "metric_id": metric_id,
        "unit": unit,
        "value": None,
        "evidence_ref": f"telemetry://{telemetry_fp}/signal/{signal_id}",
        "method": "validated_time_series_reference",
        "source_signals": [signal_id],
        "sample_count": len(values),
        "summary": {
            "min": min(numeric),
            "max": max(numeric),
            "mean": sum(numeric) / len(numeric),
        },
    }


def _deadman_decay(
    series: dict[str, list[dict[str, float]]],
    events: list[dict],
    telemetry_fp: str,
    threshold_a: float = 0.5,
) -> dict | None:
    releases = [
        event
        for event in events
        if event.get("event_type") == "DEADMAN_TRANSITION"
        and event.get("details", {}).get("active") is False
    ]
    left = series.get("drive_current_cmd_left_a", [])
    right = series.get("drive_current_cmd_right_a", [])
    if not releases or not left or not right or len(left) != len(right):
        return None

    decays: list[float] = []
    for release in releases:
        start = float(release["session_time_s"])
        for lrow, rrow in zip(left, right):
            t = max(lrow["t"], rrow["t"])
            if t < start:
                continue
            propulsion = max(0.0, lrow["value"], rrow["value"])
            if propulsion <= threshold_a:
                decays.append(t - start)
                break
    if not decays:
        return None
    return {
        "metric_id": "remote_release_propulsion_decay_s",
        "unit": "s",
        "value": max(decays),
        "evidence_ref": (
            f"telemetry://{telemetry_fp}/derived/remote_release_propulsion_decay_s"
        ),
        "method": (
            "maximum DEADMAN_TRANSITION(active=false) to first synchronized "
            f"left/right positive drive-current command <= {threshold_a:g} A"
        ),
        "source_signals": [
            "drive_current_cmd_left_a",
            "drive_current_cmd_right_a",
        ],
        "source_events": ["DEADMAN_TRANSITION"],
        "trial_values_s": decays,
    }


def _stopping_distance(
    series: dict[str, list[dict[str, float]]],
    events: list[dict],
    telemetry_fp: str,
    stop_threshold_mps: float = 0.1,
    sustained_stop_s: float = 0.5,
) -> dict | None:
    starts = [
        float(event["session_time_s"])
        for event in events
        if event.get("event_type") == "STOPPING_TEST_START"
    ]
    speed = series.get("ground_speed_mps", [])
    if not starts or len(speed) < 2:
        return None

    distances: list[float] = []
    for start in starts:
        points = [item for item in speed if item["t"] >= start]
        if len(points) < 2:
            continue

        stop_index: int | None = None
        for i, point in enumerate(points):
            if abs(point["value"]) > stop_threshold_mps:
                continue
            t0 = point["t"]
            j = i
            while j + 1 < len(points):
                next_point = points[j + 1]
                if abs(next_point["value"]) > stop_threshold_mps:
                    break
                j += 1
                if points[j]["t"] - t0 >= sustained_stop_s:
                    stop_index = j
                    break
            if stop_index is not None:
                break

        if stop_index is None:
            continue

        distance = 0.0
        previous = {"t": start, "value": points[0]["value"]}
        for point in points[: stop_index + 1]:
            dt = point["t"] - previous["t"]
            if dt > 0:
                distance += 0.5 * (
                    max(0.0, abs(previous["value"]))
                    + max(0.0, abs(point["value"]))
                ) * dt
            previous = point
        distances.append(distance)

    if not distances:
        return None
    return {
        "metric_id": "stopping_distance_m",
        "unit": "m",
        "value": max(distances),
        "evidence_ref": f"telemetry://{telemetry_fp}/derived/stopping_distance_m",
        "method": (
            "maximum trapezoidal integral of |ground_speed_mps| after "
            "STOPPING_TEST_START until speed <= "
            f"{stop_threshold_mps:g} m/s for >= {sustained_stop_s:g} s"
        ),
        "source_signals": ["ground_speed_mps"],
        "source_events": ["STOPPING_TEST_START"],
        "trial_values_m": distances,
    }


def replay(
    manifest: dict,
    base_dir: Path,
    telemetry_authority: dict,
    *,
    signal_registry: dict | None = None,
    commissioning_snapshot: dict | None = None,
) -> dict:
    signal_registry = signal_registry or json.loads(SIGNALS.read_text(encoding="utf-8"))
    commissioning_snapshot = commissioning_snapshot or json.loads(
        COMMISSIONING.read_text(encoding="utf-8")
    )
    errors: list[str] = []

    if telemetry_authority.get("authority") != "x1_telemetry_session":
        errors.append("telemetry authority must be x1_telemetry_session")
    if telemetry_authority.get("qualified") is not True:
        errors.append("telemetry session must be qualified")
    if not _valid_fp(telemetry_authority):
        errors.append("telemetry authority fingerprint is invalid")

    telemetry_fp = telemetry_authority.get("authority_fingerprint_sha256", "")
    for key in ("session_id", "board_id", "configuration_id", "commissioning_stage_id"):
        if manifest.get(key) != telemetry_authority.get(key):
            errors.append(f"manifest/telemetry authority {key} mismatch")

    if (
        manifest.get("power_architecture_fingerprint_sha256")
        != telemetry_authority.get("power_architecture_fingerprint_sha256")
    ):
        errors.append("power-architecture lineage mismatch")

    if errors:
        return {
            "schema_version": 1,
            "authority": "x1_commissioning_telemetry_replay",
            "qualified": False,
            "errors": errors,
            "powered_operation_authorized": False,
            "public_operation_authorized": False,
            "dog_accompanied_operation_authorized": False,
        }

    try:
        series = _load_stream_rows(manifest, base_dir)
        events = _load_events(manifest, base_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
        series = {}
        events = []

    signal_defs = {
        item["signal_id"]: item
        for item in signal_registry.get("signals", [])
        if isinstance(item, dict) and item.get("signal_id")
    }

    stage_id = manifest.get("commissioning_stage_id")
    stages = {
        stage["stage_id"]: stage
        for stage in commissioning_snapshot.get("stages", [])
    }
    stage = stages.get(stage_id)
    if stage is None:
        errors.append(f"unknown commissioning stage {stage_id!r}")
        required_metrics: list[str] = []
    else:
        required_metrics = list(stage.get("required_measurements", []))

    alias = {
        "left_motor_speed": "left_motor_erpm",
        "right_motor_speed": "right_motor_erpm",
    }

    metrics: list[dict] = []
    for metric_id in required_metrics:
        if metric_id == "remote_release_propulsion_decay_s":
            item = _deadman_decay(series, events, telemetry_fp)
        elif metric_id == "stopping_distance_m":
            item = _stopping_distance(series, events, telemetry_fp)
        else:
            signal_id = alias.get(metric_id, metric_id)
            definition = signal_defs.get(signal_id)
            item = (
                _series_metric(
                    metric_id,
                    signal_id,
                    definition["unit"],
                    series,
                    telemetry_fp,
                )
                if definition is not None
                else None
            )
        if item is None:
            errors.append(f"could not produce required telemetry metric: {metric_id}")
        else:
            metrics.append(item)

    qualified = not errors
    report = {
        "schema_version": 1,
        "authority": "x1_commissioning_telemetry_replay",
        "qualified": qualified,
        "errors": errors,
        "issues": [47, 49],
        "session_id": manifest.get("session_id"),
        "board_id": manifest.get("board_id"),
        "configuration_id": manifest.get("configuration_id"),
        "commissioning_stage_id": stage_id,
        "power_architecture_fingerprint_sha256": telemetry_authority.get(
            "power_architecture_fingerprint_sha256"
        ),
        "telemetry_session_fingerprint_sha256": telemetry_fp,
        "metrics": metrics,
        "metric_ids": sorted(item["metric_id"] for item in metrics),
        "commissioning_stage_qualified": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": (
            "Replay metrics are traceable summaries/references derived from the "
            "validated sealed telemetry session. They do not establish sensor "
            "calibration, pass/fail the commissioning stage, or grant operation "
            "authority."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--telemetry-authority", type=Path, required=True)
    parser.add_argument("--signal-registry", type=Path, default=SIGNALS)
    parser.add_argument("--commissioning-snapshot", type=Path, default=COMMISSIONING)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    report = replay(
        json.loads(manifest_path.read_text(encoding="utf-8")),
        manifest_path.parent,
        json.loads(args.telemetry_authority.read_text(encoding="utf-8")),
        signal_registry=json.loads(args.signal_registry.read_text(encoding="utf-8")),
        commissioning_snapshot=json.loads(
            args.commissioning_snapshot.read_text(encoding="utf-8")
        ),
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["qualified"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
