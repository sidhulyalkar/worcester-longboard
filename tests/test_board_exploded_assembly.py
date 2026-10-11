"""Assembly graph source binding and board sport negative safety checks."""
import copy
import json
from pathlib import Path
import pytest
from configurator.platform_engine import load_platform_bundle,generate_board_design_space
from configurator.assembly_graph import build_assembly_graph
ROOT=Path(__file__).resolve().parents[1]
read=lambda p:json.loads((ROOT/p).read_text(encoding="utf-8"))
RECIPES=read("catalog/outdoor_assembly_recipes.v1.json")
BUNDLE=load_platform_bundle()
CATALOG=read("catalog/board_components.v1.json")
PACK=read("catalog/board_package_inclusions.v1.json")
CANDIDATES=generate_board_design_space(read("configurator/examples/trail_rider_profile.json"),BUNDLE)["candidates"]

def build(s,recipes=RECIPES,reg=PACK):
    return build_assembly_graph(s,recipes,CATALOG,reg)

def find(id):
    return next(x for x in CANDIDATES if x["id"]==id)

def test_all_selected_candidate_parts_kept_and_never_qualified():
    for candidate in CANDIDATES:
        report=build(candidate)
        assert [x["component_id"] for x in report["components"]]==[x["component_id"] for x in candidate["bom"]]
        assert report["completeness"]["unique_bom_component_ids"]==len(candidate["bom"])
        assert all(x["assembly_required_quantity"] is None and x["supplier_order_quantity"] is None for x in report["components"])
        assert all(not x["exact_variant_verified"] for x in report["components"])
        assert not any(report["authority"].values())
        assert report["safety"]["physical_qualification"]=="NOT_QUALIFIED"

def test_source_bound_donor_contents_not_confirmed():
    report=build(find("brake_first_trail_core"))
    donor=next(x for x in report["package_inclusion_hypotheses"] if x["container_component_id"]=="DONOR-COMP95")
    assert donor["source_registry_binding"]=="BOUND_REFERENCE_ONLY"
    assert donor["actual_contents_verified"] is False
    assert all(x["included_quantity"] is None for x in donor["content_tokens"])
    stale=copy.deepcopy(PACK)
    stale["packages"][0]["catalog_snapshot_id"]="different"
    report=build(find("brake_first_trail_core"),reg=stale)
    assert report["package_inclusion_hypotheses"][0]["source_registry_binding"]=="UNBOUND_OR_STALE_HOLD"

def test_cross_sport_schematics_have_no_real_product_claims():
    assert len(RECIPES["examples"])==5
    for e in RECIPES["examples"]:
        report=build(e)
        assert report["origin"]=="ILLUSTRATIVE_DOMAIN_RECIPE"
        assert report["source_snapshot_as_of"] is None
        assert all(x["source_url"] is None and x["assembly_required_quantity"] is None for x in report["components"])
        assert not report["safety"]["usable_for_binding_release"]
        assert report["package_inclusion_hypotheses"]==[]
    ski=next(x for x in RECIPES["examples"] if x["domain_id"]=="alpine_ski")
    assert "ski_brake" in [x["role"] for x in ski["components"]]
    assert any("release testing" in x for x in build(ski)["unresolved_system_checks"])

def test_duplicate_unknown_roles_or_forged_concept_fail_closed():
    c=copy.deepcopy(find("brake_first_trail_core"))
    c["bom"].append(copy.deepcopy(c["bom"][0]))
    with pytest.raises(ValueError,match="Duplicate or invalid"):build(c)
    c["bom"].pop()
    c["bom"][0]["component_id"]="FAKE-CATALOG"
    with pytest.raises(ValueError,match="Unknown catalog"):build(c)
    e=copy.deepcopy(RECIPES["examples"][0])
    e["components"][0]["sku"]="fake"
    with pytest.raises(ValueError,match="exact source-bound recipe"):build(e)
    bad=copy.deepcopy(RECIPES)
    bad["groups"][0]["roles"].append("truck")
    with pytest.raises(ValueError,match="Ambiguous assembly role"):build(find("brake_first_trail_core"),bad)
