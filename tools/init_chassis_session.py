#!/usr/bin/env python3
"""Initialize a private Worcester X1 donor/chassis qualification session."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOINT_CONTRACT = ROOT / "hardware" / "critical_joint_register_v1.json"

WHEEL_POSITIONS = ("fl", "fr", "rl", "rr")


def _joint_records() -> list[dict]:
    contract = json.loads(JOINT_CONTRACT.read_text(encoding="utf-8"))
    records: list[dict] = []
    for group in contract["required_joint_groups"]:
        records.append(
            {
                "id": group["id"],
                "hardware_description": "",
                "fastener_material_or_grade_if_known": None,
                "manufacturer_torque_nm": None,
                "torque_source": None,
                "assembly_state": "",
                "locking_method": "",
                "witness_method": "",
                "pre_test_inspection_passed": False,
                "post_test_inspection_passed": False,
                "movement_detected": None,
                "notes": "",
            }
        )
    return records


def build_manifest(args) -> dict:
    wheels = {
        pos: getattr(args, f"wheel_{pos}_id")
        for pos in WHEEL_POSITIONS
    }
    return {
        "schema_version": 1,
        "scope": "unpowered_rolling_chassis_physical_measurement",
        "issue": 12,
        "hardware_ids": {
            "donor_id": args.donor_id,
            "deck_id": args.deck_id,
            "front_truck_id": args.front_truck_id,
            "rear_truck_id": args.rear_truck_id,
            "wheels": wheels,
            "brake_id": args.brake_id,
        },
        "configuration": {
            "donor_family": "MBS Comp 95 / Matrix III 400 reference",
            "stock_8in_wheels_baseline": True,
            "axle_configuration": "50mm_stock_reference",
            "drivetrain_installed": False,
            "traction_battery_installed": False,
            "powered_test_performed": False,
        },
        "measurements_mm": {
            "deck_tip_to_tip": None,
            "deck_max_width": None,
            "axle_to_axle": None,
            "front_truck_total_width": None,
            "rear_truck_total_width": None,
            "static_ground_clearance_min": None,
            "loaded_ground_clearance_min": None,
            "wheel_diameter": {pos: None for pos in WHEEL_POSITIONS},
            "wheel_width": {pos: None for pos in WHEEL_POSITIONS},
            "wheel_axial_play": {pos: None for pos in WHEEL_POSITIONS},
        },
        "measurement_context": {
            "tire_pressure": {pos: None for pos in WHEEL_POSITIONS},
            "tire_pressure_unit": "psi",
            "loaded_clearance_test_mass_kg": None,
            "measurement_tools": [],
        },
        "stock_baseline": {
            "captured_before_x1_modification": False,
            "all_wheels_free_spin": False,
            "bearing_play_acceptable": False,
            "deck_inspection_passed": False,
            "truck_axle_hanger_inspection_passed": False,
            "steering_left_right_effort_reasonable": False,
            "return_to_center_passed": False,
            "walking_push_coast_passed": False,
            "jogging_push_coast_passed": False,
            "rough_surface_push_coast_passed": False,
            "post_baseline_inspection_passed": False,
        },
        "brake_installed_chassis": {
            "brake_authority_path": None,
            "full_steer_brake_clearance_passed": False,
            "full_lean_brake_clearance_passed": False,
            "brake_cable_clear_of_wheel_sweep": False,
            "brake_cable_clear_of_service_paths": False,
            "rough_surface_push_coast_passed": False,
            "wheel_tube_service_dry_run_passed": False,
            "service_did_not_require_unrelated_safety_disassembly": False,
            "post_test_deck_truck_wheel_brake_inspection_passed": False,
        },
        "retention": {
            "contract": "hardware/critical_joint_register_v1.json",
            "joints": _joint_records(),
        },
        "notes": [],
    }


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("session_dir", type=Path)
    p.add_argument("--donor-id", required=True)
    p.add_argument("--deck-id", required=True)
    p.add_argument("--front-truck-id", required=True)
    p.add_argument("--rear-truck-id", required=True)
    for pos in WHEEL_POSITIONS:
        p.add_argument(f"--wheel-{pos}-id", required=True)
    p.add_argument("--brake-id")
    return p


def main() -> None:
    args = _parser().parse_args()
    root = args.session_dir.resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"Refusing to overwrite nonempty session directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(args)
    (root / "chassis_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (root / "NOTES.md").write_text(
        "# Private X1 physical chassis session\n\n"
        "Preserve the received donor as the baseline before adding X1 variables.\n"
        "Record measured values, not catalog values. Record tire pressure for every wheel.\n"
        "Do not invent torque values: leave manufacturer_torque_nm null unless a cited manufacturer source exists.\n"
        "Any moved witness mark is a failed retention event until its cause is understood.\n\n"
        "## Required sequence\n\n"
        "1. Assign hardware IDs and photograph the received condition.\n"
        "2. Measure the untouched stock donor.\n"
        "3. Perform stock free-spin, steering, push/coast and post-test inspection.\n"
        "4. Install/qualify the V5 separately through Issue #14.\n"
        "5. Link the resulting brake authority report in brake_installed_chassis.brake_authority_path.\n"
        "6. Apply witness marks or equivalent inspection to every required critical joint.\n"
        "7. Perform full steer/lean, rough-surface and wheel/tube service tests.\n"
        "8. Run tools/qualify_rolling_chassis.py only after all physical evidence is complete.\n",
        encoding="utf-8",
    )
    print(root)


if __name__ == "__main__":
    main()
