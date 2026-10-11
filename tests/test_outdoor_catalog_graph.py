"""Read-only catalog graph provenance/quantity safety and v1 exact-lossless regressions."""
import copy
import json
from pathlib import Path
import pytest
from configurator.outdoor_catalog_graph import build_outdoor_catalog_graph,replay_legacy_board_catalog
from configurator.platform_engine import generate_board_design_space,load_platform_bundle
from configurator.build_passport import build_build_passport

ROOT=Path(__file__).resolve().parents[1]
read=lambda x:json.loads((ROOT/x).read_text())
CATALOG=read("catalog/board_components.v1.json")
DOMAINS=read("catalog/outdoor_equipment_domains.v0.json")
INCLUSIONS=read("catalog/board_package_inclusions.v1.json")

def build(c=CATALOG,d=DOMAINS,p=INCLUSIONS):
    return build_outdoor_catalog_graph(c,d,p)

def test_lossless_adapter_one_family_per_legacy_reference():
    g=build()
    assert replay_legacy_board_catalog(g)==CATALOG
    assert len(g["families"])==len(CATALOG["components"])
    assert len(g["variants"])==len(CATALOG["components"])
    assert g["summary"]["confirmed_exact_variants"]==0
    assert g["summary"]["orderable_kits"]==0
    assert g["summary"]["live_offers"]==0
    assert not any(g["authority"].values())
    assert all(x["provisional"] and not x["variant_equivalence_verified"] for x in g["families"])
    assert all(x["actual_assembly_quantity"] is None for x in g["variants"])

def test_family_sku_text_not_verified_as_exact_revision_or_orderable_unit():
    g=build()
    idx={x["legacy_component_id"]:x for x in g["variants"]}
    assert idx["TRUCK-M3-400"]["sku_resolution"]=="FAMILY_OR_ALTERNATE_SKUS_UNRESOLVED"
    assert idx["HUB-RSII"]["sku_resolution"]=="FAMILY_OR_ALTERNATE_SKUS_UNRESOLVED"
    assert idx["BRAKE-V5"]["sku_resolution"]=="CATALOG_SKU_TEXT_NOT_RECEIVED_VARIANT"
    assert not idx["BRAKE-V5"]["exact_received_variant_verified"]
    offers={x["variant_id"]:x for x in g["supplier_offer_references"]}
    assert offers["variant:mountainboard:HUB-RSII"]["catalog_price_qty_factor"]==4
    assert offers["variant:mountainboard:HUB-RSII"]["seller_pack_unit_count"] is None
    assert offers["variant:mountainboard:HUB-RSII"]["assembly_units_per_pack"] is None
    assert not offers["variant:mountainboard:HUB-RSII"]["verified_quote"]
    assert not offers["variant:mountainboard:HUB-RSII"]["checkout_authorized"]
    assert "variant:mountainboard:BATTERY-TRAIL-CLASS" not in offers

def test_source_scoped_raw_claims_not_physical_compatibility():
    g=build()
    claim=next(x for x in g["engineering_claims"] if
               x["id"]=="claim:mountainboard:WHEEL-TRAMPA-ALPHA8:published_diameter_mm")
    assert claim["raw_value_units"]=="mm"
    assert isinstance(claim["raw_catalog_value"],int|float)
    assert not claim["typed_interface_qualified"]
    assert not claim["exact_revision_applicability_verified"]
    pkg=g["sellable_package_hypotheses"][0]
    assert pkg["registry_mapping_status"]=="BOUND_REFERENCE_NOT_CONTENTS_PROOF"
    assert all(x["included_quantity"] is None and
               not x["exact_variant_equivalence_verified"] for x in pkg["items"])

def test_negative_categories_duplicates_and_orphan_donors():
    c=copy.deepcopy(CATALOG)
    c["components"].append({**c["components"][0],"id":"MAGIC","category":"new_critical_interface"})
    with pytest.raises(ValueError,match="unmapped category"):build(c)
    c["components"].pop()
    c["components"].append(copy.deepcopy(c["components"][0]))
    with pytest.raises(ValueError,match="duplicate or invalid"):build(c)
    donor=copy.deepcopy(INCLUSIONS)
    donor["packages"][0]["component_id"]="DONOR-NOT-FOUND"
    with pytest.raises(ValueError,match="orphan"):build(CATALOG,DOMAINS,donor)
    d=copy.deepcopy(DOMAINS)
    d["legacy_migration"]["mappings"].append(copy.deepcopy(d["legacy_migration"]["mappings"][0]))
    with pytest.raises(ValueError,match="duplicate legacy category"):build(CATALOG,d)

def test_replay_rejects_stale_or_missing_variant_identity():
    g=build()
    wrong=copy.deepcopy(g)
    wrong["legacy_catalog_snapshot"]["components"][0]["source"]["snapshot_id"]="new-vendor"
    with pytest.raises(ValueError,match="stale graph snapshot"):replay_legacy_board_catalog(wrong)
    wrong=copy.deepcopy(g)
    wrong["legacy_catalog_snapshot"]["components"][0]["sku"]="new-sku"
    with pytest.raises(ValueError,match="stale graph snapshot"):replay_legacy_board_catalog(wrong)
    wrong=copy.deepcopy(g)
    wrong["variants"].pop()
    with pytest.raises(ValueError,match="partial graph"):replay_legacy_board_catalog(wrong)

def test_original_board_engine_and_passport_exact_parity():
    bundle=load_platform_bundle()
    profile=read("configurator/examples/trail_rider_profile.json")
    original=generate_board_design_space(profile,bundle)
    other={**bundle,"catalog":replay_legacy_board_catalog(build())}
    assert generate_board_design_space(profile,other)==original
    for c in original["candidates"][:4]:
        assert build_build_passport(c,bundle)==build_build_passport(c,other)

def test_source_credentials_invalid_date_and_price_snapshot_tamper_fail_closed():
    changed=copy.deepcopy(CATALOG)
    changed["components"][0]["source"]["url"]="https://user:secret@www.mbs.com/product"
    g=build(changed)
    assert not any(x["variant_id"]=="variant:mountainboard:DONOR-COMP95"
                   for x in g["supplier_offer_references"])
    changed["components"][0]["source"]["url"]="https://www.mbs.com/product"
    changed["components"][0]["source"]["as_of"]="2026-02-30"
    g=build(changed)
    assert not any(x["variant_id"]=="variant:mountainboard:DONOR-COMP95"
                   for x in g["supplier_offer_references"])
    graph=build()
    graph["legacy_catalog_snapshot"]["components"][0]["price"]["unit_price_usd"]=0.01
    with pytest.raises(ValueError,match="stale graph snapshot"):
        replay_legacy_board_catalog(graph)
