#!/usr/bin/env python3
"""Initialize an inert Worcester X1 dummy-pack mechanical qualification session."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

POSITIONS = ("fl", "fr", "rl", "rr")


def _digest(data: dict) -> str:
    unsigned = dict(data)
    fingerprint = unsigned.pop("authority_fingerprint_sha256", None)
    payload = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest(), fingerprint


def _require_authority(data: dict, authority: str) -> None:
    expected, actual = _digest(data)
    if data.get("authority") != authority:
        raise ValueError(f"expected {authority} authority")
    if data.get("qualified") is not True:
        raise ValueError(f"{authority} authority is not qualified")
    if data.get("powered_operation_authorized") is not False:
        raise ValueError(f"{authority} violates powered-operation boundary")
    if actual != expected:
        raise ValueError(f"{authority} authority fingerprint is invalid")


def build_manifest(candidate: dict, chassis: dict, enclosure_id: str, mount_id: str) -> dict:
    _require_authority(candidate, "x1_power_packaging_candidate")
    _require_authority(chassis, "x1_rolling_chassis_physical")
    return {
        "schema_version": 1,
        "scope": "inert_dummy_pack_mount_measurement",
        "issue": 21,
        "linked_authorities": {
            "power_packaging_candidate_fingerprint_sha256": candidate["authority_fingerprint_sha256"],
            "rolling_chassis_fingerprint_sha256": chassis["authority_fingerprint_sha256"],
        },
        "hardware_ids": {
            "dummy_enclosure_id": enclosure_id,
            "mount_hardware_set_id": mount_id,
        },
        "candidate_snapshot": {
            "pack_mass_target_kg": candidate["pack_mass_target_kg"],
            "pack_mass_tolerance_kg": candidate["pack_mass_tolerance_kg"],
            "enclosure_envelope_mm": candidate["enclosure_envelope_mm"],
            "target_cg_local_mm": candidate["target_cg_local_mm"],
            "cg_tolerance_mm": candidate["cg_tolerance_mm"],
            "static_load_requirements": candidate["static_load_requirements"],
            "minimum_vulnerable_component_ground_keepout_mm": candidate[
                "minimum_vulnerable_component_ground_keepout_mm"
            ],
        },
        "measurements": {
            "dummy_mass_kg": None,
            "dummy_cg_local_mm": {"x": None, "y": None, "z": None},
            "bare_system_mass_kg": None,
            "dummy_installed_system_mass_kg": None,
            "wheel_loads_n": {
                "bare": {pos: None for pos in POSITIONS},
                "dummy_installed": {pos: None for pos in POSITIONS},
            },
            "minimum_vulnerable_component_ground_clearance_mm": None,
        },
        "checks": {
            "dummy_contains_no_live_cells_or_high_energy_source": False,
            "positive_retention_independent_of_adhesive": False,
            "load_spreading_matches_candidate": False,
            "full_steer_clearance_passed": False,
            "full_lean_clearance_passed": False,
            "deck_flex_clearance_passed": False,
            "tilt_inversion_retention_passed": False,
            "rough_surface_unpowered_push_coast_passed": False,
            "service_removal_reinstallation_passed": False,
            "service_requires_no_unrelated_safety_disassembly": False,
            "no_witness_mark_movement": False,
            "no_cracking_crushing_pullthrough_or_fretting": False,
            "post_test_deck_insert_mount_inspection_passed": False,
            "no_powered_test_performed": False,
        },
        "notes": [],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("session_dir", type=Path)
    p.add_argument("--candidate-authority", type=Path, required=True)
    p.add_argument("--chassis-authority", type=Path, required=True)
    p.add_argument("--enclosure-id", required=True)
    p.add_argument("--mount-id", required=True)
    args = p.parse_args()

    candidate = json.loads(args.candidate_authority.read_text(encoding="utf-8"))
    chassis = json.loads(args.chassis_authority.read_text(encoding="utf-8"))
    try:
        manifest = build_manifest(candidate, chassis, args.enclosure_id, args.mount_id)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    root = args.session_dir.resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"Refusing to overwrite nonempty session directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "dummy_pack_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (root / "NOTES.md").write_text(
        "# Private X1 inert dummy-pack session\n\n"
        "Use inert ballast only. Do not install cells, BMS, charger, ESC, motors, or a traction connector for this test.\n"
        "Match candidate mass and local CG before structural testing.\n"
        "Record four independent wheel loads on the same level surface, with the board settled identically between runs.\n"
        "Any witness movement, cracking, crushing, pull-through, fretting, or unrelated safety-system disassembly is a fail.\n",
        encoding="utf-8",
    )
    print(root)


if __name__ == "__main__":
    main()
