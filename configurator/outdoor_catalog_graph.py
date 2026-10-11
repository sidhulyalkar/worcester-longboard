"""Read-only v1 mountainboard -> generalized outdoor catalog graph adapter.

No inference of exact family equivalence, sellable order quantities, mechanical
compatibility, live stock or physical/charging/procurement authorization.
"""
from __future__ import annotations
import copy
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


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _assert(value: Any, message: str) -> None:
    if not value:
        raise ValueError("Outdoor catalog graph: " + message)


def _namespaced(kind: str, id: str) -> str:
    return f"{kind}:mountainboard:{id}"


def _stable_binding(c: dict) -> str:
    s = c.get("source") or {}
    price = c.get("price") or {}
    return json.dumps([
        c["id"], c["category"], c.get("label"), c.get("manufacturer"), c.get("sku"),
        s.get("kind"), s.get("snapshot_id"), s.get("as_of"), s.get("url"),
        s.get("seller"), s.get("native_price_snapshot"),
        price.get("kind"), price.get("qty"), price.get("unit_price_usd"),
        price.get("min_usd"), price.get("max_usd")
    ], ensure_ascii=False, separators=(",", ":"))


def _sku_resolution(c: dict) -> str:
    sku = c.get("sku")
    if not sku:
        return "ABSENT"
    if re.search(r"/|\bfamily\b|\bclass\b", sku, re.IGNORECASE):
        return "FAMILY_OR_ALTERNATE_SKUS_UNRESOLVED"
    return "CATALOG_SKU_TEXT_NOT_RECEIVED_VARIANT"


def _trusted_listing(s: dict) -> bool:
    if not (s.get("kind") in ("vendor", "retailer") and
            isinstance(s.get("url"), str) and
            s.get("snapshot_id") and s.get("as_of") and s.get("seller")):
        return False
    try:
        parsed = urlsplit(s["url"])
        stamp = s["as_of"]
        return (parsed.scheme == "https" and bool(parsed.hostname) and
                not parsed.username and not parsed.password and
                bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp)) and
                date.fromisoformat(stamp).isoformat() == stamp)
    except (TypeError, ValueError):
        return False


