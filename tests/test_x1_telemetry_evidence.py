import csv
import hashlib
import json
from pathlib import Path

import pytest

from tools.init_x1_telemetry_session import initialize
from tools.populate_synthetic_x1_telemetry_session import populate
from tools.qualify_x1_telemetry_evidence import qualify

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = json.loads(
    (
        ROOT / "hardware/rev_c_telemetry_evidence_snapshot_2026-10-01.json"
    ).read_text()
)
REGISTRY = json.loads(
    (ROOT / "hardware/x1_telemetry_signal_registry.json").read_text()
)


def _stamp(doc):
    payload = json.dumps(
        doc,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    out = dict(doc)
    out["authority_fingerprint_sha256"] = hashlib.sha256(payload).hexdigest()
    return out


def _power():
    return _stamp(
        {
            "schema_version": 1,
            "authority": "x1_power_architecture",
            "qualified": True,
        }
    )


def _health(board_id="X1-TEST", config_id="CFG-A"):
    return _stamp(
        {
            "schema_version": 1,
            "authority": "x1_lifecycle_health_state",
            "valid": True,
            "board_id": board_id,
            "current_configuration_id": config_id,
            "health_state": "READY_FOR_ALLOWED_ACTIVITY",
            "ready_for_allowed_activity": True,
            "powered_operation_authorized": False,
            "public_operation_authorized": False,
            "dog_accompanied_operation_authorized": False,
        }
    )


def _write(path: Path, doc):
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _session(tmp_path: Path, stage_id="RIDER_ONLY_VERY_LOW_SPEED"):
    power = _power()
    health = _health()
    power_path = tmp_path / "power.json"
    health_path = tmp_path / "health.json"
    _write(power_path, power)
    _write(health_path, health)

    session = tmp_path / "session"
    initialize(
        session,
        stage_id,
        "X1-TEST",
        "CFG-A",
        power_path,
        health_path,
        "ci-build",
        "ci-source-revision",
        "ci-logger-hardware",
        "synthetic-memory",
    )
    populate(session, duration_s=2.0)
    manifest = json.loads((session / "telemetry_manifest.json").read_text())
    return session, manifest, power, health


def _qualify(session, manifest, power, health):
    return qualify(
        manifest,
        session,
        power,
        health,
        snapshot=SNAPSHOT,
        registry=REGISTRY,
    )


@pytest.mark.parametrize(
    "stage_id",
    [
        "SECURED_UNLOADED_SPIN",
        "RESTRAINED_LOADED_BENCH",
        "RIDER_FREE_CONTROLLED_GROUND",
        "RIDER_ONLY_VERY_LOW_SPEED",
    ],
)
def test_synthetic_stage_telemetry_can_qualify_without_operation_authority(
    tmp_path: Path,
    stage_id: str,
):
    session, manifest, power, health = _session(tmp_path, stage_id)
    report = _qualify(session, manifest, power, health)

    assert report["qualified"] is True
    assert report["data_quality_qualified"] is True
    assert report["commissioning_stage_id"] == stage_id
    assert report["record_drop_fraction"] == 0
    assert report["controller_configuration_authority"] is False
    assert report["battery_configuration_authority"] is False
    assert report["powered_operation_authorized"] is False
    assert report["public_operation_authorized"] is False
    assert report["dog_accompanied_operation_authorized"] is False
    assert len(report["authority_fingerprint_sha256"]) == 64


def test_stage_zero_is_deliberately_not_a_telemetry_session(tmp_path: Path):
    power = _power()
    health = _health()
    power_path = tmp_path / "power.json"
    health_path = tmp_path / "health.json"
    _write(power_path, power)
    _write(health_path, health)

    with pytest.raises(ValueError, match="Stages 1-4"):
        initialize(
            tmp_path / "stage-0",
            "BENCH_READINESS",
            "X1-TEST",
            "CFG-A",
            power_path,
            health_path,
            "build",
            "rev",
            "hw",
            "memory",
        )


def test_manifest_must_link_exact_power_and_health_authorities(tmp_path: Path):
    session, manifest, power, health = _session(tmp_path)
    manifest["power_architecture_fingerprint_sha256"] = "0" * 64
    manifest["pre_lifecycle_health_fingerprint_sha256"] = "1" * 64

    report = _qualify(session, manifest, power, health)
    assert report["qualified"] is False
    assert "manifest power-architecture fingerprint mismatch" in report["errors"]
    assert "manifest pre-health fingerprint mismatch" in report["errors"]


def test_initializer_rejects_wrong_board_health(tmp_path: Path):
    power = _power()
    health = _health(board_id="OTHER")
    power_path = tmp_path / "power.json"
    health_path = tmp_path / "health.json"
    _write(power_path, power)
    _write(health_path, health)

    with pytest.raises(ValueError, match="READY state"):
        initialize(
            tmp_path / "session",
            "SECURED_UNLOADED_SPIN",
            "X1-TEST",
            "CFG-A",
            power_path,
            health_path,
            "build",
            "rev",
            "hw",
            "memory",
        )


def test_record_sequence_gap_must_be_reported_and_within_budget(tmp_path: Path):
    session, manifest, power, health = _session(
        tmp_path,
        "SECURED_UNLOADED_SPIN",
    )
    path = session / "telemetry.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fields = rows[0].keys()
    rows.pop(len(rows) // 2)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    report = _qualify(session, manifest, power, health)
    assert report["qualified"] is False
    assert any(
        "reported_dropped_records must equal record-sequence gaps" in x
        for x in report["errors"]
    )


def test_undersampled_required_signal_fails(tmp_path: Path):
    session, manifest, power, health = _session(
        tmp_path,
        "RIDER_ONLY_VERY_LOW_SPEED",
    )
    path = session / "telemetry.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fields = rows[0].keys()

    target = "longitudinal_accel_mps2"
    kept = []
    target_index = 0
    for row in rows:
        if row["signal_id"] == target:
            target_index += 1
            if target_index % 4 != 1:
                continue
        kept.append(row)

    # Re-sequence so this failure is about sample rate/gap, not record drops.
    for seq, row in enumerate(kept):
        row["record_seq"] = str(seq)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(kept)

    manifest["session_summary"]["expected_records"] = len(kept)
    report = _qualify(session, manifest, power, health)
    assert report["qualified"] is False
    assert any(target in x and ("below" in x or "max OK gap" in x) for x in report["errors"])


def test_stale_required_signal_fails_source_age_limit(tmp_path: Path):
    session, manifest, power, health = _session(
        tmp_path,
        "SECURED_UNLOADED_SPIN",
    )
    path = session / "telemetry.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fields = rows[0].keys()
    for row in rows:
        if row["signal_id"] == "pack_voltage_v":
            row["source_age_us"] = "999999"
            break
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    report = _qualify(session, manifest, power, health)
    assert report["qualified"] is False
    assert any(
        "pack_voltage_v: source age exceeds declared maximum" in x
        for x in report["errors"]
    )


def test_fault_transition_requires_matching_fault_edge_event(tmp_path: Path):
    session, manifest, power, health = _session(
        tmp_path,
        "SECURED_UNLOADED_SPIN",
    )
    path = session / "telemetry.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fields = rows[0].keys()

    seen = 0
    for row in rows:
        if row["signal_id"] == "control_fault_bits":
            seen += 1
            if seen >= 3:
                row["value"] = "1"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    report = _qualify(session, manifest, power, health)
    assert report["qualified"] is False
    assert any(
        "transition lacks matching FAULT_EDGE" in x
        for x in report["errors"]
    )


def test_logger_error_event_invalidates_session(tmp_path: Path):
    session, manifest, power, health = _session(
        tmp_path,
        "SECURED_UNLOADED_SPIN",
    )
    path = session / "events.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    events.insert(
        -1,
        {
            "event_seq": 2,
            "mono_us": 1_000_000,
            "event_type": "LOGGER_ERROR",
            "code": "WRITE_FAIL",
            "fault_bits": 0,
            "details": {"synthetic": True},
        },
    )
    for seq, event in enumerate(events):
        event["event_seq"] = seq
    path.write_text(
        "".join(json.dumps(x) + "\n" for x in events),
        encoding="utf-8",
    )

    report = _qualify(session, manifest, power, health)
    assert report["qualified"] is False
    assert "LOGGER_ERROR events prevent telemetry qualification" in report["errors"]


def test_derived_signal_requires_documented_method(tmp_path: Path):
    session, manifest, power, health = _session(
        tmp_path,
        "RIDER_ONLY_VERY_LOW_SPEED",
    )
    channel = next(
        item
        for item in manifest["declared_channels"]
        if item["signal_id"] == "longitudinal_jerk_mps3"
    )
    channel["derivation_method_reference"] = ""

    report = _qualify(session, manifest, power, health)
    assert report["qualified"] is False
    assert any(
        "longitudinal_jerk_mps3: DERIVED source requires" in x
        for x in report["errors"]
    )


def test_required_metric_method_and_unit_are_enforced(tmp_path: Path):
    session, manifest, power, health = _session(
        tmp_path,
        "RIDER_ONLY_VERY_LOW_SPEED",
    )
    path = session / "metrics.json"
    metrics = json.loads(path.read_text())
    stop = next(x for x in metrics if x["metric_id"] == "stopping_distance_m")
    stop["unit"] = "ft"
    stop["method_reference"] = ""
    path.write_text(json.dumps(metrics, indent=2) + "\n")

    report = _qualify(session, manifest, power, health)
    assert report["qualified"] is False
    assert any("stopping_distance_m: expected unit m" in x for x in report["errors"])
    assert any(
        "stopping_distance_m: method_reference must be nonempty" in x
        for x in report["errors"]
    )


def test_write_error_or_unclean_shutdown_invalidates_evidence(tmp_path: Path):
    session, manifest, power, health = _session(
        tmp_path,
        "SECURED_UNLOADED_SPIN",
    )
    manifest["session_summary"]["persistent_write_error_count"] = 1
    manifest["session_summary"]["unclean_shutdown"] = True

    report = _qualify(session, manifest, power, health)
    assert report["qualified"] is False
    assert "persistent_write_error_count must be zero" in report["errors"]
    assert "unclean_shutdown must be false" in report["errors"]
