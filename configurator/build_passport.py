"""Revision-aware non-authoritative Build Passport, Python mirror of builder/build_passport.mjs."""
from __future__ import annotations
import copy
import json
import math
from typing import Any

from configurator.assembly_inventory import audit_assembly_inventory

AUTHORITY = {
    "procurement_authorized": False, "fabrication_authorized": False,
    "charging_authorized": False, "powered_operation_authorized": False,
    "generic_builder_may_promote_x1_authority": False,
}
POWER = {"battery", "charger", "esc", "motor", "drive"}
STAGE = [
    ("study", "Study / verify the source", "STUDY_ONLY", "Beginner: identify selected variants, prices, manufacturer instructions and source dates"),
    ("receive", "Receiving and variant inspection", "HOLD_REVISION", "Document actual manufacturer, SKU, label photos, revision markings, included pieces and condition before any assembly"),
    ("fit", "Mechanical interface measurement", "HOLD_MEASURE", "Measure deck/truck mounts, axle/hub fit, retention, steering sweep, brake and drive clearance against exact received revisions"),
    ("mechanical", "Mechanical construction readiness", "QUALIFICATION_REQUIRED", "Use manufacturer instructions, specified fasteners and independent mechanical inspection only after separate qualification"),
    ("electrical", "Electrical system integration", "POWER_GATED", "Qualified electrical specialist only; use a separately approved pack, BMS, fuse, wiring enclosure and matched charger"),
    ("release", "Independent validation and release", "QUALIFICATION_REQUIRED", "Obtain independent structural, braking and controls verification under a separately authorized protocol"),
]


def identity(fields: list[Any]) -> str:
    return json.dumps(fields, separators=(",", ":"), ensure_ascii=False)


def numeric(value: Any) -> float | int | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def two(value: float) -> float:
    # Inputs are nonnegative, so JS Math.round with epsilon and Python round(x+epsilon,2) agree
    return math.floor((value + 1.11e-16) * 100 + .5) / 100


def price_snapshot(part: dict[str, Any]) -> dict[str, Any]:
    price = part.get("price") or {}
    qty = numeric(price.get("qty"))
    if qty is None:
        qty = 1
    lo = hi = None
    if price and qty > 0:
        if price.get("kind") == "unit" and numeric(price.get("unit_price_usd")) is not None:
            lo = hi = two(price["unit_price_usd"] * qty)
        elif price.get("kind") == "ceiling" and numeric(price.get("unit_price_usd")) is not None:
            hi = two(price["unit_price_usd"] * qty)
        elif price.get("kind") == "range" and numeric(price.get("min_usd")) is not None and numeric(price.get("max_usd")) is not None:
            lo = two(price["min_usd"] * qty)
            hi = two(price["max_usd"] * qty)
    source = part.get("source") or {}
    sourced = source.get("kind") in ("vendor", "retailer", "manufacturer") and source.get("snapshot_id") and source.get("as_of")
    return {
        "kind": price.get("kind") or "UNPRICED",
        "pricing_reference_qty": price.get("qty"),
        "assembly_required_qty": None,
        "quantity_authority": "CATALOG_PRICE_MULTIPLIER_NOT_ASSEMBLY_QUANTITY",
        "min_usd": lo, "max_usd": hi,
        "price_basis": (
            "DATED_SOURCE_CEILING_USD" if sourced else "UNSOURCED_PLANNING_CEILING_USD"
        ) if price.get("kind") == "ceiling" and hi is not None else (
            "UNKNOWN" if lo is None else "DATED_SOURCE_REFERENCE_USD" if sourced
            else "UNSOURCED_PLANNING_ESTIMATE_USD"
        ),
        "native_price_snapshot": source.get("native_price_snapshot") or None,
        "availability": "UNKNOWN_NOT_LIVE",
        "quote_verified": False,
    }