def build_outdoor_catalog_graph(catalog: dict[str, Any], domains: dict[str, Any],
                                package_registry: dict[str, Any]) -> dict[str, Any]:
    _assert(catalog.get("schema_version") == 1 and isinstance(catalog.get("components"), list),
            "expected existing board components v1")
    _assert(domains.get("scope") == "EXPERIMENTAL_DOMAIN_TAXONOMY_NO_PRODUCT_COMPATIBILITY_OR_PURCHASE_AUTHORITY",
            "unreviewed domain mapping")
    migration = domains.get("legacy_migration") or {}
    _assert(migration.get("source_of_truth") == "catalog/board_components.v1.json" and
            migration.get("policy") == "READ_ONLY_MAPPING_NO_RUNTIME_CHANGE",
            "legacy adapter must remain read-only")
    _assert(package_registry.get("scope") == "CATALOG_INCLUSION_HYPOTHESES_NOT_PACKAGE_CERTIFICATION" and
            isinstance(package_registry.get("packages"), list),
            "missing source-bound package registry")
    mapping = {x["legacy_category"]: x for x in migration.get("mappings", [])}
    _assert(len(mapping) == len(migration.get("mappings", [])), "duplicate legacy category mapping")
    seen: set[str] = set()
    families, variants, offers, snapshots, claims, packages, holds = ([] for _ in range(7))
    donor_mapping = {x["component_id"]: x for x in package_registry["packages"]}
    _assert(len(donor_mapping) == len(package_registry["packages"]), "duplicate source package")
    for comp in catalog["components"]:
        _assert(isinstance(comp.get("id"), str) and bool(comp["id"]) and comp["id"] not in seen,
                "duplicate or invalid legacy component")
        seen.add(comp["id"])
        role = mapping.get(comp["category"])
        _assert(role is not None, "unmapped category for " + comp["id"])
        source = comp.get("source") or {}
        binding = _stable_binding(comp)
        family_id = _namespaced("family", comp["id"])
        variant_id = _namespaced("variant", comp["id"])
        source_id = _namespaced("source", comp["id"])
        pkg_id = _namespaced("package", comp["id"])
        stock_id = _namespaced("offer", comp["id"])
        source_trusted = _trusted_listing(source)
        revision = comp.get("revision") if isinstance(comp.get("revision"), str) and comp["revision"].strip() else None
        families.append({
            "id": family_id, "domain_id": "mountainboard", "name": comp["label"],
            "manufacturer": comp.get("manufacturer"), "provisional": True,
            "legacy_component_id": comp["id"],
            "variant_equivalence_verified": False
        })
        variants.append({
            "id": variant_id, "family_id": family_id, "component_role": role["new_role"],
            "legacy_component_id": comp["id"], "legacy_category": comp["category"],
            "legacy_identity_binding_key": binding,
            "sku_text": comp.get("sku"), "sku_resolution": _sku_resolution(comp),
            "physical_revision": revision,
            "exact_received_variant_verified": False,
            "source_evidence_state": comp.get("evidence_state") or "UNKNOWN",
            "procurement_state": comp.get("procurement_state") or "UNKNOWN",
            "actual_assembly_quantity": None, "real_seller_order_quantity": None,
            "source_snapshot_id": source_id,
            "actual_physical_compatibility_verified": False,
            "status": "PROVISIONAL_CATALOG_REFERENCE_NOT_ORDERABLE"
        })
        snapshots.append({
            "id": source_id, "component_id": comp["id"], "binding_key": binding,
            "source_kind": source.get("kind") or "UNSPECIFIED",
            "source_url": source.get("url"),
            "source_snapshot_id": source.get("snapshot_id"),
            "source_as_of": source.get("as_of"), "seller": source.get("seller"),
            "native_price_snapshot": source.get("native_price_snapshot"),
            "live_stock_verified": False, "source_status": "REFERENCE_SNAPSHOT_ONLY"
        })
        for field, value in sorted((comp.get("interfaces") or {}).items()):
            units = ("mm" if field.endswith("_mm") else
                     "psi" if field.endswith("_psi") else
                     "g" if field.endswith("_g") else
                     "Wh" if field.endswith("_wh") else None)
            claims.append({
                "id": _namespaced("claim", comp["id"] + ":" + field),
                "variant_id": variant_id,
                "interface_field": field,
                "raw_catalog_value": _clone(value),
                "raw_value_units": units,
                "source_snapshot_id": source_id,
                "evidence_state": comp.get("evidence_state") or "UNKNOWN",
                "typed_interface_qualified": False, "independently_measured": False,
                "exact_revision_applicability_verified": False,
                "interpretation": "RAW_LEGACY_INTERFACE_CLAIM_NOT_NORMALIZED_FIT_RULE"
            })
        if source_trusted:
            price = comp.get("price")
            offers.append({
                "id": stock_id, "variant_id": variant_id,
                "source_snapshot_id": source_id,
                "supplier_name": source["seller"], "offer_url": source["url"],
                "dated_as_of": source["as_of"],
                "currency_native_text": source.get("native_price_snapshot"),
                "legacy_price_reference": _clone(price) if price else None,
                "catalog_price_qty_factor": price.get("qty") if price else None,
                "seller_pack_unit_count": None, "assembly_units_per_pack": None,
                "current_availability": "UNKNOWN_NOT_LIVE",
                "verified_quote": False, "checkout_authorized": False,
                "status": "DATED_VENDOR_OR_RETAILER_REFERENCE_ONLY"
            })
        else:
            holds.append({
                "component_id": comp["id"], "variant_id": variant_id,
                "reason": "NO_ORDERABLE_SOURCE_SNAPSHOT",
                "source_kind": source.get("kind") or "UNSPECIFIED"
            })
        included = comp.get("includes") if isinstance(comp.get("includes"), list) else []
        if included:
            record = donor_mapping.get(comp["id"])
            bound = bool(record and record.get("catalog_sku_text") == comp.get("sku") and
                         record.get("catalog_snapshot_id") == source.get("snapshot_id"))
            _assert(not record or len({x["token"] for x in record["inclusions"]}) == len(record["inclusions"]),
                    "duplicate donor inclusion tokens")
            if record:
                _assert(len(set(included)) == len(record["inclusions"]) and
                        all(x["token"] in included for x in record["inclusions"]),
                        "donor token mismatch " + comp["id"])
            items = []
            for token in included:
                entry = next((x for x in record["inclusions"] if x["token"] == token), None) if record else None
                items.append({
                    "inclusion_token": token,
                    "possible_reference_variant_ids": [
                        _namespaced("variant", x)
                        for x in (entry.get("possible_catalog_reference_ids") or [])
                    ] if entry else [],
                    "included_quantity": None,
                    "exact_variant_equivalence_verified": False,
                    "review_question": entry["review_question"] if entry else
                      "Determine actual contents, marked revision and included counts."
                })
            packages.append({
                "id": pkg_id, "container_variant_id": variant_id,
                "component_id": comp["id"], "source_snapshot_id": source_id,
                "registry_mapping_status": (
                    "MISSING_REGISTRY_HOLD" if not record else
                    "BOUND_REFERENCE_NOT_CONTENTS_PROOF" if bound else
                    "STALE_REGISTRY_HOLD"
                ),
                "contents_verified": False, "items": items,
            })
    _assert(len(seen) == len(catalog["components"]), "missing legacy components")
    for donor in package_registry["packages"]:
        _assert(donor["component_id"] in seen, "orphan source-bound donor mapping")
    legacy_snap = {
        "schema_version": catalog["schema_version"], "as_of": catalog.get("as_of"),
        "currency": catalog.get("currency"),
        "refresh_before_checkout": catalog.get("refresh_before_checkout"),
        "note": catalog.get("note"), "components": _clone(catalog["components"])
    }
    return {
        "schema_version": 1, "scope": "EXPERIMENTAL_READ_ONLY_OUTDOOR_CATALOG_GRAPH",
        "domain_registry_version": domains["schema_version"],
        "migration": "LOSSLESS_V1_MOUNTAINBOARD_ADAPTER_NO_RUNTIME_CHANGE",
        "legacy_source_of_truth": "catalog/board_components.v1.json",
        "families": families, "variants": variants,
        "source_snapshots": snapshots, "supplier_offer_references": offers,
        "engineering_claims": claims, "sellable_package_hypotheses": packages,
        "source_holds": holds, "legacy_catalog_snapshot": legacy_snap,
        "summary": {
            "imported_legacy_components": len(seen),
            "provisional_families": len(families),
            "provisional_variants": len(variants),
            "catalog_interface_claims": len(claims),
            "dated_supplier_references": len(offers),
            "package_content_hypotheses": len(packages),
            "confirmed_exact_variants": 0, "live_offers": 0, "orderable_kits": 0,
            "independently_qualified_interfaces": 0,
            "physical_release_status": "NOT_QUALIFIED"
        },
        "authority": dict(AUTHORITY)
    }


