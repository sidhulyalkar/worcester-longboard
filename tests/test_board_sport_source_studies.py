"""Longboard maker option and Burton mounting-family checks do not qualify parts."""
import json
import copy
from pathlib import Path
import pytest
from configurator.assembly_graph import build_assembly_graph
from configurator.snowboard_mount_reference import evaluate_snowboard_mount_reference

ROOT=Path(__file__).resolve().parents[1]
read=lambda p:json.loads((ROOT/p).read_text())
REG=read("catalog/board_sport_reference_studies.v1.json")
RECIPES=read("catalog/outdoor_assembly_recipes.v1.json")
CATALOG=read("catalog/board_components.v1.json")
PACK=read("catalog/board_package_inclusions.v1.json")

def build(s,reg=REG):
    return build_assembly_graph(s,RECIPES,CATALOG,PACK,reg)

def test_all_studies_preserve_maker_refs_and_qualification_holds():
    assert len(REG["studies"])>=5
    for s in REG["studies"]:
        result=build(s)
        assert result["origin"]=="MANUFACTURER_REFERENCED_INTEGRATION_STUDY"
        assert result["source_snapshot_as_of"]==REG["reviewed_as_of"]
        assert [x["component_id"] for x in result["components"]]==[x["component_id"] for x in s["components"]]
        assert not any(result["authority"].values())
        assert result["completeness"]["physical_connections_qualified"]==0
        assert all(x["assembly_required_quantity"] is None for x in result["components"])
        assert all(x["shipped_quantity"] is None for x in result["manufacturer_advertised_contents"])

def test_loaded_complete_option_parts_are_source_claims_not_received_counts():
    result=build(next(x for x in REG["studies"] if x["id"]=="source-loaded-tangent-complete"))
    assert any(x["role"]=="bracket_set" and "loadedboards.com" in x["source_url"] for x in result["components"])
    assert any(x["role"]=="wheelset" and "105mm" in x["label"] for x in result["components"])
    assert len(result["manufacturer_advertised_contents"])==6
    assert result["manufacturer_mount_reference"] is None

def test_burton_mounting_reference_and_est_3d_steps_remain_gated():
    study=next(x for x in REG["studies"] if x["id"]=="source-burton-custom-mission")
    graph=build(study)
    result=evaluate_snowboard_mount_reference(graph["manufacturer_mount_reference"])
    assert result["verdict"]=="MAKER_FAMILY_REFERENCE_MATCH_REVIEW_REQUIRED"
    assert result["physical_fit_verified"] is False
    assert result["install_authorized"] is False
    assert any(x["role"]=="boot_pair" and x["source_url"] is None for x in graph["components"])
    assert evaluate_snowboard_mount_reference({"board_mount":"2X4_REFERENCE",
       "binding_mount":"EST","disc_family":None})["verdict"]=="MANUFACTURER_REFERENCE_INCOMPATIBLE"
    assert evaluate_snowboard_mount_reference({"board_mount":"3D_LEGACY_REFERENCE",
       "binding_mount":"REFLEX","disc_family":"BURTON_REFLEX_COMBO"})["verdict"]=="REQUIRED_SPECIAL_DISC_MISSING"
    step=evaluate_snowboard_mount_reference({"board_mount":"CHANNEL_M6_REFERENCE",
       "binding_mount":"REFLEX","disc_family":"BURTON_REFLEX_COMBO","boot_retention":"STEP_ON_ONLY"})
    assert step["boot_fit"]=="STEP_ON_BOOT_MODEL_SIZE_REQUIRED"
    assert not any(step["authority"].values())

def test_forged_source_path_or_quantity_rejected():
    altered=copy.deepcopy(REG["studies"][0])
    altered["components"][0]["source_url"]="https://bad.vendor.example"
    with pytest.raises(ValueError,match="exact reviewed registry"):build(altered)
    altered=copy.deepcopy(REG["studies"][0])
    altered["components"][0]["quantity_verified"]=42
    with pytest.raises(ValueError,match="exact reviewed registry"):build(altered)
    copy_reg=copy.deepcopy(REG)
    copy_reg["studies"][0]["components"][0]["label"]="fake maker variant"
    with pytest.raises(ValueError,match="exact reviewed registry"):build(REG["studies"][0],copy_reg)
