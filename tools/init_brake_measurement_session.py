#!/usr/bin/env python3
"""Create a private Worcester X1 brake-interface measurement session."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_manifest(args) -> dict:
    return {
        "schema_version": 1,
        "scope": "unpowered_mechanical_brake_interface_measurement",
        "hardware_ids": {
            "truck_id": args.truck_id,
            "brake_kit_id": args.brake_kit_id,
            "hub_id": args.hub_id,
            "tire_id": args.tire_id,
            "tube_id": args.tube_id,
        },
        "vendor_refs": {
            "truck": "MBS Matrix III 400 mm brake-compatible reference",
            "brake": "MBS V5 / SKU 15006 reference",
            "hub": "MBS Rockstar II reference",
            "tire": "MBS T2 9 in reference",
        },
        "measurements_mm": {
            "rotor_outer_diameter": None,
            "rotor_inner_diameter": None,
            "rotor_thickness": None,
            "rotor_bolt_circle_diameter": None,
            "rotor_to_hub_axial_offset": None,
            "brake_arm_pivot_thread_major_diameter": None,
            "brake_arm_pivot_axis_to_axle_x": None,
            "brake_arm_pivot_axis_to_axle_z": None,
            "spring_pin_offset_x": None,
            "spring_pin_offset_z": None,
            "pad_radial_center": None,
            "released_arm_max_extent": None,
            "applied_arm_max_extent": None,
            "cable_min_bend_radius": None,
            "inflated_tire_max_diameter": None,
            "inflated_tire_max_width": None
        },
        "checks": {
            "exact_brake_revision_recorded": False,
            "truck_interface_verified": False,
            "hub_rotor_interface_verified": False,
            "released_wheel_spins_freely": False,
            "full_application_has_no_unintended_contact": False,
            "cable_clear_of_wheel_sweep": False,
            "static_brake_torque_measured": False,
            "unpowered_rolling_stop_passed": False,
            "post_test_fastener_inspection_passed": False
        },
        "static_brake_test": {
            "wheel_radius_m": None,
            "applied_tangential_force_n": None,
            "brake_torque_nm": None,
            "method_note": "Measure safely on an unpowered restrained fixture; do not infer torque from hand feel."
        },
        "authority": {
            "brake_interface_verified": False,
            "powered_operation_authorized": False
        }
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("session_dir", type=Path)
    p.add_argument("--truck-id", required=True)
    p.add_argument("--brake-kit-id", required=True)
    p.add_argument("--hub-id", required=True)
    p.add_argument("--tire-id", required=True)
    p.add_argument("--tube-id", required=True)
    args = p.parse_args()

    root = args.session_dir.resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"Refusing to overwrite nonempty session directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "brake_measurement_manifest.json").write_text(
        json.dumps(build_manifest(args), indent=2) + "\n", encoding="utf-8"
    )
    (root / "NOTES.md").write_text(
        "# Private X1 brake measurement notes\n\n"
        "Record direct caliper/gauge measurements; do not scale vendor photos.\n"
        "Keep the board unpowered for this authority.\n"
        "Record any shims/spacers/cable hardware actually installed.\n",
        encoding="utf-8",
    )
    print(root)


if __name__ == "__main__":
    main()
