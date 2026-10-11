#!/usr/bin/env python3
"""Measure research completeness honestly, without rating a board physically safe.

CLI:
    python tools/audit_parts_picker_readiness.py --as-of 2026-10-11
    python tools/audit_parts_picker_readiness.py --as-of 2026-10-11 \
        --out /tmp/worcester-readiness.json

Read-only, offline; no vendor network calls, stock claims, cart generation or
mechanical certification.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWN_APPROVALS = (
    "procurement_authorized", "fabrication_authorized", "charging_authorized",
    "powered_operation_authorized", "generic_builder_may_promote_x1_authority"
)


def _read(root: Path, name: str) -> dict:
    return json.loads((root / "catalog" / name).read_text(encoding="utf-8"))


def _age(current: date, value: str) -> int:
    return (current - date.fromisoformat(value)).days


def assess(root: Path = ROOT, *, as_of: str) -> dict:
    today = date.fromisoformat(as_of)
    catalog = _read(root, "outdoor_parts_picker.v1.json")
    supplier = _read(root, "outdoor_supplier_observations.v1.json")
    retail = _read(root, "outdoor_retail_comparisons.v1.json")
    builds = _read(root, "outdoor_build_studies.v1.json")
    complete_kits = _read(root, "outdoor_complete_kit_claims.v1.json")

    domain_ids = [x["id"] for x in catalog["domains"]]
    templates = {x["domain_id"]: x for x in catalog["assembly_templates"]}
    products = catalog["products"]
    option_count = sum(len(x["variants"]) for x in products)
    retail_options = retail["offers"]
    maker_observations = supplier["listing_observations"]
    package_claims = complete_kits["kits"]
    child_claims = [part for kit in package_claims for part in kit["children"]]

    # Structural integrity checks intentionally independent of marketing claims.
    errors = []
    for name, registry in (("supplier", supplier), ("retail", retail),
                           ("builds", builds), ("complete_kits", complete_kits)):
        authority = registry.get("authority", {})
        if any(authority.get(key) is not False for key in KNOWN_APPROVALS):
            errors.append(name + ": missing or promoted authority lock")
    if not catalog.get("policy") or any(catalog["policy"].values()):
        errors.append("parts catalog has missing or enabled policy values")
    if len(set(domain_ids)) != len(domain_ids):
        errors.append("duplicate sport taxonomy ID")
    if set(templates) - set(domain_ids):
        errors.append("active sport missing canonical domain")
    if len({x["id"] for x in products}) != len(products):
        errors.append("duplicate product family ID")
    if len({v["id"] for p in products for v in p["variants"]}) != option_count:
        errors.append("duplicate research variant ID")
    product_index = {x["id"]: x for x in products}
    complete_variants = {v["id"] for p in products if p["slot"] == "long_complete"
                         for v in p["variants"]}
    if len(package_claims) != 2 or any(
        k["variant_id"] not in complete_variants
        or k["seller_checkout_option_verified"]
        or k["actual_received_kit_verified"]
        for k in package_claims
    ):
        errors.append("complete-kit maker claims invalid or falsely received")
    if any(
        p["actual_received_units"] is not None
        or p["direct_seller_purchase_required"] is not False
        for p in child_claims
    ):
        errors.append("complete-kit child claim promoted to received item or separate purchase")
    variant_ids = {v["id"] for p in products for v in p["variants"]}
    for p in products:
        if p["domain_id"] not in templates:
            errors.append("unsupported live product: " + p["id"])
        for v in p["variants"]:
            if v.get("manufacturer_sku") is not None:
                errors.append("unsupported source-verified manufacturer SKU: " + v["id"])

    for o in retail_options:
        if o.get("selected_variant_id") is not None and o["selected_variant_id"] not in variant_ids:
            errors.append("retail variant outside catalog: " + o["id"])
        if o.get("related_product_family_id") is not None and (
            o["related_product_family_id"] not in product_index or o["selected_variant_id"] is not None
        ):
            errors.append("ambiguous related family listing: " + o["id"])
        if o.get("checkout_eligible") is not False or o.get("exact_checkout_variant_verified") is not False:
            errors.append("retailer claims qualified checkout variant: " + o["id"])
    for o in maker_observations:
        if o["selected_variant_id"] not in variant_ids:
            errors.append("maker observation outside catalog: " + o["id"])
        if o["financial_checkout_authorized"] is not False or o["physical_fit_verified"] is not False:
            errors.append("maker source promoted to physical/cart approval: " + o["id"])

    studies_by_domain = Counter(s["domain_id"] for s in builds["studies"])
    domains = []
    for domain in domain_ids:
        active = domain in templates
        subset = [x for x in products if x["domain_id"] == domain]
        slots = templates[domain]["slots"] if active else []
        sourced_slots = {x["slot"] for x in subset}
        required = [s for s in slots if s["status"].startswith("REQUIRED")]
        missing = [s["id"] for s in required if s["id"] not in sourced_slots]
        domain_studies = studies_by_domain[domain]
        related = [x for x in retail_options if x.get("related_product_family_id") in
                   {p["id"] for p in subset}]
        named = [x for x in retail_options if x.get("selected_variant_id") in
                 {v["id"] for p in subset for v in p["variants"]}]
        domains.append({
            "domain_id": domain,
            "active_research_template": active,
            "taxonomy_only": not active,
            "manufacturer_product_families": len(subset),
            "reference_variant_options": sum(len(p["variants"]) for p in subset),
            "catalog_slots": len(slots),
            "required_slot_reference_coverage": len(required) - len(missing),
            "required_slot_count": len(required),
            "missing_required_reference_slots": missing,
            "curated_studies": domain_studies,
            "historical_named_retail_offer_rows": len(named),
            "related_family_only_retail_rows": len(related),
            "exact_checkout_size_sku_verified": 0,
            "qualified_physical_mates": 0,
            "qualified_orderable_builds": 0,
        })
        if active and domain_studies != 3:
            errors.append(domain + ": expected 3 bounded studies")
        if not active and (subset or domain_studies):
            errors.append(domain + ": taxonomy-only sport unexpectedly has active products/studies")
    names = Counter(o["selected_variant_id"] for o in retail_options
                    if o.get("selected_variant_id") is not None
                    and 0 <= _age(today, o["observed_on"]) <= 30)
    distinct_named_comparisons = 0
    conflicting_inclusion_revisions = 0
    for variant in names:
        offers = [x for x in retail_options
                  if x.get("selected_variant_id") == variant
                  and 0 <= _age(today, x["observed_on"]) <= 30]
        merchants = {x["merchant_id"] for x in offers}
        revisions = {x.get("advertised_truck_revision_claim") for x in offers}
        if len(merchants) < 2:
            continue
        if len(revisions) != 1:
            conflicting_inclusion_revisions += 1
        else:
            distinct_named_comparisons += 1
    source_age = [_age(today, x["reviewed_on"]) for x in catalog["sources"]]
    expired = sum(1 for a in source_age if a < 0 or a > 30)
    offer_age = [_age(today, x["observed_on"]) for x in retail_options]
    current_retail = sum(0 <= age <= 30 for age in offer_age)
    maker_age = [_age(today, x["observed_on"]) for x in maker_observations]
    current_maker = sum(0 <= age <= 30 for age in maker_age)

    blockers = [
        {"priority": "P0", "code": "UNMERGED_FIVE_PR_STACK",
         "owner": "engineering", "next": "Human QA of PR #114 and ordered merge/revalidation"},
        {"priority": "P0", "code": "NO_EXACT_CHECKOUT_VARIANT_QUALIFIED",
         "owner": "sourcing", "next": "Maker and seller-specific size/revision, package, quote and availability"},
        {"priority": "P0", "code": "NO_MEASURED_PHYSICAL_MATES",
         "owner": "mechanical", "next": "Authorized CAD with datum/fastener/tolerance and independent validation"},
        {"priority": "P1", "code": "FIVE_DOMAINS_TAXONOMY_ONLY",
         "owner": "catalog", "next": "Deepen one active sport before activating another"},
        {"priority": "P1", "code": "NO_SUCCESSFUL_WEBGL_QUALIFICATION",
         "owner": "experience", "next": "Human GPU/browser orbit, responsive, keyboard and touch signoff"},
    ]
    if conflicting_inclusion_revisions:
        blockers.append({
            "priority": "P0", "code": "RETAILER_INCLUDED_TRUCK_REVISION_CONFLICT",
            "owner": "sourcing",
            "next": "Loaded current Paris V3 versus Skates USA Paris V2: verify seller shipped revision before equivalence",
        })
    if expired:
        blockers.append({
            "priority": "P1", "code": "STALE_MANUFACTURER_REFERENCES",
            "owner": "sourcing", "next": "Revisit maker pages and record new dated evidence"
        })
    return {
        "schema_version": 1,
        "scope": "RESEARCH_PRODUCT_COMPLETENESS_NOT_CHECKOUT_OR_SAFETY_APPROVAL",
        "as_of": as_of,
        "summary": {
            "domains_in_taxonomy": len(domain_ids),
            "domains_with_research_template": len(templates),
            "domains_taxonomy_only": len(domain_ids) - len(templates),
            "product_families": len(products),
            "reference_variant_choices": option_count,
            "manufacturer_source_documents": len(catalog["sources"]),
            "manufacturer_pages_due_refresh": expired,
            "supplier_directory_entries": len(catalog["vendors"]),
            "maker_observations_total": len(maker_observations),
            "maker_observations_within_30d": current_maker,
            "retail_observations_total": len(retail_options),
            "retail_observations_within_30d": current_retail,
            "different_variant_comparisons_with_2_merchants": distinct_named_comparisons,
            "named_variant_comparisons_blocked_by_inclusion_revision": conflicting_inclusion_revisions,
            "curated_unqualified_studies": len(builds["studies"]),
            "maker_advertised_complete_kits": len(package_claims),
            "maker_advertised_kit_child_claims": len(child_claims),
            "physically_received_kit_child_claims_verified": 0,
            "seller_exact_checkout_variants_qualified": 0,
            "physical_connections_qualified": 0,
            "procurement_authorized_builds": 0,
        },
        "domains": domains,
        "blockers": blockers,
        "integrity_valid": len(errors) == 0,
        "integrity_errors": errors,
        "authority": {key: False for key in KNOWN_APPROVALS},
        "note": "Counts are catalog breadth, not coverage of the market or safety readiness. No live web refresh performed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, help="ISO date, e.g. 2026-10-11")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = assess(as_of=args.as_of)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["integrity_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
