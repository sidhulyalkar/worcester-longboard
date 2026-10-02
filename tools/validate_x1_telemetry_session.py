#!/usr/bin/env python3
"""Validate one Worcester X1 synchronized telemetry session.

A passing session proves file/schema/timebase/lineage integrity only.
Commissioning-evidence readiness additionally requires qualified sources and
stage-specific synchronization/derived-input coverage.
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
REGISTRY_PATH = ROOT / "hardware/x1_telemetry_signal_registry.json"
SNAPSHOT_PATH = ROOT / "hardware/rev_c_telemetry_snapshot_2026-10-02.json"

BOOL_TRUE = {"true", "1", "yes"}
BOOL_FALSE = {"false", "0", "no"}


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _file_sha256(path: Path) -> str:
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


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _positive(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0
    )


def _nonnegative(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) >= 0
    )


def _parse_time(errors: list[str], label: str, value: Any) -> datetime | None:
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


def _safe_child(base: Path, relative: Any, label: str, errors: list[str]) -> Path | None:
    if not _nonempty(relative):
        errors.append(f"{label} must be a nonempty relative path")
        return None
    candidate = (base / relative).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError:
        errors.append(f"{label} escapes the telemetry session directory")
        return None
    return candidate


def _parse_value(raw: str, spec: dict, label: str, errors: list[str]) -> Any:
    kind = spec["type"]
    if kind == "float":
        try:
            value = float(raw)
        except ValueError:
            errors.append(f"{label} must be numeric")
            return None
        if not math.isfinite(value):
            errors.append(f"{label} must be finite")
            return None
        return value
    if kind == "integer":
        try:
            value = int(raw)
        except ValueError:
            errors.append(f"{label} must be an integer")
            return None
        return value
    if kind == "boolean":
        token = raw.strip().lower()
        if token in BOOL_TRUE:
            return True
        if token in BOOL_FALSE:
            return False
        errors.append(f"{label} must be boolean")
        return None
    if kind == "string":
        if not raw.strip():
            errors.append(f"{label} must be nonempty")
            return None
        return raw.strip()
    errors.append(f"{label} has unsupported registry type {kind!r}")
    return None


def _validate_power(errors: list[str], power: dict) -> None:
    if power.get("authority") != "x1_power_architecture":
        errors.append("power architecture authority has wrong type")
    if power.get("qualified") is not True:
        errors.append("power architecture must be qualified")
    if not _valid_fp(power):
        errors.append("power architecture fingerprint is invalid")


def _validate_health(
    errors: list[str],
    health: dict,
    board_id: str,
    configuration_id: str,
) -> None:
    if health.get("authority") != "x1_lifecycle_health_state":
        errors.append("pre-health authority has wrong type")
    if health.get("valid") is not True:
        errors.append("pre-health must be valid")
    if health.get("health_state") != "READY_FOR_ALLOWED_ACTIVITY":
        errors.append("pre-health must be READY_FOR_ALLOWED_ACTIVITY")
    if health.get("ready_for_allowed_activity") is not True:
        errors.append("pre-health ready_for_allowed_activity must be true")
    if health.get("board_id") != board_id:
        errors.append("pre-health board_id mismatch")
    if health.get("current_configuration_id") != configuration_id:
        errors.append("pre-health configuration_id mismatch")
    for key in (
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if health.get(key) is not False:
            errors.append(f"pre-health {key} must be false")
    if not _valid_fp(health):
        errors.append("pre-health fingerprint is invalid")


def _unique_by(
    errors: list[str],
    values: Any,
    key: str,
    label: str,
) -> dict[str, dict]:
    if not isinstance(values, list):
        errors.append(f"{label} must be a list")
        return {}
    out: dict[str, dict] = {}
    for index, item in enumerate(values):
        if not isinstance(item, dict):
            errors.append(f"{label}[{index}] must be an object")
            continue
        item_id = item.get(key)
        if not _nonempty(item_id):
            errors.append(f"{label}[{index}].{key} must be nonempty")
            continue
        if item_id in out:
            errors.append(f"duplicate {label} {key}: {item_id}")
            continue
        out[item_id] = item
    return out


def _load_csv_stream(
    *,
    session_dir: Path,
    stream: dict,
    schema: dict,
    clock: dict | None,
    source: dict | None,
    policy: dict,
    errors: list[str],
    readiness_blockers: list[str],
    max_sync_uncertainty_s: float | None,
) -> tuple[dict, list[dict]]:
    stream_id = stream.get("stream_id", "<unknown>")
    path = _safe_child(
        session_dir,
        stream.get("file_path"),
        f"{stream_id}.file_path",
        errors,
    )
    expected_hash = stream.get("sha256")
    if not _nonempty(expected_hash):
        errors.append(f"{stream_id}: sha256 must be nonempty")

    if clock is None:
        errors.append(f"{stream_id}: unknown clock_id")
    if source is None:
        errors.append(f"{stream_id}: unknown source_id")

    if clock is not None:
        if clock.get("source_id") != stream.get("source_id"):
            errors.append(f"{stream_id}: clock/source provenance mismatch")
        if clock.get("timestamp_unit") != "s":
            errors.append(f"{stream_id}: clock timestamp_unit must be 's'")
        if not _nonempty(clock.get("synchronization_method")):
            errors.append(f"{stream_id}: synchronization_method must be nonempty")
        uncertainty = clock.get("synchronization_uncertainty_s")
        if not _nonnegative(uncertainty):
            errors.append(
                f"{stream_id}: synchronization_uncertainty_s must be finite and nonnegative"
            )
        elif (
            max_sync_uncertainty_s is not None
            and float(uncertainty) > max_sync_uncertainty_s
        ):
            readiness_blockers.append(
                f"{stream_id}: synchronization uncertainty {float(uncertainty):.6f}s "
                f"exceeds stage limit {max_sync_uncertainty_s:.6f}s"
            )

    if source is not None:
        status = source.get("qualification_status")
        if status not in {"DECLARED", "QUALIFIED"}:
            errors.append(f"{stream_id}: invalid source qualification_status")
        if status == "QUALIFIED":
            if not _nonempty(source.get("calibration_evidence_ref")):
                errors.append(
                    f"{stream_id}: QUALIFIED source requires calibration_evidence_ref"
                )
        else:
            readiness_blockers.append(
                f"{stream_id}: source is not QUALIFIED for commissioning evidence"
            )

    if not _positive(stream.get("nominal_rate_hz")):
        errors.append(f"{stream_id}: nominal_rate_hz must be positive")
    if not _positive(stream.get("max_gap_s")):
        errors.append(f"{stream_id}: max_gap_s must be positive")
    dropped_declared = stream.get("declared_dropped_samples")
    if not isinstance(dropped_declared, int) or isinstance(dropped_declared, bool) or dropped_declared < 0:
        errors.append(
            f"{stream_id}: declared_dropped_samples must be a nonnegative integer"
        )
        dropped_declared = 0

    columns = schema.get("required_columns", [])
    expected_columns = [item["name"] for item in columns]
    specs = {item["name"]: item for item in columns}
    rows: list[dict] = []

    if path is None or not path.is_file():
        errors.append(f"{stream_id}: telemetry file is missing")
        return (
            {
                "stream_id": stream_id,
                "row_count": 0,
                "start_session_time_s": None,
                "end_session_time_s": None,
            },
            rows,
        )

    actual_hash = _file_sha256(path)
    if _nonempty(expected_hash) and actual_hash != expected_hash:
        errors.append(f"{stream_id}: file sha256 mismatch")

    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != expected_columns:
                errors.append(
                    f"{stream_id}: CSV header does not exactly match canonical schema"
                )
                return (
                    {
                        "stream_id": stream_id,
                        "row_count": 0,
                        "file_sha256": actual_hash,
                        "start_session_time_s": None,
                        "end_session_time_s": None,
                    },
                    rows,
                )
            for line_no, raw in enumerate(reader, start=2):
                parsed: dict[str, Any] = {}
                for name in expected_columns:
                    parsed[name] = _parse_value(
                        raw.get(name, ""),
                        specs[name],
                        f"{stream_id}:{line_no}:{name}",
                        errors,
                    )
                rows.append(parsed)
    except OSError as exc:
        errors.append(f"{stream_id}: could not read file: {exc}")

    minimum_samples = int(policy["minimum_samples"])
    if len(rows) < minimum_samples:
        errors.append(
            f"{stream_id}: requires at least {minimum_samples} samples, found {len(rows)}"
        )

    seqs = [row.get("seq") for row in rows if isinstance(row.get("seq"), int)]
    source_times = [
        row.get("source_time_s")
        for row in rows
        if isinstance(row.get("source_time_s"), float)
    ]
    session_times = [
        row.get("session_time_s")
        for row in rows
        if isinstance(row.get("session_time_s"), float)
    ]

    missing_seq = 0
    max_gap_observed = 0.0
    if len(seqs) == len(rows):
        for prev, cur in zip(seqs, seqs[1:]):
            if cur <= prev:
                errors.append(f"{stream_id}: sequence numbers must be strictly increasing")
            elif cur > prev + 1:
                missing_seq += cur - prev - 1
    if missing_seq != dropped_declared:
        errors.append(
            f"{stream_id}: declared_dropped_samples={dropped_declared} but sequence gaps imply {missing_seq}"
        )
    denom = len(rows) + missing_seq
    drop_fraction = (missing_seq / denom) if denom else 0.0
    if drop_fraction > float(policy["max_drop_fraction"]):
        errors.append(
            f"{stream_id}: drop fraction {drop_fraction:.6f} exceeds "
            f"{float(policy['max_drop_fraction']):.6f}"
        )

    for label, values in (
        ("source_time_s", source_times),
        ("session_time_s", session_times),
    ):
        if len(values) == len(rows):
            for prev, cur in zip(values, values[1:]):
                if cur <= prev:
                    errors.append(f"{stream_id}: {label} must be strictly increasing")

    if len(session_times) == len(rows):
        gaps = [
            cur - prev for prev, cur in zip(session_times, session_times[1:])
        ]
        if gaps:
            max_gap_observed = max(gaps)
            if (
                _positive(stream.get("max_gap_s"))
                and max_gap_observed > float(stream["max_gap_s"]) + 1e-12
            ):
                errors.append(
                    f"{stream_id}: max observed gap {max_gap_observed:.6f}s "
                    f"exceeds declared max_gap_s {float(stream['max_gap_s']):.6f}s"
                )

    summary = {
        "stream_id": stream_id,
        "schema_id": stream.get("schema_id"),
        "file_sha256": actual_hash,
        "row_count": len(rows),
        "declared_dropped_samples": dropped_declared,
        "sequence_gap_samples": missing_seq,
        "drop_fraction": round(drop_fraction, 8),
        "max_observed_gap_s": round(max_gap_observed, 8),
        "start_session_time_s": (
            session_times[0] if session_times and len(session_times) == len(rows) else None
        ),
        "end_session_time_s": (
            session_times[-1] if session_times and len(session_times) == len(rows) else None
        ),
        "source_id": stream.get("source_id"),
        "clock_id": stream.get("clock_id"),
    }
    return summary, rows


def _load_events(
    *,
    session_dir: Path,
    event_log: dict,
    clocks: dict[str, dict],
    sources: dict[str, dict],
    stage_required: bool,
    errors: list[str],
    readiness_blockers: list[str],
    max_sync_uncertainty_s: float | None,
    policy: dict,
) -> tuple[dict, list[dict]]:
    path = _safe_child(
        session_dir,
        event_log.get("file_path"),
        "event_log.file_path",
        errors,
    )
    expected_hash = event_log.get("sha256")
    if not _nonempty(expected_hash):
        errors.append("event_log.sha256 must be nonempty")

    clock = clocks.get(event_log.get("clock_id"))
    source = sources.get(event_log.get("source_id"))
    if clock is None:
        errors.append("event_log references unknown clock_id")
    if source is None:
        errors.append("event_log references unknown source_id")
    if clock is not None:
        if clock.get("source_id") != event_log.get("source_id"):
            errors.append("event_log clock/source provenance mismatch")
        if clock.get("timestamp_unit") != "s":
            errors.append("event_log clock timestamp_unit must be 's'")
        if not _nonempty(clock.get("synchronization_method")):
            errors.append("event_log synchronization_method must be nonempty")
        uncertainty = clock.get("synchronization_uncertainty_s")
        if not _nonnegative(uncertainty):
            errors.append(
                "event_log synchronization_uncertainty_s must be finite and nonnegative"
            )
        elif (
            max_sync_uncertainty_s is not None
            and float(uncertainty) > max_sync_uncertainty_s
        ):
            readiness_blockers.append(
                "event_log synchronization uncertainty exceeds stage limit"
            )
    if source is not None:
        status = source.get("qualification_status")
        if status not in {"DECLARED", "QUALIFIED"}:
            errors.append("event_log source has invalid qualification_status")
        elif status != "QUALIFIED":
            readiness_blockers.append(
                "event_log source is not QUALIFIED for commissioning evidence"
            )
        elif not _nonempty(source.get("calibration_evidence_ref")):
            errors.append(
                "event_log QUALIFIED source requires calibration_evidence_ref"
            )

    events: list[dict] = []
    actual_hash = None
    if path is None or not path.is_file():
        if stage_required:
            errors.append("required event log file is missing")
        return {"event_count": 0}, events

    actual_hash = _file_sha256(path)
    if _nonempty(expected_hash) and actual_hash != expected_hash:
        errors.append("event_log file sha256 mismatch")

    required_fields = policy["required_fields"]
    try:
        with path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    errors.append(f"event_log:{line_no}: invalid JSON")
                    continue
                if not isinstance(event, dict):
                    errors.append(f"event_log:{line_no}: event must be an object")
                    continue
                for key in required_fields:
                    if key not in event:
                        errors.append(f"event_log:{line_no}: missing {key}")
                seq = event.get("seq")
                t = event.get("session_time_s")
                if not isinstance(seq, int) or isinstance(seq, bool):
                    errors.append(f"event_log:{line_no}: seq must be integer")
                if not _nonnegative(t):
                    errors.append(
                        f"event_log:{line_no}: session_time_s must be finite and nonnegative"
                    )
                if not _nonempty(event.get("event_type")):
                    errors.append(f"event_log:{line_no}: event_type must be nonempty")
                if not _nonempty(event.get("source_id")):
                    errors.append(f"event_log:{line_no}: source_id must be nonempty")
                elif event.get("source_id") not in sources:
                    errors.append(f"event_log:{line_no}: source_id is undeclared")
                if not isinstance(event.get("payload"), dict):
                    errors.append(f"event_log:{line_no}: payload must be an object")
                events.append(event)
    except OSError as exc:
        errors.append(f"event_log could not be read: {exc}")

    seqs = [e.get("seq") for e in events if isinstance(e.get("seq"), int)]
    times = [
        float(e["session_time_s"])
        for e in events
        if _nonnegative(e.get("session_time_s"))
    ]
    if len(seqs) == len(events):
        for prev, cur in zip(seqs, seqs[1:]):
            if cur != prev + 1:
                errors.append("event_log sequence must be contiguous and strictly increasing")
    if len(times) == len(events):
        for prev, cur in zip(times, times[1:]):
            if cur < prev:
                errors.append("event_log session_time_s must be non-decreasing")

    types = [e.get("event_type") for e in events]
    for required in policy["required_event_types"]:
        if required not in types:
            errors.append(f"event_log missing required event type: {required}")

    return (
        {
            "file_sha256": actual_hash,
            "event_count": len(events),
            "start_session_time_s": times[0] if times else None,
            "end_session_time_s": times[-1] if times else None,
            "event_types": sorted({x for x in types if isinstance(x, str)}),
        },
        events,
    )


def validate_session(
    manifest_path: Path,
    *,
    power_architecture: dict,
    pre_health: dict,
    registry: dict | None = None,
    snapshot: dict | None = None,
) -> tuple[dict, dict]:
    registry = registry or json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    snapshot = snapshot or json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    session_dir = manifest_path.resolve().parent
    errors: list[str] = []
    readiness_blockers: list[str] = []

    if manifest.get("schema_version") != 1:
        errors.append("manifest schema_version must be 1")
    if manifest.get("scope") != "x1_telemetry_session":
        errors.append("wrong telemetry session scope")
    for key in ("session_id", "board_id", "configuration_id", "commissioning_stage_id"):
        if not _nonempty(manifest.get(key)):
            errors.append(f"{key} must be nonempty")

    stage_id = manifest.get("commissioning_stage_id")
    stage = snapshot.get("stage_requirements", {}).get(stage_id)
    if stage is None:
        errors.append(f"unknown commissioning_stage_id: {stage_id!r}")
        stage = {
            "required_streams": [],
            "telemetry_required": False,
            "required_measurements": [],
        }

    started = _parse_time(errors, "started_at_utc", manifest.get("started_at_utc"))
    completed = _parse_time(
        errors, "completed_at_utc", manifest.get("completed_at_utc")
    )
    if started is not None and completed is not None and completed <= started:
        errors.append("completed_at_utc must be after started_at_utc")

    for key in (
        "telemetry_validity_authority_only",
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        expected = True if key == "telemetry_validity_authority_only" else False
        if manifest.get(key) is not expected:
            errors.append(f"{key} must be {str(expected).lower()}")

    logger = manifest.get("logger_contract")
    if not isinstance(logger, dict):
        errors.append("logger_contract must be an object")
        logger = {}
    if logger.get("realtime_control_dependency") is not False:
        errors.append("logger cannot be a realtime control dependency")
    if logger.get("control_loop_may_block_on_logger") is not False:
        errors.append("control loop may not block on logger")
    if logger.get("logging_failure_behavior") != (
        "DROP_OR_STOP_LOGGING_WITHOUT_PRESERVING_PROPULSION"
    ):
        errors.append("logging_failure_behavior violates fail-safe boundary")
    if logger.get("buffer_overflow_policy") != "DROP_WITH_ACCOUNTING":
        errors.append("buffer_overflow_policy must be DROP_WITH_ACCOUNTING")

    _validate_power(errors, power_architecture)
    board_id = manifest.get("board_id")
    config_id = manifest.get("configuration_id")
    _validate_health(errors, pre_health, board_id, config_id)

    power_fp = power_architecture.get("authority_fingerprint_sha256")
    health_fp = pre_health.get("authority_fingerprint_sha256")
    if manifest.get("power_architecture_fingerprint_sha256") != power_fp:
        errors.append("manifest power architecture fingerprint mismatch")
    if manifest.get("pre_lifecycle_health_fingerprint_sha256") != health_fp:
        errors.append("manifest pre-health fingerprint mismatch")

    health_time = _parse_time(
        errors,
        "pre-health latest_event_timestamp_utc",
        pre_health.get("latest_event_timestamp_utc"),
    )
    if health_time is not None and started is not None and health_time > started:
        errors.append("pre-health event cannot occur after telemetry session start")

    clocks = _unique_by(errors, manifest.get("clocks"), "clock_id", "clocks")
    sources = _unique_by(errors, manifest.get("sources"), "source_id", "sources")
    streams = _unique_by(errors, manifest.get("streams"), "stream_id", "streams")

    required_streams = list(stage.get("required_streams", []))
    required_periodic = [x for x in required_streams if x != "events"]
    for stream_id in required_periodic:
        if stream_id not in streams:
            errors.append(f"required telemetry stream missing: {stream_id}")

    max_sync = stage.get("max_sync_uncertainty_s")
    stream_summaries: dict[str, dict] = {}
    parsed_streams: dict[str, list[dict]] = {}
    policy = snapshot["periodic_stream_policy"]

    for stream_id, stream in streams.items():
        schema_id = stream.get("schema_id")
        if stream_id != schema_id:
            errors.append(
                f"{stream_id}: stream_id and schema_id must match canonical stream"
            )
        schema = registry.get("streams", {}).get(schema_id)
        if schema is None:
            errors.append(f"{stream_id}: unknown schema_id")
            continue
        summary, rows = _load_csv_stream(
            session_dir=session_dir,
            stream=stream,
            schema=schema,
            clock=clocks.get(stream.get("clock_id")),
            source=sources.get(stream.get("source_id")),
            policy=policy,
            errors=errors,
            readiness_blockers=readiness_blockers,
            max_sync_uncertainty_s=(
                float(max_sync) if _positive(max_sync) else None
            ),
        )
        stream_summaries[stream_id] = summary
        parsed_streams[stream_id] = rows

    event_required = "events" in required_streams
    event_summary, events = _load_events(
        session_dir=session_dir,
        event_log=manifest.get("event_log", {}),
        clocks=clocks,
        sources=sources,
        stage_required=event_required,
        errors=errors,
        readiness_blockers=readiness_blockers,
        max_sync_uncertainty_s=(
            float(max_sync) if _positive(max_sync) else None
        ),
        policy=snapshot["event_stream_policy"],
    )

    if required_periodic:
        bounds = []
        for stream_id in required_periodic:
            summary = stream_summaries.get(stream_id)
            if summary is None:
                continue
            start = summary.get("start_session_time_s")
            end = summary.get("end_session_time_s")
            if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                bounds.append((stream_id, float(start), float(end)))
        if len(bounds) == len(required_periodic):
            overlap_start = max(x[1] for x in bounds)
            overlap_end = min(x[2] for x in bounds)
            overlap = max(0.0, overlap_end - overlap_start)
            shortest = min(max(0.0, x[2] - x[1]) for x in bounds)
            fraction = (overlap / shortest) if shortest > 0 else 0.0
            if fraction < float(policy["minimum_common_overlap_fraction"]):
                errors.append(
                    f"required periodic-stream common overlap fraction {fraction:.6f} "
                    f"is below {float(policy['minimum_common_overlap_fraction']):.6f}"
                )
        else:
            overlap_start = overlap_end = None
            fraction = 0.0
    else:
        overlap_start = overlap_end = None
        fraction = 1.0

    event_types = set(event_summary.get("event_types", []))
    if stage_id in {"RIDER_FREE_CONTROLLED_GROUND", "RIDER_ONLY_VERY_LOW_SPEED"}:
        if not ({"DEADMAN_RELEASE", "REMOTE_TIMEOUT"} & event_types):
            readiness_blockers.append(
                "remote-release decay cannot be derived without DEADMAN_RELEASE or REMOTE_TIMEOUT"
            )
    if stage_id == "RIDER_ONLY_VERY_LOW_SPEED":
        if not ({"MECHANICAL_BRAKE_MARKER", "OPERATOR_STOP"} & event_types):
            readiness_blockers.append(
                "stopping distance cannot be derived without a brake/stop marker"
            )

    valid = not errors
    commissioning_ready = (
        valid
        and stage.get("telemetry_required") is True
        and not readiness_blockers
    )

    report = {
        "schema_version": 1,
        "authority": "x1_telemetry_session_evidence",
        "valid": valid,
        "commissioning_evidence_ready": commissioning_ready,
        "errors": errors,
        "readiness_blockers": readiness_blockers,
        "session_id": manifest.get("session_id"),
        "board_id": board_id,
        "configuration_id": config_id,
        "commissioning_stage_id": stage_id,
        "power_architecture_fingerprint_sha256": power_fp,
        "pre_lifecycle_health_fingerprint_sha256": health_fp,
        "stream_summaries": stream_summaries,
        "event_summary": event_summary,
        "common_overlap": {
            "start_session_time_s": overlap_start,
            "end_session_time_s": overlap_end,
            "fraction_of_shortest_required_stream": round(fraction, 8),
        },
        "required_measurements": list(stage.get("required_measurements", [])),
        "telemetry_required_for_stage": stage.get("telemetry_required") is True,
        "sensor_calibration_implied": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": (
            "A valid telemetry session proves only declared file, schema, timebase, "
            "hash and lineage integrity. commissioning_evidence_ready additionally "
            "requires qualified sources and stage synchronization/derived-input "
            "coverage; neither state authorizes vehicle operation."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    parsed = {
        "manifest": manifest,
        "streams": parsed_streams,
        "events": events,
        "registry": registry,
        "snapshot": snapshot,
        "report": report,
    }
    return report, parsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--power-architecture", type=Path, required=True)
    parser.add_argument("--pre-health-state", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT_PATH)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report, _ = validate_session(
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
