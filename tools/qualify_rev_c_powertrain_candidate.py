#!/usr/bin/env python3
"""Qualify a Rev-C propulsion candidate as an architecture-envelope prerequisite.

This qualifier does not authorize procurement, controller settings, battery
settings, thermal capability, or powered operation. It verifies only that a
fully sourced candidate is tied to the correct physical/topology authorities
and passes its declared first-order mission scenarios.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from simulation.rev_c_powertrain_envelope import analyze

TOPOLOGY_CLASS = {
    "same_rear_axle_v5_plus_drive": "rear",
    "rear_v5_front_2wd": "front",
    "rear_2wd_front_friction_brake": "rear",
    "alternate_drive_on_brake_first_rear": "rear",
}

REQUIRED_SOURCE_REFS = (
    "motor_kv_rpm_per_v",
    "motor_pole_pairs",
    "phase_current_limit_a_per_motor",
    "battery_current_limit_a_total",
    "erpm_limit",
    "nominal_voltage_v",
    "full_voltage_v",
    "motor_mount_and_shaft",
    "wheel_gear_teeth",
    "motor_gear_teeth",
    "drivetrain_efficiency_basis",
    "electrical_efficiency_basis",
    "rolling_resistance_basis",
    "traction_mu_basis",
)

REQUIRED_SCENARIO_CLASSES = {
    "flat_cruise",
    "grade_climb",
    "low_speed_accel",
}


def _digest(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _valid_authority(data: dict, expected: str) -> bool:
    if data.get("authority") != expected or data.get("qualified") is not True:
        return False
    if data.get("powered_operation_authorized") is not False:
        return False
    actual = data.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        return False
    unsigned = dict(data)
    unsigned.pop("authority_fingerprint_sha256", None)
    try:
        return actual == _digest(unsigned)
    except (TypeError, ValueError):
        return False


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def qualify(
    manifest: dict,
    chassis: dict,
    topology: dict,
    dummy_pack: dict,
) -> dict:
    errors: list[str] = []

    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if manifest.get("scope") != "rev_c_powertrain_candidate_qualification":
        errors.append("wrong powertrain candidate scope")
    if manifest.get("issue") != 43:
        errors.append("manifest must identify Issue #43")
    for key in ("candidate_id", "selected_drive_family"):
        if not _nonempty(manifest.get(key)):
            errors.append(f"{key} must be nonempty")

    authorities = (
        (chassis, "x1_rolling_chassis_physical", "rolling_chassis_fingerprint_sha256"),
        (topology, "x1_brake_drive_topology", "brake_drive_topology_fingerprint_sha256"),
        (dummy_pack, "x1_dummy_pack_mount", "dummy_pack_fingerprint_sha256"),
    )
    links = manifest.get("linked_authorities")
    if not isinstance(links, dict):
        errors.append("linked_authorities must be an object")
        links = {}

    for authority, expected, link_key in authorities:
        if not _valid_authority(authority, expected):
            errors.append(
                f"linked {expected} must be qualified and fingerprint-valid"
            )
        if links.get(link_key) != authority.get("authority_fingerprint_sha256"):
            errors.append(f"manifest does not link the supplied {expected}")

    source_refs = manifest.get("source_refs")
    if not isinstance(source_refs, dict):
        errors.append("source_refs must be an object")
        source_refs = {}
    for key in REQUIRED_SOURCE_REFS:
        if not _nonempty(source_refs.get(key)):
            errors.append(f"source_refs.{key} must be nonempty")

    config = manifest.get("envelope_config")
    if not isinstance(config, dict):
        errors.append("envelope_config must be an object")
        config = {}

    candidate = config.get("candidate", {}) if isinstance(config, dict) else {}
    if candidate.get("id") != manifest.get("candidate_id"):
        errors.append("envelope candidate.id must match manifest candidate_id")

    selected_topology = topology.get("selected_topology")
    expected_class = TOPOLOGY_CLASS.get(selected_topology)
    if expected_class is None:
        errors.append(
            f"selected Issue #19 topology is not mapped to a propulsion class: {selected_topology!r}"
        )
    elif candidate.get("topology") != expected_class:
        errors.append(
            f"candidate topology {candidate.get('topology')!r} does not match "
            f"Issue #19 selected topology class {expected_class!r}"
        )

    scenario_classes: set[str] = set()
    for index, scenario in enumerate(config.get("scenarios", [])):
        if not isinstance(scenario, dict):
            continue
        scenario_class = scenario.get("scenario_class")
        if not _nonempty(scenario_class):
            errors.append(f"scenario {index} requires scenario_class")
        else:
            scenario_classes.add(scenario_class)
    missing_classes = sorted(REQUIRED_SCENARIO_CLASSES - scenario_classes)
    if missing_classes:
        errors.append(
            "missing required scenario classes: " + ", ".join(missing_classes)
        )

    for key in (
        "thermal_qualification",
        "procurement_authority",
        "controller_configuration_authority",
        "battery_configuration_authority",
        "powered_operation_authorized",
    ):
        if manifest.get(key) is not False:
            errors.append(f"{key} must be false")

    analysis = analyze(config) if isinstance(config, dict) else {
        "valid": False,
        "errors": ["missing config"],
    }
    if analysis.get("valid") is not True:
        for error in analysis.get("errors", []):
            errors.append(f"envelope analysis: {error}")
    elif analysis.get("all_scenarios_pass_declared_first_order_envelope") is not True:
        failed = ", ".join(analysis.get("failed_scenarios", []))
        errors.append(
            "declared candidate fails one or more first-order scenarios"
            + (f": {failed}" if failed else "")
        )

    report = {
        "schema_version": 1,
        "authority": "x1_powertrain_envelope_candidate",
        "scope": "architecture_envelope_prerequisite_only",
        "qualified": not errors,
        "errors": errors,
        "candidate_id": manifest.get("candidate_id"),
        "selected_drive_family": manifest.get("selected_drive_family"),
        "selected_topology": selected_topology,
        "propulsion_topology_class": candidate.get("topology"),
        "ratio_wheel_over_motor": (
            candidate.get("wheel_gear_teeth") / candidate.get("motor_gear_teeth")
            if isinstance(candidate.get("wheel_gear_teeth"), int)
            and isinstance(candidate.get("motor_gear_teeth"), int)
            and candidate.get("motor_gear_teeth", 0) > 0
            else None
        ),
        "envelope_config_sha256": (
            _digest(config) if isinstance(config, dict) else None
        ),
        "analysis_sha256": _digest(analysis),
        "failed_scenarios": analysis.get("failed_scenarios", []),
        "all_declared_scenarios_pass": (
            analysis.get("all_scenarios_pass_declared_first_order_envelope")
            is True
        ),
        "source_refs": source_refs,
        "rolling_chassis_fingerprint_sha256": chassis.get(
            "authority_fingerprint_sha256"
        ),
        "brake_drive_topology_fingerprint_sha256": topology.get(
            "authority_fingerprint_sha256"
        ),
        "dummy_pack_fingerprint_sha256": dummy_pack.get(
            "authority_fingerprint_sha256"
        ),
        "thermal_qualification": False,
        "physical_authority": False,
        "procurement_authority": False,
        "controller_configuration_authority": False,
        "battery_configuration_authority": False,
        "powered_operation_authorized": False,
        "interpretation_boundary": (
            "A passing report proves only that the sourced candidate is internally "
            "consistent with the linked chassis/topology/dummy-pack state and passes "
            "the declared first-order scenarios. It does not prove thermal capability, "
            "controller settings, battery safety, traction on real terrain, procurement "
            "readiness, or powered-operation safety."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--chassis-authority", type=Path, required=True)
    parser.add_argument("--topology-authority", type=Path, required=True)
    parser.add_argument("--dummy-pack-authority", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = qualify(
        json.loads(args.manifest.read_text(encoding="utf-8")),
        json.loads(args.chassis_authority.read_text(encoding="utf-8")),
        json.loads(args.topology_authority.read_text(encoding="utf-8")),
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
