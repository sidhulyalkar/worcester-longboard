"""Revision-bound, user-reported evidence notebook. No physical safety authority."""
from __future__ import annotations
import json
import re
from datetime import date
from urllib.parse import urlsplit
from typing import Any

AUTHORITY = {
    "procurement_authorized": False, "fabrication_authorized": False,
    "charging_authorized": False, "powered_operation_authorized": False,
    "generic_builder_may_promote_x1_authority": False,
}
EVIDENCE_KINDS = (
    "SOURCE_REFERENCE", "RECEIVING_OBSERVATION",
    "MANUFACTURER_INSTRUCTIONS_CANDIDATE", "INTERFACE_MEASUREMENT_NOTE",
)


def _text(value: Any, max_length: int = 240) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or len(value) > max_length or not value.strip():
        raise ValueError("Invalid bounded evidence text")
    result = value.strip()
    if any(ord(c) < 32 or ord(c) == 127 for c in result):
        raise ValueError("Evidence contains control characters")
    return result


def _url(value: Any) -> str | None:
    raw = _text(value, 600)
    if raw is None:
        return None
    parsed = urlsplit(raw)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or " " in parsed.netloc:
        raise ValueError("Evidence link must be an HTTPS URL without credentials")
    return raw


def _date(value: Any) -> str | None:
    raw = _text(value, 10)
    if raw is None:
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raise ValueError("Use a real YYYY-MM-DD evidence date")
    try:
        date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("Use a real YYYY-MM-DD evidence date") from exc
    return raw


def _passport(passport: dict[str, Any]) -> None:
    if not isinstance(passport, dict) or passport.get("scope") != "NON_AUTHORITATIVE_BUILD_PASSPORT" or not isinstance(passport.get("study_identity_key"), str) or not isinstance(passport.get("parts"), list) or not isinstance(passport.get("interface_claims"), list):
        raise ValueError("Evidence notebook needs a complete Build Passport")


def empty_evidence_notebook(passport: dict[str, Any]) -> dict[str, Any]:
    _passport(passport)
    return {
        "schema_version": 1, "scope": "SELF_REPORTED_UNVERIFIED_EVIDENCE",
        "candidate_id": passport["candidate_id"],
        "study_identity_key": passport["study_identity_key"],
        "records": [], "authority": dict(AUTHORITY),
    }


def _assert_notebook(passport: dict[str, Any], book: dict[str, Any]) -> None:
    _passport(passport)
    if not isinstance(book, dict) or book.get("schema_version") != 1 or book.get("scope") != "SELF_REPORTED_UNVERIFIED_EVIDENCE" or book.get("candidate_id") != passport["candidate_id"] or book.get("study_identity_key") != passport["study_identity_key"] or not isinstance(book.get("records"), list) or len(book["records"]) > 80:
        raise ValueError("Evidence notebook belongs to a different Build Passport snapshot")


def record_evidence(book: dict[str, Any], passport: dict[str, Any], fields: dict[str, Any]) -> dict[str, Any]:
    _assert_notebook(passport, book)
    if not isinstance(fields, dict) or fields.get("kind") not in EVIDENCE_KINDS:
        raise ValueError("Select a supported evidence record kind")
    kind = fields["kind"]
    component_id = _text(fields.get("component_id"), 128)
    part = next((p for p in passport["parts"] if p["component_id"] == component_id), None)
    if part is None:
        raise ValueError("Evidence component is not in this exact passport")
    interface_id = _text(fields.get("interface_id"), 240)
    if interface_id and not any(x["id"] == interface_id and component_id in x["component_ids"] for x in passport["interface_claims"]):
        raise ValueError("Interface claim does not include the selected component")
    if kind == "INTERFACE_MEASUREMENT_NOTE" and not interface_id:
        raise ValueError("Measurement notes must name an affected interface claim")
    if kind != "INTERFACE_MEASUREMENT_NOTE" and interface_id:
        raise ValueError("Interface ID is only supported on measurement notes")
    revision = _text(fields.get("observed_revision"), 120)
    quantity = fields.get("quantity_received")
    if quantity == "":
        quantity = None
    if quantity is not None and (not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1 or quantity > 500):
        raise ValueError("Receiving count must be a positive integer at most 500")
    url = _url(fields.get("evidence_url"))
    as_of = _date(fields.get("as_of"))
    note = _text(fields.get("note"), 500)
    if revision is None and quantity is None and url is None and note is None:
        raise ValueError("Record a revision, quantity, HTTPS evidence link or observation")
    if kind == "SOURCE_REFERENCE" and (not url or not as_of):
        raise ValueError("Source reference requires an HTTPS link and date")
    if kind == "MANUFACTURER_INSTRUCTIONS_CANDIDATE" and (not url or not as_of or not revision):
        raise ValueError("Instruction candidate requires HTTPS link, date and exact marked revision")
    if kind == "RECEIVING_OBSERVATION" and (not revision or quantity is None or not as_of):
        raise ValueError("Receiving observation needs exact marked revision, received count and date")
    if kind == "INTERFACE_MEASUREMENT_NOTE" and not note:
        raise ValueError("Interface note must describe the measured question and missing evidence")
    if kind != "RECEIVING_OBSERVATION" and quantity is not None:
        raise ValueError("Received count only applies to receiving observations")
    if len(book["records"]) >= 80:
        raise ValueError("Notebook limit reached; export before more entries")
    record = {
        "seq": len(book["records"]) + 1, "kind": kind, "component_id": component_id,
        "interface_id": interface_id, "target_variant_identity_key": part["variant_identity_key"],
        "observed_revision": revision, "quantity_received": quantity,
        "evidence_url": url, "as_of": as_of, "note": note,
        "review_status": "USER_RECORDED_NOT_INDEPENDENTLY_VERIFIED",
        "usable_for_qualification": False,
    }
    return {**empty_evidence_notebook(passport), "records": [*book["records"], record]}


