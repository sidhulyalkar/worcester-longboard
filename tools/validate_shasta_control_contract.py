#!/usr/bin/env python3
"""Validate that the Rev-C Shasta research contract matches the host controller."""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

KEYS = (
    "speed_cap_mps",
    "accel_max_mps2",
    "regen_decel_max_mps2",
    "phase_current_max_a",
    "drive_current_slew_max_a_per_s",
    "brake_current_slew_max_a_per_s",
    "fault_release_current_slew_a_per_s",
)

SHASTA_CASE = re.compile(
    r"case\s+RideMode::Shasta\s*:\s*return\s*\{([^}]*)\}\s*;"
)


def _parse_float(token: str) -> float:
    token = token.strip()
    if token.endswith(("f", "F")):
        token = token[:-1]
    return float(token)


def validate(
    requirements_path: Path = ROOT / "hardware/rev_c_shasta_mode_requirements.json",
    header_path: Path = ROOT / "firmware/include/x1_control_core.hpp",
    source_path: Path = ROOT / "firmware/src/x1_control_core.cpp",
) -> dict:
    errors: list[str] = []
    requirements = json.loads(requirements_path.read_text(encoding="utf-8"))
    header = header_path.read_text(encoding="utf-8")
    source = source_path.read_text(encoding="utf-8")

    if requirements.get("scope") != "rev_c_shasta_companion_mode_research_requirements":
        errors.append("wrong Shasta requirements scope")
    if requirements.get("powered_operation_authorized") is not False:
        errors.append("Shasta requirements cannot authorize powered operation")

    envelope = requirements.get("provisional_control_envelope", {})
    if envelope.get("status") != "UNQUALIFIED_SOFTWARE_HYPOTHESIS":
        errors.append("Shasta envelope must remain an unqualified software hypothesis")

    match = SHASTA_CASE.search(source)
    parsed: dict[str, float] = {}
    if match is None:
        errors.append("RideMode::Shasta limits case missing from controller")
    else:
        raw = [part.strip() for part in match.group(1).split(",")]
        if len(raw) != len(KEYS):
            errors.append(
                f"Shasta limits case must contain {len(KEYS)} values, found {len(raw)}"
            )
        else:
            try:
                parsed = {
                    key: _parse_float(token)
                    for key, token in zip(KEYS, raw)
                }
            except ValueError as exc:
                errors.append(f"could not parse Shasta controller limits: {exc}")

    for key in KEYS:
        expected = envelope.get(key)
        actual = parsed.get(key)
        if not isinstance(expected, (int, float)):
            errors.append(f"requirements missing numeric {key}")
            continue
        if actual is None:
            continue
        if not math.isclose(float(expected), actual, rel_tol=0, abs_tol=1e-6):
            errors.append(
                f"{key} mismatch: requirements={float(expected):g}, controller={actual:g}"
            )

    required_header_contracts = {
        "RideMode::Shasta enum": "Shasta=4",
        "deadman input": "remote_deadman_active",
        "deadman fault": "FAULT_DEADMAN_RELEASED",
        "overspeed fault": "FAULT_OVERSPEED",
        "lighting request": "lights_requested",
    }
    for label, token in required_header_contracts.items():
        if token not in header:
            errors.append(f"missing header contract: {label}")

    required_source_contracts = {
        "deadman fault generation": "FAULT_DEADMAN_RELEASED",
        "overspeed handling": "FAULT_OVERSPEED",
        "Shasta lighting request": "mode == RideMode::Shasta",
    }
    for label, token in required_source_contracts.items():
        if token not in source:
            errors.append(f"missing controller contract: {label}")

    behavior = requirements.get("required_behavior", {})
    if behavior.get("deliberate_differential_carve_assist") is not False:
        errors.append("Shasta requirements must keep deliberate carve assist disabled")
    if behavior.get("independent_mechanical_brake_remains_required") is not True:
        errors.append("Shasta requirements must preserve independent mechanical braking")

    boundary = requirements.get("companion_boundary", {})
    if boundary.get("leash_attachment_to_board") != "PROHIBITED":
        errors.append("board-mounted leash attachment must remain prohibited")
    if boundary.get("dog_use_requires_future_explicit_authority") is not True:
        errors.append("dog use must require future explicit authority")

    return {
        "schema_version": 1,
        "authority": "x1_rev_c_shasta_contract_validation",
        "valid": not errors,
        "errors": errors,
        "physical_authority": False,
        "procurement_authority": False,
        "powered_operation_authorized": False,
        "parsed_controller_envelope": parsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path)
    parser.add_argument("--header", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = validate(
        args.requirements or ROOT / "hardware/rev_c_shasta_mode_requirements.json",
        args.header or ROOT / "firmware/include/x1_control_core.hpp",
        args.source or ROOT / "firmware/src/x1_control_core.cpp",
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
