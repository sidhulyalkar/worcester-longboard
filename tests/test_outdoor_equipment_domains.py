"""Cross-domain catalog pilot tests. No v1 product recommendations are changed."""
import copy
import json
from pathlib import Path
import pytest

from tools.validate_outdoor_equipment_domains import validate

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "catalog/outdoor_equipment_domains.v0.json").read_text())
LEGACY = json.loads((ROOT / "catalog/board_components.v1.json").read_text())


def test_all_current_categories_migrate_without_changing_existing_engine():
    result = validate(REGISTRY, LEGACY)
    assert result["domain_count"] >= 9
    assert result["typed_interface_count"] >= 17
    assert result["legacy_category_count"] == len({x["category"] for x in LEGACY["components"]})
    assert result["new_product_variants_registered"] == 0
    assert result["physical_authority"] is False
    assert result["validation"] == "DOMAIN_VOCABULARY_ONLY_NO_V1_RUNTIME_CHANGES"


@pytest.mark.parametrize("field", [
    "procurement_authorized", "fabrication_authorized", "charging_authorized",
    "powered_operation_authorized", "generic_builder_may_promote_x1_authority",
])
def test_authority_never_promoted(field):
    mutated = copy.deepcopy(REGISTRY)
    mutated["authority"][field] = True
    with pytest.raises(AssertionError):
        validate(mutated, LEGACY)


def test_categories_cannot_silently_be_dropped_or_misrouted():
    mutated = copy.deepcopy(REGISTRY)
    mutated["legacy_migration"]["mappings"].pop()
    with pytest.raises(AssertionError, match="cover every current"):
        validate(mutated, LEGACY)
    mutated = copy.deepcopy(REGISTRY)
    mutated["legacy_migration"]["mappings"][0]["new_role"] = "magic_replacement"
    with pytest.raises(AssertionError, match="not declared"):
        validate(mutated, LEGACY)


def test_new_domain_requires_explicit_roles_interfaces_and_safety_review():
    mutated = copy.deepcopy(REGISTRY)
    mutated["domains"].append({
        "id": "skis_unknown", "stage": "FUTURE_ADAPTER", "required_roles": [],
        "optional_roles": [], "interface_type_ids": [], "automatic_purchase_authority": False,
    })
    with pytest.raises(AssertionError):
        validate(mutated, LEGACY)
    mutated = copy.deepcopy(REGISTRY)
    mutated["domains"][0]["interface_type_ids"].append("unproved_magic_interface")
    with pytest.raises(AssertionError):
        validate(mutated, LEGACY)


def test_ski_release_never_approved_from_catalog_claim_state():
    assert "INDEPENDENTLY_QUALIFIED" not in REGISTRY["claim_states"]
    mutated = copy.deepcopy(REGISTRY)
    mutated["claim_states"].append("INDEPENDENTLY_QUALIFIED")
    with pytest.raises(AssertionError, match="outside source claim"):
        validate(mutated, LEGACY)
    ski = next(x for x in REGISTRY["domains"] if x["id"] == "alpine_ski")
    assert "CERTIFIED_PROFESSIONAL" in ski["qualification_policy"]
    assert "ski_boot_to_binding_release" in ski["interface_type_ids"]
    binding = next(x for x in REGISTRY["interface_types"] if x["id"] == "ski_boot_to_binding_release")
    assert binding["comparison"] == "PROFESSIONAL_INSPECTION_AND_RELEASE_TEST_REQUIRED"


def test_disciplines_do_not_share_blanket_pairwise_compatibility():
    board = next(x for x in REGISTRY["domains"] if x["id"] == "snowboard")
    surf = next(x for x in REGISTRY["domains"] if x["id"] == "surfboard")
    street = next(x for x in REGISTRY["domains"] if x["id"] == "skateboard_longboard")
    assert "skateboard_deck_to_truck" in street["interface_type_ids"]
    assert "snowboard_binding_mount" in board["interface_type_ids"]
    assert "surfboard_fin_box" in surf["interface_type_ids"]
    assert "surfboard_fin_box" not in board["interface_type_ids"]
    assert all(x["automatic_purchase_authority"] is False for x in REGISTRY["domains"])


def test_avalanche_terrain_requires_equipment_review_and_finless_surf_remains_possible():
    for domain_id in ("touring_ski", "splitboard"):
        domain = next(x for x in REGISTRY["domains"] if x["id"] == domain_id)
        assert any(x["role"] == "avalanche_safety_kit" and
                   x["when"] == "AVALANCHE_TERRAIN" for x in
                   domain["conditional_required_roles"])
        assert "avalanche_safety_kit" not in domain["optional_roles"]
    surf = next(x for x in REGISTRY["domains"] if x["id"] == "surfboard")
    assert "fin_set" not in surf["required_roles"]
    assert "fin_set" in surf["optional_roles"]
    corrupted = copy.deepcopy(REGISTRY)
    next(x for x in corrupted["domains"] if x["id"] == "splitboard")["conditional_required_roles"] = []
    with pytest.raises(AssertionError, match="avalanche"):
        validate(corrupted, LEGACY)
