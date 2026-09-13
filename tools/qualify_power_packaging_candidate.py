#!/usr/bin/env python3
"""Qualify a low-energy Worcester X1 power-packaging candidate for dummy-mass testing."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _positive(value: Any) -> bool:
    return _finite(value) and float(value) > 0


def qualify(data: dict) -> dict:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("scope") != "power_packaging_candidate_definition":
        errors.append("wrong candidate scope")
    if data.get("powered_operation_authorized") is not False:
        errors.append("candidate cannot authorize powered operation")

    topology_fp = data.get("brake_drive_topology_authority_fingerprint_sha256")
    if not isinstance(topology_fp, str) or len(topology_fp) != 64:
        errors.append("missing brake-drive topology authority fingerprint")

    rev_b_fp = data.get("rev_b_template_authority_fingerprint_sha256")
    if not isinstance(rev_b_fp, str) or len(rev_b_fp) != 64:
        errors.append("missing Rev-B template authority fingerprint")

    mass = data.get("pack_mass_target_kg")
    tolerance = data.get("pack_mass_tolerance_kg")
    if not _positive(mass):
        errors.append("pack_mass_target_kg must be positive")
    if not _positive(tolerance):
        errors.append("pack_mass_tolerance_kg must be positive")
    elif _positive(mass) and float(tolerance) > 0.20 * float(mass):
        errors.append("pack mass tolerance exceeds 20% of target")

    envelope = data.get("enclosure_envelope_mm", {})
    for axis in ("length", "width", "height"):
        if not _positive(envelope.get(axis)):
            errors.append(f"invalid enclosure envelope: {axis}")

    cg = data.get("target_cg_local_mm", {})
    cg_tol = data.get("cg_tolerance_mm", {})
    for axis in ("x", "y", "z"):
        if not _finite(cg.get(axis)):
            errors.append(f"invalid target CG coordinate: {axis}")
        if not _positive(cg_tol.get(axis)):
            errors.append(f"invalid CG tolerance: {axis}")

    if all(_positive(envelope.get(axis)) for axis in ("length", "width", "height")) and all(
        _finite(cg.get(axis)) for axis in ("x", "y", "z")
    ):
        half = {
            "x": float(envelope["length"]) / 2.0,
            "y": float(envelope["width"]) / 2.0,
            "z": float(envelope["height"]) / 2.0,
        }
        for axis in ("x", "y", "z"):
            if abs(float(cg[axis])) > half[axis]:
                errors.append(f"target CG {axis} lies outside enclosure envelope")

    for field in (
        "mounting_region",
        "service_removal_direction",
        "positive_retention_concept",
        "load_spreading_concept",
        "skid_guard_concept",
    ):
        if not isinstance(data.get(field), str) or not data[field].strip():
            errors.append(f"missing candidate field: {field}")

    keepout = data.get("minimum_vulnerable_component_ground_keepout_mm")
    if not _positive(keepout):
        errors.append("minimum vulnerable-component ground keepout must be positive")

    load_req = data.get("static_load_requirements", {})
    for axis in ("front_fraction", "left_fraction"):
        low = load_req.get(f"{axis}_min")
        high = load_req.get(f"{axis}_max")
        if not _finite(low) or not _finite(high):
            errors.append(f"missing static load requirement: {axis}")
        elif not 0.0 < float(low) < float(high) < 1.0:
            errors.append(f"invalid static load range: {axis}")

    report = {
        "schema_version": 1,
        "authority": "x1_power_packaging_candidate",
        "scope": "inert_dummy_pack_definition_only",
        "qualified": not errors,
        "errors": errors,
        "powered_operation_authorized": False,
        "pack_mass_target_kg": mass,
        "pack_mass_tolerance_kg": tolerance,
        "enclosure_envelope_mm": envelope,
        "target_cg_local_mm": cg,
        "cg_tolerance_mm": cg_tol,
        "mounting_region": data.get("mounting_region"),
        "service_removal_direction": data.get("service_removal_direction"),
        "minimum_vulnerable_component_ground_keepout_mm": keepout,
        "static_load_requirements": load_req,
        "brake_drive_topology_authority_fingerprint_sha256": topology_fp,
        "rev_b_template_authority_fingerprint_sha256": rev_b_fp,
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
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
