#!/usr/bin/env python3
"""Qualify the unpowered X1 mechanical-brake measurement authority."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

POSITIVE_MEASUREMENTS = (
    "rotor_outer_diameter", "rotor_inner_diameter", "rotor_thickness",
    "rotor_bolt_circle_diameter", "brake_arm_pivot_thread_major_diameter",
    "pad_radial_center", "released_arm_max_extent", "applied_arm_max_extent",
    "cable_min_bend_radius", "inflated_tire_max_diameter", "inflated_tire_max_width"
)
SIGNED_DATUM_MEASUREMENTS = (
    "rotor_to_hub_axial_offset", "brake_arm_pivot_axis_to_axle_x",
    "brake_arm_pivot_axis_to_axle_z", "spring_pin_offset_x", "spring_pin_offset_z"
)
REQUIRED_CHECKS = (
    "exact_brake_revision_recorded", "truck_interface_verified",
    "hub_rotor_interface_verified", "released_wheel_spins_freely",
    "full_application_has_no_unintended_contact", "cable_clear_of_wheel_sweep",
    "static_brake_torque_measured", "unpowered_rolling_stop_passed",
    "post_test_fastener_inspection_passed"
)


def _finite_number(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def qualify(data: dict) -> dict:
    errors: list[str] = []
    if data.get("scope") != "unpowered_mechanical_brake_interface_measurement":
        errors.append("wrong measurement scope")

    measurements = data.get("measurements_mm", {})
    for key in POSITIVE_MEASUREMENTS:
        value = measurements.get(key)
        if value is None:
            errors.append(f"missing measurement: {key}")
        elif not _finite_number(value) or float(value) <= 0:
            errors.append(f"invalid positive measurement: {key}")
    for key in SIGNED_DATUM_MEASUREMENTS:
        value = measurements.get(key)
        if value is None:
            errors.append(f"missing measurement: {key}")
        elif not _finite_number(value):
            errors.append(f"invalid signed datum: {key}")

    rotor_od = measurements.get("rotor_outer_diameter")
    rotor_id = measurements.get("rotor_inner_diameter")
    rotor_bcd = measurements.get("rotor_bolt_circle_diameter")
    tire_od = measurements.get("inflated_tire_max_diameter")
    if all(_finite_number(x) for x in (rotor_od, rotor_id)) and float(rotor_od) <= float(rotor_id):
        errors.append("rotor outer diameter must exceed inner diameter")
    if all(_finite_number(x) for x in (rotor_od, rotor_bcd)) and float(rotor_bcd) >= float(rotor_od):
        errors.append("rotor bolt circle must lie inside rotor outer diameter")
    if all(_finite_number(x) for x in (rotor_od, tire_od)) and float(rotor_od) >= float(tire_od):
        errors.append("rotor outer diameter must fit inside inflated tire diameter")

    checks = data.get("checks", {})
    for key in REQUIRED_CHECKS:
        if checks.get(key) is not True:
            errors.append(f"check not passed: {key}")

    torque = data.get("static_brake_test", {})
    r = torque.get("wheel_radius_m")
    f = torque.get("applied_tangential_force_n")
    measured_torque = torque.get("brake_torque_nm")
    if not all(_finite_number(x) and float(x) > 0 for x in (r, f, measured_torque)):
        errors.append("static brake torque evidence incomplete")
    else:
        if abs(float(r) * float(f) - float(measured_torque)) > max(0.5, 0.05 * float(measured_torque)):
            errors.append("static brake torque inconsistent with radius × tangential force")
        if _finite_number(tire_od):
            expected_r = float(tire_od) / 2000.0
            if abs(float(r) - expected_r) > max(0.002, 0.02 * expected_r):
                errors.append("static brake wheel radius inconsistent with measured inflated tire diameter")

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
