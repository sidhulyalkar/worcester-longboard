#!/usr/bin/env python3
"""Reproducible exact normalized graph parity and unchanged v1 board design output."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from configurator.outdoor_catalog_graph import build_outdoor_catalog_graph,replay_legacy_board_catalog
from configurator.platform_engine import generate_board_design_space,load_platform_bundle
from configurator.build_passport import build_build_passport


def main():
    def read(path):
        return json.loads((ROOT/path).read_text(encoding="utf-8"))
    catalog=read("catalog/board_components.v1.json")
    domains=read("catalog/outdoor_equipment_domains.v0.json")
    incl=read("catalog/board_package_inclusions.v1.json")
    graph=build_outdoor_catalog_graph(catalog,domains,incl)
    js=json.loads(subprocess.check_output(["node","tools/generate_outdoor_catalog_graph.mjs"],cwd=ROOT,text=True))
    if graph != js:
        def first_difference(a, b, route="$"):
            if type(a) is not type(b):
                return f"{route}: types {type(a).__name__} != {type(b).__name__}; values {str(a)[:140]} != {str(b)[:140]}"
            if isinstance(a, dict):
                for key in sorted(set(a) | set(b)):
                    if key not in a or key not in b:
                        return f"{route}.{key}: missing from one graph"
                    result = first_difference(a[key], b[key], f"{route}.{key}")
                    if result:
                        return result
            if isinstance(a, list):
                if len(a) != len(b):
                    return f"{route}: list length {len(a)} != {len(b)}"
                for i, (x, y) in enumerate(zip(a, b)):
                    result = first_difference(x, y, f"{route}[{i}]")
                    if result:
                        return result
            if a != b:
                return f"{route}: {str(a)[:250]} != {str(b)[:250]}"
            return ""
        raise AssertionError("Cross-runtime outdoor catalog graph mismatch: " + first_difference(graph,js))
    assert replay_legacy_board_catalog(graph)==catalog
    assert graph["summary"]["imported_legacy_components"]==len(catalog["components"])
    assert graph["summary"]["confirmed_exact_variants"]==0
    assert not any(graph["authority"].values())
    assert not any(x["checkout_authorized"] for x in graph["supplier_offer_references"])
    bundle=load_platform_bundle()
    profile=read("configurator/examples/trail_rider_profile.json")
    before=generate_board_design_space(profile,bundle)
    copy_bundle=dict(bundle,catalog=replay_legacy_board_catalog(graph))
    after=generate_board_design_space(profile,copy_bundle)
    assert before==after,"Existing candidate/BOM/readiness/evidence output changed by graph adapter"
    for item in before["candidates"][:4]:
        a=build_build_passport(item,bundle)
        b=build_build_passport(item,copy_bundle)
        assert a==b,"Build Passport changed for "+item["id"]
    print(json.dumps({
      "result":"PASS", "engine_parity":"EXACT",
      "legacy_replay":"EXACT", "board_design_space_parity":"EXACT",
      "build_passport_parity":"EXACT",
      "families":len(graph["families"]),"variants":len(graph["variants"]),
      "claims":len(graph["engineering_claims"]),
      "dated_offer_references":len(graph["supplier_offer_references"]),
      "package_hypotheses":len(graph["sellable_package_hypotheses"]),
      "physically_qualified":False},indent=2))


if __name__=="__main__":
    main()
