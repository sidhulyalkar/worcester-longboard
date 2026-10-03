#!/usr/bin/env python3
"""Validate a sealed Worcester X1 telemetry session.

Validation proves file/hash/schema/chronology/provenance/synchronization/coverage
integrity only. It does not prove physical calibration, vehicle safety, or any
operating authority.
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
SNAPSHOT = ROOT / "hardware/rev_c_telemetry_reference_snapshot_2026-10-02.json"
SIGNALS = ROOT / "hardware/x1_telemetry_signal_registry_2026-10-02.json"
EVENT_SCHEMA = ROOT / "hardware/x1_telemetry_event_schema.json"

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


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _positive(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0
    )


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _parse_utc(errors: list[str], label: str, value: Any) -> datetime | None:
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


def _validate_power_architecture(errors: list[str], data: dict) -> None:
    if data.get("authority") != "x1_power_architecture":
        errors.append("power architecture authority must be x1_power_architecture")
    if data.get("qualified") is not True:
        errors.append("power architecture must be qualified")
    if not _valid_fp(data):
        errors.append("power architecture fingerprint is invalid")


def _sync_contract(
    errors: list[str],
    label: str,
    item: dict,
) -> tuple[float, float, float] | None:
    unit = item.get("timestamp_unit")
    if unit not in TIME_SCALE:
        errors.append(f"{label}.timestamp_unit must be one of {sorted(TIME_SCALE)}")
        return None

    if not _nonempty(item.get("clock_id")):
        errors.append(f"{label}.clock_id must be nonempty")
    if not _nonempty(item.get("source_device_id")):
        errors.append(f"{label}.source_device_id must be nonempty")

    sync = item.get("sync_model")
    if not isinstance(sync, dict):
        errors.append(f"{label}.sync_model must be an object")
        return None
    if not _nonempty(sync.get("method")):
        errors.append(f"{label}.sync_model.method must be nonempty")
    if not _nonempty(sync.get("evidence_ref")):
        errors.append(f"{label}.sync_model.evidence_ref must be nonempty")

    scale = sync.get("scale")
    offset = sync.get("offset_s")
    uncertainty = sync.get("uncertainty_ms")
    if not _positive(scale):
        errors.append(f"{label}.sync_model.scale must be positive")
        return None
    if not _finite(offset):
        errors.append(f"{label}.sync_model.offset_s must be finite")
        return None
    if not (
        isinstance(uncertainty, (int, float))
        and not isinstance(uncertainty, bool)
        and math.isfinite(float(uncertainty))
        and float(uncertainty) >= 0
    ):
        errors.append(f"{label}.sync_model.uncertainty_ms must be nonnegative")
        return None
    return TIME_SCALE[unit] * float(scale), float(offset), float(uncertainty)


def _parse_value(value: str, value_type: str) -> bool:
    try:
        if value_type == "float":
            return math.isfinite(float(value))
        if value_type == "int":
            int(value)
            return True
        if value_type == "uint32":
            parsed = int(value)
            return 0 <= parsed <= 0xFFFFFFFF
        if value_type == "bool":
            return value.strip().lower() in {"0", "1", "true", "false"}
    except (TypeError, ValueError):
        return False
    return False


def _declared_drop_ranges(
    errors: list[str],
    label: str,
    ranges: Any,
) -> set[tuple[int, int]]:
    if not isinstance(ranges, list):
        errors.append(f"{label}.dropped_sequence_ranges must be a list")
        return set()
    result: set[tuple[int, int]] = set()
    for index, item in enumerate(ranges):
        if not isinstance(item, dict):
            errors.append(f"{label}.dropped_sequence_ranges[{index}] must be an object")
            continue
        start = item.get("start_seq")
        end = item.get("end_seq")
        reason = item.get("reason")
        if not (
            isinstance(start, int)
            and not isinstance(start, bool)
            and isinstance(end, int)
            and not isinstance(end, bool)
            and 0 <= start <= end
        ):
            errors.append(f"{label}: invalid dropped sequence range")
            continue
        if not _nonempty(reason):
            errors.append(f"{label}: dropped sequence range requires reason")
        pair = (start, end)
        if pair in result:
            errors.append(f"{label}: duplicate dropped sequence range {pair}")
        result.add(pair)
    return result


def _read_stream(
    errors: list[str],
    base_dir: Path,
    stream: dict,
    registry: dict[str, dict],
) -> dict:
    stream_id = stream.get("stream_id", "<stream>")
    label = f"stream {stream_id}"
    path = base_dir / str(stream.get("file", ""))

    summary = {
        "stream_id": stream_id,
        "row_count": 0,
        "session_start_s": None,
        "session_end_s": None,
        "max_observed_gap_s": None,
        "signal_ids": [],
    }

    if stream.get("format") != "csv_wide_v1":
        errors.append(f"{label}.format must be csv_wide_v1")
    if not path.is_file():
        errors.append(f"{label}: missing file {path}")
        return summary
    if not _nonempty(stream.get("file_sha256")):
        errors.append(f"{label}.file_sha256 must be nonempty")
    elif _sha256(path) != stream.get("file_sha256"):
        errors.append(f"{label}: file SHA-256 mismatch")

    sync = _sync_contract(errors, label, stream)
    if sync is None:
        factor, offset, _uncertainty = 1.0, 0.0, 0.0
    else:
        factor, offset, _uncertainty = sync

    nominal_rate = stream.get("nominal_rate_hz")
    max_gap = stream.get("max_gap_s")
    if not _positive(nominal_rate):
        errors.append(f"{label}.nominal_rate_hz must be positive")
    if not _positive(max_gap):
        errors.append(f"{label}.max_gap_s must be positive")
        max_gap = math.inf

    seq_col = stream.get("sequence_column")
    ts_col = stream.get("timestamp_column")
    if not _nonempty(seq_col):
        errors.append(f"{label}.sequence_column must be nonempty")
    if not _nonempty(ts_col):
        errors.append(f"{label}.timestamp_column must be nonempty")

    declared_signals = stream.get("signals")
    if not isinstance(declared_signals, list) or not declared_signals:
        errors.append(f"{label}.signals must be a nonempty list")
        declared_signals = []

    signal_columns: dict[str, tuple[str, str]] = {}
    column_set: set[str] = set()
    for index, decl in enumerate(declared_signals):
        if not isinstance(decl, dict):
            errors.append(f"{label}.signals[{index}] must be an object")
            continue
        signal_id = decl.get("signal_id")
        column = decl.get("column")
        if signal_id not in registry:
            errors.append(f"{label}: unknown signal_id {signal_id!r}")
            continue
        definition = registry[signal_id]
        if definition.get("family") != stream.get("family"):
            errors.append(
                f"{label}/{signal_id}: family does not match signal registry"
            )
        if not _nonempty(column):
            errors.append(f"{label}/{signal_id}: column must be nonempty")
            continue
        if column in column_set:
            errors.append(f"{label}: duplicate signal column {column}")
        column_set.add(column)
        if not _nonempty(decl.get("source_id")):
            errors.append(f"{label}/{signal_id}: source_id must be nonempty")

        kind = str(definition.get("kind", ""))
        if kind.startswith("derived") and not _nonempty(decl.get("derivation_id")):
            errors.append(f"{label}/{signal_id}: derived signal requires derivation_id")
        if kind == "calibrated_or_derived_motion":
            if not (
                _nonempty(decl.get("calibration_id"))
                or _nonempty(decl.get("derivation_id"))
            ):
                errors.append(
                    f"{label}/{signal_id}: requires calibration_id or derivation_id"
                )
        signal_columns[column] = (signal_id, definition["value_type"])

    declared_drops = _declared_drop_ranges(
        errors, label, stream.get("dropped_sequence_ranges")
    )
    actual_drops: set[tuple[int, int]] = set()

    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                errors.append(f"{label}: missing CSV header")
                return summary
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                errors.append(f"{label}: duplicate CSV header columns")

            required_columns = {seq_col, ts_col, *signal_columns.keys()}
            missing = sorted(required_columns - set(reader.fieldnames))
            if missing:
                errors.append(f"{label}: missing CSV columns {missing}")
            extra = sorted(set(reader.fieldnames) - required_columns)
            if extra:
                errors.append(f"{label}: undeclared CSV columns {extra}")

            prev_seq: int | None = None
            prev_raw: float | None = None
            prev_session: float | None = None
            first_session: float | None = None
            max_observed_gap = 0.0
            row_count = 0

            for line_no, row in enumerate(reader, start=2):
                row_count += 1
                try:
                    seq = int(str(row.get(seq_col, "")).strip())
                except ValueError:
                    errors.append(f"{label}:{line_no}: invalid sequence")
                    continue
                if seq < 0:
                    errors.append(f"{label}:{line_no}: sequence must be nonnegative")
                if prev_seq is not None:
                    if seq <= prev_seq:
                        errors.append(f"{label}:{line_no}: sequence not strictly increasing")
                    elif seq > prev_seq + 1:
                        actual_drops.add((prev_seq + 1, seq - 1))

                try:
                    raw_ts = float(str(row.get(ts_col, "")).strip())
                except ValueError:
                    errors.append(f"{label}:{line_no}: invalid timestamp")
                    prev_seq = seq
                    continue
                if not math.isfinite(raw_ts):
                    errors.append(f"{label}:{line_no}: timestamp must be finite")
                if prev_raw is not None and raw_ts <= prev_raw:
                    errors.append(f"{label}:{line_no}: timestamp not strictly increasing")

                session_t = raw_ts * factor + offset
                if prev_session is not None:
                    gap = session_t - prev_session
                    if gap <= 0:
                        errors.append(f"{label}:{line_no}: synchronized time not increasing")
                    max_observed_gap = max(max_observed_gap, gap)
                    if gap > float(max_gap):
                        errors.append(
                            f"{label}:{line_no}: synchronized gap {gap:.6g}s "
                            f"exceeds declared max {float(max_gap):.6g}s"
                        )

                for column, (signal_id, value_type) in signal_columns.items():
                    if not _parse_value(str(row.get(column, "")).strip(), value_type):
                        errors.append(
                            f"{label}:{line_no}: invalid {value_type} value for {signal_id}"
                        )

                if first_session is None:
                    first_session = session_t
                prev_session = session_t
                prev_raw = raw_ts
                prev_seq = seq

    except OSError as exc:
        errors.append(f"{label}: {exc}")
        return summary

    undeclared = sorted(actual_drops - declared_drops)
    stale_declared = sorted(declared_drops - actual_drops)
    if undeclared:
        errors.append(f"{label}: undeclared sequence gaps {undeclared}")
    if stale_declared:
        errors.append(f"{label}: declared sequence gaps not observed {stale_declared}")

    summary.update(
        {
            "row_count": row_count,
            "session_start_s": first_session,
            "session_end_s": prev_session,
            "max_observed_gap_s": round(max_observed_gap, 9) if row_count else None,
            "signal_ids": sorted(
                signal_id for signal_id, _value_type in signal_columns.values()
            ),
            "declared_drop_ranges": sorted([list(x) for x in declared_drops]),
        }
    )
    return summary


def _read_events(
    errors: list[str],
    base_dir: Path,
    event: dict,
    allowed_types: set[str],
) -> dict:
    path = base_dir / str(event.get("file", ""))
    label = "event_log"
    summary = {
        "row_count": 0,
        "session_start_s": None,
        "session_end_s": None,
        "observed_event_types": [],
    }

    if event.get("format") != "jsonl_v1":
        errors.append("event_log.format must be jsonl_v1")
    if event.get("sequence_gaps_allowed") is not False:
        errors.append("event_log.sequence_gaps_allowed must be false")
    if not path.is_file():
        errors.append(f"event_log: missing file {path}")
        return summary
    if not _nonempty(event.get("file_sha256")):
        errors.append("event_log.file_sha256 must be nonempty")
    elif _sha256(path) != event.get("file_sha256"):
        errors.append("event_log file SHA-256 mismatch")

    sync = _sync_contract(errors, label, event)
    if sync is None:
        factor, offset, _uncertainty = 1.0, 0.0, 0.0
    else:
        factor, offset, _uncertainty = sync

    supported = event.get("supported_event_types")
    if not isinstance(supported, list):
        errors.append("event_log.supported_event_types must be a list")
        supported = []
    supported_set = set(supported)
    unknown_supported = sorted(supported_set - allowed_types)
    if unknown_supported:
        errors.append(f"event_log has unknown supported event types {unknown_supported}")

    seq_field = event.get("sequence_field")
    ts_field = event.get("timestamp_field")
    if not _nonempty(seq_field) or not _nonempty(ts_field):
        errors.append("event_log sequence/timestamp fields must be nonempty")

    observed: set[str] = set()
    prev_seq: int | None = None
    prev_raw: float | None = None
    first_session: float | None = None
    last_session: float | None = None
    count = 0

    try:
        with path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                count += 1
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    errors.append(f"event_log:{line_no}: invalid JSON")
                    continue
                if not isinstance(row, dict):
                    errors.append(f"event_log:{line_no}: event must be an object")
                    continue

                seq = row.get(seq_field)
                if not isinstance(seq, int) or isinstance(seq, bool) or seq < 0:
                    errors.append(f"event_log:{line_no}: invalid sequence")
                elif prev_seq is not None and seq != prev_seq + 1:
                    errors.append(f"event_log:{line_no}: event sequence gap or reversal")
                if isinstance(seq, int) and not isinstance(seq, bool):
                    prev_seq = seq

                raw = row.get(ts_field)
                if not _finite(raw):
                    errors.append(f"event_log:{line_no}: invalid timestamp")
                    continue
                raw_ts = float(raw)
                if prev_raw is not None and raw_ts <= prev_raw:
                    errors.append(f"event_log:{line_no}: timestamp not strictly increasing")
                session_t = raw_ts * factor + offset
                if first_session is None:
                    first_session = session_t
                last_session = session_t
                prev_raw = raw_ts

                event_type = row.get("event_type")
                if event_type not in allowed_types:
                    errors.append(f"event_log:{line_no}: unknown event_type {event_type!r}")
                else:
                    observed.add(event_type)
                    if event_type not in supported_set:
                        errors.append(
                            f"event_log:{line_no}: observed event type {event_type} "
                            "is not declared supported"
                        )
                if not _nonempty(row.get("source_id")):
                    errors.append(f"event_log:{line_no}: source_id must be nonempty")
                if not isinstance(row.get("details"), dict):
                    errors.append(f"event_log:{line_no}: details must be an object")
    except OSError as exc:
        errors.append(f"event_log: {exc}")

    summary.update(
        {
            "row_count": count,
            "session_start_s": first_session,
            "session_end_s": last_session,
            "observed_event_types": sorted(observed),
        }
    )
    return summary


def validate(
    manifest: dict,
    base_dir: Path,
    power_architecture: dict,
    *,
    snapshot: dict | None = None,
    signal_registry: dict | None = None,
    event_schema: dict | None = None,
) -> dict:
    snapshot = snapshot or json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    signal_registry = signal_registry or json.loads(SIGNALS.read_text(encoding="utf-8"))
    event_schema = event_schema or json.loads(EVENT_SCHEMA.read_text(encoding="utf-8"))
    errors: list[str] = []

    if manifest.get("schema_version") != 1:
        errors.append("manifest schema_version must be 1")
    if manifest.get("scope") != "x1_telemetry_session_manifest":
        errors.append("wrong telemetry manifest scope")
    if manifest.get("sealed") is not True:
        errors.append("telemetry manifest must be sealed")
    if manifest.get("synthetic_fixture") not in (True, False):
        errors.append("synthetic_fixture must be boolean")
    if not _nonempty(manifest.get("sealed_at_utc")):
        errors.append("sealed_at_utc must be nonempty")

    for key in ("session_id", "board_id", "configuration_id", "commissioning_stage_id"):
        if not _nonempty(manifest.get(key)):
            errors.append(f"{key} must be nonempty")

    for key in (
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if manifest.get(key) is not False:
            errors.append(f"{key} must be false")

    started = _parse_utc(errors, "started_at_utc", manifest.get("started_at_utc"))
    ended = _parse_utc(errors, "ended_at_utc", manifest.get("ended_at_utc"))
    _parse_utc(errors, "sealed_at_utc", manifest.get("sealed_at_utc"))
    duration_s: float | None = None
    if started is not None and ended is not None:
        duration_s = (ended - started).total_seconds()
        if duration_s <= 0:
            errors.append("ended_at_utc must be after started_at_utc")

    _validate_power_architecture(errors, power_architecture)
    power_fp = power_architecture.get("authority_fingerprint_sha256")
    if manifest.get("power_architecture_fingerprint_sha256") != power_fp:
        errors.append("manifest power-architecture fingerprint mismatch")

    stage_id = manifest.get("commissioning_stage_id")
    stage = snapshot.get("commissioning_integration", {}).get(stage_id)
    if not isinstance(stage, dict) or stage.get("telemetry_required") is not True:
        errors.append(f"stage {stage_id!r} is not telemetry-required")
        stage = {"required_signals": [], "required_observed_events": []}

    if signal_registry.get("scope") != "x1_telemetry_signal_registry":
        errors.append("wrong telemetry signal registry scope")
    registry = {
        item["signal_id"]: item
        for item in signal_registry.get("signals", [])
        if isinstance(item, dict) and _nonempty(item.get("signal_id"))
    }

    streams = manifest.get("streams")
    if not isinstance(streams, list) or not streams:
        errors.append("streams must be a nonempty list")
        streams = []
    stream_ids: set[str] = set()
    stream_summaries: list[dict] = []
    available_signals: set[str] = set()
    signal_to_stream: dict[str, dict] = {}

    for stream in streams:
        if not isinstance(stream, dict):
            errors.append("stream entry must be an object")
            continue
        stream_id = stream.get("stream_id")
        if not _nonempty(stream_id):
            errors.append("stream_id must be nonempty")
        elif stream_id in stream_ids:
            errors.append(f"duplicate stream_id: {stream_id}")
        else:
            stream_ids.add(stream_id)

        summary = _read_stream(errors, base_dir, stream, registry)
        stream_summaries.append(summary)
        if summary["row_count"] > 0:
            for signal_id in summary["signal_ids"]:
                if signal_id in signal_to_stream:
                    errors.append(
                        f"signal {signal_id} appears in multiple nonempty streams"
                    )
                signal_to_stream[signal_id] = summary
                available_signals.add(signal_id)

    required_signals = set(stage.get("required_signals", []))
    missing_signals = sorted(required_signals - available_signals)
    if missing_signals:
        errors.append(f"required telemetry signals missing: {missing_signals}")

    event = manifest.get("event_log")
    if not isinstance(event, dict):
        errors.append("event_log must be an object")
        event = {}
    allowed_event_types = set(event_schema.get("event_types", []))
    required_supported = set(
        snapshot.get("event_log", {}).get("required_supported_event_types", [])
    )
    supported = set(event.get("supported_event_types", []))
    missing_supported = sorted(required_supported - supported)
    if missing_supported:
        errors.append(
            f"event_log missing supported event declarations: {missing_supported}"
        )

    event_summary = _read_events(
        errors, base_dir, event, allowed_event_types
    )
    observed_events = set(event_summary["observed_event_types"])
    universal_observed = {"SESSION_START", "SESSION_STOP", "STAGE_START", "STAGE_STOP"}
    missing_events = sorted(universal_observed - observed_events)
    if missing_events:
        errors.append(f"required session/stage events missing: {missing_events}")
    stage_events = set(stage.get("required_observed_events", []))
    missing_stage_events = sorted(stage_events - observed_events)
    if missing_stage_events:
        errors.append(
            f"required stage telemetry events missing: {missing_stage_events}"
        )

    overlap_fraction: float | None = None
    if duration_s is not None and duration_s > 0 and not missing_signals:
        required_streams = {
            summary["stream_id"]: summary
            for signal_id, summary in signal_to_stream.items()
            if signal_id in required_signals
        }
        if required_streams:
            starts = [
                x["session_start_s"]
                for x in required_streams.values()
                if x["session_start_s"] is not None
            ]
            ends = [
                x["session_end_s"]
                for x in required_streams.values()
                if x["session_end_s"] is not None
            ]
            if len(starts) != len(required_streams) or len(ends) != len(required_streams):
                errors.append("one or more required streams have no data")
            else:
                overlap = max(0.0, min(ends) - max(starts))
                overlap_fraction = overlap / duration_s
                minimum = float(
                    snapshot["clock_contract"][
                        "minimum_required_stream_overlap_fraction"
                    ]
                )
                if overlap_fraction < minimum:
                    errors.append(
                        f"required-stream overlap fraction {overlap_fraction:.4f} "
                        f"is below {minimum:.4f}"
                    )

    if duration_s is not None:
        for summary in stream_summaries + [event_summary]:
            start_s = summary.get("session_start_s")
            end_s = summary.get("session_end_s")
            if start_s is None or end_s is None:
                continue
            if start_s < -1e-6:
                errors.append(
                    f"{summary.get('stream_id', 'event_log')}: synchronized data "
                    "begins before session time zero"
                )
            if end_s > duration_s + 1e-6:
                errors.append(
                    f"{summary.get('stream_id', 'event_log')}: synchronized data "
                    "extends beyond declared session duration"
                )

    file_hashes = {
        stream.get("stream_id", f"stream-{i}"): stream.get("file_sha256")
        for i, stream in enumerate(streams)
        if isinstance(stream, dict)
    }
    file_hashes["event_log"] = event.get("file_sha256")

    qualified = not errors
    report = {
        "schema_version": 1,
        "authority": "x1_telemetry_session",
        "qualified": qualified,
        "errors": errors,
        "issues": [47, 49],
        "session_id": manifest.get("session_id"),
        "board_id": manifest.get("board_id"),
        "configuration_id": manifest.get("configuration_id"),
        "commissioning_stage_id": stage_id,
        "started_at_utc": manifest.get("started_at_utc"),
        "ended_at_utc": manifest.get("ended_at_utc"),
        "duration_s": round(duration_s, 6) if duration_s is not None else None,
        "power_architecture_fingerprint_sha256": power_fp,
        "available_signals": sorted(available_signals),
        "required_signals": sorted(required_signals),
        "observed_event_types": sorted(observed_events),
        "stream_summaries": stream_summaries,
        "event_summary": event_summary,
        "required_stream_overlap_fraction": (
            round(overlap_fraction, 6) if overlap_fraction is not None else None
        ),
        "raw_file_sha256": file_hashes,
        "physical_sensor_calibration_proven": False,
        "synthetic_fixture": manifest.get("synthetic_fixture") is True,
        "physical_evidence_eligible": (
            qualified and manifest.get("synthetic_fixture") is False
        ),
        "commissioning_stage_qualified": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": (
            "A passing telemetry authority proves file/hash/schema/chronology/"
            "provenance/synchronization/coverage integrity for the exact sealed "
            "session. It does not prove sensor calibration, stage success, vehicle "
            "safety, or any operating authority."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--power-architecture", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--signal-registry", type=Path, default=SIGNALS)
    parser.add_argument("--event-schema", type=Path, default=EVENT_SCHEMA)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    report = validate(
        json.loads(manifest_path.read_text(encoding="utf-8")),
        manifest_path.parent,
        json.loads(args.power_architecture.read_text(encoding="utf-8")),
        snapshot=json.loads(args.snapshot.read_text(encoding="utf-8")),
        signal_registry=json.loads(args.signal_registry.read_text(encoding="utf-8")),
        event_schema=json.loads(args.event_schema.read_text(encoding="utf-8")),
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
