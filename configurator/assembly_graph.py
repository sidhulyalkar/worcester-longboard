"""Python mirror of semantic assembly / exploded diagram source graph."""
from __future__ import annotations
from typing import Any

AUTH = {
    "procurement_authorized": False, "fabrication_authorized": False,
    "charging_authorized": False, "powered_operation_authorized": False,
    "generic_builder_may_promote_x1_authority": False,
}


def _unique(rows, label):
    names = [x["id"] for x in rows]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate " + label)


def build_assembly_graph(subject: dict[str, Any], recipes: dict[str, Any],
                         catalog: dict[str, Any] | None = None,
                         package_registry: dict[str, Any] | None = None,
                         reference_studies: dict[str, Any] | None = None) -> dict[str, Any]:
    if (recipes.get("scope") != "CONCEPTUAL_ASSEMBLY_VISUALIZATION_NOT_PHYSICAL_INSTRUCTIONS" or
            recipes.get("schema_version") != 1 or not isinstance(recipes.get("groups"), list) or
            not isinstance(recipes.get("domains"), list)):
        raise ValueError("Invalid assembly recipe contract")
    _unique(recipes["groups"], "assembly group")
    _unique(recipes["domains"], "assembly domain")
    domain_id = subject.get("domain_id") or "mountainboard"
    domain = next((x for x in recipes["domains"] if x["id"] == domain_id), None)
    if not domain:
        raise ValueError("Unknown assembly sport " + domain_id)
    if domain_id == "mountainboard" and domain["source"] != "LIVE_EXISTING_BOARD_CANDIDATE":
        raise ValueError("Mountainboard must be sourced from existing design candidate")
    if domain_id != "mountainboard" and domain["source"] != "UNSOURCED_ILLUSTRATIVE_CONCEPT":
        raise ValueError("Non-board examples cannot imply a live product")
    concept = domain_id != "mountainboard"
    rows = subject.get("components") if concept else subject.get("bom")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Missing assembly parts")
    source_parts = {x["id"]: x for x in (catalog or {}).get("components", [])}
    reference_backed = False
    if concept:
        canonical = next((x for x in recipes["examples"] if
                          x["id"] == subject["id"] and x["domain_id"] == domain_id), None)
        studied = next((x for x in (reference_studies.get("studies") or []) if
                        x["id"] == subject["id"] and x["domain_id"] == domain_id), None) if (
                            reference_studies and
                            reference_studies.get("scope") == "SOURCE_REFERENCED_BOARD_SPORT_STUDIES_NOT_VERIFIED_FIT_OR_CHECKOUT"
                        ) else None
        exact_concept = canonical is not None and canonical == subject
        exact_study = studied is not None and studied == subject
        if not exact_concept and not exact_study:
            raise ValueError("Concept or reference study must match exact reviewed registry")
        reference_backed = exact_study
    if not concept and (not catalog or not package_registry or
                        package_registry.get("scope") != "CATALOG_INCLUSION_HYPOTHESES_NOT_PACKAGE_CERTIFICATION"):
        raise ValueError("Existing board requires full source and donor registers")
    group_by_role = {}
    for group in recipes["groups"]:
        if (not isinstance(group["roles"], list) or len(group["vector"]) != 2 or
                any(not isinstance(x, (int, float)) for x in group["vector"])):
            raise ValueError("Invalid group geometry")
        for role in group["roles"]:
            if role in group_by_role:
                raise ValueError("Ambiguous assembly role " + role)
            group_by_role[role] = group
    seen = set()
    component_nodes = []
    for i, row in enumerate(rows):
        component_id = row.get("component_id")
        if not isinstance(component_id, str) or not component_id or component_id in seen:
            raise ValueError("Duplicate or invalid assembly component ID")
        seen.add(component_id)
        reference = source_parts.get(component_id)
        if not concept and not reference:
            raise ValueError("Unknown catalog reference " + component_id)
        role = row["role"] if concept else reference["category"]
        group = group_by_role.get(role)
        if not group:
            raise ValueError("Unknown assembly role " + role)
        source = (reference or {}).get("source") or {}
        ref_kind = ((row["source_kind"] if reference_backed else "illustrative_concept")
                    if concept else source.get("kind") or "repository_reference")
        component_nodes.append({
            "id": "part:" + component_id,
            "component_id": component_id, "group_id": group["id"],
            "role": role, "label": row["label"], "order_index": i,
            "manufacturer": (row.get("manufacturer") if reference_backed else None) if concept
                else reference.get("manufacturer"),
            "sku_text": (row.get("sku") if reference_backed else None) if concept
                else reference.get("sku"),
            "source_kind": ref_kind,
            "source_url": (row.get("source_url") if reference_backed else None) if concept
                else source.get("url"),
            "source_snapshot_id": (row.get("source_id") if reference_backed else None) if concept
                else source.get("snapshot_id"),
            "exact_variant_verified": False,
            "assembly_required_quantity": None, "supplier_order_quantity": None,
            "visual_proxy_only": True,
            "inclusion_status": "NOT_INDEPENDENTLY_CONFIRMED",
            "approval_status": "HOLD_SOURCE_REVISION_AND_INTERFACE_REVIEW",
            "reference_price_factor": None if concept else (reference.get("price") or {}).get("qty"),
        })
    active_groups = [
        {
            "id": group["id"], "label": group["label"],
            "shape": group["shape"], "vector": list(group["vector"]),
            "component_ids": [x["component_id"] for x in component_nodes if x["group_id"] == group["id"]],
            "item_count": sum(x["group_id"] == group["id"] for x in component_nodes),
            "exact_assembly_geometry_verified": False,
        }
        for group in recipes["groups"]
        if any(x["group_id"] == group["id"] for x in component_nodes)
    ]
    package_claims, connections = [], []
    if not concept:
        packs = {x["component_id"]: x for x in package_registry["packages"]}
        for node in component_nodes:
            reference = source_parts[node["component_id"]]
            included = reference.get("includes") or []
            if not included:
                continue
            package = packs.get(node["component_id"])
            valid = bool(
                package and package.get("catalog_snapshot_id") == (reference.get("source") or {}).get("snapshot_id") and
                package.get("catalog_sku_text") == reference.get("sku") and
                len(included) == len(package["inclusions"]) and
                all(any(x["token"] == token for x in package["inclusions"]) for token in included)
            )
            tokens = []
            for token in included:
                entry = next((x for x in package["inclusions"] if x["token"] == token), None) if valid else None
                ids = (entry.get("possible_catalog_reference_ids") or []) if entry else []
                tokens.append({
                    "token": token,
                    "possible_component_ids": ids,
                    "included_quantity": None,
                    "exact_part_match_verified": False,
                    "potential_duplicate_bom_component_ids": [x for x in ids if x in seen],
                    "review_question": entry["review_question"] if entry else
                        "Inspect included variant and count",
                })
            package_claims.append({
                "container_component_id": node["component_id"],
                "source_registry_binding": "BOUND_REFERENCE_ONLY" if valid else "UNBOUND_OR_STALE_HOLD",
                "actual_contents_verified": False,
                "content_tokens": tokens,
            })
            connections.append({
                "from": node["component_id"], "to": "unverified-package-contents:" + node["component_id"],
                "kind": "POSSIBLE_PACKAGE_CONTENTS_NOT_PHYSICAL_CONNECTION",
                "verified": False,
            })
    return {
        "schema_version": 1, "scope": "UNQUALIFIED_SEMANTIC_ASSEMBLY_EXPLODED_VIEW",
        "subject_id": subject["id"], "domain_id": domain_id, "label": subject["label"],
        "origin": ("MANUFACTURER_REFERENCED_INTEGRATION_STUDY" if reference_backed else
                   "ILLUSTRATIVE_DOMAIN_RECIPE" if concept else "EXISTING_BOARD_CANDIDATE"),
        "source_snapshot_as_of": (reference_studies["reviewed_as_of"] if reference_backed else
                                  None if concept else catalog.get("as_of")),
        "groups": active_groups, "components": component_nodes, "connections": connections,
        "package_inclusion_hypotheses": package_claims,
        "manufacturer_advertised_contents": [
            {"role": role, "source_listed": True,
             "physically_received_and_counted": False, "shipped_quantity": None}
            for role in subject["advertised_contents"]
        ] if reference_backed else [],
        "manufacturer_mount_reference": subject["known_mount_lookups"] if reference_backed else None,
        "unresolved_system_checks": list(domain["important_checks"]) +
            (list(subject["additional_checks"]) if reference_backed else []),
        "completeness": {
            "catalog_components_included": len(component_nodes),
            "unique_bom_component_ids": len(seen),
            "conceptual_assembly_groups": len(active_groups),
            "source_bound_variant_revisions_qualified": 0,
            "supplier_order_quantities_qualified": 0,
            "physical_connections_qualified": 0,
        },
        "safety": {
            "visual_geometry": "ILLUSTRATIVE_SEMANTIC_PROXY_ONLY",
            "sequence": "NOT_INSTALLATION_INSTRUCTIONS",
            "physical_qualification": "NOT_QUALIFIED",
            "usable_for_fabrication": False,
            "usable_for_mounting": False,
            "usable_for_binding_release": False,
        },
        "authority": dict(AUTH),
        "note": "Exploded positions and silhouettes explain relationships only. They are not measured geometry, a verified parts inventory, a bill of order quantities or installation instructions.",
    }