def restore_evidence_notebook(passport: dict[str, Any], raw: Any) -> dict[str, Any]:
    empty = empty_evidence_notebook(passport)
    if not raw:
        return empty
    try:
        input_data = json.loads(raw) if isinstance(raw, str) else raw
        _assert_notebook(passport, input_data)
        restored = empty
        for record in input_data["records"]:
            part = next((p for p in passport["parts"] if p["component_id"] == record["component_id"]), None)
            if not part or part["variant_identity_key"] != record["target_variant_identity_key"]:
                return empty
            restored = record_evidence(restored, passport, record)
        return restored
    except (ValueError, TypeError, KeyError, AttributeError, json.JSONDecodeError):
        return empty


def evaluate_evidence_notebook(passport: dict[str, Any], book: dict[str, Any]) -> dict[str, Any]:
    _assert_notebook(passport, book)
    observed, instructions, sources, invalidated, measurements = (set() for _ in range(5))
    part_index = {p["component_id"]: p for p in passport["parts"]}
    for record in book["records"]:
        if record["kind"] == "RECEIVING_OBSERVATION":
            observed.add(record["component_id"])
            part = part_index[record["component_id"]]
            for claim in passport["interface_claims"]:
                if record["component_id"] in claim["component_ids"] or part["included_by_donor"]:
                    invalidated.add(claim["id"])
        if record["kind"] == "MANUFACTURER_INSTRUCTIONS_CANDIDATE":
            instructions.add(record["component_id"])
        if record["kind"] == "SOURCE_REFERENCE":
            sources.add(record["component_id"])
        if record["kind"] == "INTERFACE_MEASUREMENT_NOTE":
            measurements.add(record["interface_id"])
    return {
        "schema_version": 1, "scope": "USER_EVIDENCE_REVIEW_QUEUE",
        "candidate_id": passport["candidate_id"],
        "evidence_count": len(book["records"]),
        "receiving_observed_part_ids": sorted(observed),
        "source_reference_part_ids": sorted(sources),
        "instruction_candidates_part_ids": sorted(instructions),
        "noted_interface_ids": sorted(measurements),
        "invalidated_interface_ids": sorted(invalidated),
        "still_unverified_part_ids": [p["component_id"] for p in passport["parts"] if p["component_id"] not in observed],
        "unresolved_interface_ids": sorted(
            x["id"] for x in passport["interface_claims"]
            if x["reference_state"] in ("UNKNOWN", "MEASURE_FIRST")
        ),
        "manufacturer_manuals_independently_verified": 0,
        "assembly_quantities_authorized": 0, "stock_confirmed": 0,
        "physical_qualification": "NOT_QUALIFIED",
        "authority": dict(AUTHORITY),
        "note": "All entries are user-provided observations or candidate links. Receiving counts are not order quantities; notes do not resolve interface claims. Independent revision-specific evidence and separate engineering approvals remain necessary.",
    }
