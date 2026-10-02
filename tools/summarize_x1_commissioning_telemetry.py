#!/usr/bin/env python3
"""Replay validated X1 telemetry into Issue #45 commissioning evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import fmean
from typing import Any

from tools.validate_x1_telemetry_session import (
    REGISTRY_PATH,
    SNAPSHOT_PATH,
    _digest,
    validate_session,
)


DIRECT_METRICS = {
    "pack_voltage_v": ("powertrain", "pack_voltage_v"),
    "battery_current_a": ("powertrain", "battery_current_a"),
    "left_phase_current_a": ("powertrain", "left_phase_current_a"),
    "right_phase_current_a": ("powertrain", "right_phase_current_a"),
    "left_motor_erpm": ("powertrain", "left_motor_erpm"),
    "right_motor_erpm": ("powertrain", "right_motor_erpm"),
    "left_motor_speed": ("powertrain", "left_motor_erpm"),
    "right_motor_speed": ("powertrain", "right_motor_erpm"),
    "left_motor_temperature_c": ("powertrain", "left_motor_temperature_c"),
    "right_motor_temperature_c": ("powertrain", "right_motor_temperature_c"),
    "left_controller_temperature_c": (
        "powertrain",
        "left_controller_temperature_c",
    ),
    "right_controller_temperature_c": (
        "powertrain",
        "right_controller_temperature_c",
    ),
    "ground_speed_mps": ("motion", "ground_speed_mps"),
    "longitudinal_accel_mps2": ("motion", "longitudinal_accel_mps2"),
}

UNITS = {
    "pack_voltage_v": "V",
    "battery_current_a": "A",
    "left_phase_current_a": "A",
    "right_phase_current_a": "A",
    "left_motor_erpm": "ERPM",
    "right_motor_erpm": "ERPM",
    "left_motor_speed": "ERPM",
    "right_motor_speed": "ERPM",
    "left_motor_temperature_c": "degC",
    "right_motor_temperature_c": "degC",
    "left_controller_temperature_c": "degC",
    "right_controller_temperature_c": "degC",
    "ground_speed_mps": "m/s",
    "longitudinal_accel_mps2": "m/s^2",
    "longitudinal_jerk_mps3": "m/s^3",
    "stopping_distance_m": "m",
    "remote_release_propulsion_decay_s": "s",
}


def _numeric(values: list[Any]) -> list[float]:
    return [
        float(value)
        for value in values
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    ]


def _stats(rows: list[dict], field: str) -> dict:
    values = _numeric([row.get(field) for row in rows])
    if not values:
        raise ValueError(f"no finite values for {field}")
    return {
        "sample_count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": fmean(values),
        "peak_abs": max(abs(value) for value in values),
    }


def _events_of(events: list[dict], types: set[str]) -> list[dict]:
    return [
        event
        for event in events
        if event.get("event_type") in types
        and isinstance(event.get("session_time_s"), (int, float))
    ]


def _remote_release_decay(
    control: list[dict],
    events: list[dict],
    *,
    current_threshold_a: float,
    stable_window_s: float,
) -> tuple[float, dict]:
    candidates = _events_of(events, {"DEADMAN_RELEASE", "REMOTE_TIMEOUT"})
    if not candidates:
        raise ValueError("remote-release event is missing")

    for event in candidates:
        event_time = float(event["session_time_s"])
        after = [
            row
            for row in control
            if isinstance(row.get("session_time_s"), (int, float))
            and float(row["session_time_s"]) >= event_time
        ]
        for index, row in enumerate(after):
            left = row.get("left_drive_current_cmd_a")
            right = row.get("right_drive_current_cmd_a")
            if not all(
                isinstance(x, (int, float))
                and math.isfinite(float(x))
                and abs(float(x)) <= current_threshold_a
                for x in (left, right)
            ):
                continue
            start = float(row["session_time_s"])
            target_end = start + stable_window_s
            window = [
                sample
                for sample in after[index:]
                if float(sample["session_time_s"]) <= target_end + 1e-12
            ]
            if not window or float(window[-1]["session_time_s"]) < target_end:
                continue
            if all(
                abs(float(sample["left_drive_current_cmd_a"])) <= current_threshold_a
                and abs(float(sample["right_drive_current_cmd_a"])) <= current_threshold_a
                for sample in window
            ):
                return (
                    max(0.0, start - event_time),
                    {
                        "event_type": event["event_type"],
                        "event_seq": event.get("seq"),
                        "event_time_s": event_time,
                        "stable_current_start_s": start,
                        "current_threshold_a": current_threshold_a,
                        "stable_window_s": stable_window_s,
                    },
                )
    raise ValueError(
        "drive current never reached the declared stable zero-current window "
        "after a remote-release event"
    )


def _peak_jerk(motion: list[dict]) -> tuple[float, dict]:
    points = [
        (
            float(row["session_time_s"]),
            float(row["longitudinal_accel_mps2"]),
        )
        for row in motion
        if isinstance(row.get("session_time_s"), (int, float))
        and isinstance(row.get("longitudinal_accel_mps2"), (int, float))
    ]
    jerks: list[float] = []
    for (t0, a0), (t1, a1) in zip(points, points[1:]):
        dt = t1 - t0
        if dt <= 0:
            raise ValueError("motion timestamps are not strictly increasing")
        jerk = (a1 - a0) / dt
        if not math.isfinite(jerk):
            raise ValueError("nonfinite jerk derived from motion stream")
        jerks.append(jerk)
    if not jerks:
        raise ValueError("not enough motion samples to derive jerk")
    return max(abs(value) for value in jerks), {
        "method_id": "finite_difference_peak_abs_v1",
        "derived_sample_count": len(jerks),
    }


def _stopping_distance(
    motion: list[dict],
    events: list[dict],
    *,
    stop_speed_threshold_mps: float,
) -> tuple[float, dict]:
    markers = _events_of(
        events,
        {"MECHANICAL_BRAKE_MARKER", "OPERATOR_STOP"},
    )
    if not markers:
        raise ValueError("brake/stop marker is missing")

    for marker in markers:
        marker_time = float(marker["session_time_s"])
        points = [
            (
                float(row["session_time_s"]),
                max(0.0, float(row["ground_speed_mps"])),
            )
            for row in motion
            if isinstance(row.get("session_time_s"), (int, float))
            and isinstance(row.get("ground_speed_mps"), (int, float))
            and float(row["session_time_s"]) >= marker_time
        ]
        if len(points) < 2 or points[0][1] <= stop_speed_threshold_mps:
            continue

        distance = 0.0
        end_time = None
        for (t0, v0), (t1, v1) in zip(points, points[1:]):
            dt = t1 - t0
            if dt <= 0:
                raise ValueError("motion timestamps are not strictly increasing")
            if v1 <= stop_speed_threshold_mps:
                if v0 > stop_speed_threshold_mps and v1 != v0:
                    fraction = (
                        (v0 - stop_speed_threshold_mps) / (v0 - v1)
                    )
                    fraction = min(1.0, max(0.0, fraction))
                    dt_stop = dt * fraction
                    v_end = v0 + (v1 - v0) * fraction
                    distance += 0.5 * (v0 + v_end) * dt_stop
                    end_time = t0 + dt_stop
                else:
                    distance += 0.5 * (v0 + v1) * dt
                    end_time = t1
                break
            distance += 0.5 * (v0 + v1) * dt

        if end_time is not None:
            return distance, {
                "method_id": "trapezoid_until_stop_threshold_v1",
                "marker_event_type": marker["event_type"],
                "marker_event_seq": marker.get("seq"),
                "marker_time_s": marker_time,
                "stop_time_s": end_time,
                "stop_speed_threshold_mps": stop_speed_threshold_mps,
            }

    raise ValueError(
        "no brake/stop marker is followed by a measurable transition to the stop threshold"
    )


def summarize(
    manifest_path: Path,
    *,
    power_architecture: dict,
    pre_health: dict,
    registry: dict | None = None,
    snapshot: dict | None = None,
) -> dict:
    report, parsed = validate_session(
        manifest_path,
        power_architecture=power_architecture,
        pre_health=pre_health,
        registry=registry,
        snapshot=snapshot,
    )
    errors: list[str] = []
    if not report["valid"]:
        errors.append("telemetry session is structurally invalid")
    if not report["commissioning_evidence_ready"]:
        errors.append("telemetry session is not commissioning-evidence ready")

    stage_id = report["commissioning_stage_id"]
    snapshot_data = parsed["snapshot"]
    stage = snapshot_data["stage_requirements"].get(stage_id, {})
    required = list(stage.get("required_measurements", []))
    measurements: list[dict] = []
    details: dict[str, dict] = {}
    session_fp = report["authority_fingerprint_sha256"]

    if not errors:
        for metric_id in required:
            if metric_id in DIRECT_METRICS:
                stream_id, field = DIRECT_METRICS[metric_id]
                rows = parsed["streams"].get(stream_id, [])
                try:
                    stats = _stats(rows, field)
                except ValueError as exc:
                    errors.append(f"{metric_id}: {exc}")
                    continue
                details[metric_id] = {
                    "kind": "direct_time_series",
                    "stream_id": stream_id,
                    "field": field,
                    **stats,
                }
                measurements.append(
                    {
                        "metric_id": metric_id,
                        "unit": UNITS[metric_id],
                        "source": (
                            f"validated telemetry {stream_id}.{field}"
                        ),
                        "evidence_ref": (
                            f"x1_telemetry_session_evidence:{session_fp}#"
                            f"{stream_id}.{field}"
                        ),
                    }
                )
                continue

            defaults = snapshot_data["replay_defaults"]
            try:
                if metric_id == "remote_release_propulsion_decay_s":
                    value, method = _remote_release_decay(
                        parsed["streams"].get("control", []),
                        parsed["events"],
                        current_threshold_a=float(
                            defaults["drive_current_zero_threshold_a"]
                        ),
                        stable_window_s=float(
                            defaults["stable_zero_window_s"]
                        ),
                    )
                elif metric_id == "longitudinal_jerk_mps3":
                    value, method = _peak_jerk(
                        parsed["streams"].get("motion", [])
                    )
                elif metric_id == "stopping_distance_m":
                    value, method = _stopping_distance(
                        parsed["streams"].get("motion", []),
                        parsed["events"],
                        stop_speed_threshold_mps=float(
                            defaults["stop_speed_threshold_mps"]
                        ),
                    )
                else:
                    raise ValueError("no replay method is registered")
            except ValueError as exc:
                errors.append(f"{metric_id}: {exc}")
                continue

            if not math.isfinite(float(value)):
                errors.append(f"{metric_id}: derived value is nonfinite")
                continue
            details[metric_id] = {
                "kind": "derived_scalar",
                "value": float(value),
                **method,
            }
            measurements.append(
                {
                    "metric_id": metric_id,
                    "unit": UNITS[metric_id],
                    "source": (
                        f"validated telemetry replay {method.get('method_id', 'remote_release_decay_v1')}"
                    ),
                    "value": float(value),
                    "evidence_ref": (
                        f"x1_telemetry_session_evidence:{session_fp}#derived/{metric_id}"
                    ),
                }
            )

    observed_ids = {item["metric_id"] for item in measurements}
    missing = sorted(set(required) - observed_ids)
    if missing:
        errors.append(
            "required commissioning telemetry measurements missing: "
            + ", ".join(missing)
        )

    valid = not errors
    output = {
        "schema_version": 1,
        "authority": "x1_commissioning_telemetry_evidence",
        "valid": valid,
        "errors": errors,
        "issue_49_contract": True,
        "issue_47_replay": True,
        "session_id": report["session_id"],
        "board_id": report["board_id"],
        "configuration_id": report["configuration_id"],
        "commissioning_stage_id": stage_id,
        "telemetry_session_fingerprint_sha256": session_fp,
        "power_architecture_fingerprint_sha256": report[
            "power_architecture_fingerprint_sha256"
        ],
        "pre_lifecycle_health_fingerprint_sha256": report[
            "pre_lifecycle_health_fingerprint_sha256"
        ],
        "measurements": measurements,
        "metric_details": details,
        "raw_telemetry_authority": False,
        "commissioning_measurement_evidence_only": True,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": (
            "A passing replay report proves only that the listed Issue #45 "
            "measurements are backed by one validated synchronized telemetry "
            "session for the recorded lineage. It does not qualify the vehicle, "
            "controller settings, sensor safety, or any operating activity."
        ),
    }
    output["authority_fingerprint_sha256"] = _digest(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--power-architecture", type=Path, required=True)
    parser.add_argument("--pre-health-state", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT_PATH)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = summarize(
        args.manifest,
        power_architecture=json.loads(
            args.power_architecture.read_text(encoding="utf-8")
        ),
        pre_health=json.loads(
            args.pre_health_state.read_text(encoding="utf-8")
        ),
        registry=json.loads(args.registry.read_text(encoding="utf-8")),
        snapshot=json.loads(args.snapshot.read_text(encoding="utf-8")),
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
