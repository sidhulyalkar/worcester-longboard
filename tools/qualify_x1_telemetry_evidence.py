#!/usr/bin/env python3
"""Qualify Worcester X1 black-box telemetry evidence.

A passing report establishes data quality only for the declared Issue #45
commissioning stage. It never authorizes controller settings, battery settings,
powered riding, public operation, or dog-accompanied operation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "hardware/rev_c_telemetry_evidence_snapshot_2026-10-01.json"
REGISTRY = ROOT / "hardware/x1_telemetry_signal_registry.json"

METRIC_UNITS = {
    "remote_release_propulsion_decay_s": "s",
    "stopping_distance_m": "m",
}


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


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


def _load_csv(path: Path, expected_columns: list[str]) -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    rows: list[dict] = []
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != expected_columns:
                return [], [
                    f"{path}: expected CSV columns {expected_columns}, "
                    f"found {reader.fieldnames}"
                ]
            rows = list(reader)
    except OSError as exc:
        errors.append(f"{path}: {exc}")
    return rows, errors


def _load_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    rows: list[dict] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line_no, raw in enumerate(handle, start=1):
                text = raw.strip()
                if not text:
                    continue
                try:
                    item = json.loads(text)
                except json.JSONDecodeError as exc:
                    errors.append(f"{path}:{line_no}: invalid JSON: {exc}")
                    continue
                if not isinstance(item, dict):
                    errors.append(f"{path}:{line_no}: event must be an object")
                    continue
                rows.append(item)
    except OSError as exc:
        errors.append(f"{path}: {exc}")
    return rows, errors


def _load_json_array(path: Path) -> tuple[list[dict], list[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"{path}: {exc}"]
    if not isinstance(data, list):
        return [], [f"{path}: expected a JSON array"]
    errors = [
        f"{path}: item {i} must be an object"
        for i, item in enumerate(data)
        if not isinstance(item, dict)
    ]
    return [item for item in data if isinstance(item, dict)], errors


def _validate_power(errors: list[str], data: dict) -> None:
    if data.get("authority") != "x1_power_architecture":
        errors.append("power architecture must be x1_power_architecture")
    if data.get("qualified") is not True:
        errors.append("power architecture must be qualified")
    if not _valid_fp(data):
        errors.append("power architecture fingerprint is invalid")


def _validate_health(
    errors: list[str],
    data: dict,
    board_id: str,
    configuration_id: str,
) -> None:
    if data.get("authority") != "x1_lifecycle_health_state":
        errors.append("pre-health must be x1_lifecycle_health_state")
    if data.get("valid") is not True:
        errors.append("pre-health must be valid")
    if data.get("health_state") != "READY_FOR_ALLOWED_ACTIVITY":
        errors.append("pre-health must be READY_FOR_ALLOWED_ACTIVITY")
    if data.get("ready_for_allowed_activity") is not True:
        errors.append("pre-health must be ready_for_allowed_activity")
    if data.get("board_id") != board_id:
        errors.append("pre-health board_id mismatch")
    if data.get("current_configuration_id") != configuration_id:
        errors.append("pre-health configuration_id mismatch")
    for key in (
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if data.get(key) is not False:
            errors.append(f"pre-health {key} must be false")
    if not _valid_fp(data):
        errors.append("pre-health fingerprint is invalid")


def qualify(
    manifest: dict,
    base_dir: Path,
    power_architecture: dict,
    pre_health: dict,
    *,
    snapshot: dict | None = None,
    registry: dict | None = None,
) -> dict:
    snapshot = snapshot or json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    registry = registry or json.loads(REGISTRY.read_text(encoding="utf-8"))
    errors: list[str] = []

    if manifest.get("schema_version") != 1:
        errors.append("manifest schema_version must be 1")
    if manifest.get("scope") != "x1_telemetry_session":
        errors.append("wrong telemetry session scope")
    if manifest.get("issue") != 49:
        errors.append("telemetry session issue must be 49")

    board_id = manifest.get("board_id")
    configuration_id = manifest.get("configuration_id")
    session_id = manifest.get("session_id")
    for label, value in (
        ("session_id", session_id),
        ("board_id", board_id),
        ("configuration_id", configuration_id),
    ):
        if not _nonempty(value):
            errors.append(f"{label} must be nonempty")

    stages = snapshot.get("stage_requirements", {})
    stage_id = manifest.get("commissioning_stage_id")
    if stage_id not in stages:
        errors.append("commissioning_stage_id must be a Stage 1-4 telemetry stage")
        stage = {}
    else:
        stage = stages[stage_id]
        if manifest.get("commissioning_stage_index") != stage.get("stage_index"):
            errors.append("commissioning_stage_index does not match stage reference")

    started = _parse_timestamp(errors, "started_at_utc", manifest.get("started_at_utc"))
    completed = _parse_timestamp(
        errors, "completed_at_utc", manifest.get("completed_at_utc")
    )
    if started is not None and completed is not None and completed <= started:
        errors.append("completed_at_utc must be after started_at_utc")

    _validate_power(errors, power_architecture)
    _validate_health(errors, pre_health, board_id, configuration_id)
    power_fp = power_architecture.get("authority_fingerprint_sha256")
    health_fp = pre_health.get("authority_fingerprint_sha256")
    if manifest.get("power_architecture_fingerprint_sha256") != power_fp:
        errors.append("manifest power-architecture fingerprint mismatch")
    if manifest.get("pre_lifecycle_health_fingerprint_sha256") != health_fp:
        errors.append("manifest pre-health fingerprint mismatch")

    for key in (
        "powered_operation_authorized",
        "controller_configuration_authority",
        "battery_configuration_authority",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if manifest.get(key) is not False:
            errors.append(f"manifest {key} must be false")

    logger = manifest.get("logger_identity")
    if not isinstance(logger, dict):
        errors.append("logger_identity must be an object")
        logger = {}
    for key in (
        "firmware_build_id",
        "firmware_source_revision",
        "hardware_id",
        "storage_type",
    ):
        if not _nonempty(logger.get(key)):
            errors.append(f"logger_identity.{key} must be nonempty")
    for key in (
        "real_time_control_task_separate_from_storage_task",
        "bounded_nonblocking_enqueue_design",
    ):
        if logger.get(key) is not True:
            errors.append(f"logger_identity.{key} must be true")

    if manifest.get("fault_edge_logging_enabled") is not True:
        errors.append("fault_edge_logging_enabled must be true")
    if manifest.get("stage_marker_recorded") is not True:
        errors.append("stage_marker_recorded must be true")

    known = {
        item["id"]: item
        for item in registry.get("signals", [])
        if isinstance(item, dict) and _nonempty(item.get("id"))
    }
    allowed_sources = set(snapshot.get("source_kinds", []))
    channels = manifest.get("declared_channels")
    if not isinstance(channels, list) or not channels:
        errors.append("declared_channels must be a nonempty list")
        channels = []

    channel_map: dict[str, dict] = {}
    for index, channel in enumerate(channels):
        if not isinstance(channel, dict):
            errors.append(f"declared channel {index} must be an object")
            continue
        signal_id = channel.get("signal_id")
        if not _nonempty(signal_id):
            errors.append(f"declared channel {index} needs signal_id")
            continue
        if signal_id in channel_map:
            errors.append(f"duplicate declared signal_id: {signal_id}")
            continue
        channel_map[signal_id] = channel

        if signal_id not in known:
            errors.append(f"unknown declared signal_id: {signal_id}")
        if channel.get("enabled") is not True:
            errors.append(f"{signal_id}: required declared channel must be enabled")
        if channel.get("source_kind") not in allowed_sources:
            errors.append(f"{signal_id}: invalid source_kind")
        if not _nonempty(channel.get("source_id")):
            errors.append(f"{signal_id}: source_id must be nonempty")
        if not _positive(channel.get("expected_hz")):
            errors.append(f"{signal_id}: expected_hz must be positive")
        if not _positive(channel.get("max_source_age_us")):
            errors.append(f"{signal_id}: max_source_age_us must be positive")
        if not _nonempty(channel.get("frame_or_sign_convention")):
            errors.append(f"{signal_id}: frame_or_sign_convention must be nonempty")

        kind = known.get(signal_id, {}).get("kind")
        if kind in {"DERIVED", "MEASURED_OR_DERIVED"} and channel.get(
            "source_kind"
        ) == "DERIVED":
            if not _nonempty(channel.get("derivation_method_reference")):
                errors.append(
                    f"{signal_id}: DERIVED source requires derivation_method_reference"
                )

    for signal_id, min_hz in stage.get("required_signals_hz", {}).items():
        channel = channel_map.get(signal_id)
        if channel is None:
            errors.append(f"required stage signal not declared: {signal_id}")
        elif _positive(channel.get("expected_hz")) and float(
            channel["expected_hz"]
        ) < float(min_hz):
            errors.append(
                f"{signal_id}: declared expected_hz below stage minimum {min_hz}"
            )

    files = manifest.get("files")
    if not isinstance(files, dict):
        errors.append("files must be an object")
        files = {}
    file_names = {}
    for key in ("telemetry_csv", "events_jsonl", "metrics_json"):
        value = files.get(key)
        if not _nonempty(value):
            errors.append(f"files.{key} must be nonempty")
        else:
            file_names[key] = value

    telemetry_rows: list[dict] = []
    event_rows: list[dict] = []
    metric_rows: list[dict] = []
    if "telemetry_csv" in file_names:
        telemetry_rows, load_errors = _load_csv(
            base_dir / file_names["telemetry_csv"],
            list(snapshot["record_format"]["telemetry_csv_columns"]),
        )
        errors.extend(load_errors)
    if "events_jsonl" in file_names:
        event_rows, load_errors = _load_jsonl(
            base_dir / file_names["events_jsonl"]
        )
        errors.extend(load_errors)
    if "metrics_json" in file_names:
        metric_rows, load_errors = _load_json_array(
            base_dir / file_names["metrics_json"]
        )
        errors.extend(load_errors)

    allowed_quality = set(snapshot["record_format"]["allowed_quality"])
    by_signal: dict[str, list[tuple[int, int, float, int, str]]] = {}
    record_seqs: list[int] = []
    last_seq: int | None = None
    last_mono: int | None = None
    for row_no, row in enumerate(telemetry_rows, start=2):
        try:
            seq = int(row["record_seq"])
            mono = int(row["mono_us"])
            value = float(row["value"])
            source_age = int(row["source_age_us"])
        except (TypeError, ValueError):
            errors.append(f"telemetry row {row_no}: numeric parse failure")
            continue
        signal_id = str(row["signal_id"])
        quality = str(row["quality"])
        if seq < 0 or mono < 0 or source_age < 0 or not math.isfinite(value):
            errors.append(f"telemetry row {row_no}: invalid numeric value")
            continue
        if last_seq is not None and seq <= last_seq:
            errors.append("record_seq must strictly increase")
        if last_mono is not None and mono < last_mono:
            errors.append("telemetry mono_us must not decrease")
        last_seq, last_mono = seq, mono
        record_seqs.append(seq)

        if signal_id not in channel_map:
            errors.append(
                f"telemetry row {row_no}: signal {signal_id} is not declared"
            )
            continue
        if quality not in allowed_quality:
            errors.append(f"telemetry row {row_no}: invalid quality {quality}")
            continue
        by_signal.setdefault(signal_id, []).append(
            (seq, mono, value, source_age, quality)
        )

    missing_sequence_records = 0
    if record_seqs:
        missing_sequence_records = (
            record_seqs[-1] - record_seqs[0] + 1 - len(record_seqs)
        )
        if missing_sequence_records < 0:
            errors.append("record sequence accounting is invalid")
            missing_sequence_records = 0
    else:
        errors.append("telemetry.csv contains no records")

    summary = manifest.get("session_summary")
    if not isinstance(summary, dict):
        errors.append("session_summary must be an object")
        summary = {}
    reported_drops = summary.get("reported_dropped_records")
    if not isinstance(reported_drops, int) or reported_drops < 0:
        errors.append("reported_dropped_records must be a nonnegative integer")
        reported_drops = 0
    if reported_drops != missing_sequence_records:
        errors.append(
            "reported_dropped_records must equal record-sequence gaps"
        )
    if summary.get("persistent_write_error_count") != 0:
        errors.append("persistent_write_error_count must be zero")
    if summary.get("unclean_shutdown") is not False:
        errors.append("unclean_shutdown must be false")
    expected_records = summary.get("expected_records")
    if not isinstance(expected_records, int) or expected_records <= 0:
        errors.append("expected_records must be a positive integer")
    elif expected_records != len(telemetry_rows) + missing_sequence_records:
        errors.append(
            "expected_records must equal persisted records plus sequence gaps"
        )

    denominator = len(telemetry_rows) + missing_sequence_records
    drop_fraction = (
        missing_sequence_records / denominator if denominator > 0 else 1.0
    )
    max_drop = min(
        float(snapshot["integrity_policy"]["max_overall_record_drop_fraction"]),
        float(stage.get("max_record_drop_fraction", 1.0)),
    )
    if drop_fraction > max_drop:
        errors.append(
            f"record drop fraction {drop_fraction:.6f} exceeds {max_drop:.6f}"
        )

    signal_quality: dict[str, dict] = {}
    gap_multiplier = float(
        snapshot["integrity_policy"]["signal_max_gap_multiplier"]
    )
    for signal_id, min_hz in stage.get("required_signals_hz", {}).items():
        rows = [
            item
            for item in by_signal.get(signal_id, [])
            if item[4] == "OK"
        ]
        if len(rows) < 2:
            errors.append(f"{signal_id}: fewer than two OK samples")
            continue
        times = [item[1] for item in rows]
        span_s = (times[-1] - times[0]) / 1_000_000.0
        if span_s <= 0:
            errors.append(f"{signal_id}: nonpositive OK sample span")
            continue
        achieved_hz = (len(rows) - 1) / span_s
        gaps = [
            (b - a) / 1_000_000.0
            for a, b in zip(times, times[1:])
        ]
        max_gap_s = max(gaps) if gaps else 0.0
        allowed_gap_s = gap_multiplier / float(min_hz)
        channel = channel_map.get(signal_id, {})
        max_source_age_us = int(channel.get("max_source_age_us") or 0)
        max_observed_source_age_us = max(item[3] for item in rows)

        if achieved_hz + 1e-9 < float(min_hz):
            errors.append(
                f"{signal_id}: achieved {achieved_hz:.3f} Hz below {min_hz} Hz"
            )
        if max_gap_s > allowed_gap_s + 1e-9:
            errors.append(
                f"{signal_id}: max OK gap {max_gap_s:.6f}s exceeds "
                f"{allowed_gap_s:.6f}s"
            )
        if max_observed_source_age_us > max_source_age_us:
            errors.append(
                f"{signal_id}: source age exceeds declared maximum"
            )
        signal_quality[signal_id] = {
            "ok_sample_count": len(rows),
            "achieved_hz": round(achieved_hz, 4),
            "max_gap_s": round(max_gap_s, 6),
            "max_observed_source_age_us": max_observed_source_age_us,
            "stage_min_hz": min_hz,
        }

    allowed_event_types = set(snapshot["event_types"])
    event_seqs: list[int] = []
    event_monos: list[int] = []
    parsed_events: list[dict] = []
    for index, event in enumerate(event_rows):
        try:
            seq = int(event.get("event_seq"))
            mono = int(event.get("mono_us"))
            fault_bits = int(event.get("fault_bits"))
        except (TypeError, ValueError):
            errors.append(f"event {index}: numeric parse failure")
            continue
        if seq < 0 or mono < 0 or fault_bits < 0:
            errors.append(f"event {index}: numeric values must be nonnegative")
            continue
        event_type = event.get("event_type")
        if event_type not in allowed_event_types:
            errors.append(f"event {index}: unsupported event_type {event_type}")
        if not _nonempty(event.get("code")):
            errors.append(f"event {index}: code must be nonempty")
        if not isinstance(event.get("details"), (dict, list, str, int, float, bool, type(None))):
            errors.append(f"event {index}: details must be JSON-compatible")
        if event_seqs and seq <= event_seqs[-1]:
            errors.append("event_seq must strictly increase")
        if event_monos and mono < event_monos[-1]:
            errors.append("event mono_us must not decrease")
        event_seqs.append(seq)
        event_monos.append(mono)
        parsed = dict(event)
        parsed["event_seq"] = seq
        parsed["mono_us"] = mono
        parsed["fault_bits"] = fault_bits
        parsed_events.append(parsed)

    starts = [x for x in parsed_events if x.get("event_type") == "SESSION_START"]
    ends = [x for x in parsed_events if x.get("event_type") == "SESSION_END"]
    markers = [x for x in parsed_events if x.get("event_type") == "STAGE_MARKER"]
    logger_errors = [x for x in parsed_events if x.get("event_type") == "LOGGER_ERROR"]
    if len(starts) != 1:
        errors.append("events must contain exactly one SESSION_START")
    if len(ends) != 1:
        errors.append("events must contain exactly one SESSION_END")
    if len(markers) != 1 or markers[0].get("code") != stage_id:
        errors.append("events must contain exactly one matching STAGE_MARKER")
    if logger_errors:
        errors.append("LOGGER_ERROR events prevent telemetry qualification")

    fault_rows = [
        item for item in by_signal.get("control_fault_bits", [])
        if item[4] == "OK"
    ]
    fault_edges = [
        item for item in parsed_events if item.get("event_type") == "FAULT_EDGE"
    ]
    tolerance_us = int(
        round(
            float(snapshot["integrity_policy"]["fault_edge_match_tolerance_ms"])
            * 1000.0
        )
    )
    for previous, current in zip(fault_rows, fault_rows[1:]):
        prev_bits = int(round(previous[2]))
        current_bits = int(round(current[2]))
        if current_bits == prev_bits:
            continue
        mono = current[1]
        if not any(
            abs(edge["mono_us"] - mono) <= tolerance_us
            and int(edge["fault_bits"]) == current_bits
            for edge in fault_edges
        ):
            errors.append(
                "control_fault_bits transition lacks matching FAULT_EDGE event"
            )

    metric_map: dict[str, dict] = {}
    for index, metric in enumerate(metric_rows):
        metric_id = metric.get("metric_id")
        if not _nonempty(metric_id):
            errors.append(f"metric {index}: metric_id must be nonempty")
            continue
        if metric_id in metric_map:
            errors.append(f"duplicate metric_id: {metric_id}")
            continue
        metric_map[metric_id] = metric
        if not _finite(metric.get("value")):
            errors.append(f"{metric_id}: value must be finite")
        if not _nonempty(metric.get("unit")):
            errors.append(f"{metric_id}: unit must be nonempty")
        expected_unit = METRIC_UNITS.get(metric_id)
        if expected_unit is not None and metric.get("unit") != expected_unit:
            errors.append(
                f"{metric_id}: expected unit {expected_unit}, got {metric.get('unit')}"
            )
        start = metric.get("start_mono_us")
        end = metric.get("end_mono_us")
        if not isinstance(start, int) or start < 0:
            errors.append(f"{metric_id}: start_mono_us must be nonnegative integer")
        if not isinstance(end, int) or end < 0:
            errors.append(f"{metric_id}: end_mono_us must be nonnegative integer")
        if isinstance(start, int) and isinstance(end, int) and end < start:
            errors.append(f"{metric_id}: end_mono_us precedes start_mono_us")
        if not _nonempty(metric.get("method_reference")):
            errors.append(f"{metric_id}: method_reference must be nonempty")
        sources = metric.get("source_signal_ids")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{metric_id}: source_signal_ids must be nonempty list")
        else:
            unknown = [item for item in sources if item not in known]
            if unknown:
                errors.append(
                    f"{metric_id}: unknown source signals {sorted(set(unknown))}"
                )

    for metric_id in stage.get("required_metrics", []):
        if metric_id not in metric_map:
            errors.append(f"required stage metric missing: {metric_id}")

    qualified = not errors
    report = {
        "schema_version": 1,
        "authority": "x1_telemetry_evidence",
        "qualified": qualified,
        "errors": errors,
        "issue": 49,
        "session_id": session_id,
        "board_id": board_id,
        "configuration_id": configuration_id,
        "commissioning_stage_id": stage_id,
        "commissioning_stage_index": stage.get("stage_index"),
        "power_architecture_fingerprint_sha256": power_fp,
        "pre_lifecycle_health_fingerprint_sha256": health_fp,
        "logger_identity": logger,
        "persisted_record_count": len(telemetry_rows),
        "record_sequence_gap_count": missing_sequence_records,
        "record_drop_fraction": round(drop_fraction, 8),
        "event_count": len(parsed_events),
        "metric_ids": sorted(metric_map),
        "required_signal_quality": signal_quality,
        "data_quality_qualified": qualified,
        "controller_configuration_authority": False,
        "battery_configuration_authority": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": (
            "A passing report qualifies only telemetry evidence quality for the "
            "declared Issue #45 commissioning stage and exact configuration. It "
            "does not authorize controller/battery settings or any operation."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--power-architecture", type=Path, required=True)
    parser.add_argument("--pre-health-state", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = qualify(
        manifest,
        args.manifest.parent,
        json.loads(args.power_architecture.read_text(encoding="utf-8")),
        json.loads(args.pre_health_state.read_text(encoding="utf-8")),
        snapshot=json.loads(args.snapshot.read_text(encoding="utf-8")),
        registry=json.loads(args.registry.read_text(encoding="utf-8")),
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
