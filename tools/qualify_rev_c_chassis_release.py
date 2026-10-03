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
    "selected_deck_candidate_id",
    "selected_chassis_family",
    "selected_wheel_family",
    "selected_brake_architecture",
    "selected_topology_for_measurement",
)

DECK_TO_CHASSIS = {
    "comp95_class": "COMP95_BASELINE",
    "pro_warren_iii_class": "PRO_WARREN_III_REFERENCE",
    "agent_class": "AGENT_AIR_REFERENCE",
}

TOPOLOGY_TO_BRAKE = {
    "REAR_V5_FRONT_2WD": "MBS_V5_REAR",
    "REAR_V5_REAR_2WD_SHARED": "MBS_V5_REAR",
    "REAR_2WD_FRONT_VENDOR_HYDRAULIC": "VENDOR_FRONT_HYDRAULIC",
    "ALTERNATE_REAR_DRIVE_PRESERVING_V5": "MBS_V5_REAR",
}

REQUIRED_CHECKS = (
    "deck_envelope_comparison_completed",
    "traction_trade_study_reviewed",
    "independent_stopping_path_credible",
    "range_pack_inert_envelope_plausible",
    "no_unqualified_safety_critical_adapter",
    "rejected_alternatives_recorded",
)

REQUIRED_EVIDENCE = (
    "deck_comparison_authority_fingerprint_sha256",
    "topology_trade_authority_fingerprint_sha256",
    "inert_pack_envelope_authority_fingerprint_sha256",
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


def _valid_authority(doc: dict, expected_authority: str) -> bool:
    return (
        doc.get("authority") == expected_authority
        and doc.get("qualified") is True
        and doc.get("powered_operation_authorized") is False
        and _valid_fingerprint(doc)
    )


def _valid_fit_pilot_authority(doc: dict) -> bool:
    provenance = doc.get("hardware_provenance")
    mass_provenance = doc.get("mass_reference_provenance")
    return (
        doc.get("authority") == "x1_one_zone_pilot"
        and doc.get("scope") == "unpowered_fit_rig_only"
        and doc.get("qualified_for_four_zone_duplication") is True
        and doc.get("powered_operation_authorized") is False
        and isinstance(provenance, dict)
        and _nonempty(provenance.get("selection_authority_fingerprint_sha256"))
        and _nonempty(provenance.get("selection_record_sha256"))
        and isinstance(mass_provenance, dict)
        and _nonempty(
            mass_provenance.get("mass_reference_authority_fingerprint_sha256")
        )
        and _nonempty(mass_provenance.get("mass_reference_record_sha256"))
        and _valid_fingerprint(doc)
    )


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def qualify(
    data: dict,
    fit_pilot_authority: dict | None = None,
    deck_authority: dict | None = None,
    topology_authority: dict | None = None,
    inert_pack_authority: dict | None = None,
) -> dict:
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

    selected_deck = data.get("selected_deck_candidate_id")
    selected_chassis = data.get("selected_chassis_family")
    expected_chassis = DECK_TO_CHASSIS.get(selected_deck)
    if expected_chassis is None:
        errors.append("selected_deck_candidate_id is not a current Rev-C deck candidate")
    elif selected_chassis != expected_chassis:
        errors.append(
            "selected chassis family disagrees with selected deck candidate: "
            f"expected {expected_chassis}"
        )

    selected_topology = data.get("selected_topology_for_measurement")
    selected_brake = data.get("selected_brake_architecture")
    expected_brake = TOPOLOGY_TO_BRAKE.get(selected_topology)
    if expected_brake is None:
        errors.append("selected_topology_for_measurement is not a current Rev-C topology")
    elif selected_brake != expected_brake:
        errors.append(
            "selected brake architecture disagrees with selected topology: "
            f"expected {expected_brake}"
        )

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
        if not _valid_fit_pilot_authority(fit_pilot_authority):
            errors.append(
                "linked fit-pilot authority is invalid, unqualified, or lacks Issue #59/#61 provenance"
            )
        elif refs.get("fit_pilot_authority_fingerprint_sha256") != fit_pilot_authority.get(
            "authority_fingerprint_sha256"
        ):
            errors.append("release references a different fit-pilot authority")

    if deck_authority is not None:
        if not _valid_authority(deck_authority, "x1_rev_c_deck_comparison"):
            errors.append("linked deck-comparison authority is invalid")
        elif refs.get(
            "deck_comparison_authority_fingerprint_sha256"
        ) != deck_authority.get("authority_fingerprint_sha256"):
            errors.append("release references a different deck-comparison authority")
        elif data.get("selected_deck_candidate_id") != deck_authority.get(
            "selected_candidate_id"
        ):
            errors.append("release selected deck disagrees with deck-comparison authority")

    if topology_authority is not None:
        if not _valid_authority(topology_authority, "x1_rev_c_topology_trade"):
            errors.append("linked topology-trade authority is invalid")
        elif refs.get(
            "topology_trade_authority_fingerprint_sha256"
        ) != topology_authority.get("authority_fingerprint_sha256"):
            errors.append("release references a different topology-trade authority")
        elif data.get("selected_topology_for_measurement") != topology_authority.get(
            "selected_topology_for_measurement"
        ):
            errors.append("release topology disagrees with topology-trade authority")

    if inert_pack_authority is not None:
        if not _valid_authority(
            inert_pack_authority, "x1_rev_c_inert_pack_envelope"
        ):
            errors.append("linked inert-pack envelope authority is invalid")
        elif refs.get(
            "inert_pack_envelope_authority_fingerprint_sha256"
        ) != inert_pack_authority.get("authority_fingerprint_sha256"):
            errors.append("release references a different inert-pack envelope authority")
        elif inert_pack_authority.get("range_pack_inert_envelope_plausible") is not True:
            errors.append("linked inert-pack authority does not qualify the range envelope")
        elif inert_pack_authority.get("chassis_candidate_id") != data.get(
            "selected_chassis_family"
        ):
            errors.append(
                "release chassis disagrees with inert-pack envelope authority"
            )

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
        "selected_deck_candidate_id": data.get("selected_deck_candidate_id"),
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
    parser.add_argument("--deck-authority", type=Path, required=True)
    parser.add_argument("--topology-authority", type=Path, required=True)
    parser.add_argument("--inert-pack-authority", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = qualify(
        json.loads(args.manifest.read_text(encoding="utf-8")),
        json.loads(args.fit_pilot_authority.read_text(encoding="utf-8")),
        json.loads(args.deck_authority.read_text(encoding="utf-8")),
        json.loads(args.topology_authority.read_text(encoding="utf-8")),
        json.loads(args.inert_pack_authority.read_text(encoding="utf-8")),
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
