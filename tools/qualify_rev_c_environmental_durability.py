#!/usr/bin/env python3
"""Qualify Worcester X1 inert environmental durability evidence.

This qualifier validates only the declared inert enclosure/interface/service
behavior. It does not establish an IP rating, waterproof claim, corrosion life,
energized wet-operation authority, or powered riding authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

EXPOSURE_TYPES = {"dry_grit", "splash", "mud_surrogate"}

INTERFACE_TEXT = (
    "id",
    "function",
    "exposure_location",
    "protection_method",
    "drainage_or_shedding_method",
    "inspection_method",
    "service_method",
)

INTERFACE_TRUE = (
    "external_protection_inspectable_without_breaking_primary_seal",
    "strain_relief_or_not_applicable",
    "direct_spray_orientation_or_shielding_checked",
)

CYCLE_TRUE = (
    "drainage_or_shedding_path_functional",
    "steering_brake_wheel_motion_free",
    "service_access_preserved",
)

CYCLE_FALSE = (
    "protected_zone_ingress_observed",
    "seal_or_gasket_displaced",
    "harness_or_hose_chafe_created",
    "contamination_trapped_against_protected_component",
)

CONNECTOR_TRUE = (
    "fully_reseated_after_service",
    "positive_latch_or_retention_verified",
)

CONNECTOR_FALSE = (
    "energized",
    "contamination_beyond_intended_seal_observed",
    "pin_or_contact_damage_observed",
    "seal_damage_or_displacement_observed",
    "cable_used_as_disconnect_handle",
)

RECOVERY_TRUE = (
    "wheel_free_spin_after_cleaning",
    "tire_valve_access_preserved",
    "brake_releases_without_drag",
    "brake_actuation_normal",
    "steering_returns_freely",
    "service_completed_without_opening_traction_enclosure",
)

RECOVERY_FALSE = (
    "bearing_play_increase_observed",
    "brake_friction_surface_contaminated",
)

POST_TRUE = (
    "drainage_paths_clear",
    "hidden_zone_witness_dry",
    "contamination_guard_reusable_or_replaced",
)

POST_FALSE = (
    "visible_retained_moisture",
    "corrosion_observed",
    "fretting_or_contact_discoloration_observed",
    "harness_chafe_observed",
    "fastener_or_witness_migration_observed",
    "enclosure_crack_or_seal_damage_observed",
)


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _valid_fp(data: dict) -> bool:
    actual = data.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        return False
    unsigned = dict(data)
    unsigned.pop("authority_fingerprint_sha256", None)
    try:
        return actual == _digest(unsigned)
    except (TypeError, ValueError):
        return False


def _require_authority(
    errors: list[str],
    data: dict,
    expected: str,
) -> None:
    if data.get("authority") != expected:
        errors.append(f"wrong linked authority type: expected {expected}")
    if data.get("qualified") is not True:
        errors.append(f"linked {expected} is not qualified")
    if data.get("powered_operation_authorized") is not False:
        errors.append(f"linked {expected} violates powered-operation boundary")
    if not _valid_fp(data):
        errors.append(f"linked {expected} fingerprint is invalid")


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _positive(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0
    )


def qualify(data: dict, chassis: dict, dummy_pack: dict) -> dict:
    errors: list[str] = []

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("scope") != "rev_c_inert_environmental_durability_trial":
        errors.append("wrong environmental durability trial scope")

    _require_authority(errors, chassis, "x1_rolling_chassis_physical")
    _require_authority(errors, dummy_pack, "x1_dummy_pack_mount")

    if (
        data.get("chassis_authority_fingerprint_sha256")
        != chassis.get("authority_fingerprint_sha256")
    ):
        errors.append("manifest does not link the supplied rolling-chassis authority")
    if (
        data.get("dummy_pack_authority_fingerprint_sha256")
        != dummy_pack.get("authority_fingerprint_sha256")
    ):
        errors.append("manifest does not link the supplied dummy-pack authority")

    for key in (
        "session_id",
        "candidate_enclosure_id",
        "harness_revision_id",
    ):
        if not _nonempty(data.get(key)):
            errors.append(f"{key} must be a nonempty string")

    for key in (
        "live_battery_present",
        "traction_voltage_present",
        "charger_connected",
        "powered_vehicle",
        "ip_rating_claimed",
        "waterproof_claimed",
        "corrosion_life_claimed",
        "pressure_washer_used",
        "immersion_used",
        "electrical_wet_operation_qualified",
        "procurement_authority",
        "powered_operation_authorized",
    ):
        if data.get(key) is not False:
            errors.append(f"{key} must be false")

    interfaces = data.get("interface_inventory")
    if not isinstance(interfaces, list) or not interfaces:
        errors.append("interface_inventory must be a nonempty list")
        interfaces = []

    interface_ids: set[str] = set()
    for index, item in enumerate(interfaces):
        if not isinstance(item, dict):
            errors.append(f"interface {index} must be an object")
            continue
        item_id = item.get("id")
        if not _nonempty(item_id):
            errors.append(f"interface {index} requires a nonempty id")
            item_id = f"<interface-{index}>"
        elif item_id in interface_ids:
            errors.append(f"duplicate interface id: {item_id}")
        else:
            interface_ids.add(item_id)

        for key in INTERFACE_TEXT:
            if not _nonempty(item.get(key)):
                errors.append(f"{item_id}: {key} must be nonempty")
        for key in INTERFACE_TRUE:
            if item.get(key) is not True:
                errors.append(f"{item_id}: {key} must be true")

    cycles = data.get("exposure_cycles")
    if not isinstance(cycles, list) or len(cycles) < 3:
        errors.append("at least three environmental exposure cycles are required")
        cycles = []

    cycle_ids: set[str] = set()
    observed_types: set[str] = set()
    for index, cycle in enumerate(cycles):
        if not isinstance(cycle, dict):
            errors.append(f"exposure cycle {index} must be an object")
            continue
        cycle_id = cycle.get("id")
        if not _nonempty(cycle_id):
            errors.append(f"exposure cycle {index} requires a nonempty id")
            cycle_id = f"<cycle-{index}>"
        elif cycle_id in cycle_ids:
            errors.append(f"duplicate exposure cycle id: {cycle_id}")
        else:
            cycle_ids.add(cycle_id)

        exposure_type = cycle.get("exposure_type")
        if exposure_type not in EXPOSURE_TYPES:
            errors.append(
                f"{cycle_id}: exposure_type must be one of "
                + ", ".join(sorted(EXPOSURE_TYPES))
            )
        else:
            observed_types.add(exposure_type)

        for key in (
            "media_description",
            "method_description",
            "exposure_quantity_unit",
        ):
            if not _nonempty(cycle.get(key)):
                errors.append(f"{cycle_id}: {key} must be nonempty")
        for key in ("exposure_quantity", "duration_s"):
            if not _positive(cycle.get(key)):
                errors.append(f"{cycle_id}: {key} must be positive")
        for key in CYCLE_TRUE:
            if cycle.get(key) is not True:
                errors.append(f"{cycle_id}: {key} must be true")
        for key in CYCLE_FALSE:
            if cycle.get(key) is not False:
                errors.append(f"{cycle_id}: {key} must be false")

    missing_types = sorted(EXPOSURE_TYPES - observed_types)
    if missing_types:
        errors.append(
            "environmental exposure set missing: " + ", ".join(missing_types)
        )

    connectors = data.get("connector_service_trials")
    if not isinstance(connectors, list) or not connectors:
        errors.append("connector_service_trials must be a nonempty list")
        connectors = []

    connector_trial_ids: set[str] = set()
    for index, trial in enumerate(connectors):
        if not isinstance(trial, dict):
            errors.append(f"connector trial {index} must be an object")
            continue
        trial_id = trial.get("id")
        if not _nonempty(trial_id):
            errors.append(f"connector trial {index} requires a nonempty id")
            trial_id = f"<connector-{index}>"
        elif trial_id in connector_trial_ids:
            errors.append(f"duplicate connector trial id: {trial_id}")
        else:
            connector_trial_ids.add(trial_id)

        for key in (
            "connector_id",
            "connector_role",
            "contamination_description",
            "cleaning_method",
            "manufacturer_service_guidance_source",
        ):
            if not _nonempty(trial.get(key)):
                errors.append(f"{trial_id}: {key} must be nonempty")
        for key in CONNECTOR_TRUE:
            if trial.get(key) is not True:
                errors.append(f"{trial_id}: {key} must be true")
        for key in CONNECTOR_FALSE:
            if trial.get(key) is not False:
                errors.append(f"{trial_id}: {key} must be false")

    recovery = data.get("wheel_brake_steering_recovery")
    if not isinstance(recovery, dict):
        errors.append("wheel_brake_steering_recovery must be an object")
    else:
        for key in RECOVERY_TRUE:
            if recovery.get(key) is not True:
                errors.append(f"wheel_brake_steering_recovery.{key} must be true")
        for key in RECOVERY_FALSE:
            if recovery.get(key) is not False:
                errors.append(f"wheel_brake_steering_recovery.{key} must be false")

    post = data.get("drying_and_post_inspection")
    if not isinstance(post, dict):
        errors.append("drying_and_post_inspection must be an object")
    else:
        if not _nonempty(post.get("drying_method")):
            errors.append("drying_and_post_inspection.drying_method must be nonempty")
        if not _positive(post.get("declared_dry_time_minutes")):
            errors.append(
                "drying_and_post_inspection.declared_dry_time_minutes must be positive"
            )
        for key in POST_TRUE:
            if post.get(key) is not True:
                errors.append(f"drying_and_post_inspection.{key} must be true")
        for key in POST_FALSE:
            if post.get(key) is not False:
                errors.append(f"drying_and_post_inspection.{key} must be false")

    report = {
        "schema_version": 1,
        "authority": "x1_environmental_inert_candidate",
        "scope": "inert_environmental_packaging_service_only",
        "qualified": not errors,
        "errors": errors,
        "session_id": data.get("session_id"),
        "candidate_enclosure_id": data.get("candidate_enclosure_id"),
        "harness_revision_id": data.get("harness_revision_id"),
        "rolling_chassis_fingerprint_sha256": chassis.get(
            "authority_fingerprint_sha256"
        ),
        "dummy_pack_fingerprint_sha256": dummy_pack.get(
            "authority_fingerprint_sha256"
        ),
        "environmental_inert_candidate_qualified": not errors,
        "ip_rating_claimed": False,
        "waterproof_claimed": False,
        "corrosion_life_claimed": False,
        "electrical_wet_operation_qualified": False,
        "live_battery_test_authorized": False,
        "procurement_authority": False,
        "powered_operation_authorized": False,
        "interpretation_boundary": (
            "A passing report qualifies only the tested inert enclosure/interface/"
            "drainage/service-recovery candidate. It does not establish an IP rating, "
            "waterproofing, corrosion life, energized wet operation, or powered trail "
            "operation."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--chassis-authority", type=Path, required=True)
    parser.add_argument("--dummy-pack-authority", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = qualify(
        json.loads(args.manifest.read_text(encoding="utf-8")),
        json.loads(args.chassis_authority.read_text(encoding="utf-8")),
        json.loads(args.dummy_pack_authority.read_text(encoding="utf-8")),
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["qualified"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