def replay_legacy_board_catalog(graph: dict[str, Any]) -> dict[str, Any]:
    _assert(graph.get("scope") == "EXPERIMENTAL_READ_ONLY_OUTDOOR_CATALOG_GRAPH" and
            graph.get("migration") == "LOSSLESS_V1_MOUNTAINBOARD_ADAPTER_NO_RUNTIME_CHANGE",
            "cannot replay non-v1 read-only graph")
    original = graph.get("legacy_catalog_snapshot") or {}
    _assert(original.get("schema_version") == 1 and isinstance(original.get("components"), list),
            "missing legacy snapshot")
    components = original["components"]
    _assert(len(graph["variants"]) == len(components) and
            len(graph["families"]) == len(components) and
            len(graph["source_snapshots"]) == len(components),
            "partial graph cannot be replayed")
    variants = {x["legacy_component_id"]: x for x in graph["variants"]}
    sources = {x["component_id"]: x for x in graph["source_snapshots"]}
    _assert(len(variants) == len(components) and len(sources) == len(components),
            "duplicate graph identity")
    for comp in components:
        variant = variants.get(comp["id"])
        source = sources.get(comp["id"])
        _assert(bool(variant) and bool(source) and
                variant["legacy_identity_binding_key"] == _stable_binding(comp) and
                source["binding_key"] == _stable_binding(comp),
                "stale graph snapshot binding " + comp["id"])
        _assert(variant["family_id"] == _namespaced("family", comp["id"]) and
                source["id"] == _namespaced("source", comp["id"]),
                "graph ID mismatch " + comp["id"])
    return _clone(original)
