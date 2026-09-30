#!/usr/bin/env python3
"""Qualify the Worcester X1 Rev-C chassis/brake purchase release.

This is a pre-purchase architecture authority only. It may release selected
MEASURE_FIRST hardware for physical investigation. It cannot qualify a brake,
rolling chassis, drivetrain, battery, or powered operation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

_SHA256 = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_SELECTIONS = (
    "selected_chassis_family",
    "selected_wheel_family",
    "selected_brake_architecture",
    "selected_topology_for_measurement",
)

REQUIRED_CHECKS = (
    "deck_envelope_comparison_completed",
    "traction_trade_study_reviewed",
    "independent_stopping_path_credible",
    "range_pack_inert_envelope_plausible",
    "no_unqualified_safety_critical_adapter",
    "rejected_alternatives_recorded",
)

REQUIRED_EVIDENCE = (
    "deck_envelope_record_sha256",
    "topology_trade_record_sha256",
    "inert_pack_envelope_record_sha256",
    "fit_pilot_authority_fingerprint_sha256",
)


def _digest(data: dict) -> str:
    payload = json.dumps(
        data, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _valid_fingerprint(doc: dict) -> bool:
    actual = doc.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not _SHA256.fullmatch(actual):
        return False
    unsigned = dict(doc)
    unsigned.pop("authority_fingerprint_sha256", None)
    try:
        return actual == _digest(unsigned)
    except (TypeError, ValueError):
        return False


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def qualify(data: dict, fit_pilot_authority: dict | None = None) -> dict:
    errors: list[str] = []

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("scope") != "rev_c_chassis_purchase_release":
        errors.append("wrong release scope")
    if data.get("powered_operation_authorized") is not False:
        errors.append("chassis release cannot authorize powered operation")

    for key in REQUIRED_SELECTIONS:
        if not _nonempty(data.get(key)):
            errors.append(f"missing selection: {key}")

    checks = data.get("checks", {})
    if not isinstance(checks, dict):
        errors.append("checks must be an object")
        checks = {}
    for key in REQUIRED_CHECKS:
        if checks.get(key) is not True:
            errors.append(f"check not passed: {key}")

    refs = data.get("evidence_refs", {})
    if not isinstance(refs, dict):
        errors.append("evidence_refs must be an object")
        refs = {}
    for key in REQUIRED_EVIDENCE:
        value = refs.get(key)
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            errors.append(f"invalid sha256 evidence reference: {key}")

    if fit_pilot_authority is not None:
        if fit_pilot_authority.get("qualified_for_four_zone_duplication") is not True:
            errors.append("linked fit-pilot authority is not qualified")
        elif not _valid_fingerprint(fit_pilot_authority):
            errors.append("linked fit-pilot authority fingerprint is invalid")
        elif refs.get("fit_pilot_authority_fingerprint_sha256") != fit_pilot_authority.get(
            "authority_fingerprint_sha256"
        ):
            errors.append("release references a different fit-pilot authority")

    rejected = data.get("rejected_alternatives")
    if not isinstance(rejected, list) or not rejected:
        errors.append("rejected_alternatives must record at least one rejected branch")
    else:
        for index, entry in enumerate(rejected):
            if not isinstance(entry, dict):
                errors.append(f"rejected alternative {index} must be an object")
                continue
            if not _nonempty(entry.get("id")):
                errors.append(f"rejected alternative {index} missing id")
            if not _nonempty(entry.get("reason")):
                errors.append(f"rejected alternative {index} missing reason")

    open_questions = data.get("open_questions")
    if not isinstance(open_questions, list):
        errors.append("open_questions must be a list")
        open_questions = []
    for index, question in enumerate(open_questions):
        if not _nonempty(question):
            errors.append(f"open question {index} must be nonempty")

    report = {
        "schema_version": 1,
        "authority": "x1_rev_c_chassis_release",
        "scope": "rev_c_chassis_purchase_release_only",
        "qualified": not errors,
        "errors": errors,
        "deck_envelope_comparison_completed": checks.get(
            "deck_envelope_comparison_completed"
        ) is True,
        "selected_chassis_family": data.get("selected_chassis_family"),
        "selected_wheel_family": data.get("selected_wheel_family"),
        "selected_brake_architecture": data.get("selected_brake_architecture"),
        "selected_topology_for_measurement": data.get(
            "selected_topology_for_measurement"
        ),
        "range_pack_inert_envelope_plausible": checks.get(
            "range_pack_inert_envelope_plausible"
        ) is True,
        "no_unqualified_safety_critical_adapter": checks.get(
            "no_unqualified_safety_critical_adapter"
        ) is True,
        "rejected_alternatives": rejected,
        "open_questions": open_questions,
        "evidence_refs": refs,
        "powered_operation_authorized": False,
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--fit-pilot-authority", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = qualify(
        json.loads(args.manifest.read_text(encoding="utf-8")),
        json.loads(args.fit_pilot_authority.read_text(encoding="utf-8")),
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
