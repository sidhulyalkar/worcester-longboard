#!/usr/bin/env python3
"""Fail closed if sport concept recipes are misclassified as product/assembly authority."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DOMAINS=json.loads((ROOT/"catalog/outdoor_equipment_domains.v0.json").read_text())
COMPONENTS=json.loads((ROOT/"catalog/board_components.v1.json").read_text())
RECIPES=json.loads((ROOT/"catalog/outdoor_assembly_recipes.v1.json").read_text())

def main():
    r=RECIPES
    assert r["schema_version"]==1
    assert r["scope"]=="CONCEPTUAL_ASSEMBLY_VISUALIZATION_NOT_PHYSICAL_INSTRUCTIONS"
    assert not any(r["authority"].values())
    groups={g["id"]:g for g in r["groups"]}
    assert len(groups)==len(r["groups"])
    roles=[role for g in r["groups"] for role in g["roles"]]
    assert len(roles)==len(set(roles)), "Duplicate exploded group role"
    assert all(len(g["vector"])==2 and isinstance(g["shape"],str) for g in r["groups"])
    assert set(x["category"] for x in COMPONENTS["components"]).issubset(set(roles))
    domains={d["id"]:d for d in r["domains"]}
    assert len(domains)==len(r["domains"])
    ontology={d["id"]:d for d in DOMAINS["domains"]}
    assert set(domains).issubset(set(ontology))
    assert domains["mountainboard"]["source"]=="LIVE_EXISTING_BOARD_CANDIDATE"
    assert domains["mountainboard"]["example_id"] is None
    assert len(r["examples"])==len(domains)-1
    expected_ids={d["example_id"] for d in r["domains"] if d["id"]!="mountainboard"}
    assert {x["id"] for x in r["examples"]}==expected_ids
    assert all(d["source"]=="UNSOURCED_ILLUSTRATIVE_CONCEPT" for d in r["domains"] if d["id"]!="mountainboard")
    for ex in r["examples"]:
        domain=ontology[ex["domain_id"]]
        allowed=set(domain["required_roles"]+domain["optional_roles"]+
                    [x["role"] for x in domain.get("conditional_required_roles",[])])
        ids=[x["component_id"] for x in ex["components"]]
        assert len(ids)==len(set(ids))
        assert all(x["role"] in roles for x in ex["components"])
        assert all(x["role"] in allowed or
                   (ex["domain_id"]=="skateboard_longboard" and x["role"]=="truck")
                   for x in ex["components"]),f"Role unavailable for domain: {ex['domain_id']}"
        assert all(x["source_kind"]=="illustrative_concept" and
                   x["manufacturer"] is None and x["sku"] is None and
                   x["source_url"] is None and x["price"] is None and
                   x["quantity_verified"] is None
                   for x in ex["components"])
        assert all(x["component_id"].startswith("DEMO-") for x in ex["components"])
    print({"validated_sport_domains":len(domains),
           "illustrative_examples":len(r["examples"]),
           "assembly_groups":len(groups),
           "verified_product_items":0,
           "physical_authorization":False})
if __name__=="__main__":
    main()
