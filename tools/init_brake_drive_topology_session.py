#!/usr/bin/env python3
"""Initialize a Worcester X1 Issue #19 brake/drive topology session."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

TOPOLOGIES = (
    "same_rear_axle_v5_plus_drive",
    "rear_v5_front_2wd",
    "rear_2wd_front_friction_brake",
    "alternate_drive_on_brake_first_rear",
)


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _require_authority(data: dict, authority: str) -> None:
    actual = data.get("authority_fingerprint_sha256")
    unsigned = dict(data)
    unsigned.pop("authority_fingerprint_sha256", None)
    if data.get("authority") != authority or data.get("qualified") is not True:
        raise ValueError(f"linked {authority} authority is not qualified")
    if data.get("powered_operation_authorized") is not False:
        raise ValueError(f"linked {authority} violates powered-operation boundary")
    if actual != _digest(unsigned):
        raise ValueError(f"linked {authority} fingerprint is invalid")


def build_manifest(args, brake: dict, chassis: dict) -> dict:
    _require_authority(brake, "x1_mechanical_brake_interface")
    _require_authority(chassis, "x1_rolling_chassis_physical")
    return {
        "schema_version": 1,
        "scope": "unpowered_brake_drive_topology_measurement",
        "issue": 19,
        "selected_topology": None,
        "powered_operation_authorized": False,
        "hardware_ids": {
            "front_truck": args.front_truck_id,
            "rear_truck": args.rear_truck_id,
            "rear_axle": args.rear_axle_id,
            "rear_hub": args.rear_hub_id,
            "rear_wheel": args.rear_wheel_id,
            "brake": args.brake_id,
            "drive_reference": args.drive_reference_id,
        },
        "candidate_evaluations": {
            topology: {
                "status": "PENDING",
                "reason": "",
                "coexistence_geometry_passed": False,
                "front_drive_traction_control_passed": False,
                "front_brake_proven_interface_passed": False,
                "alternate_drive_debris_tension_retention_passed": False,
            }
            for topology in TOPOLOGIES
        },
        "checks": {
            "manufacturer_constraints_recorded": False,
            "brake_static_and_rolling_evidence_linked": False,
            "motion_sweep_passed": False,
            "wheel_service_without_battery_disturbance_passed": False,
            "positive_wheel_and_drive_retention_defined": False,
            "cable_hose_sweep_clear": False,
            "replaceable_guard_strategy_defined": False,
            "rejected_topologies_documented": False,
            "mechanical_brake_independent_of_traction_power": False,
            "at_least_two_friction_braked_wheels": False,
        },
        "evidence_refs": {
            "brake_authority_fingerprint_sha256": brake["authority_fingerprint_sha256"],
            "rolling_chassis_authority_fingerprint_sha256": chassis["authority_fingerprint_sha256"],
            "collision_sweep_sha256": None,
            "service_record_sha256": None,
        },
        "notes": [],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("session_dir", type=Path)
    p.add_argument("--brake-authority", type=Path, required=True)
    p.add_argument("--chassis-authority", type=Path, required=True)
    p.add_argument("--front-truck-id", required=True)
    p.add_argument("--rear-truck-id", required=True)
    p.add_argument("--rear-axle-id", required=True)
    p.add_argument("--rear-hub-id", required=True)
    p.add_argument("--rear-wheel-id", required=True)
    p.add_argument("--brake-id", required=True)
    p.add_argument("--drive-reference-id", required=True)
    args = p.parse_args()

    brake = json.loads(args.brake_authority.read_text(encoding="utf-8"))
    chassis = json.loads(args.chassis_authority.read_text(encoding="utf-8"))
    try:
        manifest = build_manifest(args, brake, chassis)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    root = args.session_dir.resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"Refusing to overwrite nonempty session directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "topology_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (root / "NOTES.md").write_text(
        "# Private X1 brake/drive topology session\n\n"
        "Evaluate every candidate. Exactly one may be PASS; every other candidate must be explicitly REJECTED with a reason.\n"
        "Do not mark a geometry check passed from product-family names alone. Use measured interfaces or manufacturer drawings.\n"
        "Candidate A should normally be investigated first because a clean shared rear axle gives the simplest conventional layout.\n"
        "Reject any candidate that needs an unqualified safety-critical brake-arm spacer/extender.\n",
        encoding="utf-8",
    )
    print(root)


if __name__ == "__main__":
    main()
