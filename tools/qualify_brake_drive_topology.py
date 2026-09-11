#!/usr/bin/env python3
"""Qualify Worcester X1 brake/drive topology without authorizing traction power."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

TOPOLOGIES = {
    "same_rear_axle_v5_plus_drive": "coexistence_geometry_passed",
    "rear_v5_front_2wd": "front_drive_traction_control_passed",
    "rear_2wd_front_friction_brake": "front_brake_proven_interface_passed",
    "alternate_drive_on_brake_first_rear": "alternate_drive_debris_tension_retention_passed",
}

REQUIRED_CHECKS = (
    "manufacturer_constraints_recorded",
    "brake_static_and_rolling_evidence_linked",
    "motion_sweep_passed",
    "wheel_service_without_battery_disturbance_passed",
    "positive_wheel_and_drive_retention_defined",
    "cable_hose_sweep_clear",
    "replaceable_guard_strategy_defined",
    "rejected_topologies_documented",
    "mechanical_brake_independent_of_traction_power",
    "at_least_two_friction_braked_wheels",
)

REQUIRED_HARDWARE_IDS = (
    "front_truck",
    "rear_truck",
    "rear_axle",
    "rear_hub",
    "rear_wheel",
    "brake",
    "drive_reference",
)

REQUIRED_EVIDENCE_REFS = (
    "brake_authority_fingerprint_sha256",
    "rolling_chassis_authority_fingerprint_sha256",
    "collision_sweep_sha256",
    "service_record_sha256",
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _digest(report: dict) -> str:
    payload = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def qualify(data: dict) -> dict:
    errors: list[str] = []
    if data.get("scope") != "unpowered_brake_drive_topology_measurement":
        errors.append("wrong topology measurement scope")

    selected = data.get("selected_topology")
    if selected not in TOPOLOGIES:
        errors.append("selected_topology is not a supported X1 candidate")

    candidates = data.get("candidate_evaluations", {})
    if not isinstance(candidates, dict):
        errors.append("candidate_evaluations must be an object")
        candidates = {}

    for topology in TOPOLOGIES:
        entry = candidates.get(topology)
        if not isinstance(entry, dict):
            errors.append(f"missing candidate evaluation: {topology}")
            continue
        status = entry.get("status")
        if topology == selected:
            if status != "PASS":
                errors.append("selected topology must have status PASS")
            if entry.get(TOPOLOGIES[topology]) is not True:
                errors.append(f"selected topology missing specific check: {TOPOLOGIES[topology]}")
        elif status != "REJECTED":
            errors.append(f"non-selected topology must be explicitly REJECTED: {topology}")
        if not isinstance(entry.get("reason"), str) or not entry["reason"].strip():
            errors.append(f"candidate evaluation requires reason: {topology}")

    checks = data.get("checks", {})
    for key in REQUIRED_CHECKS:
        if checks.get(key) is not True:
            errors.append(f"check not passed: {key}")

    hardware = data.get("hardware_ids", {})
    for key in REQUIRED_HARDWARE_IDS:
        if not isinstance(hardware.get(key), str) or not hardware[key].strip():
            errors.append(f"missing hardware id: {key}")

    evidence = data.get("evidence_refs", {})
    for key in REQUIRED_EVIDENCE_REFS:
        value = evidence.get(key)
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            errors.append(f"invalid sha256 evidence reference: {key}")

    if data.get("powered_operation_authorized") is True:
        errors.append("topology qualification cannot authorize powered operation")

    report = {
        "schema_version": 1,
        "authority": "x1_brake_drive_topology",
        "scope": "unpowered_brake_drive_topology_only",
        "qualified": not errors,
        "selected_topology": selected,
        "errors": errors,
        "powered_operation_authorized": False,
        "hardware_ids": hardware,
        "evidence_refs": evidence,
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: qualify_brake_drive_topology.py manifest.json [out.json]")
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
