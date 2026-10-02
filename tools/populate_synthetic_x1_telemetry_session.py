#!/usr/bin/env python3
"""Populate an X1 telemetry workspace with deterministic synthetic test data.

This is CI/test-fixture tooling only. The generated data is not physical
commissioning evidence.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "hardware/rev_c_telemetry_evidence_snapshot_2026-10-01.json"
REGISTRY = ROOT / "hardware/x1_telemetry_signal_registry.json"

SOURCE_BY_FAMILY = {
    "motion": "EXTERNAL_GROUND_TRUTH",
    "imu": "IMU_LOCAL",
    "energy": "BMS_OR_PACK_TELEMETRY",
    "thermal": "VESC_CAN_LEFT",
    "drive": "VESC_CAN_LEFT",
    "remote": "REMOTE_INPUT",
    "control": "ECU_LOCAL",
    "fault": "ECU_LOCAL",
    "logger": "ECU_LOCAL",
    "lifecycle": "DERIVED",
}


def _value(signal_id: str, t_s: float) -> float:
    if signal_id == "pack_voltage_v":
        return 60.0 - 0.02 * t_s
    if signal_id == "battery_current_a":
        return 2.0 + 0.2 * math.sin(t_s * 2.0)
    if signal_id.endswith("_temperature_c"):
        return 30.0 + 0.1 * t_s
    if signal_id.endswith("_erpm"):
        return 1500.0 + 25.0 * math.sin(t_s * 3.0)
    if signal_id.endswith("_phase_current_a"):
        return 4.0 + 0.3 * math.sin(t_s * 4.0)
    if signal_id.endswith("_wheel_speed_mps") or signal_id == "ground_speed_mps":
        return 1.0 + 0.05 * math.sin(t_s * 2.0)
    if signal_id == "longitudinal_accel_mps2":
        return 0.15 * math.sin(t_s * 2.0)
    if signal_id == "longitudinal_jerk_mps3":
        return 0.30 * math.cos(t_s * 2.0)
    if signal_id == "remote_deadman_active":
        return 1.0
    if signal_id == "remote_age_s":
        return 0.01
    if signal_id.startswith("commanded_drive_current"):
        return 2.0
    if signal_id.startswith("slip_"):
        return 0.02
    if signal_id == "control_fault_bits":
        return 0.0
    return 0.0


def populate(session_dir: Path, duration_s: float = 2.0) -> dict:
    session_dir = session_dir.resolve()
    manifest_path = session_dir / "telemetry_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    signal_defs = {item["id"]: item for item in registry["signals"]}

    stage_id = manifest["commissioning_stage_id"]
    stage = snapshot["stage_requirements"][stage_id]
    if duration_s <= 0:
        raise ValueError("duration_s must be positive")

    manifest["started_at_utc"] = "2026-10-01T12:00:00Z"
    manifest["completed_at_utc"] = "2026-10-01T12:00:05Z"
    manifest["logger_identity"][
        "real_time_control_task_separate_from_storage_task"
    ] = True
    manifest["logger_identity"]["bounded_nonblocking_enqueue_design"] = True
    manifest["fault_edge_logging_enabled"] = True
    manifest["stage_marker_recorded"] = True

    channels = []
    records = []
    for signal_id, hz in stage["required_signals_hz"].items():
        definition = signal_defs[signal_id]
        source_kind = SOURCE_BY_FAMILY.get(definition["family"], "ECU_LOCAL")
        if signal_id in {
            "right_motor_erpm",
            "right_phase_current_a",
            "right_motor_temperature_c",
            "right_controller_temperature_c",
        }:
            source_kind = "VESC_CAN_RIGHT"
        if signal_id == "front_left_wheel_speed_mps":
            source_kind = "FRONT_WHEEL_SENSOR_LEFT"
        if signal_id == "front_right_wheel_speed_mps":
            source_kind = "FRONT_WHEEL_SENSOR_RIGHT"
        if signal_id in {"ground_speed_mps"}:
            source_kind = "EXTERNAL_GROUND_TRUTH"
        if signal_id in {"longitudinal_jerk_mps3"}:
            source_kind = "DERIVED"

        channels.append(
            {
                "signal_id": signal_id,
                "source_kind": source_kind,
                "source_id": f"SYNTH-{signal_id}",
                "expected_hz": hz,
                "max_source_age_us": int(round(1_000_000.0 / hz)),
                "derivation_method_reference": (
                    "synthetic-ci-derived-method-v1"
                    if source_kind == "DERIVED"
                    else ""
                ),
                "frame_or_sign_convention": "synthetic-ci-convention-v1",
                "enabled": True,
            }
        )

        count = int(round(duration_s * hz)) + 1
        period_us = 1_000_000.0 / hz
        for index in range(count):
            mono_us = int(round(index * period_us))
            t_s = mono_us / 1_000_000.0
            records.append(
                {
                    "mono_us": mono_us,
                    "signal_id": signal_id,
                    "value": _value(signal_id, t_s),
                    "source_age_us": 0,
                    "quality": "OK",
                }
            )

    records.sort(key=lambda item: (item["mono_us"], item["signal_id"]))
    with (session_dir / manifest["files"]["telemetry_csv"]).open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=snapshot["record_format"]["telemetry_csv_columns"],
        )
        writer.writeheader()
        for seq, item in enumerate(records):
            writer.writerow({"record_seq": seq, **item})

    final_mono = max(item["mono_us"] for item in records)
    events = [
        {
            "event_seq": 0,
            "mono_us": 0,
            "event_type": "SESSION_START",
            "code": "START",
            "fault_bits": 0,
            "details": {"synthetic": True},
        },
        {
            "event_seq": 1,
            "mono_us": 1,
            "event_type": "STAGE_MARKER",
            "code": stage_id,
            "fault_bits": 0,
            "details": {"synthetic": True},
        },
        {
            "event_seq": 2,
            "mono_us": final_mono,
            "event_type": "SESSION_END",
            "code": "END",
            "fault_bits": 0,
            "details": {"synthetic": True},
        },
    ]
    with (session_dir / manifest["files"]["events_jsonl"]).open(
        "w", encoding="utf-8"
    ) as handle:
        for event in events:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    metrics = []
    for metric_id in stage.get("required_metrics", []):
        if metric_id == "remote_release_propulsion_decay_s":
            value, unit = 0.12, "s"
            sources = [
                "remote_deadman_active",
                "commanded_drive_current_l_a",
                "commanded_drive_current_r_a",
            ]
        elif metric_id == "stopping_distance_m":
            value, unit = 0.75, "m"
            sources = ["ground_speed_mps", "longitudinal_accel_mps2"]
        else:
            raise ValueError(f"no synthetic metric fixture for {metric_id}")
        metrics.append(
            {
                "metric_id": metric_id,
                "value": value,
                "unit": unit,
                "start_mono_us": 0,
                "end_mono_us": final_mono,
                "method_reference": "synthetic-ci-metric-method-v1",
                "source_signal_ids": sources,
            }
        )
    (session_dir / manifest["files"]["metrics_json"]).write_text(
        json.dumps(metrics, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest["declared_channels"] = channels
    manifest["session_summary"].update(
        {
            "expected_records": len(records),
            "reported_dropped_records": 0,
            "persistent_write_error_count": 0,
            "unclean_shutdown": False,
        }
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "schema_version": 1,
        "scope": "x1_synthetic_telemetry_fixture",
        "physical_authority": False,
        "record_count": len(records),
        "stage_id": stage_id,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir", type=Path)
    parser.add_argument("--duration-s", type=float, default=2.0)
    args = parser.parse_args()
    print(json.dumps(populate(args.session_dir, args.duration_s), indent=2))


if __name__ == "__main__":
    main()
