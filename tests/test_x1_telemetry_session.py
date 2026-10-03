import csv
import hashlib
import json
import math
from pathlib import Path

import pytest

from tools.init_x1_telemetry_session import initialize
from tools.seal_x1_telemetry_session import seal
from tools.summarize_x1_commissioning_telemetry import replay
from tools.validate_x1_telemetry_session import validate

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = json.loads(
    (ROOT / "hardware/rev_c_telemetry_reference_snapshot_2026-10-02.json").read_text()
)
SIGNALS = json.loads(
    (ROOT / "hardware/x1_telemetry_signal_registry_2026-10-02.json").read_text()
)
EVENT_SCHEMA = json.loads(
    (ROOT / "hardware/x1_telemetry_event_schema.json").read_text()
)
COMMISSIONING = json.loads(
    (ROOT / "hardware/rev_c_powered_commissioning_snapshot_2026-10-01.json").read_text()
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
            "general_powered_operation_authorized": False,
        }
    )


def _write_csv(path: Path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _configure_manifest(workspace: Path):
    path = workspace / "telemetry_manifest.json"
    data = json.loads(path.read_text())
    for stream in data["streams"]:
        stream["source_device_id"] = f"device-{stream['stream_id']}"
        stream["clock_id"] = f"clock-{stream['stream_id']}"
        stream["nominal_rate_hz"] = 10.0
        stream["max_gap_s"] = 0.2
        stream["sync_model"] = {
            "method": "synthetic affine sync",
            "scale": 1.0,
            "offset_s": 0.0,
            "uncertainty_ms": 1.0,
            "evidence_ref": f"synthetic://sync/{stream['stream_id']}",
        }
        definitions = {
            item["signal_id"]: item
            for item in SIGNALS["signals"]
        }
        for signal in stream["signals"]:
            signal["source_id"] = f"source-{signal['signal_id']}"
            kind = definitions[signal["signal_id"]]["kind"]
            if kind.startswith("derived"):
                signal["derivation_id"] = f"synthetic-{signal['signal_id']}-v1"
            if kind == "calibrated_or_derived_motion":
                signal["calibration_id"] = f"synthetic-{signal['signal_id']}-frame"

    data["event_log"].update(
        {
            "source_device_id": "device-events",
            "clock_id": "clock-events",
            "supported_event_types": SNAPSHOT["event_log"][
                "required_supported_event_types"
            ],
            "sync_model": {
                "method": "synthetic affine sync",
                "scale": 1.0,
                "offset_s": 0.0,
                "uncertainty_ms": 1.0,
                "evidence_ref": "synthetic://sync/events",
            },
        }
    )
    path.write_text(json.dumps(data, indent=2) + "\n")
    return data


def _populate_stage4(workspace: Path):
    manifest = _configure_manifest(workspace)
    times = [i / 10 for i in range(101)]

    for stream in manifest["streams"]:
        fields = [
            stream["sequence_column"],
            stream["timestamp_column"],
            *[x["column"] for x in stream["signals"]],
        ]
        rows = []
        for seq, t in enumerate(times):
            row = {"seq": seq, "timestamp": t}
            for decl in stream["signals"]:
                sid = decl["signal_id"]
                if sid == "remote_throttle_norm":
                    value = 0.5 if t < 4.0 else 0.0
                elif sid == "remote_deadman_active":
                    value = 1 if t < 4.0 else 0
                elif sid == "remote_age_s":
                    value = 0.01
                elif sid == "ride_mode":
                    value = 4
                elif sid in {"drive_current_cmd_left_a", "drive_current_cmd_right_a"}:
                    if t < 4.0:
                        value = 5.0
                    elif t < 4.1:
                        value = 4.0
                    elif t < 4.2:
                        value = 2.0
                    else:
                        value = 0.4
                elif sid in {"regen_current_cmd_left_a", "regen_current_cmd_right_a"}:
                    value = 3.0 if 6.0 <= t < 8.0 else 0.0
                elif sid in {"tc_scale_left", "tc_scale_right"}:
                    value = 1.0
                elif sid == "controller_fault_bits":
                    value = 0
                elif sid == "pack_voltage_v":
                    value = 54.0 - 0.02 * t
                elif sid == "battery_current_a":
                    value = 8.0 if t < 6.0 else -2.0
                elif sid == "pack_soc_fraction":
                    value = 0.8
                elif sid in {"left_phase_current_a", "right_phase_current_a"}:
                    value = 10.0 if t < 6.0 else -3.0
                elif sid in {"left_motor_erpm", "right_motor_erpm"}:
                    value = 3000.0 if t < 6.0 else max(0.0, 3000.0 * (8.0 - t) / 2.0)
                elif sid == "ground_speed_mps":
                    value = 2.0 if t < 6.0 else max(0.0, 2.0 * (8.0 - t) / 2.0)
                elif sid in {"front_left_wheel_speed_mps", "front_right_wheel_speed_mps"}:
                    value = 2.0 if t < 6.0 else max(0.0, 2.0 * (8.0 - t) / 2.0)
                elif sid == "longitudinal_accel_mps2":
                    value = -1.0 if 6.0 <= t < 8.0 else 0.0
                elif sid == "longitudinal_jerk_mps3":
                    value = -10.0 if math.isclose(t, 6.0) else (10.0 if math.isclose(t, 8.0) else 0.0)
                elif sid.startswith("imu_accel_"):
                    value = 9.80665 if sid.endswith("z_mps2") else 0.0
                elif sid.startswith("imu_gyro_"):
                    value = 0.0
                elif sid == "pack_temperature_c":
                    value = 28.0 + 0.02 * t
                elif "motor_temperature" in sid:
                    value = 32.0 + 0.03 * t
                elif "controller_temperature" in sid:
                    value = 31.0 + 0.03 * t
                else:
                    value = 0.0
                row[decl["column"]] = value
            rows.append(row)
        _write_csv(workspace / stream["file"], fields, rows)

    events = [
        {"seq":0,"timestamp":0.0,"event_type":"SESSION_START","source_id":"logger","details":{}},
        {"seq":1,"timestamp":0.01,"event_type":"STAGE_START","source_id":"logger","details":{"stage_id":"RIDER_ONLY_VERY_LOW_SPEED"}},
        {"seq":2,"timestamp":4.0,"event_type":"DEADMAN_TRANSITION","source_id":"controller","details":{"active":False}},
        {"seq":3,"timestamp":6.0,"event_type":"STOPPING_TEST_START","source_id":"operator","details":{}},
        {"seq":4,"timestamp":9.9,"event_type":"STAGE_STOP","source_id":"logger","details":{"stage_id":"RIDER_ONLY_VERY_LOW_SPEED"}},
        {"seq":5,"timestamp":10.0,"event_type":"SESSION_STOP","source_id":"logger","details":{}},
    ]
    event_path = workspace / manifest["event_log"]["file"]
    event_path.write_text(
        "".join(json.dumps(x, separators=(",", ":")) + "\n" for x in events),
        encoding="utf-8",
    )


def _build_stage4(tmp_path: Path):
    power = _power()
    power_path = tmp_path / "power.json"
    power_path.write_text(json.dumps(power))
    workspace = tmp_path / "telemetry"
    initialize(
        workspace,
        board_id="X1-TEST",
        configuration_id="CFG-A",
        stage_id="RIDER_ONLY_VERY_LOW_SPEED",
        started_at_utc="2026-10-02T12:00:00Z",
        power_architecture_path=power_path,
    )
    _populate_stage4(workspace)
    seal(
        workspace / "telemetry_manifest.json",
        ended_at_utc="2026-10-02T12:00:10Z",
    )
    manifest = json.loads((workspace / "telemetry_manifest.json").read_text())
    return workspace, manifest, power


def test_stage4_session_validates_and_replays_all_required_metrics(tmp_path: Path):
    workspace, manifest, power = _build_stage4(tmp_path)
    authority = validate(
        manifest,
        workspace,
        power,
        snapshot=SNAPSHOT,
        signal_registry=SIGNALS,
        event_schema=EVENT_SCHEMA,
    )
    assert authority["qualified"] is True
    assert authority["commissioning_stage_qualified"] is False
    assert authority["physical_sensor_calibration_proven"] is False
    assert authority["required_stream_overlap_fraction"] == pytest.approx(1.0)
    assert authority["powered_operation_authorized"] is False

    replay_report = replay(
        manifest,
        workspace,
        authority,
        signal_registry=SIGNALS,
        commissioning_snapshot=COMMISSIONING,
    )
    assert replay_report["qualified"] is True
    required = {
        stage["stage_id"]: set(stage["required_measurements"])
        for stage in COMMISSIONING["stages"]
    }["RIDER_ONLY_VERY_LOW_SPEED"]
    assert set(replay_report["metric_ids"]) == required

    by_id = {item["metric_id"]: item for item in replay_report["metrics"]}
    assert by_id["remote_release_propulsion_decay_s"]["value"] == pytest.approx(0.2)
    assert by_id["stopping_distance_m"]["value"] == pytest.approx(2.0, abs=0.15)
    assert by_id["longitudinal_jerk_mps3"]["sample_count"] == 101
    assert replay_report["powered_operation_authorized"] is False


def test_hash_mutation_after_sealing_invalidates_session(tmp_path: Path):
    workspace, manifest, power = _build_stage4(tmp_path)
    path = workspace / "streams/control.csv"
    path.write_text(path.read_text() + "\n", encoding="utf-8")

    report = validate(
        manifest,
        workspace,
        power,
        snapshot=SNAPSHOT,
        signal_registry=SIGNALS,
        event_schema=EVENT_SCHEMA,
    )
    assert report["qualified"] is False
    assert any("SHA-256 mismatch" in error for error in report["errors"])


def test_undeclared_sequence_gap_is_rejected(tmp_path: Path):
    workspace, manifest, power = _build_stage4(tmp_path)
    stream = next(x for x in manifest["streams"] if x["stream_id"] == "control")
    path = workspace / stream["file"]
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    fields = list(rows[0].keys())
    rows = [row for row in rows if row["seq"] != "20"]
    _write_csv(path, fields, rows)

    # Re-seal manually because this test intentionally changes raw bytes before validation.
    stream["file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    report = validate(
        manifest,
        workspace,
        power,
        snapshot=SNAPSHOT,
        signal_registry=SIGNALS,
        event_schema=EVENT_SCHEMA,
    )
    assert report["qualified"] is False
    assert any("undeclared sequence gaps" in error for error in report["errors"])


def test_declared_sequence_gap_is_accounted_but_excessive_time_gap_still_fails(tmp_path: Path):
    workspace, manifest, power = _build_stage4(tmp_path)
    stream = next(x for x in manifest["streams"] if x["stream_id"] == "control")
    path = workspace / stream["file"]
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    fields = list(rows[0].keys())
    rows = [row for row in rows if row["seq"] not in {"20", "21"}]
    _write_csv(path, fields, rows)
    stream["dropped_sequence_ranges"] = [
        {"start_seq":20,"end_seq":21,"reason":"synthetic logger overrun"}
    ]
    stream["file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()

    report = validate(
        manifest,
        workspace,
        power,
        snapshot=SNAPSHOT,
        signal_registry=SIGNALS,
        event_schema=EVENT_SCHEMA,
    )
    assert report["qualified"] is False
    assert not any("undeclared sequence gaps" in error for error in report["errors"])
    assert any("exceeds declared max" in error for error in report["errors"])


def test_nonmonotonic_timestamp_is_rejected(tmp_path: Path):
    workspace, manifest, power = _build_stage4(tmp_path)
    stream = next(x for x in manifest["streams"] if x["stream_id"] == "motion")
    path = workspace / stream["file"]
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    fields = list(rows[0].keys())
    rows[30]["timestamp"] = rows[29]["timestamp"]
    _write_csv(path, fields, rows)
    stream["file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()

    report = validate(
        manifest,
        workspace,
        power,
        snapshot=SNAPSHOT,
        signal_registry=SIGNALS,
        event_schema=EVENT_SCHEMA,
    )
    assert report["qualified"] is False
    assert any("timestamp not strictly increasing" in error for error in report["errors"])


def test_missing_source_provenance_is_rejected(tmp_path: Path):
    workspace, manifest, power = _build_stage4(tmp_path)
    manifest["streams"][0]["signals"][0]["source_id"] = ""

    report = validate(
        manifest,
        workspace,
        power,
        snapshot=SNAPSHOT,
        signal_registry=SIGNALS,
        event_schema=EVENT_SCHEMA,
    )
    assert report["qualified"] is False
    assert any("source_id must be nonempty" in error for error in report["errors"])


def test_cross_stream_overlap_below_contract_is_rejected(tmp_path: Path):
    workspace, manifest, power = _build_stage4(tmp_path)
    motion = next(x for x in manifest["streams"] if x["stream_id"] == "motion")
    motion["sync_model"]["offset_s"] = 2.0

    report = validate(
        manifest,
        workspace,
        power,
        snapshot=SNAPSHOT,
        signal_registry=SIGNALS,
        event_schema=EVENT_SCHEMA,
    )
    assert report["qualified"] is False
    assert any("overlap fraction" in error for error in report["errors"])


def test_required_deadman_event_is_rejected_when_missing(tmp_path: Path):
    workspace, manifest, power = _build_stage4(tmp_path)
    event_path = workspace / manifest["event_log"]["file"]
    events = [
        json.loads(line)
        for line in event_path.read_text().splitlines()
        if line.strip()
    ]
    events = [e for e in events if e["event_type"] != "DEADMAN_TRANSITION"]
    for i, event in enumerate(events):
        event["seq"] = i
    event_path.write_text(
        "".join(json.dumps(x) + "\n" for x in events),
        encoding="utf-8",
    )
    manifest["event_log"]["file_sha256"] = hashlib.sha256(
        event_path.read_bytes()
    ).hexdigest()

    report = validate(
        manifest,
        workspace,
        power,
        snapshot=SNAPSHOT,
        signal_registry=SIGNALS,
        event_schema=EVENT_SCHEMA,
    )
    assert report["qualified"] is False
    assert any("required stage telemetry events missing" in error for error in report["errors"])


def test_replay_rehashes_raw_data_and_rejects_post_validation_mutation(tmp_path: Path):
    workspace, manifest, power = _build_stage4(tmp_path)
    authority = validate(
        manifest,
        workspace,
        power,
        snapshot=SNAPSHOT,
        signal_registry=SIGNALS,
        event_schema=EVENT_SCHEMA,
    )
    assert authority["qualified"] is True

    path = workspace / "streams/motion.csv"
    path.write_text(path.read_text() + "\n", encoding="utf-8")
    replay_report = replay(
        manifest,
        workspace,
        authority,
        signal_registry=SIGNALS,
        commissioning_snapshot=COMMISSIONING,
    )
    assert replay_report["qualified"] is False
    assert any("changed after validation" in error for error in replay_report["errors"])
