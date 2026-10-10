"""Exact Python mirror of the non-authoritative donor inclusion/ordering-unit audit."""
from __future__ import annotations
from typing import Any

AUTHORITY = {
    "procurement_authorized": False, "fabrication_authorized": False,
    "charging_authorized": False, "powered_operation_authorized": False,
    "generic_builder_may_promote_x1_authority": False,
}


def _invalid(message: str) -> None:
    raise ValueError("Package inclusion registry: " + message)


def audit_assembly_inventory(passport: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(passport, dict) or passport.get("scope") != "NON_AUTHORITATIVE_BUILD_PASSPORT" or not isinstance(passport.get("parts"), list) or not passport.get("study_identity_key"):
        raise ValueError("Assembly inventory requires exact Build Passport snapshot")
    if not isinstance(registry, dict) or registry.get("schema_version") != 1 or registry.get("scope") != "CATALOG_INCLUSION_HYPOTHESES_NOT_PACKAGE_CERTIFICATION" or not isinstance(registry.get("packages"), list):
        _invalid("unexpected schema")
    parts = {p["component_id"]: p for p in passport["parts"]}
    if len(parts) != len(passport["parts"]):
        raise ValueError("Duplicate BOM component ID cannot be treated as a resolved order")
    packages: list[dict[str, Any]] = []
    overlap: list[dict[str, Any]] = []
    retrofit: list[dict[str, Any]] = []
    unknown_tokens: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pkg in registry["packages"]:
        if not isinstance(pkg, dict) or not isinstance(pkg.get("component_id"), str) or pkg["component_id"] in seen:
            _invalid("missing or duplicate donor package id")
        seen.add(pkg["component_id"])
        if not isinstance(pkg.get("inclusions"), list) or not isinstance(pkg.get("retrofit_warnings"), list):
            _invalid("missing inclusion/retrofit lists")
        part = parts.get(pkg["component_id"])
        if part is None:
            continue
        tokens = part.get("included_by_donor") or []
        declared = [x["token"] for x in pkg["inclusions"]]
        if len(set(declared)) != len(declared) or len(tokens) != len(declared) or not all(t in tokens for t in declared):
            _invalid("included token mismatch for " + pkg["component_id"])
        snapshot_matches = (
            part["supplier"]["snapshot_id"] == pkg.get("catalog_snapshot_id") and
            part["sku_text"] == pkg.get("catalog_sku_text") and
            not part.get("proposed_revision")
        )
        packages.append({
            "package_id": pkg["component_id"],
            "reference_source_snapshot_id": pkg.get("catalog_snapshot_id"),
            "snapshot_binding_status": "BOUND_TO_REFERENCE_SNAPSHOT" if snapshot_matches else "STALE_OR_CHANGED_SOURCE_HOLD",
            "exact_received_contents_verified": False, "order_unit_quantity": None,
            "source_document_status": "PACKAGE_CONTENTS_UNVERIFIED",
        })
        for entry in pkg["inclusions"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("token"), str) or not isinstance(entry.get("possible_catalog_reference_ids"), list) or not isinstance(entry.get("review_question"), str) or not entry["review_question"].strip():
                _invalid("invalid inclusion token entry")
            for related_id in entry["possible_catalog_reference_ids"]:
                if not isinstance(related_id, str) or related_id == pkg["component_id"]:
                    _invalid("invalid possible included catalog reference")
            selected = [x for x in entry["possible_catalog_reference_ids"] if x in parts]
            for part_id in selected:
                overlap.append({
                    "package_id": pkg["component_id"], "component_id": part_id,
                    "inclusion_token": entry["token"],
                    "classification": "POSSIBLE_DOUBLE_COUNT" if snapshot_matches else "MAPPING_STALE_CONSERVATIVE_HOLD",
                    "source_snapshot_verified_for_exact_revision": False,
                    "possible_included_quantity": None,
                    "review_question": entry["review_question"],
                    "action": "Check actual received contents and vendor assembly/order units before pricing or buying",
                })
            if not entry["possible_catalog_reference_ids"] or not snapshot_matches:
                unknown_tokens.append({
                    "package_id": pkg["component_id"], "inclusion_token": entry["token"],
                    "reason": "STALE_OR_CHANGED_SOURCE_HOLD" if not snapshot_matches else "NO_EXACT_CATALOG_COUNTERPART",
                    "review_question": entry["review_question"],
                })
        known_tokens = set(declared)
        for warn in pkg["retrofit_warnings"]:
            if not isinstance(warn, dict) or not isinstance(warn.get("when_component_id"), str) or not isinstance(warn.get("included_token"), str) or warn["included_token"] not in known_tokens or not warn.get("question"):
                _invalid("invalid retrofit reference")
            if warn["when_component_id"] in parts:
                retrofit.append({
                    "package_id": pkg["component_id"],
                    "component_id": warn["when_component_id"],
                    "related_inclusion_token": warn["included_token"],
                    "status": "MEASURE_AND_VERIFY_RETROFIT_BEFORE_PHYSICAL_USE",
                    "question": warn["question"],
                })
    for part in passport["parts"]:
        if part.get("included_by_donor") and part["component_id"] not in seen:
            packages.append({
                "package_id": part["component_id"], "reference_source_snapshot_id": None,
                "snapshot_binding_status": "UNMAPPED_BUNDLE_HOLD",
                "exact_received_contents_verified": False, "order_unit_quantity": None,
                "source_document_status": "PACKAGE_CONTENTS_UNVERIFIED",
            })
            for token in part["included_by_donor"]:
                unknown_tokens.append({
                    "package_id": part["component_id"], "inclusion_token": token,
                    "reason": "NO_REVIEWED_BUNDLE_MAPPING",
                    "review_question": "Determine exact received contents, variants and quantities",
                })
    overlap_by_part: dict[str, list[str]] = {}
    for row in overlap:
        overlap_by_part.setdefault(row["component_id"], []).append(row["package_id"])
    order_lines = [{
        "component_id": p["component_id"],
        "variant_identity_key": p["variant_identity_key"],
        "catalog_price_reference_multiplier": p["price"].get("pricing_reference_qty"),
        "actual_assembly_quantity": None,
        "actual_supplier_order_quantity": None,
        "vendor_package_unit_description": None,
        "donor_overlap_candidate_ids": sorted(set(overlap_by_part.get(p["component_id"], []))),
        "current_availability": "UNKNOWN_NOT_LIVE",
        "quote_verified": False,
        "state": "HOLD_RECEIVING_AND_ORDER_UNIT_AUDIT",
    } for p in passport["parts"]]
    source_worklist = [{
        "component_id": p["component_id"],
        "missing": [
            *([] if p["supplier"].get("source_url") else ["VENDOR_SOURCE_URL"]),
            *([] if p["supplier"].get("snapshot_id") else ["SOURCE_SNAPSHOT"]),
            *([] if p.get("sku_text") else ["EXACT_SKU_OR_VARIANT"]),
            "EXACT_PHYSICAL_REVISION",
            "REVISION_MATCHED_MANUFACTURER_INSTRUCTIONS",
            "CURRENT_STOCK_CHECK",
            "VERIFIED_ASSEMBLY_QUANTITY",
            "VERIFIED_VENDOR_ORDER_UNIT",
            "CONFIRMED_CURRENT_QUOTE",
        ],
        "source_health": p["supplier"].get("source_health") or "HEALTH_UNAVAILABLE",
    } for p in passport["parts"]]
    packages.sort(key=lambda x: x.get("package_id") or "")
    overlap.sort(key=lambda x: ":".join((x.get("package_id") or "", x.get("component_id") or "")))
    retrofit.sort(key=lambda x: ":".join((x.get("package_id") or "", x.get("component_id") or "")))
    unknown_tokens.sort(key=lambda x: ":".join((x.get("package_id") or "", x.get("inclusion_token") or "")))
    return {
        "schema_version": 1, "scope": "NON_AUTHORITATIVE_ASSEMBLY_INCLUSION_AUDIT",
        "candidate_id": passport["candidate_id"],
        "study_identity_key": passport["study_identity_key"],
        "source_note": "Bundle inclusion labels describe vendor/catalog reference claims only. Similar part families do not establish equal revisions, included quantities, fit, or a buyable kit.",
        "package_claims": packages, "overlap_worklist": overlap,
        "retrofit_worklist": retrofit, "unmapped_inclusion_worklist": unknown_tokens,
        "order_lines": order_lines, "source_worklist": source_worklist,
        "costs": {
            "existing_bom_subtotal_has_possible_double_count": bool(overlap),
            "overlap_adjusted_total_usd": None, "confirmed_quote_total_usd": None,
            "all_in_assembly_total_usd": None,
            "warning": "Never subtract bundled items from the existing BOM by guess. Source values are not assembly quotes.",
        },
        "eligibility": {
            "parts_quantities_qualified": False, "bundle_contents_qualified": False,
            "manual_instructions_qualified": False, "mechanical_interfaces_qualified": False,
            "electrical_integration_qualified": False,
        },
        "authority": dict(AUTHORITY),
    }
