#!/usr/bin/env python3
"""Qualify inert Worcester X1 trail-armor geometry and low-energy behavior.

This qualifier never certifies powered impact survivability. It only checks the
declared inert armor geometry, service path, retention evidence, and repeated
low-energy surrogate contacts.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

REQUIRED_GEOMETRY = (
    "wear_shoe_is_intended_first_hard_contact",
    "vulnerable_component_not_lowest_exposed_hard_point",
    "full_steer_clearance_verified",
    "full_lean_clearance_verified",
    "deck_flex_clearance_verified",
    "wheel_and_tire_sweep_clear",
    "brake_hardware_and_cable_clear",
    "harness_and_connector_clear",
    "no_forward_facing_terrain_hook",
    "debris_escape_path_present",
    "no_exposed_sharp_edge_toward_rider_or_harness",
    "wear_hardware_not_intended_as_terrain_contact",
)

REQUIRED_SERVICE = (
    "wear_part_individually_replaceable",
    "replacement_does_not_open_traction_enclosure",
    "replacement_does_not_disturb_brake_critical_joint",
    "wheel_tube_service_preserved",
    "drivetrain_service_preserved",
)

REQUIRED_POST_FALSE = (
    "structural_mount_damage",
    "protected_component_damage",
    "new_crack_or_permanent_deformation",
    "retention_or_witness_movement",
    "loose_or_missing_hardware",
    "new_wheel_brake_steering_interference",
)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _positive_finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0
    )


def qualify(data: dict) -> dict:
    errors: list[str] = []

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("scope") != "rev_c_inert_trail_armor_trial":
        errors.append("wrong trail-armor trial scope")

    for key in (
        "session_id",
        "protected_zone_id",
        "armor_architecture",
        "wear_shoe_id",
        "carrier_or_vendor_guard_id",
        "structural_mount_id",
        "protected_inert_component_id",
    ):
        if not _nonempty(data.get(key)):
            errors.append(f"{key} must be a nonempty string")

    for key in (
        "live_battery_present",
        "electrical_energy_present",
        "powered_vehicle",
        "impact_energy_qualified",
        "procurement_authority",
        "powered_operation_authorized",
    ):
        if data.get(key) is not False:
            errors.append(f"{key} must be false")

    geometry = data.get("geometry_checks")
    if not isinstance(geometry, dict):
        errors.append("geometry_checks must be an object")
    else:
        for key in REQUIRED_GEOMETRY:
            if geometry.get(key) is not True:
                errors.append(f"geometry_checks.{key} must be true")

    load = data.get("load_path")
    if not isinstance(load, dict):
        errors.append("load_path must be an object")
    else:
        if load.get("type") not in {
            "separate_sacrificial_skid",
            "vendor_integrated_replaceable_guard",
        }:
            errors.append("load_path.type must name a supported armor load path")
        if not _nonempty(load.get("description")):
            errors.append("load_path.description must be nonempty")
        for key in (
            "battery_shell_is_primary_impact_structure",
            "electrical_connector_is_structural_member",
            "adhesive_only_retention",
        ):
            if load.get(key) is not False:
                errors.append(f"load_path.{key} must be false")
        for key in (
            "structural_mount_retention_inspectable",
            "witness_or_migration_check_present",
            "no_unqualified_safety_critical_adapter",
        ):
            if load.get(key) is not True:
                errors.append(f"load_path.{key} must be true")

    service = data.get("service_checks")
    if not isinstance(service, dict):
        errors.append("service_checks must be an object")
    else:
        for key in REQUIRED_SERVICE:
            if service.get(key) is not True:
                errors.append(f"service_checks.{key} must be true")
        if not _nonempty(service.get("replacement_method")):
            errors.append("service_checks.replacement_method must be nonempty")
        if not _positive_finite(service.get("replacement_time_minutes")):
            errors.append(
                "service_checks.replacement_time_minutes must be positive"
            )

    trials = data.get("low_energy_surrogate_trials")
    if not isinstance(trials, list) or len(trials) < 3:
        errors.append("at least three low-energy surrogate trials are required")
        trials = []

    ids: set[str] = set()
    for index, trial in enumerate(trials):
        if not isinstance(trial, dict):
            errors.append(f"trial {index} must be an object")
            continue
        trial_id = trial.get("id")
        if not _nonempty(trial_id):
            errors.append(f"trial {index} requires a nonempty id")
        elif trial_id in ids:
            errors.append(f"duplicate trial id: {trial_id}")
        else:
            ids.add(trial_id)

        for key in ("surrogate_description", "contact_direction"):
            if not _nonempty(trial.get(key)):
                errors.append(f"{trial_id or index}: {key} must be nonempty")
        if not _positive_finite(trial.get("measured_entry_speed_mps")):
            errors.append(
                f"{trial_id or index}: measured_entry_speed_mps must be positive"
            )
        for key in (
            "intended_wear_surface_contacted_first",
            "armor_slid_or_deflected_over_surrogate_without_hooking",
        ):
            if trial.get(key) is not True:
                errors.append(f"{trial_id or index}: {key} must be true")
        for key in (
            "protected_component_contacted",
            "wheel_brake_or_steering_interference",
            "armor_or_fastener_became_loose",
        ):
            if trial.get(key) is not False:
                errors.append(f"{trial_id or index}: {key} must be false")

    post = data.get("post_trial_inspection")
    if not isinstance(post, dict):
        errors.append("post_trial_inspection must be an object")
    else:
        for key in REQUIRED_POST_FALSE:
            if post.get(key) is not False:
                errors.append(f"post_trial_inspection.{key} must be false")
        if post.get("wear_part_condition_recorded") is not True:
            errors.append(
                "post_trial_inspection.wear_part_condition_recorded must be true"
            )

    qualified = not errors
    return {
        "schema_version": 1,
        "authority": "x1_rev_c_inert_trail_armor_geometry_service",
        "qualified": qualified,
        "errors": errors,
        "session_id": data.get("session_id"),
        "protected_zone_id": data.get("protected_zone_id"),
        "inert_geometry_service_qualified": qualified,
        "impact_energy_qualified": False,
        "live_battery_test_authorized": False,
        "procurement_authority": False,
        "powered_operation_authorized": False,
        "interpretation_boundary": (
            "A passing report validates only the declared inert geometry, service, "
            "retention, and low-energy surrogate-contact checks. It does not certify "
            "impact energy, powered trail survivability, battery safety, or vehicle "
            "operation."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = qualify(json.loads(args.manifest.read_text(encoding="utf-8")))
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["qualified"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