def build_build_passport(candidate: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    if not candidate or not candidate.get("id") or not isinstance(candidate.get("evidence"), dict) or not isinstance(candidate.get("bom"), list) or not (bundle or {}).get("catalog", {}).get("components"):
        raise ValueError("Passport requires a scored candidate and catalog")
    index = {row["id"]: row for row in bundle["catalog"]["components"]}
    health = {row["component_id"]: row for row in bundle.get("catalogHealth", {}).get("component_health", [])}
    parts = []
    for row in candidate["bom"]:
        component_id = row["component_id"]
        if component_id not in index:
            raise ValueError("Missing catalog part " + component_id)
        c = index[component_id]
        h = health.get(component_id, {})
        source = c.get("source") or {}
        raw_revision = c.get("revision")
        revision = raw_revision if isinstance(raw_revision, str) and raw_revision.strip() else None
        dated_source = source.get("snapshot_id") and source.get("as_of") and source.get("url")
        part_identity = identity([c["id"], c.get("sku") or None, revision, source.get("snapshot_id") or None, source.get("as_of") or None])
        parts.append({
            "component_id": c["id"], "category": c["category"], "label": c["label"],
            "manufacturer": c.get("manufacturer") or None, "sku_text": c.get("sku") or None,
            "catalog_revision": revision,
            "revision_status": "EXACT_VARIANT_REVISION_UNVERIFIED",
            "variant_identity_key": part_identity,
            "procurement_state": c.get("procurement_state"),
            "evidence_state": c.get("evidence_state"),
            "supplier": {
                "name": source.get("seller") or None, "source_url": source.get("url") or None,
                "source_kind": source.get("kind") or "UNKNOWN",
                "snapshot_id": source.get("snapshot_id") or None,
                "catalog_as_of": source.get("as_of") or None,
                "verified_as_of": h.get("verified_as_of"),
                "source_health": h.get("status") or "HEALTH_UNAVAILABLE",
                "verified_specific_revision": False, "verified_current_stock": False,
                "source_status": "DATED_REFERENCE_ONLY" if dated_source else "INCOMPLETE_OR_NON_VENDOR_REFERENCE",
            },
            "price": price_snapshot(c),
            "included_by_donor": list(c["includes"]) if isinstance(c.get("includes"), list) else [],
            "hold_reason": c.get("hold_reason") or None,
            "manufacturer_instructions_url": None,
            "instructions_state": "MANUFACTURER_INSTRUCTIONS_NOT_INDEXED",
            "receiving_checks": [
                "Record exact received brand/SKU/revision and photograph markings",
                "Verify item counts, contents, damage and included fasteners against maker documentation",
                "Obtain revision-matched installation and torque instructions",
            ],
        })
    part_index = {p["component_id"]: p for p in parts}
    dep_keys = {x["component_id"]: identity([x["component_id"], None, None, x.get("snapshot_id") or None, x.get("verified_as_of") or None])
                for x in candidate["evidence"].get("source_evidence", [])}
    interfaces = []
    for rule in candidate["evidence"].get("interfaces", []):
        ids = sorted([rule["a"], rule["b"]])
        interfaces.append({
            "id": rule["id"], "component_ids": ids, "reference_state": rule["state"],
            "catalog_rule_origin": rule.get("evidence_kind") or "UNKNOWN_RULE_SOURCE",
            "reason": rule["reason"],
            "variant_binding": [{
                "component_id": x,
                "identity_key": part_index[x]["variant_identity_key"] if x in part_index else dep_keys.get(x),
                "direct_bom_part": x in part_index,
            } for x in ids],
            "revision_evidence_state": "EXACT_VARIANT_CONFIRMATION_REQUIRED",
            "valid_for_physical_build": False,
        })
    interfaces.sort(key=lambda x: x["id"])
    sourced = [p for p in parts if p["price"]["min_usd"] is not None and p["price"]["price_basis"] == "DATED_SOURCE_REFERENCE_USD"]
    planning = [p for p in parts if p["price"]["min_usd"] is not None and p["price"]["price_basis"] == "UNSOURCED_PLANNING_ESTIMATE_USD"]

    def sums(rows: list[dict[str, Any]], key: str) -> float:
        return two(sum(p["price"][key] for p in rows))

    drive_path = (candidate.get("capabilities") or {}).get("drive_path")
    powered = any(p["category"] in POWER for p in parts) or drive_path is not None and drive_path != "NOT_PRESENT"
    stages = []
    for stage_id, label, status, skill in STAGE:
        resolved_status = ("NOT_APPLICABLE" if stage_id == "electrical" and not powered
                           else "POWER_GATED" if stage_id == "release" and powered else status)
        required_evidence = {
            "study": "Dated vendor sources and variant-specific manuals",
            "receive": "Receiving photos and exact counts",
            "fit": "Dimensioned measurements, brake and retention evidence",
            "mechanical": "Qualified drawings, torque and inspection records",
            "electrical": "Professional electrical/battery/charger review",
            "release": "Independent qualification artifacts and formal authority",
        }[stage_id]
        stages.append({"id": stage_id, "label": label, "status": resolved_status,
                       "skills_and_work": skill, "required_evidence": required_evidence})
    passport = {
        "schema_version": 1, "scope": "NON_AUTHORITATIVE_BUILD_PASSPORT",
        "candidate_id": candidate["id"], "candidate_label": candidate.get("label"),
        "origin": candidate.get("origin") or "CURATED",
        "study_identity_key": identity([candidate["id"], *sorted(p["variant_identity_key"] for p in parts)]),
        "parts": parts, "interface_claims": interfaces,
        "sourcing": {
            "sourced_usd_snapshot": {"min": sums(sourced, "min_usd"), "max": sums(sourced, "max_usd")},
            "unsourced_planning_usd_estimate": {"min": sums(planning, "min_usd"), "max": sums(planning, "max_usd")},
            "native_currency_snapshots": [{"component_id": p["component_id"], "raw_text": p["price"]["native_price_snapshot"]}
                                          for p in parts if p["price"]["native_price_snapshot"]],
            "unpriced_ids": [p["component_id"] for p in parts if p["price"]["min_usd"] is None and p["price"]["max_usd"] is None],
            "ceiling_only_ids": [p["component_id"] for p in parts if p["price"]["min_usd"] is None and p["price"]["max_usd"] is not None],
            "all_in_total_usd": None, "all_in_status": "UNKNOWN_INCOMPLETE_COST_AND_QUANTITY",
            "purchase_quantities_confirmed": False, "live_stock_verified": False,
            "exclusions": ["shipping", "sales tax/duties", "tools and PPE",
                           "professional assembly and electrical inspection", "testing/validation",
                           "quantity and inclusion audit"],
        },
        "assembly": {
            "powered": bool(powered), "stages": stages,
            "instructions_status": "REQUIRES_EXACT_VARIANT_MANUFACTURER_MANUALS",
            "receiving_inspection_complete": False,
            "electrical_integration_authorized": False,
            "chassis_assembly_authorized": False,
            "note": "Assembly planning/learning only. Never energize or charge from this guide.",
        },
        "unresolved": {
            "blocker_reasons": list(candidate.get("blockers") or []),
            "measurement_worklist": [{
                "id": x["id"], "component_ids": list(x["component_ids"]),
                "state": x["state"], "question": x["question"],
                "evidence_required": x["evidence_required"]
            } for x in candidate["evidence"].get("measurement_worklist", [])],
            "unverified_revision_part_ids": [p["component_id"] for p in parts if p["revision_status"] != "VERIFIED_EXACT_REVISION"],
            "missing_manual_part_ids": [p["component_id"] for p in parts if not p["manufacturer_instructions_url"]],
            "source_refresh_ids": [p["component_id"] for p in parts if p["supplier"]["source_health"] != "SOURCE_FRESH"],
            "donor_inclusion_review_ids": [p["component_id"] for p in parts if p["included_by_donor"]],
        },
        "physical_qualification": "NOT_QUALIFIED", "authority": dict(AUTHORITY),
        "disclaimer": "Catalog reference, SKU text, vendor listing and source price do not specify a revision-qualified, compatible or buyable kit.",
    }
    if bundle.get("packageInclusions"):
        passport["assembly_inventory_audit"] = audit_assembly_inventory(passport, bundle["packageInclusions"])
    return passport


def propose_passport_revision_change(passport: dict[str, Any], component_id: str, new_revision: str) -> dict[str, Any]:
    if (passport or {}).get("scope") != "NON_AUTHORITATIVE_BUILD_PASSPORT" or not any(
        p["component_id"] == component_id for p in passport.get("parts", [])
    ):
        raise ValueError("Choose a component from the passport")
    if not isinstance(new_revision, str) or not new_revision.strip() or len(new_revision) > 120:
        raise ValueError("Enter a bounded, explicit proposed revision")
    result = copy.deepcopy(passport)
    part = next(p for p in result["parts"] if p["component_id"] == component_id)
    part["proposed_revision"] = new_revision.strip()
    part["revision_status"] = "PROPOSED_REVISION_REQUIRES_NEW_VENDOR_EVIDENCE"
    part["variant_identity_key"] = identity([part["component_id"], part["sku_text"], part["proposed_revision"], None, None])
    part["supplier"]["verified_specific_revision"] = False
    part["supplier"]["verified_current_stock"] = False
    part["supplier"]["source_status"] = "PROPOSED_REVISION_NOT_VERIFIED_BY_SNAPSHOT"
    invalidated = []
    # Donor boards can contain unlisted hubs/trucks: fail closed on all claims.
    bundled_donor = bool(part["included_by_donor"])
    for claim in result["interface_claims"]:
        if bundled_donor or component_id in claim["component_ids"]:
            claim["revision_evidence_state"] = "INVALIDATED_BY_REVISION_CHANGE"
            claim["valid_for_physical_build"] = False
            invalidated.append(claim["id"])
    result["study_identity_key"] = identity([result["candidate_id"], *sorted(p["variant_identity_key"] for p in result["parts"])])
    result["change_receipt"] = {
        "component_id": component_id, "proposed_revision": part["proposed_revision"],
        "invalidated_interface_ids": sorted(invalidated),
        "required_action": "Refresh vendor variant evidence, repeat affected dimensional interface checks and independently requalify physical system.",
    }
    result["physical_qualification"] = "NOT_QUALIFIED"
    if "assembly_inventory_audit" in result:
        # Revision what-if invalidates the old inclusion audit; recompute via an
        # explicit catalog registry after a separately reviewed source update.
        result["assembly_inventory_audit"] = None
    return result
