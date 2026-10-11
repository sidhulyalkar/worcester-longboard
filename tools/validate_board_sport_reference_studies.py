#!/usr/bin/env python3
"""Public product studies are source lead records, not physical fit/checkout."""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlsplit
from datetime import date

ROOT=Path(__file__).resolve().parents[1]

def validate(studies,ontology):
    assert studies["schema_version"]==1
    assert studies["scope"]=="SOURCE_REFERENCED_BOARD_SPORT_STUDIES_NOT_VERIFIED_FIT_OR_CHECKOUT"
    assert date.fromisoformat(studies["reviewed_as_of"]).isoformat()==studies["reviewed_as_of"]
    assert not any(studies["authority"].values())
    domain_index={x["id"]:x for x in ontology["domains"]}
    sources=studies["sources"]
    source_map={}
    for ref in sources:
        assert ref["id"] not in source_map
        source_map[ref["id"]]=ref
        url=urlsplit(ref["url"])
        assert url.scheme=="https" and not url.username and not url.password
        assert url.hostname in {"www.loadedboards.com","www.burton.com"}
        assert url.hostname=="www.loadedboards.com" if ref["id"].startswith("loaded") else url.hostname=="www.burton.com"
        assert ref["title"].strip() and ref["claim"].strip()
    assert len(sources)>=8
    seen_study=set()
    for study in studies["studies"]:
        assert study["id"] not in seen_study
        seen_study.add(study["id"])
        assert study["domain_id"] in ("skateboard_longboard","snowboard")
        assert study["domain_id"] in domain_index
        assert study["source_state"]=="MAKER_PRODUCT_FAMILY_OR_COMPLETE_OFFER_REFERENCE"
        assert not study["checkout_authorized"] and not study["manufacturer_variant_selected"]
        assert not study["actually_received_contents_verified"]
        assert study["note"] and study["additional_checks"]
        ontology_domain=domain_index[study["domain_id"]]
        allowed=set(ontology_domain["required_roles"]+ontology_domain["optional_roles"])
        roles=[x["role"] for x in study["components"]]
        assert set(ontology_domain["required_roles"]).issubset(set(roles))
        assert set(roles).issubset(allowed)
        assert len(set(x["component_id"] for x in study["components"]))==len(study["components"])
        assert all(x["component_id"].startswith("REF-") for x in study["components"])
        assert all(x in set(roles) for x in study["advertised_contents"])
        for item in study["components"]:
            assert item["quantity_verified"] is None
            assert item["exact_received_revision_verified"] is False
            assert item["source_kind"] in ("manufacturer_reference","fit_placeholder")
            if item["source_kind"]=="manufacturer_reference":
                assert item["source_id"] in source_map
                assert item["source_url"]==source_map[item["source_id"]]["url"]
                assert item["source_as_of"]==studies["reviewed_as_of"]
                assert item["source_claim_status"]=="MAKER_LISTING_REFERENCE_UNVERIFIED_PHYSICAL_VARIANT"
                assert item["manufacturer"]
            else:
                assert item["source_url"] is None and item["manufacturer"] is None
                assert item["sku"] is None and item["source_id"] is None and item["source_as_of"] is None
                assert item["source_claim_status"]=="FIT_PLACEHOLDER_NO_SOURCE"
        if study["domain_id"]=="snowboard":
            mount=study["known_mount_lookups"]
            assert mount["board_mount"]=="CHANNEL_M6_REFERENCE"
            assert mount["binding_mount"]=="REFLEX"
            assert mount["disc_family"]=="BURTON_REFLEX_COMBO"
            assert mount["boot_retention"] in ("STRAP","STEP_ON_ONLY")
            assert any(x["role"]=="boot_pair" and x["source_kind"]=="fit_placeholder"
                       for x in study["components"])
            if mount["boot_retention"]=="STEP_ON_ONLY":
                assert any(x["source_id"]=="burton-stepon" for x in study["components"])
        else:
            assert study["known_mount_lookups"] is None
    return {"source_references":len(sources),"maker_reference_studies":len(studies["studies"]),
            "verified_physical_assemblies":0,"qualified_ski_binding_release":0,"checkout":False}

def main():
    studies=json.loads((ROOT/"catalog/board_sport_reference_studies.v1.json").read_text())
    ontology=json.loads((ROOT/"catalog/outdoor_equipment_domains.v0.json").read_text())
    print(json.dumps(validate(studies,ontology),indent=2))

if __name__=="__main__":
    main()
