#!/usr/bin/env python3
"""Validate a future Worcester X1 powered-test venue record.

This tool validates venue evidence only. It never authorizes the vehicle,
powered operation, public-road operation, or dog-accompanied operation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_TEXT = (
    "session_id",
    "venue_id",
    "venue_name",
    "venue_type",
    "owner_or_jurisdiction",
    "permission_basis",
    "permission_source_or_record",
    "permission_checked_date",
    "surface_description",
    "pedestrian_vehicle_separation_method",
    "emergency_stop_plan",
)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def qualify(data: dict) -> dict:
    errors: list[str] = []

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("scope") != "x1_powered_test_venue_record":
        errors.append("wrong powered-test venue scope")

    for key in REQUIRED_TEXT:
        if not _nonempty(data.get(key)):
            errors.append(f"{key} must be a nonempty string")

    if data.get("public_access_controlled") is not True:
        errors.append("public_access_controlled must be true")
    if data.get("course_boundary_defined") is not True:
        errors.append("course_boundary_defined must be true")
    if data.get("mechanical_brake_required") is not True:
        errors.append("mechanical_brake_required must be true")
    if data.get("dog_present") is not False:
        errors.append("dog_present must be false for initial powered test venue qualification")
    if data.get("leash_attachment_to_board") is not False:
        errors.append("leash_attachment_to_board must be false")

    max_speed = data.get("maximum_planned_speed_mps")
    if not isinstance(max_speed, (int, float)) or isinstance(max_speed, bool) or max_speed <= 0:
        errors.append("maximum_planned_speed_mps must be positive")

    restrictions = data.get("applicable_restrictions")
    if not isinstance(restrictions, list):
        errors.append("applicable_restrictions must be a list")

    if data.get("venue_permission_verified") is not True:
        errors.append("venue_permission_verified must be true")

    # Current Los Gatos park rules prohibit skateboards in Town parks/trails.
    # Worcester Park therefore remains blocked in this dated qualifier.
    if data.get("worcester_park") is True:
        errors.append(
            "Worcester Park is blocked by the current dated Town park skateboard rule"
        )

    # These fields are deliberately not accepted as authority even if true.
    if data.get("vehicle_powered_operation_authority") is not False:
        errors.append("vehicle_powered_operation_authority must be false")
    if data.get("dog_accompanied_operation_authority") is not False:
        errors.append("dog_accompanied_operation_authority must be false")

    venue_permission_qualified = not errors

    return {
        "schema_version": 1,
        "authority": "x1_powered_test_venue_evidence",
        "qualified": venue_permission_qualified,
        "errors": errors,
        "venue_id": data.get("venue_id"),
        "venue_name": data.get("venue_name"),
        "venue_permission_qualified": venue_permission_qualified,
        "vehicle_operation_legality_verified_recorded": (
            data.get("vehicle_operation_legality_verified") is True
        ),
        "vehicle_powered_operation_authority": False,
        "public_operation_authority": False,
        "dog_accompanied_operation_authority": False,
        "interpretation_boundary": (
            "A passing report only says the venue record is complete and the "
            "location permission evidence represented by the manifest passed this "
            "dated checklist. It does not make the vehicle legal, safe, powered-"
            "operation-qualified, or dog-accompanied-operation-qualified."
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
