#!/usr/bin/env python3
"""Validate a synchronized Worcester X1 telemetry flight-recorder session.

This validator establishes schema, file-hash, timing, synchronization and
lineage integrity only. It does not establish physical sensor calibration,
vehicle safety or operation authority.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "hardware/x1_telemetry_contract_2026-10-01.json"

CALIBRATION_STATES = {"DECLARED_ONLY", "CALIBRATED", "NOT_APPLICABLE"}
SAMPLING_MODES = {"continuous", "event_driven"}


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_authority_fingerprint(data: dict) -> bool:
    actual = data.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        return False
    unsigned = dict(data)
    unsigned.pop("authority_fingerprint_sha256", None)
    try:
        return actual == _digest(unsigned)
    except (TypeError, ValueError):
        return False


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _positive(value: Any) -> bool:
    return _finite(value) and float(value) > 0


def _nonnegative(value: Any) -> bool:
    return _finite(value) and float(value) >= 0


def _parse_timestamp(errors: list[str], label: str, value: Any) -> datetime | None:
    if not _nonempty(value):
        errors.append(f"{label} must be a nonempty ISO-8601 timestamp")
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label} is not valid ISO-8601")
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        errors.append(f"{label} must include a timezone offset")
        return None
    return dt.astimezone(timezone.utc)


def _safe_stream_path(base_dir: Path, raw_path: Any) -> Path | None:
    if not _nonempty(raw_path):
        return None
    candidate = (base_dir / raw_path).resolve()
    try:
        candidate.relative_to(base_dir.resolve())
    except ValueError:
        return None
    return candidate


def _stream_contract(contract: dict) -> dict[str, dict]:
    return {
        item["stream_type"]: item
        for item in contract.get("streams", [])
        if isinstance(item, dict) and _nonempty(item.get("stream_type"))
    }


def _read_stream(
    path: Path,
    stream_type: str,
    spec: dict,
    manifest_stream: dict,
) -> tuple[dict, list[str], list[dict[str, str]]]:
    errors: list[str] = []
    rows: list[dict[str, str]] = []

    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            missing = [
                column
                for column in spec.get("required_columns", [])
                if column not in fieldnames
            ]
            if missing:
                errors.append(
                    f"{stream_type}: missing columns {', '.join(missing)}"
                )
                return {}, errors, []
            rows = list(reader)
    except OSError as exc:
        return {}, [f"{stream_type}: cannot read {path}: {exc}"], []

    if not rows:
        errors.append(f"{stream_type}: stream has no data rows")
        return {}, errors, rows

    times: list[float] = []
    numeric_columns = set(spec.get("numeric_columns", []))
    for line_no, row in enumerate(rows, start=2):
        for column in numeric_columns:
            raw = row.get(column, "")
            try:
                value = float(raw)
            except (TypeError, ValueError):
                errors.append(
                    f"{stream_type}:{line_no}: {column} must be numeric"
                )
                continue
            if not math.isfinite(value):
                errors.append(
                    f"{stream_type}:{line_no}: {column} must be finite"
                )
            if column == "controller_fault_bits" and value < 0:
                errors.append(
                    f"{stream_type}:{line_no}: controller_fault_bits must be nonnegative"
                )
        try:
            t = float(row.get("time_s", ""))
        except (TypeError, ValueError):
            continue
        if math.isfinite(t):
            times.append(t)

        if stream_type == "control":
            deadman = str(row.get("remote_deadman_active", "")).strip().lower()
            if deadman not in {"0", "1", "true", "false"}:
                errors.append(
                    f"{stream_type}:{line_no}: remote_deadman_active must be boolean-like"
                )
            if not str(row.get("ride_mode", "")).strip():
                errors.append(
                    f"{stream_type}:{line_no}: ride_mode must be nonempty"
                )
        elif stream_type == "events":
            if not str(row.get("event_type", "")).strip():
                errors.append(f"{stream_type}:{line_no}: event_type must be nonempty")
            if not str(row.get("event_code", "")).strip():
                errors.append(f"{stream_type}:{line_no}: event_code must be nonempty")

    if len(times) != len(rows):
        errors.append(f"{stream_type}: every row requires finite time_s")

    if times:
        if any(t < 0 for t in times):
            errors.append(f"{stream_type}: time_s must be nonnegative")
        for before, after in zip(times, times[1:]):
            if after <= before:
                errors.append(
                    f"{stream_type}: time_s must be strictly increasing"
                )
                break

    sampling_mode = manifest_stream.get("sampling_mode")
    gaps = [
        after - before
        for before, after in zip(times, times[1:])
        if after > before
    ]

    effective_rate_hz = None
    max_gap_observed_s = max(gaps) if gaps else None
    if sampling_mode == "continuous":
        if len(times) < 2:
            errors.append(
                f"{stream_type}: continuous stream requires at least two samples"
            )
        max_gap = manifest_stream.get("max_gap_s")
        if not _positive(max_gap):
            errors.append(f"{stream_type}: max_gap_s must be positive")
        elif max_gap_observed_s is not None and max_gap_observed_s > float(max_gap):
            errors.append(
                f"{stream_type}: observed gap {max_gap_observed_s:.6f}s exceeds "
                f"declared {float(max_gap):.6f}s"
            )

        nominal_rate = manifest_stream.get("nominal_rate_hz")
        tolerance = manifest_stream.get("nominal_rate_tolerance_fraction")
        if not _positive(nominal_rate):
            errors.append(f"{stream_type}: nominal_rate_hz must be positive")
        if not _nonnegative(tolerance) or float(tolerance) > 1:
            errors.append(
                f"{stream_type}: nominal_rate_tolerance_fraction must be in [0, 1]"
            )

        if gaps:
            median_gap = statistics.median(gaps)
            if median_gap > 0:
                effective_rate_hz = 1.0 / median_gap
                if _positive(nominal_rate) and _nonnegative(tolerance):
                    fractional_error = abs(
                        effective_rate_hz - float(nominal_rate)
                    ) / float(nominal_rate)
                    if fractional_error > float(tolerance):
                        errors.append(
                            f"{stream_type}: effective median rate "
                            f"{effective_rate_hz:.3f} Hz differs from declared "
                            f"{float(nominal_rate):.3f} Hz by more than tolerance"
                        )
    elif sampling_mode == "event_driven":
        if manifest_stream.get("nominal_rate_hz") is not None:
            errors.append(
                f"{stream_type}: event-driven stream nominal_rate_hz must be null"
            )
        if manifest_stream.get("max_gap_s") is not None:
            errors.append(
                f"{stream_type}: event-driven stream max_gap_s must be null"
            )
    else:
        errors.append(f"{stream_type}: invalid sampling_mode")

    stats = {
        "sample_count": len(rows),
        "start_time_s": times[0] if times else None,
        "end_time_s": times[-1] if times else None,
        "duration_s": (
            times[-1] - times[0]
            if len(times) >= 2
            else 0.0 if times else None
        ),
        "effective_median_rate_hz": (
            round(effective_rate_hz, 6)
            if effective_rate_hz is not None
            else None
        ),
        "max_gap_observed_s": (
            round(max_gap_observed_s, 6)
            if max_gap_observed_s is not None
            else None
        ),
    }
    return stats, errors, rows


def validate(
    manifest: dict,
    base_dir: Path,
    power_architecture: dict,
    contract: dict | None = None,
) -> dict:
    contract = contract or json.loads(CONTRACT.read_text(encoding="utf-8"))
    errors: list[str] = []

    if manifest.get("schema_version") != 1:
        errors.append("manifest schema_version must be 1")
    if manifest.get("scope") != "x1_telemetry_session":
        errors.append("wrong telemetry manifest scope")

    for key in ("session_id", "board_id", "configuration_id", "reference_clock_id"):
        if not _nonempty(manifest.get(key)):
            errors.append(f"{key} must be a nonempty string")

    stage_id = manifest.get("commissioning_stage_id")
    stage_req = contract.get("stage_requirements", {}).get(stage_id)
    if not isinstance(stage_req, dict):
        errors.append(
            "commissioning_stage_id must be one of the telemetry-supported Stage 1-4 IDs"
        )
        stage_req = {
            "required_stream_types": [],
            "required_metric_ids": [],
            "required_event_codes": [],
        }

    started = _parse_timestamp(errors, "started_at_utc", manifest.get("started_at_utc"))
    ended = _parse_timestamp(errors, "ended_at_utc", manifest.get("ended_at_utc"))
    session_duration_s = None
    if started is not None and ended is not None:
        if ended <= started:
            errors.append("ended_at_utc must be after started_at_utc")
        else:
            session_duration_s = (ended - started).total_seconds()

    if (
        power_architecture.get("authority") != "x1_power_architecture"
        or power_architecture.get("qualified") is not True
        or not _valid_authority_fingerprint(power_architecture)
    ):
        errors.append("power architecture must be qualified and fingerprint-valid")
    power_fp = power_architecture.get("authority_fingerprint_sha256")
    if manifest.get("power_architecture_fingerprint_sha256") != power_fp:
        errors.append("power_architecture_fingerprint_sha256 mismatch")

    if not _nonempty(manifest.get("firmware_revision")):
        errors.append("firmware_revision must be nonempty")

    for key in (
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if manifest.get(key) is not False:
            errors.append(f"{key} must be false")

    minimum_overlap = manifest.get("minimum_required_overlap_s")
    if not _positive(minimum_overlap):
        errors.append("minimum_required_overlap_s must be positive")

    processing = manifest.get("processing")
    if not isinstance(processing, dict):
        errors.append("processing must be an object")
        processing = {}
    if not _nonempty(processing.get("longitudinal_accel_column")):
        errors.append("processing.longitudinal_accel_column must be nonempty")
    window = processing.get("jerk_smoothing_window_samples")
    if not isinstance(window, int) or isinstance(window, bool) or window <= 0 or window % 2 == 0:
        errors.append(
            "processing.jerk_smoothing_window_samples must be a positive odd integer"
        )
    if not _positive(processing.get("propulsion_zero_threshold_a")):
        errors.append("processing.propulsion_zero_threshold_a must be positive")
    if not _positive(processing.get("propulsion_zero_hold_s")):
        errors.append("processing.propulsion_zero_hold_s must be positive")

    anomalies = manifest.get("anomalies")
    if not isinstance(anomalies, list):
        errors.append("anomalies must be a list")
    elif anomalies:
        errors.append("telemetry session cannot qualify with unresolved capture anomalies")

    specs = _stream_contract(contract)
    streams = manifest.get("streams")
    if not isinstance(streams, list) or not streams:
        errors.append("streams must be a nonempty list")
        streams = []

    by_type: dict[str, dict] = {}
    for index, stream in enumerate(streams):
        if not isinstance(stream, dict):
            errors.append(f"stream {index} must be an object")
            continue
        stream_type = stream.get("stream_type")
        if stream_type not in specs:
            errors.append(f"stream {index}: unsupported stream_type {stream_type!r}")
            continue
        if stream_type in by_type:
            errors.append(f"duplicate stream_type: {stream_type}")
            continue
        by_type[stream_type] = stream

    required_streams = set(stage_req.get("required_stream_types", []))
    for stream_type in sorted(required_streams):
        if stream_type not in by_type:
            errors.append(f"required stream missing: {stream_type}")

    stream_stats: dict[str, dict] = {}
    event_rows: list[dict[str, str]] = []

    for stream_type, stream in by_type.items():
        spec = specs[stream_type]

        if stream.get("sampling_mode") not in SAMPLING_MODES:
            errors.append(f"{stream_type}: invalid sampling_mode")
        expected_mode = spec.get("sampling_mode")
        if stream.get("sampling_mode") != expected_mode:
            errors.append(
                f"{stream_type}: sampling_mode must be {expected_mode}"
            )

        for key in ("source_id", "clock_id", "synchronization_method"):
            if not _nonempty(stream.get(key)):
                errors.append(f"{stream_type}: {key} must be nonempty")

        if stream.get("timestamps_normalized_to_reference") is not True:
            errors.append(
                f"{stream_type}: timestamps_normalized_to_reference must be true"
            )

        sync_uncertainty = stream.get("synchronization_uncertainty_s")
        max_sync_uncertainty = stream.get("max_allowed_sync_uncertainty_s")
        if not _nonnegative(sync_uncertainty):
            errors.append(
                f"{stream_type}: synchronization_uncertainty_s must be nonnegative"
            )
        if not _positive(max_sync_uncertainty):
            errors.append(
                f"{stream_type}: max_allowed_sync_uncertainty_s must be positive"
            )
        if (
            _nonnegative(sync_uncertainty)
            and _positive(max_sync_uncertainty)
            and float(sync_uncertainty) > float(max_sync_uncertainty)
        ):
            errors.append(
                f"{stream_type}: synchronization uncertainty exceeds declared maximum"
            )

        sync_method = stream.get("synchronization_method")
        if sync_method != "same_reference_clock" and not _nonempty(
            stream.get("synchronization_evidence_ref")
        ):
            errors.append(
                f"{stream_type}: synchronization_evidence_ref required for "
                f"{sync_method!r}"
            )

        calibration = stream.get("calibration_status")
        if calibration not in CALIBRATION_STATES:
            errors.append(f"{stream_type}: invalid calibration_status")
        if calibration == "CALIBRATED" and not _nonempty(
            stream.get("calibration_evidence_ref")
        ):
            errors.append(
                f"{stream_type}: calibrated stream requires calibration_evidence_ref"
            )

        path = _safe_stream_path(base_dir, stream.get("file_path"))
        if path is None:
            errors.append(f"{stream_type}: invalid or escaping file_path")
            continue
        if not path.exists():
            errors.append(f"{stream_type}: stream file does not exist")
            continue

        expected_hash = stream.get("file_sha256")
        if not _nonempty(expected_hash):
            errors.append(f"{stream_type}: file_sha256 must be finalized")
        else:
            actual_hash = _sha256_file(path)
            if expected_hash != actual_hash:
                errors.append(f"{stream_type}: file SHA-256 mismatch")

        stats, stream_errors, rows = _read_stream(
            path, stream_type, spec, stream
        )
        errors.extend(stream_errors)
        if stats:
            stream_stats[stream_type] = stats
        if stream_type == "events":
            event_rows = rows

        if session_duration_s is not None and stats:
            end_time = stats.get("end_time_s")
            allowance = (
                float(sync_uncertainty)
                if _nonnegative(sync_uncertainty)
                else 0.0
            )
            if (
                isinstance(end_time, (int, float))
                and end_time > session_duration_s + allowance
            ):
                errors.append(
                    f"{stream_type}: normalized stream extends past declared session duration"
                )

    if required_streams and required_streams.issubset(stream_stats):
        starts = [
            float(stream_stats[stream_type]["start_time_s"])
            for stream_type in required_streams
        ]
        ends = [
            float(stream_stats[stream_type]["end_time_s"])
            for stream_type in required_streams
        ]
        overlap_start = max(starts)
        overlap_end = min(ends)
        common_overlap_s = overlap_end - overlap_start
        if (
            _positive(minimum_overlap)
            and common_overlap_s < float(minimum_overlap)
        ):
            errors.append(
                f"required stream common overlap {common_overlap_s:.6f}s is below "
                f"minimum {float(minimum_overlap):.6f}s"
            )
    else:
        common_overlap_s = None

    event_codes = [
        str(row.get("event_code", "")).strip()
        for row in event_rows
        if str(row.get("event_code", "")).strip()
    ]
    required_session_events = [
        "SESSION_START",
        "COMMISSIONING_STAGE_START",
        "COMMISSIONING_STAGE_STOP",
        "SESSION_STOP",
    ]
    for event_code in required_session_events:
        if event_code not in event_codes:
            errors.append(f"required event missing: {event_code}")

    if all(event in event_codes for event in required_session_events):
        positions = [event_codes.index(event) for event in required_session_events]
        if positions != sorted(positions) or len(set(positions)) != len(positions):
            errors.append("session/stage start-stop events are out of order")

    for event_code in stage_req.get("required_event_codes", []):
        if event_code not in event_codes:
            errors.append(
                f"required stage event missing: {event_code}"
            )

    calibration_summary = {
        stream_type: stream.get("calibration_status")
        for stream_type, stream in by_type.items()
    }
    all_required_calibrated = all(
        calibration_summary.get(stream_type) in {"CALIBRATED", "NOT_APPLICABLE"}
        for stream_type in required_streams
    ) if required_streams else False

    valid = not errors
    report = {
        "schema_version": 1,
        "authority": "x1_telemetry_session",
        "valid": valid,
        "errors": errors,
        "issue": 47,
        "session_id": manifest.get("session_id"),
        "board_id": manifest.get("board_id"),
        "configuration_id": manifest.get("configuration_id"),
        "commissioning_stage_id": stage_id,
        "power_architecture_fingerprint_sha256": power_fp,
        "firmware_revision": manifest.get("firmware_revision"),
        "reference_clock_id": manifest.get("reference_clock_id"),
        "stream_stats": stream_stats,
        "common_required_stream_overlap_s": (
            round(common_overlap_s, 6)
            if isinstance(common_overlap_s, (int, float))
            else None
        ),
        "calibration_status_by_stream": calibration_summary,
        "all_required_streams_calibrated_or_not_applicable": (
            all_required_calibrated
        ),
        "telemetry_integrity_qualified": valid,
        "sensor_calibration_authority": False,
        "physical_vehicle_authority": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": (
            "A passing telemetry report proves file/schema/hash/timebase/lineage "
            "integrity for the declared private session. It does not prove physical "
            "sensor calibration, safe vehicle behavior, or operation authority."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--power-architecture", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    power = json.loads(args.power_architecture.read_text(encoding="utf-8"))
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    report = validate(manifest, manifest_path.parent, power, contract)

    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
