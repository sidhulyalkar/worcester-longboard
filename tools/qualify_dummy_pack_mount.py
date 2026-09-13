#!/usr/bin/env python3
"""Qualify Worcester X1 inert dummy-pack enclosure/mount evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

G = 9.80665
POSITIONS = ("fl", "fr", "rl", "rr")


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
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


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _positive(value: Any) -> bool:
    return _finite(value) and float(value) > 0


def _require_authority(errors: list[str], data: dict, authority: str) -> None:
    if data.get("authority") != authority:
        errors.append(f"wrong linked authority type: expected {authority}")
    if data.get("qualified") is not True:
        errors.append(f"linked {authority} is not qualified")
    if data.get("powered_operation_authorized") is not False:
        errors.append(f"linked {authority} violates powered-operation boundary")
    if not _valid_fp(data):
        errors.append(f"linked {authority} fingerprint is invalid")


def qualify(data: dict, candidate: dict, chassis: dict) -> dict:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("dummy-pack manifest schema_version must be 1")
    if data.get("scope") != "inert_dummy_pack_mount_measurement":
        errors.append("wrong dummy-pack measurement scope")
    if data.get("issue") != 21:
        errors.append("dummy-pack manifest must identify Issue #21")

    _require_authority(errors, candidate, "x1_power_packaging_candidate")
    _require_authority(errors, chassis, "x1_rolling_chassis_physical")

    links = data.get("linked_authorities", {})
    if links.get("power_packaging_candidate_fingerprint_sha256") != candidate.get("authority_fingerprint_sha256"):
        errors.append("manifest does not link the supplied power-packaging candidate")
    if links.get("rolling_chassis_fingerprint_sha256") != chassis.get("authority_fingerprint_sha256"):
        errors.append("manifest does not link the supplied rolling-chassis authority")

    ids = data.get("hardware_ids", {})
    for key in ("dummy_enclosure_id", "mount_hardware_set_id"):
        if not isinstance(ids.get(key), str) or not ids[key].strip():
            errors.append(f"missing dummy-pack hardware id: {key}")

    snapshot = data.get("candidate_snapshot", {})
    for key in (
        "pack_mass_target_kg",
        "pack_mass_tolerance_kg",
        "enclosure_envelope_mm",
        "target_cg_local_mm",
        "cg_tolerance_mm",
        "static_load_requirements",
        "minimum_vulnerable_component_ground_keepout_mm",
    ):
        if snapshot.get(key) != candidate.get(key):
            errors.append(f"candidate snapshot drift: {key}")

    measurements = data.get("measurements", {})
    dummy_mass = measurements.get("dummy_mass_kg")
    target_mass = candidate.get("pack_mass_target_kg")
    mass_tol = candidate.get("pack_mass_tolerance_kg")
    if not _positive(dummy_mass):
        errors.append("dummy mass missing/invalid")
    elif _positive(target_mass) and _positive(mass_tol):
        if abs(float(dummy_mass) - float(target_mass)) > float(mass_tol):
            errors.append("dummy mass outside candidate tolerance")

    measured_cg = measurements.get("dummy_cg_local_mm", {})
    target_cg = candidate.get("target_cg_local_mm", {})
    cg_tol = candidate.get("cg_tolerance_mm", {})
    for axis in ("x", "y", "z"):
        value = measured_cg.get(axis)
        if not _finite(value):
            errors.append(f"dummy CG missing/invalid: {axis}")
        elif _finite(target_cg.get(axis)) and _positive(cg_tol.get(axis)):
            if abs(float(value) - float(target_cg[axis])) > float(cg_tol[axis]):
                errors.append(f"dummy CG outside candidate tolerance: {axis}")

    bare_mass = measurements.get("bare_system_mass_kg")
    installed_mass = measurements.get("dummy_installed_system_mass_kg")
    if not _positive(bare_mass):
        errors.append("bare system mass missing/invalid")
    if not _positive(installed_mass):
        errors.append("dummy-installed system mass missing/invalid")
    if _positive(bare_mass) and _positive(installed_mass) and float(installed_mass) <= float(bare_mass):
        errors.append("dummy-installed system mass must exceed bare system mass")

    wheel_loads = measurements.get("wheel_loads_n", {})
    totals: dict[str, float] = {}
    for state in ("bare", "dummy_installed"):
        loads = wheel_loads.get(state, {})
        state_values: list[float] = []
        for pos in POSITIONS:
            value = loads.get(pos)
            if not _positive(value):
                errors.append(f"missing/invalid wheel load: {state}.{pos}")
            else:
                state_values.append(float(value))
        if len(state_values) == 4:
            totals[state] = sum(state_values)

    if "bare" in totals and _positive(bare_mass):
        inferred = totals["bare"] / G
        if abs(inferred - float(bare_mass)) > max(0.5, 0.05 * float(bare_mass)):
            errors.append("bare wheel-load sum inconsistent with recorded bare mass")
    if "dummy_installed" in totals and _positive(installed_mass):
        inferred = totals["dummy_installed"] / G
        if abs(inferred - float(installed_mass)) > max(0.5, 0.05 * float(installed_mass)):
            errors.append("dummy-installed wheel-load sum inconsistent with recorded installed mass")
    if "bare" in totals and "dummy_installed" in totals and _positive(dummy_mass):
        inferred_delta = (totals["dummy_installed"] - totals["bare"]) / G
        allowed = max(float(mass_tol) if _positive(mass_tol) else 0.0, 0.5, 0.08 * float(dummy_mass))
        if abs(inferred_delta - float(dummy_mass)) > allowed:
            errors.append("wheel-load delta inconsistent with measured dummy mass")

    derived = {
        "front_fraction": None,
        "left_fraction": None,
        "bare_load_sum_n": totals.get("bare"),
        "dummy_installed_load_sum_n": totals.get("dummy_installed"),
    }
    if "dummy_installed" in totals:
        loads = wheel_loads["dummy_installed"]
        total = totals["dummy_installed"]
        front_fraction = (float(loads["fl"]) + float(loads["fr"])) / total
        left_fraction = (float(loads["fl"]) + float(loads["rl"])) / total
        derived["front_fraction"] = front_fraction
        derived["left_fraction"] = left_fraction
        req = candidate.get("static_load_requirements", {})
        if not float(req.get("front_fraction_min", -1)) <= front_fraction <= float(req.get("front_fraction_max", 2)):
            errors.append("dummy-installed front load fraction outside candidate requirement")
        if not float(req.get("left_fraction_min", -1)) <= left_fraction <= float(req.get("left_fraction_max", 2)):
            errors.append("dummy-installed left load fraction outside candidate requirement")

    clearance = measurements.get("minimum_vulnerable_component_ground_clearance_mm")
    required_clearance = candidate.get("minimum_vulnerable_component_ground_keepout_mm")
    if not _positive(clearance):
        errors.append("minimum vulnerable-component ground clearance missing/invalid")
    elif _positive(required_clearance) and float(clearance) < float(required_clearance):
        errors.append("vulnerable-component ground clearance below candidate requirement")

    checks = data.get("checks", {})
    required_checks = (
        "dummy_contains_no_live_cells_or_high_energy_source",
        "positive_retention_independent_of_adhesive",
        "load_spreading_matches_candidate",
        "full_steer_clearance_passed",
        "full_lean_clearance_passed",
        "deck_flex_clearance_passed",
        "tilt_inversion_retention_passed",
        "rough_surface_unpowered_push_coast_passed",
        "service_removal_reinstallation_passed",
        "service_requires_no_unrelated_safety_disassembly",
        "no_witness_mark_movement",
        "no_cracking_crushing_pullthrough_or_fretting",
        "post_test_deck_insert_mount_inspection_passed",
        "no_powered_test_performed",
    )
    for key in required_checks:
        if checks.get(key) is not True:
            errors.append(f"check not passed: {key}")

    report = {
        "schema_version": 1,
        "authority": "x1_dummy_pack_mount",
        "scope": "inert_dummy_pack_mechanical_only",
        "qualified": not errors,
        "errors": errors,
        "powered_operation_authorized": False,
        "hardware_ids": ids,
        "derived_static_loads": derived,
        "measured_dummy_mass_kg": dummy_mass,
        "measured_dummy_cg_local_mm": measured_cg,
        "power_packaging_candidate_fingerprint_sha256": candidate.get("authority_fingerprint_sha256"),
        "rolling_chassis_fingerprint_sha256": chassis.get("authority_fingerprint_sha256"),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("--candidate-authority", type=Path, required=True)
    p.add_argument("--chassis-authority", type=Path, required=True)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    report = qualify(
        json.loads(args.manifest.read_text(encoding="utf-8")),
        json.loads(args.candidate_authority.read_text(encoding="utf-8")),
        json.loads(args.chassis_authority.read_text(encoding="utf-8")),
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
