#!/usr/bin/env python3
"""Generate a deterministic synthetic X1 telemetry session for tests/CI only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from tools.init_x1_telemetry_session import initialize

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads(
    (ROOT / "hardware/x1_telemetry_signal_registry.json").read_text()
)


def _stamp(doc: dict) -> dict:
    payload = json.dumps(
        doc,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    out = dict(doc)
    out["authority_fingerprint_sha256"] = hashlib.sha256(payload).hexdigest()
    return out


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _rows(stream_id: str, n: int = 41) -> list[dict]:
    rows: list[dict] = []
    for i in range(n):
        t = i * 0.05
        common = {"seq": i, "source_time_s": t, "session_time_s": t}
        if stream_id == "control":
            if t < 0.5:
                drive = 4.0
            elif t < 0.7:
                drive = max(0.0, 4.0 * (0.7 - t) / 0.2)
            else:
                drive = 0.0
            rows.append(
                {
                    **common,
                    "throttle_request": 0.3 if t < 0.5 else 0.0,
                    "brake_request": 0.0 if t < 1.0 else 0.4,
                    "ride_mode": "Shasta",
                    "remote_deadman_active": t < 0.5,
                    "remote_age_s": 0.01,
                    "left_drive_current_cmd_a": drive,
                    "right_drive_current_cmd_a": drive,
                    "left_regen_current_cmd_a": 0.0 if t < 1.0 else 1.0,
                    "right_regen_current_cmd_a": 0.0 if t < 1.0 else 1.0,
                    "control_fault_bits": 0,
                }
            )
        elif stream_id == "powertrain":
            rows.append(
                {
                    **common,
                    "pack_voltage_v": 50.4 - 0.2 * min(t, 2.0),
                    "battery_current_a": 3.0 if t < 1.0 else -1.0,
                    "left_phase_current_a": 4.0 if t < 1.0 else -1.5,
                    "right_phase_current_a": 4.0 if t < 1.0 else -1.5,
                    "left_motor_erpm": 1800.0
                    * max(0.0, 1.0 - max(0.0, t - 1.0)),
                    "right_motor_erpm": 1790.0
                    * max(0.0, 1.0 - max(0.0, t - 1.0)),
                    "left_motor_temperature_c": 30.0 + t,
                    "right_motor_temperature_c": 30.5 + t,
                    "left_controller_temperature_c": 31.0 + t,
                    "right_controller_temperature_c": 31.5 + t,
                    "pack_soc": 0.8,
                    "battery_temperature_c": 26.0,
                }
            )
        elif stream_id == "motion":
            speed = (
                2.0
                if t < 1.0
                else max(0.0, 2.0 * (1.8 - t) / 0.8)
            )
            accel = 0.0 if t < 1.0 else (-2.5 if t < 1.8 else 0.0)
            rows.append(
                {
                    **common,
                    "ground_speed_mps": speed,
                    "longitudinal_accel_mps2": accel,
                    "accel_y_mps2": 0.0,
                    "accel_z_mps2": 9.80665,
                    "gyro_roll_dps": 0.0,
                    "gyro_pitch_dps": 0.0,
                    "gyro_yaw_dps": 0.0,
                    "front_left_speed_mps": speed,
                    "front_right_speed_mps": speed,
                    "rear_left_speed_mps": speed,
                    "rear_right_speed_mps": speed,
                }
            )
        else:
            raise ValueError(f"unsupported synthetic stream: {stream_id}")
    return rows


def _events(stage_id: str) -> list[dict]:
    events = [
        {
            "seq": 0,
            "session_time_s": 0.0,
            "event_type": "SESSION_START",
            "source_id": "events-source",
            "payload": {},
        },
        {
            "seq": 1,
            "session_time_s": 0.05,
            "event_type": "STAGE_START",
            "source_id": "events-source",
            "payload": {"stage_id": stage_id},
        },
    ]
    if stage_id in {
        "RIDER_FREE_CONTROLLED_GROUND",
        "RIDER_ONLY_VERY_LOW_SPEED",
    }:
        events.append(
            {
                "seq": len(events),
                "session_time_s": 0.5,
                "event_type": "DEADMAN_RELEASE",
                "source_id": "control-source",
                "payload": {},
            }
        )
    if stage_id == "RIDER_ONLY_VERY_LOW_SPEED":
        events.append(
            {
                "seq": len(events),
                "session_time_s": 1.0,
                "event_type": "MECHANICAL_BRAKE_MARKER",
                "source_id": "events-source",
                "payload": {},
            }
        )
    events.append(
        {
            "seq": len(events),
            "session_time_s": 1.9,
            "event_type": "STAGE_STOP",
            "source_id": "events-source",
            "payload": {"stage_id": stage_id},
        }
    )
    events.append(
        {
            "seq": len(events),
            "session_time_s": 2.0,
            "event_type": "SESSION_STOP",
            "source_id": "events-source",
            "payload": {},
        }
    )
    return events


def generate(session_dir: Path, stage_id: str) -> dict:
    session_dir = session_dir.resolve()
    parent = session_dir.parent
    parent.mkdir(parents=True, exist_ok=True)

    power = _stamp(
        {
            "schema_version": 1,
            "authority": "x1_power_architecture",
            "qualified": True,
        }
    )
    health = _stamp(
        {
            "schema_version": 1,
            "authority": "x1_lifecycle_health_state",
            "valid": True,
            "board_id": "X1-SYNTHETIC",
            "current_configuration_id": "CFG-SYNTHETIC-A",
            "health_state": "READY_FOR_ALLOWED_ACTIVITY",
            "ready_for_allowed_activity": True,
            "latest_event_timestamp_utc": "2026-10-02T11:59:00Z",
            "powered_operation_authorized": False,
            "public_operation_authorized": False,
            "dog_accompanied_operation_authorized": False,
        }
    )

    tmp_power = parent / ".x1_synthetic_power.json"
    tmp_health = parent / ".x1_synthetic_health.json"
    tmp_power.write_text(json.dumps(power), encoding="utf-8")
    tmp_health.write_text(json.dumps(health), encoding="utf-8")
    try:
        initialize(
            session_dir,
            board_id="X1-SYNTHETIC",
            configuration_id="CFG-SYNTHETIC-A",
            stage_id=stage_id,
            started_at_utc="2026-10-02T12:00:00Z",
            power_architecture_path=tmp_power,
            pre_health_path=tmp_health,
        )
    finally:
        tmp_power.unlink(missing_ok=True)
        tmp_health.unlink(missing_ok=True)

    power_path = session_dir / "fixture_power_architecture.json"
    health_path = session_dir / "fixture_pre_health.json"
    power_path.write_text(json.dumps(power, indent=2) + "\n", encoding="utf-8")
    health_path.write_text(json.dumps(health, indent=2) + "\n", encoding="utf-8")

    manifest_path = session_dir / "telemetry_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["completed_at_utc"] = "2026-10-02T12:00:03Z"

    for clock in manifest["clocks"]:
        clock["synchronization_method"] = "synthetic_shared_monotonic_clock"
        clock["synchronization_uncertainty_s"] = 0.005
    for source in manifest["sources"]:
        source["qualification_status"] = "QUALIFIED"
        source["calibration_evidence_ref"] = (
            f"synthetic-calibration:{source['source_id']}"
        )

    for stream in manifest["streams"]:
        stream["nominal_rate_hz"] = 20.0
        stream["max_gap_s"] = 0.06
        stream["declared_dropped_samples"] = 0
        schema = REGISTRY["streams"][stream["stream_id"]]
        columns = [item["name"] for item in schema["required_columns"]]
        path = session_dir / stream["file_path"]
        _write_csv(path, columns, _rows(stream["stream_id"]))
        stream["sha256"] = _sha(path)

    event_path = session_dir / manifest["event_log"]["file_path"]
    event_path.write_text(
        "".join(json.dumps(event) + "\n" for event in _events(stage_id)),
        encoding="utf-8",
    )
    manifest["event_log"]["sha256"] = _sha(event_path)

    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "manifest": str(manifest_path),
        "power_architecture": str(power_path),
        "pre_health": str(health_path),
        "stage_id": stage_id,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir", type=Path)
    parser.add_argument(
        "--stage-id",
        default="RIDER_ONLY_VERY_LOW_SPEED",
        choices=(
            "SECURED_UNLOADED_SPIN",
            "RESTRAINED_LOADED_BENCH",
            "RIDER_FREE_CONTROLLED_GROUND",
            "RIDER_ONLY_VERY_LOW_SPEED",
        ),
    )
    args = parser.parse_args()
    print(json.dumps(generate(args.session_dir, args.stage_id), indent=2))


if __name__ == "__main__":
    main()
