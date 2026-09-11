#!/usr/bin/env python3
"""Qualify the unpowered X1 mechanical-brake measurement authority."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REQUIRED_MEASUREMENTS = (
    "rotor_outer_diameter", "rotor_inner_diameter", "rotor_thickness",
    "rotor_bolt_circle_diameter", "rotor_to_hub_axial_offset",
    "brake_arm_pivot_thread_major_diameter", "brake_arm_pivot_axis_to_axle_x",
    "brake_arm_pivot_axis_to_axle_z", "spring_pin_offset_x", "spring_pin_offset_z",
    "pad_radial_center", "released_arm_max_extent", "applied_arm_max_extent",
    "cable_min_bend_radius", "inflated_tire_max_diameter", "inflated_tire_max_width"
)
REQUIRED_CHECKS = (
    "exact_brake_revision_recorded", "truck_interface_verified",
    "hub_rotor_interface_verified", "released_wheel_spins_freely",
    "full_application_has_no_unintended_contact", "cable_clear_of_wheel_sweep",
    "static_brake_torque_measured", "unpowered_rolling_stop_passed",
    "post_test_fastener_inspection_passed"
)


def qualify(data: dict) -> dict:
    errors: list[str] = []
    if data.get("scope") != "unpowered_mechanical_brake_interface_measurement":
        errors.append("wrong measurement scope")

    measurements = data.get("measurements_mm", {})
    for key in REQUIRED_MEASUREMENTS:
        value = measurements.get(key)
        if value is None:
            errors.append(f"missing measurement: {key}")
        elif not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) <= 0:
            errors.append(f"invalid measurement: {key}")

    checks = data.get("checks", {})
    for key in REQUIRED_CHECKS:
        if checks.get(key) is not True:
            errors.append(f"check not passed: {key}")

    torque = data.get("static_brake_test", {})
    r = torque.get("wheel_radius_m")
    f = torque.get("applied_tangential_force_n")
    measured_torque = torque.get("brake_torque_nm")
    if not all(isinstance(x, (int, float)) and x > 0 for x in (r, f, measured_torque)):
        errors.append("static brake torque evidence incomplete")
    elif abs(float(r) * float(f) - float(measured_torque)) > max(0.5, 0.05 * float(measured_torque)):
        errors.append("static brake torque inconsistent with radius × tangential force")

    incoming_authority = data.get("authority", {})
    if incoming_authority.get("powered_operation_authorized") is True:
        errors.append("brake qualification cannot authorize powered operation")

    return {
        "schema_version": 1,
        "qualified": not errors,
        "errors": errors,
        "brake_interface_verified": not errors,
        "powered_operation_authorized": False,
        "hardware_ids": data.get("hardware_ids", {}),
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: qualify_brake_interface.py manifest.json [out.json]")
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    report = qualify(json.loads(src.read_text(encoding="utf-8")))
    text = json.dumps(report, indent=2) + "\n"
    if out:
        out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["qualified"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
