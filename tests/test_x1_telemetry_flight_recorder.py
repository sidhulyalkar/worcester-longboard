import csv
import hashlib
import json
import math
from pathlib import Path

from tools.finalize_x1_telemetry_session import finalize
from tools.init_x1_telemetry_session import initialize
from tools.summarize_x1_commissioning_telemetry import summarize
from tools.validate_x1_telemetry_session import validate

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (ROOT / "hardware/x1_telemetry_contract_2026-10-01.json").read_text()
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


def _power(tmp_path: Path):
    doc = _stamp(
        {
            "schema_version": 1,
            "authority": "x1_power_architecture",
            "qualified": True,
        }
    )
    path = tmp_path / "power.json"
    path.write_text(json.dumps(doc, indent=2) + "\n")
    return path, doc


def _write_rows(path: Path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _configure_stage4_session(tmp_path: Path):
    power_path, power = _power(tmp_path)
    session = tmp_path / "telemetry"
    initialize(
        session,
        session_id="TEL-STAGE4",
        board_id="X1-A",
        configuration_id="CFG-A",
        stage_id="RIDER_ONLY_VERY_LOW_SPEED",
        power_architecture_path=power_path,
        firmware_revision="firmware-test-sha",
        reference_clock_id="CLOCK-REF",
        started_at_utc="2026-10-01T12:00:00Z",
    )

    manifest_path = session / "telemetry_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["minimum_required_overlap_s"] = 3.5
    manifest["processing"] = {
        "longitudinal_accel_column": "accel_x_mps2",
        "jerk_smoothing_window_samples": 3,
        "propulsion_zero_threshold_a": 0.2,
        "propulsion_zero_hold_s": 0.2,
    }

    for stream in manifest["streams"]:
        stream["source_id"] = f"SRC-{stream['stream_type'].upper()}"
        stream["clock_id"] = "CLOCK-REF"
        stream["timestamps_normalized_to_reference"] = True
        stream["synchronization_method"] = "same_reference_clock"
        stream["synchronization_evidence_ref"] = ""
        stream["synchronization_uncertainty_s"] = 0.0
        stream["max_allowed_sync_uncertainty_s"] = 0.01
        stream["calibration_status"] = (
            "NOT_APPLICABLE"
            if stream["stream_type"] == "events"
            else "DECLARED_ONLY"
        )
        if stream["sampling_mode"] == "continuous":
            stream["nominal_rate_hz"] = 10.0
            stream["nominal_rate_tolerance_fraction"] = 0.05
            stream["max_gap_s"] = 0.11
        else:
            stream["nominal_rate_hz"] = None
            stream["nominal_rate_tolerance_fraction"] = None
            stream["max_gap_s"] = None

    times = [round(i * 0.1, 1) for i in range(41)]

    control_rows = []
    for t in times:
        if t < 1.0:
            drive = 5.0
            deadman = "true"
        elif t < 1.3:
            drive = max(0.0, 5.0 * (1.3 - t) / 0.3)
            deadman = "false"
        else:
            drive = 0.0
            deadman = "false"
        control_rows.append(
            {
                "time_s": t,
                "throttle_request": 0.2 if t < 1.0 else 0.0,
                "brake_request": 0.0,
                "ride_mode": "Shasta",
                "remote_deadman_active": deadman,
                "drive_command_left_a": drive,
                "drive_command_right_a": drive,
                "regen_command_left_a": 0.0,
                "regen_command_right_a": 0.0,
                "controller_fault_bits": 0,
            }
        )

    electrical_rows = []
    for t in times:
        electrical_rows.append(
            {
                "time_s": t,
                "pack_voltage_v": 58.0 - 0.2 * math.sin(t),
                "battery_current_a": 2.0 * math.sin(t),
                "left_phase_current_a": 4.0 * math.sin(t),
                "right_phase_current_a": 3.8 * math.sin(t),
                "left_motor_erpm": 1200.0 * math.sin(t),
                "right_motor_erpm": 1180.0 * math.sin(t),
                "left_motor_speed_rpm": 400.0 * math.sin(t),
                "right_motor_speed_rpm": 395.0 * math.sin(t),
                "left_motor_temperature_c": 30.0 + t,
                "right_motor_temperature_c": 30.5 + t,
                "left_controller_temperature_c": 29.0 + 0.8 * t,
                "right_controller_temperature_c": 29.5 + 0.8 * t,
            }
        )

    motion_rows = []
    for t in times:
        if 2.0 <= t <= 3.0:
            speed = max(0.0, 2.0 * (3.0 - t))
        elif t < 2.0:
            speed = 2.0
        else:
            speed = 0.0
        accel_x = 0.4 * math.sin(2.0 * t)
        motion_rows.append(
            {
                "time_s": t,
                "ground_speed_mps": speed,
                "front_left_speed_mps": speed,
                "front_right_speed_mps": speed,
                "rear_left_speed_mps": speed,
                "rear_right_speed_mps": speed,
                "accel_x_mps2": accel_x,
                "accel_y_mps2": 0.05 * math.sin(t),
                "accel_z_mps2": 9.80665 + 0.1 * math.sin(t),
                "gyro_x_dps": 1.0 * math.sin(t),
                "gyro_y_dps": 2.0 * math.sin(t),
                "gyro_z_dps": 3.0 * math.sin(t),
            }
        )

    event_rows = [
        {"time_s": 0.0, "event_type": "session", "event_code": "SESSION_START", "detail": ""},
        {"time_s": 0.1, "event_type": "commissioning", "event_code": "COMMISSIONING_STAGE_START", "detail": ""},
        {"time_s": 1.0, "event_type": "control", "event_code": "REMOTE_DEADMAN_RELEASE", "detail": ""},
        {"time_s": 2.0, "event_type": "stopping", "event_code": "STOPPING_START", "detail": ""},
        {"time_s": 3.0, "event_type": "stopping", "event_code": "VEHICLE_STOPPED", "detail": ""},
        {"time_s": 3.8, "event_type": "commissioning", "event_code": "COMMISSIONING_STAGE_STOP", "detail": ""},
        {"time_s": 4.0, "event_type": "session", "event_code": "SESSION_STOP", "detail": ""},
    ]

    specs = {item["stream_type"]: item for item in CONTRACT["streams"]}
    rows_by_type = {
        "control": control_rows,
        "electrical": electrical_rows,
        "motion": motion_rows,
        "events": event_rows,
    }
    for stream in manifest["streams"]:
        stream_type = stream["stream_type"]
        _write_rows(
            session / stream["file_path"],
            specs[stream_type]["required_columns"],
            rows_by_type[stream_type],
        )

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    finalized = finalize(
        manifest_path,
        "2026-10-01T12:00:04Z",
    )
    return session, manifest_path, finalized, power_path, power


def test_initializer_creates_only_stage_required_streams(tmp_path: Path):
    power_path, _ = _power(tmp_path)
    session = tmp_path / "stage1"
    initialize(
        session,
        session_id="TEL-STAGE1",
        board_id="X1-A",
        configuration_id="CFG-A",
        stage_id="SECURED_UNLOADED_SPIN",
        power_architecture_path=power_path,
        firmware_revision="firmware-test",
        reference_clock_id="CLOCK",
        started_at_utc="2026-10-01T12:00:00Z",
    )
    manifest = json.loads((session / "telemetry_manifest.json").read_text())
    assert {x["stream_type"] for x in manifest["streams"]} == {
        "control",
        "electrical",
        "events",
    }
    assert not (session / "streams/motion.csv").exists()


def test_valid_stage4_session_hashes_syncs_and_replays(tmp_path: Path):
    session, manifest_path, manifest, _, power = _configure_stage4_session(tmp_path)

    report = validate(manifest, session, power, CONTRACT)
    assert report["valid"] is True
    assert report["telemetry_integrity_qualified"] is True
    assert report["common_required_stream_overlap_s"] == 4.0
    assert report["sensor_calibration_authority"] is False
    assert report["powered_operation_authorized"] is False
    assert len(report["authority_fingerprint_sha256"]) == 64

    summary = summarize(
        manifest,
        session,
        report,
        power,
        CONTRACT,
    )
    assert summary["valid"] is True
    assert summary["all_required_metrics_derived"] is True
    assert summary["pass_threshold_authority"] is False
    assert summary["powered_operation_authorized"] is False

    metrics = {item["metric_id"]: item for item in summary["metrics"]}
    assert set(metrics) == set(
        CONTRACT["stage_requirements"]["RIDER_ONLY_VERY_LOW_SPEED"][
            "required_metric_ids"
        ]
    )
    assert 0.2 <= metrics["remote_release_propulsion_decay_s"]["value"] <= 0.4
    assert 0.9 <= metrics["stopping_distance_m"]["value"] <= 1.1
    assert metrics["longitudinal_jerk_mps3"]["value"] > 0


def test_hash_drift_is_rejected_and_summary_refuses_stale_authority(tmp_path: Path):
    session, manifest_path, manifest, _, power = _configure_stage4_session(tmp_path)
    authority = validate(manifest, session, power, CONTRACT)
    assert authority["valid"] is True

    control = session / "streams/control.csv"
    control.write_text(control.read_text() + "\n", encoding="utf-8")

    current = json.loads(manifest_path.read_text())
    report = validate(current, session, power, CONTRACT)
    assert report["valid"] is False
    assert any("file SHA-256 mismatch" in error for error in report["errors"])

    summary = summarize(current, session, authority, power, CONTRACT)
    assert summary["valid"] is False
    assert any("no longer validate" in error for error in summary["errors"])


def test_nonmonotonic_timestamp_and_excessive_gap_are_rejected(tmp_path: Path):
    session, manifest_path, manifest, _, power = _configure_stage4_session(tmp_path)
    path = session / "streams/control.csv"
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    fieldnames = rows[0].keys()
    rows[10]["time_s"] = "0.5"
    _write_rows(path, fieldnames, rows)
    finalize(manifest_path, "2026-10-01T12:00:04Z")

    current = json.loads(manifest_path.read_text())
    report = validate(current, session, power, CONTRACT)
    assert report["valid"] is False
    assert any("strictly increasing" in error for error in report["errors"])


def test_sync_uncertainty_and_missing_required_event_fail(tmp_path: Path):
    session, manifest_path, manifest, _, power = _configure_stage4_session(tmp_path)
    current = json.loads(manifest_path.read_text())
    motion = next(x for x in current["streams"] if x["stream_type"] == "motion")
    motion["synchronization_uncertainty_s"] = 0.02
    motion["max_allowed_sync_uncertainty_s"] = 0.01

    events_path = session / "streams/events.csv"
    rows = list(csv.DictReader(events_path.open(newline="", encoding="utf-8")))
    fieldnames = rows[0].keys()
    rows = [row for row in rows if row["event_code"] != "VEHICLE_STOPPED"]
    _write_rows(events_path, fieldnames, rows)
    manifest_path.write_text(json.dumps(current, indent=2) + "\n")
    finalize(manifest_path, "2026-10-01T12:00:04Z")

    current = json.loads(manifest_path.read_text())
    report = validate(current, session, power, CONTRACT)
    assert report["valid"] is False
    assert any("synchronization uncertainty exceeds" in x for x in report["errors"])
    assert "required stage event missing: VEHICLE_STOPPED" in report["errors"]


def test_stream_rate_mismatch_is_rejected(tmp_path: Path):
    session, manifest_path, manifest, _, power = _configure_stage4_session(tmp_path)
    current = json.loads(manifest_path.read_text())
    electrical = next(
        x for x in current["streams"] if x["stream_type"] == "electrical"
    )
    electrical["nominal_rate_hz"] = 100.0
    electrical["nominal_rate_tolerance_fraction"] = 0.05
    manifest_path.write_text(json.dumps(current, indent=2) + "\n")

    report = validate(current, session, power, CONTRACT)
    assert report["valid"] is False
    assert any("effective median rate" in error for error in report["errors"])


def test_capture_anomaly_and_missing_overlap_fail_closed(tmp_path: Path):
    session, manifest_path, manifest, _, power = _configure_stage4_session(tmp_path)
    current = json.loads(manifest_path.read_text())
    current["anomalies"] = ["logger reboot observed"]
    current["minimum_required_overlap_s"] = 5.0
    manifest_path.write_text(json.dumps(current, indent=2) + "\n")

    report = validate(current, session, power, CONTRACT)
    assert report["valid"] is False
    assert "telemetry session cannot qualify with unresolved capture anomalies" in report["errors"]
    assert any("common overlap" in error for error in report["errors"])


def test_declared_only_streams_do_not_masquerade_as_calibration_authority(tmp_path: Path):
    session, _, manifest, _, power = _configure_stage4_session(tmp_path)
    report = validate(manifest, session, power, CONTRACT)
    assert report["valid"] is True
    assert report["all_required_streams_calibrated_or_not_applicable"] is False
    assert report["sensor_calibration_authority"] is False
