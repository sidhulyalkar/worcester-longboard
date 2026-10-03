#!/usr/bin/env python3
"""Populate an initialized X1 telemetry workspace with deterministic synthetic data.

This is a CI/developer fixture only. It always marks the manifest
synthetic_fixture=true and is never eligible for physical commissioning.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGNALS = json.loads(
    (
        ROOT / "hardware/x1_telemetry_signal_registry_2026-10-02.json"
    ).read_text(encoding="utf-8")
)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def populate(workspace_dir: Path) -> dict:
    workspace_dir = workspace_dir.resolve()
    manifest_path = workspace_dir / "telemetry_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("sealed") is True:
        raise ValueError("cannot populate an already sealed telemetry session")

    definitions = {
        item["signal_id"]: item
        for item in SIGNALS["signals"]
    }
    manifest["synthetic_fixture"] = True

    times = [i / 10 for i in range(101)]
    for stream in manifest["streams"]:
        stream["source_device_id"] = f"synthetic-device-{stream['stream_id']}"
        stream["clock_id"] = f"synthetic-clock-{stream['stream_id']}"
        stream["nominal_rate_hz"] = 10.0
        stream["max_gap_s"] = 0.2
        stream["sync_model"] = {
            "method": "synthetic affine sync",
            "scale": 1.0,
            "offset_s": 0.0,
            "uncertainty_ms": 1.0,
            "evidence_ref": f"synthetic://sync/{stream['stream_id']}",
        }
        for signal in stream["signals"]:
            sid = signal["signal_id"]
            signal["source_id"] = f"synthetic-source-{sid}"
            kind = definitions[sid]["kind"]
            if kind.startswith("derived"):
                signal["derivation_id"] = f"synthetic-{sid}-v1"
            if kind == "calibrated_or_derived_motion":
                signal["calibration_id"] = f"synthetic-{sid}-frame"

        fieldnames = [
            stream["sequence_column"],
            stream["timestamp_column"],
            *[item["column"] for item in stream["signals"]],
        ]
        rows: list[dict] = []
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
                    value = (
                        3000.0
                        if t < 6.0
                        else max(0.0, 3000.0 * (8.0 - t) / 2.0)
                    )
                elif sid in {
                    "ground_speed_mps",
                    "front_left_wheel_speed_mps",
                    "front_right_wheel_speed_mps",
                }:
                    value = (
                        2.0
                        if t < 6.0
                        else max(0.0, 2.0 * (8.0 - t) / 2.0)
                    )
                elif sid == "longitudinal_accel_mps2":
                    value = -1.0 if 6.0 <= t < 8.0 else 0.0
                elif sid == "longitudinal_jerk_mps3":
                    value = (
                        -10.0
                        if math.isclose(t, 6.0)
                        else (10.0 if math.isclose(t, 8.0) else 0.0)
                    )
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
        _write_csv(workspace_dir / stream["file"], fieldnames, rows)

    event = manifest["event_log"]
    event["source_device_id"] = "synthetic-device-events"
    event["clock_id"] = "synthetic-clock-events"
    event["supported_event_types"] = [
        "SESSION_START",
        "SESSION_STOP",
        "STAGE_START",
        "STAGE_STOP",
        "DEADMAN_TRANSITION",
        "REMOTE_STALE",
        "FAULT_TRANSITION",
        "MECHANICAL_BRAKE_MARKER",
        "STOPPING_TEST_START",
        "OPERATOR_STOP",
        "ANOMALY",
    ]
    event["sync_model"] = {
        "method": "synthetic affine sync",
        "scale": 1.0,
        "offset_s": 0.0,
        "uncertainty_ms": 1.0,
        "evidence_ref": "synthetic://sync/events",
    }
    events = [
        {"seq":0,"timestamp":0.0,"event_type":"SESSION_START","source_id":"synthetic-logger","details":{}},
        {"seq":1,"timestamp":0.01,"event_type":"STAGE_START","source_id":"synthetic-logger","details":{"stage_id":manifest["commissioning_stage_id"]}},
        {"seq":2,"timestamp":4.0,"event_type":"DEADMAN_TRANSITION","source_id":"synthetic-controller","details":{"active":False}},
        {"seq":3,"timestamp":6.0,"event_type":"STOPPING_TEST_START","source_id":"synthetic-operator","details":{}},
        {"seq":4,"timestamp":9.9,"event_type":"STAGE_STOP","source_id":"synthetic-logger","details":{"stage_id":manifest["commissioning_stage_id"]}},
        {"seq":5,"timestamp":10.0,"event_type":"SESSION_STOP","source_id":"synthetic-logger","details":{}},
    ]
    (workspace_dir / event["file"]).write_text(
        "".join(
            json.dumps(item, separators=(",", ":")) + "\n"
            for item in events
        ),
        encoding="utf-8",
    )

    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "schema_version": 1,
        "scope": "x1_synthetic_telemetry_fixture",
        "session_id": manifest["session_id"],
        "synthetic_fixture": True,
        "physical_evidence_eligible": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(populate(args.workspace_dir), indent=2))


if __name__ == "__main__":
    main()
