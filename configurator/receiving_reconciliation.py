"""Python twin of the source-bound, unverified physical-receiving review."""
from __future__ import annotations
from typing import Any
from configurator.evidence_notebook import restore_evidence_notebook

AUTHORITY = {
    "procurement_authorized": False, "fabrication_authorized": False,
    "charging_authorized": False, "powered_operation_authorized": False,
    "generic_builder_may_promote_x1_authority": False,
}


def build_receiving_reconciliation(passport: dict[str, Any], raw_notebook: Any,
                                   document_index: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(passport, dict) or passport.get("scope") != "NON_AUTHORITATIVE_BUILD_PASSPORT" or not isinstance(passport.get("study_identity_key"), str) or not isinstance(passport.get("parts"), list):
        raise ValueError("Receiving reconciliation needs a Build Passport snapshot")
    if not isinstance(document_index, dict) or document_index.get("scope") != "PUBLIC_MANUFACTURER_REFERENCES_NOT_EXACT_VARIANT_INSTRUCTIONS" or document_index.get("schema_version") != 1 or not isinstance(document_index.get("entries"), list):
        raise ValueError("Receiving reconciliation needs a vetted public-reference catalog")
    notebook = restore_evidence_notebook(passport, raw_notebook)
    entries = {}
    for entry in document_index["entries"]:
        if not isinstance(entry.get("id"), str) or entry["id"] in entries or not isinstance(entry.get("component_ids"), list) or not isinstance(entry.get("url"), str) or not entry["url"].startswith("https://") or entry.get("exact_revision_verified") is not False:
            raise ValueError("Invalid or duplicate public document reference")
        entries[entry["id"]] = entry
    audit = passport.get("assembly_inventory_audit") or {}
    possible_overlaps = audit.get("overlap_worklist") or []
    donors = audit.get("package_claims") or []
    rows = []
    for part in passport["parts"]:
        receipts = [x for x in notebook["records"] if x["kind"] == "RECEIVING_OBSERVATION" and x["component_id"] == part["component_id"]]
        last = receipts[-1] if receipts else None
        revisions = sorted(set(x["observed_revision"] for x in receipts))
        counts = sorted(set(str(x["quantity_received"]) for x in receipts))
        conflicting = len(revisions) > 1 or len(counts) > 1
        candidates = [x for x in notebook["records"] if x["kind"] == "MANUFACTURER_INSTRUCTIONS_CANDIDATE" and x["component_id"] == part["component_id"]]
        docs = [{
            "id": x["id"], "title": x["title"], "url": x["url"],
            "role": x["document_role"], "scope_note": x["scope_note"],
            "exact_revision_verified": False
        } for x in entries.values() if part["component_id"] in x["component_ids"]]
        overlap = sorted(x["package_id"] for x in possible_overlaps if x["component_id"] == part["component_id"])
        donor = any(x["package_id"] == part["component_id"] for x in donors)
        missing = [
            *([] if receipts else ["RECEIVING_OBSERVATION"]),
            *([] if not conflicting else ["CONFLICTING_RECEIPT_HISTORY"]),
            *([] if not donor else ["DONOR_CONTENTS_AND_INCLUSIONS_INSPECTION"]),
            *([] if not overlap else ["POSSIBLE_DONOR_DOUBLE_COUNT"]),
            *([] if docs else ["MANUFACTURER_DOCUMENT_REFERENCE"]),
            "INDEPENDENT_RECEIVED_REVISION_VERIFICATION",
            "EXACT_REVISION_APPLICABLE_MAKER_MANUAL",
            "VERIFIED_BOM_ASSEMBLY_QUANTITY",
            "VERIFIED_SUPPLIER_ORDER_UNIT",
            "INDEPENDENT_PHYSICAL_FIT_AND_SAFETY",
        ]
        rows.append({
            "component_id": part["component_id"],
            "label": part["label"],
            "variant_identity_key": part["variant_identity_key"],
            "catalog_sku_text": part["sku_text"],
            "recorded_receiving_count": len(receipts),
            "last_observation": None if not last else {
                "observed_revision": last["observed_revision"],
                "quantity_received": last["quantity_received"],
                "observed_as_of": last["as_of"],
                "receipt_seq": last["seq"],
                "authority": "USER_REPORTED_NOT_VERIFIED",
            },
            "receipt_history_status": "NO_RECEIVING_OBSERVATION" if not receipts else (
                "CONFLICTING_RECEIPT_HISTORY_REVIEW" if conflicting else
                "SELF_REPORTED_RECEIPT_NEEDS_INDEPENDENT_REVIEW"
            ),
            "received_inventory_verified": False,
            "physical_revision_verified": False,
            "actual_assembly_quantity": None,
            "actual_supplier_order_quantity": None,
            "potential_overlap_package_ids": overlap,
            "donor_content_evidence_status": "UNVERIFIED_DONOR_CONTENTS" if donor else
                "NOT_A_SELECTED_DONOR_PACKAGE",
            "manufacturer_reference_documents": docs,
            "user_manual_candidate_count": len(candidates),
            "revision_matched_manufacturer_manual_verified": False,
            "missing_evidence": missing,
        })
    missing_receipt = [x["component_id"] for x in rows if x["recorded_receiving_count"] == 0]
    conflict = [x["component_id"] for x in rows if x["receipt_history_status"] == "CONFLICTING_RECEIPT_HISTORY_REVIEW"]
    donor_work = [x["component_id"] for x in rows if x["donor_content_evidence_status"] == "UNVERIFIED_DONOR_CONTENTS"]
    return {
        "schema_version": 1, "scope": "UNVERIFIED_RECEIVING_RECONCILIATION",
        "candidate_id": passport["candidate_id"],
        "study_identity_key": passport["study_identity_key"],
        "document_index_reviewed_as_of": document_index["reviewed_as_of"],
        "evidence_record_count": len(notebook["records"]),
        "rows": rows,
        "review_queue": {
            "no_receiving_observation_ids": missing_receipt,
            "conflicting_receipt_history_ids": conflict,
            "donor_contents_uninspected_ids": donor_work,
            "donor_overlap_questions": [{
                "package_id": x["package_id"], "component_id": x["component_id"],
                "question": x["review_question"], "physically_resolved": False
            } for x in possible_overlaps],
            "retrofit_questions": [{
                "package_id": x["package_id"], "component_id": x["component_id"],
                "question": x["question"], "physically_resolved": False
            } for x in (audit.get("retrofit_worklist") or [])],
            "unresolved_interface_ids": sorted(x["id"] for x in passport["interface_claims"]),
        },
        "confirmation": {
            "order_lines_qualified": 0, "physical_part_revisions_qualified": 0,
            "manufacturer_manuals_revision_verified": 0, "received_contents_qualified": 0,
            "price_quotes_current_verified": 0, "physical_qualification": "NOT_QUALIFIED",
        },
        "authority": dict(AUTHORITY),
        "disclaimer": "A user-reported count is not inventoried stock, a design quantity or an order count. Old or mismatched snapshots are rejected. Official manufacturer pages provide general documentation context only; no applicable exact revision or physical fit is established.",
    }
