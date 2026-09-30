#!/usr/bin/env python3
"""Qualify Rev-C pre-purchase inert battery-envelope plausibility.

This checks only whether declared inert trail/range pack envelopes fit within a
declared candidate mounting envelope and whether required keep-out/service checks
were completed. It is not structural validation, battery design, electrical
qualification, or permission to install a live traction pack.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ENERGY_CLASSES = {
    "trail": (500.0, 650.0),
    "range": (950.0, 1150.0),
}

REQUIRED_CHECKS = (
    "rider_stance_keepout_clear",
    "steering_sweep_keepout_clear",
    "deck_flex_keepout_clear",
    "service_removal_direction_defined",
    "positive_retention_concept_defined",
    "sacrificial_skid_or_impact_path_defined",
    "no_live_battery_used",
)


def _digest(data: object) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _finite_positive(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0
    )


def _valid_envelope(envelope: object) -> bool:
    return isinstance(envelope, dict) and all(
        _finite_positive(envelope.get(axis)) for axis in ("length", "width", "height")
    )


def qualify(data: dict) -> dict:
    errors: list[str] = []

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("scope") != "rev_c_pre_purchase_inert_pack_envelope":
        errors.append("wrong inert-pack envelope scope")
    if data.get("powered_operation_authorized") is not False:
        errors.append("inert envelope check cannot authorize powered operation")

    chassis_id = data.get("chassis_candidate_id")
    if not isinstance(chassis_id, str) or not chassis_id.strip():
        errors.append("chassis_candidate_id is required")

    available = data.get("available_mount_envelope_mm")
    if not _valid_envelope(available):
        errors.append("available_mount_envelope_mm must contain positive length/width/height")
        available = {}

    candidates = data.get("pack_candidates")
    if not isinstance(candidates, dict):
        errors.append("pack_candidates must be an object")
        candidates = {}

    summaries: dict[str, dict] = {}
    for class_name, (wh_min, wh_max) in ENERGY_CLASSES.items():
        candidate = candidates.get(class_name)
        if not isinstance(candidate, dict):
            errors.append(f"missing {class_name} pack candidate")
            continue

        nominal_wh = candidate.get("nominal_wh")
        if not _finite_positive(nominal_wh):
            errors.append(f"{class_name}: nominal_wh must be positive")
        elif not wh_min <= float(nominal_wh) <= wh_max:
            errors.append(
                f"{class_name}: nominal_wh must remain in Rev-C {wh_min:.0f}-{wh_max:.0f} Wh class"
            )

        envelope = candidate.get("envelope_mm")
        if not _valid_envelope(envelope):
            errors.append(f"{class_name}: invalid envelope_mm")
            envelope = {}

        mass = candidate.get("inert_target_mass_kg")
        if not _finite_positive(mass):
            errors.append(f"{class_name}: inert_target_mass_kg must be positive")

        placement = candidate.get("placement")
        if placement not in {"top", "under", "split", "other_measured"}:
            errors.append(f"{class_name}: unsupported placement")

        fits = False
        if _valid_envelope(available) and _valid_envelope(envelope):
            fits = all(
                float(envelope[axis]) <= float(available[axis])
                for axis in ("length", "width", "height")
            )
            if not fits:
                errors.append(
                    f"{class_name}: pack envelope exceeds declared available mount envelope"
                )

        summaries[class_name] = {
            "nominal_wh": nominal_wh,
            "placement": placement,
            "fits_declared_mount_envelope": fits,
            "inert_mass_recorded": _finite_positive(mass),
        }

    checks = data.get("checks")
    if not isinstance(checks, dict):
        errors.append("checks must be an object")
        checks = {}
    for key in REQUIRED_CHECKS:
        if checks.get(key) is not True:
            errors.append(f"check not passed: {key}")

    keepout = data.get("minimum_vulnerable_component_ground_keepout_mm")
    if not _finite_positive(keepout):
        errors.append("minimum vulnerable-component ground keepout must be positive")

    report = {
        "schema_version": 1,
        "authority": "x1_rev_c_inert_pack_envelope",
        "scope": "pre_purchase_inert_pack_envelope_only",
        "qualified": not errors,
        "errors": errors,
        "chassis_candidate_id": chassis_id,
        "pack_summaries": summaries,
        "range_pack_inert_envelope_plausible": (
            not errors
            and summaries.get("range", {}).get("fits_declared_mount_envelope") is True
        ),
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
