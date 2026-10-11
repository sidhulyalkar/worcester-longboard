#!/usr/bin/env python3
"""Read-only, fail-closed schema pilot for a multi-sport catalog vocabulary.

Does not mutate or migrate the Board Builder v1 catalog or imply fit/release.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalog/outdoor_equipment_domains.v0.json"
LEGACY = ROOT / "catalog/board_components.v1.json"
REQUIRED_AUTHORITY = {
    "procurement_authorized",
    "fabrication_authorized",
    "charging_authorized",
    "powered_operation_authorized",
    "generic_builder_may_promote_x1_authority",
}
STAGES = {"CURRENT_LEGACY_ADAPTER", "PROPOSED", "FUTURE_ADAPTER"}
COMPARISONS = {
    "MEASUREMENT_AND_REVISION_REQUIRED",
    "MULTI_COMPONENT_PHYSICAL_QUALIFICATION",
    "SPECIALIST_SYSTEM_QUALIFICATION",
    "MAKER_VARIANT_AND_ADAPTER_REQUIRED",
    "MODEL_SIZE_FIT_AND_MAKER_APPROVAL",
    "PROFESSIONAL_INSPECTION_AND_RELEASE_TEST_REQUIRED",
    "PROFESSIONAL_MOUNT_AND_CHECK_REQUIRED",
    "MULTI_COMPONENT_MODE_QUALIFICATION",
    "VARIANT_AND_ADAPTER_REQUIRED",
    "MAKER_AND_LOAD_REVIEW_REQUIRED",
    "MAKER_VARIANT_AND_MEASUREMENT_REQUIRED",
}
ENTITIES = {
    "PRODUCT_FAMILY",
    "PRODUCT_VARIANT",
    "SELLABLE_PACKAGE",
    "PACKAGE_CONTENTS_CLAIM",
    "SUPPLIER_OFFER_SNAPSHOT",
    "ENGINEERING_INTERFACE",
    "MEASUREMENT_CLAIM",
    "MANUFACTURER_DOCUMENT",
    "ASSEMBLY_ARCHITECTURE",
    "RIDER_MISSION",
    "QUALIFICATION_RECEIPT",
}


def validate(registry: dict, legacy: dict) -> dict:
    assert registry["schema_version"] == 0, "Unexpected domain contract version"
    assert registry["scope"] == "EXPERIMENTAL_DOMAIN_TAXONOMY_NO_PRODUCT_COMPATIBILITY_OR_PURCHASE_AUTHORITY"
    assert set(registry["authority"]) == REQUIRED_AUTHORITY
    assert all(value is False for value in registry["authority"].values()), "Catalog cannot authorize release"
    assert set(registry["shared_entity_kinds"]) == ENTITIES
    assert len(registry["shared_entity_kinds"]) == len(set(registry["shared_entity_kinds"]))
    assert registry["claim_states"] and len(registry["claim_states"]) == len(set(registry["claim_states"]))
    assert "UNKNOWN" in registry["claim_states"]
    assert "INDEPENDENTLY_QUALIFIED" not in registry["claim_states"], (
        "Physical approval must stay outside source claim vocabulary"
    )

    interfaces = registry["interface_types"]
    ids = [row["id"] for row in interfaces]
    assert len(ids) == len(set(ids)), "Duplicate typed interface"
    assert all(row["comparison"] in COMPARISONS for row in interfaces)
    for interface in interfaces:
        assert interface["required_inputs"]
        assert len(interface["required_inputs"]) == len(set(interface["required_inputs"]))
        assert interface["representation"] and interface["domain"]

    domains = registry["domains"]
    domain_ids = [domain["id"] for domain in domains]
    assert len(domain_ids) == len(set(domain_ids)), "Duplicate sport or equipment domain"
    assert {"mountainboard", "skateboard_longboard", "snowboard", "alpine_ski", "splitboard", "surfboard"}.issubset(domain_ids)
    assert "bicycle" in domain_ids and "camping_shelter" in domain_ids
    interface_index = {row["id"]: row for row in interfaces}
    for domain in domains:
        assert domain["stage"] in STAGES
        assert domain["required_roles"] and domain["interface_type_ids"]
        assert set(domain["required_roles"]).isdisjoint(domain["optional_roles"])
        assert all(isinstance(role, str) and role for role in
                   domain["required_roles"] + domain["optional_roles"])
        assert len(domain["required_roles"]) == len(set(domain["required_roles"]))
        assert len(domain["optional_roles"]) == len(set(domain["optional_roles"]))
        assert len(domain["interface_type_ids"]) == len(set(domain["interface_type_ids"]))
        assert all(interface_id in interface_index for interface_id in domain["interface_type_ids"])
        assert domain["mission_inputs"] and domain["qualification_policy"]
        assert domain["automatic_purchase_authority"] is False, (
            f"Automatic purchase must remain false in {domain['id']}"
        )
        assert domain["visual_adapter"]
    assert registry["legacy_migration"]["policy"] == "READ_ONLY_MAPPING_NO_RUNTIME_CHANGE"
    assert registry["legacy_migration"]["source_of_truth"] == "catalog/board_components.v1.json"
    legacy_categories = {row["category"] for row in legacy["components"]}
    mappings = registry["legacy_migration"]["mappings"]
    mapping_categories = [row["legacy_category"] for row in mappings]
    assert len(mapping_categories) == len(set(mapping_categories)), "Ambiguous legacy category migration"
    assert set(mapping_categories) == legacy_categories, "v0 migration must cover every current v1 category"
    target = next(domain for domain in domains if domain["id"] == "mountainboard")
    valid_roles = set(target["required_roles"] + target["optional_roles"])
    for mapping in mappings:
        assert mapping["new_role"] in valid_roles, (
            "Migration target role not declared: " + mapping["new_role"]
        )
        assert mapping["new_entity_kind"] in ENTITIES
    assert sum(1 for x in domains if x["stage"] == "CURRENT_LEGACY_ADAPTER") == 1
    assert next(x for x in domains if x["stage"] == "CURRENT_LEGACY_ADAPTER")["id"] == "mountainboard"
    for critical in ("alpine_ski", "touring_ski"):
        d = next(x for x in domains if x["id"] == critical)
        assert "PROFESSIONAL" in d["qualification_policy"] or "CERTIFIED" in d["qualification_policy"]
    assert "electrical_powertrain" in target["interface_type_ids"]
    return {
        "schema_version": 0,
        "validation": "DOMAIN_VOCABULARY_ONLY_NO_V1_RUNTIME_CHANGES",
        "domain_count": len(domains),
        "typed_interface_count": len(interfaces),
        "legacy_category_count": len(legacy_categories),
        "new_product_variants_registered": 0,
        "source_revisions_verified": 0,
        "physical_authority": False,
    }


def main() -> None:
    registry = json.loads(REGISTRY.read_text())
    legacy = json.loads(LEGACY.read_text())
    print(json.dumps(validate(registry, legacy), indent=2))


if __name__ == "__main__":
    main()
