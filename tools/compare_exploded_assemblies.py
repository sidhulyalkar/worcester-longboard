#!/usr/bin/env python3
"""Require exact Python/JS exploded graph outputs across all board and sport examples."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from configurator.assembly_graph import build_assembly_graph
from configurator.platform_engine import generate_board_design_space,load_platform_bundle

def read(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def difference(a,b,key="$"):
    if type(a)!=type(b):
        return f"{key} types {type(a).__name__} != {type(b).__name__}"
    if isinstance(a,dict):
        for k in sorted(set(a)|set(b)):
            if k not in a or k not in b:
                return f"{key}.{k} missing"
            issue=difference(a[k],b[k],key+"."+k)
            if issue:
                return issue
    elif isinstance(a,list):
        if len(a)!=len(b):
            return f"{key} length {len(a)} != {len(b)}"
        for i,(x,y) in enumerate(zip(a,b)):
            issue=difference(x,y,key+f"[{i}]")
            if issue:
                return issue
    elif a!=b:
        return f"{key}: {str(a)[:130]} != {str(b)[:130]}"
    return None

def main():
    bundle=load_platform_bundle()
    catalog=read("catalog/board_components.v1.json")
    registry=read("catalog/board_package_inclusions.v1.json")
    recipes=read("catalog/outdoor_assembly_recipes.v1.json")
    profile=read("configurator/examples/trail_rider_profile.json")
    subjects=generate_board_design_space(profile,bundle)["candidates"]+recipes["examples"]
    py=[build_assembly_graph(s,recipes,catalog,registry) for s in subjects]
    js=json.loads(subprocess.check_output(["node","tools/generate_exploded_assembly_graphs.mjs"],
                                          cwd=ROOT,text=True))
    mismatch=difference(py,js)
    assert mismatch is None, "Exploded graph cross-runtime mismatch: "+str(mismatch)
    assert all(not any(x["authority"].values()) for x in py)
    assert all(x["completeness"]["physical_connections_qualified"]==0 for x in py)
    print(json.dumps({"parity":"PASS","graphs":len(py),
       "existing_board_studies":len(subjects)-len(recipes["examples"]),
       "illustrative_sport_concepts":len(recipes["examples"]),
       "physical_approvals":0},indent=2))

if __name__=="__main__":
    main()
