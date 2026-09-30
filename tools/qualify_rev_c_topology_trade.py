#!/usr/bin/env python3
"""Qualify the Rev-C pre-purchase brake/drive topology trade.

This authority selects only the topology worth measuring first after purchase.
It does not qualify physical coexistence, braking performance, drivetrain
retention, powered operation, or final topology selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

TOPOLOGIES = (
    "REAR_V5_FRONT_2WD",
    "REAR_V5_REAR_2WD_SHARED",
    "REAR_2WD_FRONT_VENDOR_HYDRAULIC",
    "ALTERNATE_REAR_DRIVE_PRESERVING_V5",
)

ALLOWED_STATUS = {
    "SELECTED_FOR_MEASUREMENT",
    "KEEP_LIVE",
    "DEFERRED",
    "REJECTED",
}

REQUIRED_CHECKS = (
    "manufacturer_constraints_recorded",
    "traction_sweep_reviewed",
    "independent_stopping_path_credible",
    "front_hydraulic_reference_treated_as_complete_system_not_adapter",
    "no_unqualified_safety_critical_adapter",
    "physical_measurement_plan_defined",
)


def _digest(data: object) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def qualify(data: dict) -> dict:
    errors: list[str] = []

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("scope") != "rev_c_pre_purchase_topology_trade":
        errors.append("wrong topology-trade scope")
    if data.get("powered_operation_authorized") is not False:
        errors.append("topology trade cannot authorize powered operation")

    selected = data.get("selected_topology_for_measurement")
    if selected not in TOPOLOGIES:
        errors.append("selected_topology_for_measurement is not a Rev-C candidate")

    evaluations = data.get("candidate_evaluations")
    if not isinstance(evaluations, dict):
        errors.append("candidate_evaluations must be an object")
        evaluations = {}

    selected_count = 0
    sanitized: dict[str, dict] = {}
    for topology in TOPOLOGIES:
        entry = evaluations.get(topology)
        if not isinstance(entry, dict):
            errors.append(f"missing candidate evaluation: {topology}")
            continue

        status = entry.get("status")
        if status not in ALLOWED_STATUS:
            errors.append(f"{topology}: unsupported status")
        if status == "SELECTED_FOR_MEASUREMENT":
            selected_count += 1
            if topology != selected:
                errors.append(
                    f"{topology}: selected status disagrees with selected_topology_for_measurement"
                )
        elif topology == selected:
            errors.append("selected topology must have SELECTED_FOR_MEASUREMENT status")

        if not _nonempty(entry.get("reason")):
            errors.append(f"{topology}: evaluation reason is required")

        known_blocker = entry.get("known_catalog_or_safety_blocker")
        if topology == selected and known_blocker is True:
            errors.append("selected topology cannot retain a known catalog or safety blocker")

        sanitized[topology] = {
            "status": status,
            "known_catalog_or_safety_blocker": known_blocker is True,
            "reason_recorded": _nonempty(entry.get("reason")),
        }

    if selected_count != 1:
        errors.append("exactly one topology must be selected for first physical measurement")

    checks = data.get("checks")
    if not isinstance(checks, dict):
        errors.append("checks must be an object")
        checks = {}
    for key in REQUIRED_CHECKS:
        if checks.get(key) is not True:
            errors.append(f"check not passed: {key}")

    traction_ref = data.get("traction_sweep_record_sha256")
    if not isinstance(traction_ref, str) or len(traction_ref) != 64:
        errors.append("traction_sweep_record_sha256 must be a 64-character digest")

    report = {
        "schema_version": 1,
        "authority": "x1_rev_c_topology_trade",
        "scope": "pre_purchase_topology_measurement_selection_only",
        "qualified": not errors,
        "errors": errors,
        "selected_topology_for_measurement": selected,
        "candidate_summaries": sanitized,
        "traction_sweep_reviewed": checks.get("traction_sweep_reviewed") is True,
        "independent_stopping_path_credible": checks.get(
            "independent_stopping_path_credible"
        )
        is True,
        "no_unqualified_safety_critical_adapter": checks.get(
            "no_unqualified_safety_critical_adapter"
        )
        is True,
        "private_or_local_source_sha256": _digest(data),
        "powered_operation_authorized": False,
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


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
