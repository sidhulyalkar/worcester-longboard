#!/usr/bin/env python3
"""Qualify only the inert mechanical behavior of the Rev-C charge cradle.

This tool never authorizes electrical charging or powered riding. It exists to
prove repeatable board parking, connector alignment, cable protection and
serviceability using inert fixtures before live battery work.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_DOCK_CHECKS = (
    "supports_board_without_loading_brake_hardware",
    "supports_board_without_loading_drive_hardware",
    "supports_board_without_connector_as_structural_member",
    "self_centering_guides_present",
    "connector_carriage_has_compliance_or_alignment_relief",
    "charger_cable_strain_relief_present",
    "charge_connector_protected_when_board_absent",
    "service_access_preserved",
)

REQUIRED_TRIAL_CHECKS = (
    "board_set_down_without_lifting",
    "guides_centered_board",
    "inert_connector_aligned_without_forced_side_load",
    "inert_connector_reached_intended_seated_state",
    "cable_remained_strain_relieved",
    "no_interference_with_brake_drive_or_steering",
)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def qualify(data: dict) -> dict:
    errors: list[str] = []

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("scope") != "rev_c_passive_charge_cradle_mechanical_trial":
        errors.append("wrong charge-cradle trial scope")

    for key in (
        "session_id",
        "selected_pack_reference_id",
        "selected_charger_reference_id",
        "charger_compatibility_source",
        "inert_pack_fixture_id",
        "inert_connector_fixture_id",
    ):
        if not _nonempty(data.get(key)):
            errors.append(f"{key} must be a nonempty string")

    for key in (
        "electrical_energy_present",
        "board_powered",
        "charger_energized",
        "exposed_traction_voltage_contacts",
        "electrical_charge_authorized",
        "powered_operation_authorized",
    ):
        if data.get(key) is not False:
            errors.append(f"{key} must be false")

    dock = data.get("dock_design")
    if not isinstance(dock, dict):
        errors.append("dock_design must be an object")
    else:
        for key in REQUIRED_DOCK_CHECKS:
            if dock.get(key) is not True:
                errors.append(f"dock_design.{key} must be true")

    stability = data.get("stability_check")
    if not isinstance(stability, dict):
        errors.append("stability_check must be an object")
    else:
        if not _nonempty(stability.get("method")):
            errors.append("stability_check.method must be nonempty")
        if stability.get("board_remained_stable") is not True:
            errors.append("stability_check.board_remained_stable must be true")
        if stability.get("connector_not_used_as_retention") is not True:
            errors.append(
                "stability_check.connector_not_used_as_retention must be true"
            )

    cable = data.get("cable_check")
    if not isinstance(cable, dict):
        errors.append("cable_check must be an object")
    else:
        if not _nonempty(cable.get("manufacturer_or_system_source")):
            errors.append(
                "cable_check.manufacturer_or_system_source must be nonempty"
            )
        for key in (
            "bend_radius_and_strain_requirements_checked",
            "no_sharp_edge_contact",
            "no_wheel_or_steering_sweep_contact",
        ):
            if cable.get(key) is not True:
                errors.append(f"cable_check.{key} must be true")

    trials = data.get("alignment_trials")
    if not isinstance(trials, list) or len(trials) < 5:
        errors.append("at least five alignment trials are required")
        trials = []

    ids: set[str] = set()
    for index, trial in enumerate(trials):
        if not isinstance(trial, dict):
            errors.append(f"alignment trial {index} must be an object")
            continue
        trial_id = trial.get("id")
        if not _nonempty(trial_id):
            errors.append(f"alignment trial {index} requires id")
        elif trial_id in ids:
            errors.append(f"duplicate alignment trial id: {trial_id}")
        else:
            ids.add(trial_id)
        for key in REQUIRED_TRIAL_CHECKS:
            if trial.get(key) is not True:
                errors.append(f"{trial_id or index}: {key} must be true")

    post = data.get("post_trial_inspection")
    if not isinstance(post, dict):
        errors.append("post_trial_inspection must be an object")
    else:
        for key in (
            "dock_shifted_or_loosened",
            "connector_fixture_damage",
            "cable_or_strain_relief_damage",
            "board_or_chassis_damage",
        ):
            if post.get(key) is not False:
                errors.append(
                    f"post_trial_inspection.{key} must be false"
                )

    qualified = not errors
    return {
        "schema_version": 1,
        "authority": "x1_rev_c_passive_charge_cradle_mechanical",
        "qualified": qualified,
        "errors": errors,
        "session_id": data.get("session_id"),
        "selected_pack_reference_id": data.get("selected_pack_reference_id"),
        "selected_charger_reference_id": data.get(
            "selected_charger_reference_id"
        ),
        "alignment_trial_count": len(trials),
        "inert_mechanical_alignment_qualified": qualified,
        "live_battery_test_authorized": False,
        "electrical_charge_authorized": False,
        "procurement_authority": False,
        "powered_operation_authorized": False,
        "interpretation_boundary": (
            "A passing report proves only the inert mechanical cradle/alignment "
            "checks represented by this manifest. It does not qualify the battery, "
            "charger, electrical connector, charging process, or powered vehicle."
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
