#!/usr/bin/env python3
"""Qualify Worcester X1 unpowered rolling-chassis physical evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOINT_CONTRACT = ROOT / "hardware" / "critical_joint_register_v1.json"
WHEEL_POSITIONS = ("fl", "fr", "rl", "rr")


def _canonical_digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _valid_authority_fingerprint(data: dict) -> bool:
    fingerprint = data.get("authority_fingerprint_sha256")
    if not isinstance(fingerprint, str) or not fingerprint:
        return False
    unsigned = dict(data)
    unsigned.pop("authority_fingerprint_sha256", None)
    try:
        return fingerprint == _canonical_digest(unsigned)
    except (TypeError, ValueError):
        return False


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _positive(value: Any) -> bool:
    return _finite(value) and float(value) > 0


def _require_true(errors: list[str], data: dict, keys: tuple[str, ...], prefix: str) -> None:
    for key in keys:
        if data.get(key) is not True:
            errors.append(f"{prefix}.{key} not passed")


def _validate_brake_authority(errors: list[str], brake: dict) -> None:
    if brake.get("authority") != "x1_mechanical_brake_interface":
        errors.append("linked brake authority has wrong authority type")
    if brake.get("qualified") is not True or brake.get("brake_interface_verified") is not True:
        errors.append("linked brake authority is not qualified")
    if brake.get("powered_operation_authorized") is not False:
        errors.append("linked brake authority violates powered-operation boundary")
    if not _valid_authority_fingerprint(brake):
        errors.append("linked brake authority fingerprint is invalid")


def qualify(data: dict, brake: dict, joint_contract: dict) -> dict:
    errors: list[str] = []

    if data.get("schema_version") != 1:
        errors.append("chassis manifest schema_version must be 1")
    if data.get("scope") != "unpowered_rolling_chassis_physical_measurement":
        errors.append("wrong chassis measurement scope")
    if data.get("issue") != 12:
        errors.append("chassis manifest must identify Issue #12")

    hardware = data.get("hardware_ids", {})
    for key in ("donor_id", "deck_id", "front_truck_id", "rear_truck_id", "brake_id"):
        if not isinstance(hardware.get(key), str) or not hardware[key].strip():
            errors.append(f"missing hardware id: {key}")
    wheels = hardware.get("wheels", {})
    for pos in WHEEL_POSITIONS:
        if not isinstance(wheels.get(pos), str) or not wheels[pos].strip():
            errors.append(f"missing wheel hardware id: {pos}")
    if len({wheels.get(pos) for pos in WHEEL_POSITIONS}) != 4:
        errors.append("wheel hardware IDs must be unique")

    config = data.get("configuration", {})
    if config.get("stock_8in_wheels_baseline") is not True:
        errors.append("stock 8-inch wheel baseline not preserved")
    if config.get("axle_configuration") != "50mm_stock_reference":
        errors.append("Issue #12 baseline must remain on stock 50 mm axle reference")
    for key in ("drivetrain_installed", "traction_battery_installed", "powered_test_performed"):
        if config.get(key) is not False:
            errors.append(f"{key} must remain false in unpowered chassis qualification")

    measurements = data.get("measurements_mm", {})
    scalar_bounds = {
        "deck_tip_to_tip": (800.0, 1200.0),
        "deck_max_width": (180.0, 350.0),
        "axle_to_axle": (700.0, 1100.0),
        "front_truck_total_width": (300.0, 500.0),
        "rear_truck_total_width": (300.0, 500.0),
        "static_ground_clearance_min": (1.0, 250.0),
        "loaded_ground_clearance_min": (1.0, 250.0),
    }
    for key, (low, high) in scalar_bounds.items():
        value = measurements.get(key)
        if not _finite(value) or not low <= float(value) <= high:
            errors.append(f"invalid measured chassis value: {key}")

    static_clearance = measurements.get("static_ground_clearance_min")
    loaded_clearance = measurements.get("loaded_ground_clearance_min")
    if _finite(static_clearance) and _finite(loaded_clearance):
        if float(loaded_clearance) > float(static_clearance) + 2.0:
            errors.append("loaded minimum clearance is implausibly above static minimum clearance")

    for field, bounds in (("wheel_diameter", (150.0, 280.0)), ("wheel_width", (30.0, 100.0))):
        values = measurements.get(field, {})
        for pos in WHEEL_POSITIONS:
            value = values.get(pos)
            if not _finite(value) or not bounds[0] <= float(value) <= bounds[1]:
                errors.append(f"invalid {field}.{pos}")

    axial_play = measurements.get("wheel_axial_play", {})
    for pos in WHEEL_POSITIONS:
        value = axial_play.get(pos)
        if not _finite(value) or float(value) < 0 or float(value) > 5.0:
            errors.append(f"invalid wheel_axial_play.{pos}")

    context = data.get("measurement_context", {})
    pressures = context.get("tire_pressure", {})
    for pos in WHEEL_POSITIONS:
        if not _positive(pressures.get(pos)):
            errors.append(f"missing/invalid tire pressure: {pos}")
    if context.get("tire_pressure_unit") not in {"psi", "kPa"}:
        errors.append("tire pressure unit must be psi or kPa")
    if not _positive(context.get("loaded_clearance_test_mass_kg")):
        errors.append("loaded clearance test mass must be recorded")
    if not isinstance(context.get("measurement_tools"), list) or not context["measurement_tools"]:
        errors.append("measurement tools must be recorded")

    _require_true(
        errors,
        data.get("stock_baseline", {}),
        (
            "captured_before_x1_modification",
            "all_wheels_free_spin",
            "bearing_play_acceptable",
            "deck_inspection_passed",
            "truck_axle_hanger_inspection_passed",
            "steering_left_right_effort_reasonable",
            "return_to_center_passed",
            "walking_push_coast_passed",
            "jogging_push_coast_passed",
            "rough_surface_push_coast_passed",
            "post_baseline_inspection_passed",
        ),
        "stock_baseline",
    )
    _require_true(
        errors,
        data.get("brake_installed_chassis", {}),
        (
            "full_steer_brake_clearance_passed",
            "full_lean_brake_clearance_passed",
            "brake_cable_clear_of_wheel_sweep",
            "brake_cable_clear_of_service_paths",
            "rough_surface_push_coast_passed",
            "wheel_tube_service_dry_run_passed",
            "service_did_not_require_unrelated_safety_disassembly",
            "post_test_deck_truck_wheel_brake_inspection_passed",
        ),
        "brake_installed_chassis",
    )

    if joint_contract.get("schema_version") != 1:
        errors.append("critical joint contract schema_version must be 1")
    required_joint_ids = {
        row.get("id") for row in joint_contract.get("required_joint_groups", []) if row.get("id")
    }
    records = data.get("retention", {}).get("joints", [])
    record_map = {row.get("id"): row for row in records if isinstance(row, dict) and row.get("id")}
    missing_joints = sorted(required_joint_ids - set(record_map))
    if missing_joints:
        errors.append("missing critical joint records: " + ", ".join(missing_joints))
    extras = sorted(set(record_map) - required_joint_ids)
    if extras:
        errors.append("unknown critical joint records: " + ", ".join(extras))

    for joint_id in sorted(required_joint_ids & set(record_map)):
        row = record_map[joint_id]
        for field in ("hardware_description", "assembly_state", "locking_method", "witness_method"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f"{joint_id}: missing {field}")
        if row.get("pre_test_inspection_passed") is not True:
            errors.append(f"{joint_id}: pre-test inspection not passed")
        if row.get("post_test_inspection_passed") is not True:
            errors.append(f"{joint_id}: post-test inspection not passed")
        if row.get("movement_detected") is not False:
            errors.append(f"{joint_id}: retention movement detected or not assessed")
        torque = row.get("manufacturer_torque_nm")
        source = row.get("torque_source")
        if torque is not None:
            if not _positive(torque):
                errors.append(f"{joint_id}: invalid manufacturer torque")
            if not isinstance(source, str) or not source.strip():
                errors.append(f"{joint_id}: manufacturer torque lacks source")
        elif source not in (None, ""):
            errors.append(f"{joint_id}: torque source present without torque value")

    _validate_brake_authority(errors, brake)

    report = {
        "schema_version": 1,
        "authority": "x1_rolling_chassis_physical",
        "scope": "unpowered_rolling_chassis_only",
        "qualified": not errors,
        "errors": errors,
        "powered_operation_authorized": False,
        "hardware_ids": hardware,
        "measured_summary_mm": {
            "deck_tip_to_tip": measurements.get("deck_tip_to_tip"),
            "deck_max_width": measurements.get("deck_max_width"),
            "axle_to_axle": measurements.get("axle_to_axle"),
            "static_ground_clearance_min": measurements.get("static_ground_clearance_min"),
            "loaded_ground_clearance_min": measurements.get("loaded_ground_clearance_min"),
        },
        "retention_joint_count": len(required_joint_ids),
        "brake_authority_fingerprint_sha256": brake.get("authority_fingerprint_sha256"),
    }
    report["authority_fingerprint_sha256"] = _canonical_digest(report)
    return report


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("--brake-authority", type=Path, required=True)
    p.add_argument("--joint-contract", type=Path, default=DEFAULT_JOINT_CONTRACT)
    p.add_argument("--out", type=Path)
    return p


def main() -> None:
    args = _parser().parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    brake = json.loads(args.brake_authority.read_text(encoding="utf-8"))
    joints = json.loads(args.joint_contract.read_text(encoding="utf-8"))
    report = qualify(data, brake, joints)
    report["source_provenance"] = {
        "manifest_sha256": _file_digest(args.manifest),
        "brake_authority_sha256": _file_digest(args.brake_authority),
        "joint_contract_sha256": _file_digest(args.joint_contract),
    }
    unsigned = dict(report)
    unsigned.pop("authority_fingerprint_sha256", None)
    report["authority_fingerprint_sha256"] = _canonical_digest(unsigned)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["qualified"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
