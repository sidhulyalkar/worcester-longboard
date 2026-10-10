#!/usr/bin/env python3
"""Check exact JS/Python receiving reconciliation for manual/electric examples."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from configurator.platform_engine import generate_board_design_space,load_platform_bundle
from configurator.build_passport import build_build_passport
from configurator.evidence_notebook import empty_evidence_notebook,record_evidence
from configurator.receiving_reconciliation import build_receiving_reconciliation


def fixture(name: str):
    bundle=load_platform_bundle()
    profile=json.loads((ROOT/"configurator/examples/trail_rider_profile.json").read_text())
    candidates=generate_board_design_space(profile,bundle)["candidates"]
    p=build_build_passport(next(x for x in candidates if x["id"]==name),bundle)
    component=p["parts"][0]["component_id"]
    book=empty_evidence_notebook(p)
    book=record_evidence(book,p,{"kind":"RECEIVING_OBSERVATION","component_id":component,
         "observed_revision":"Sample A","quantity_received":1,"as_of":"2026-10-10"})
    book=record_evidence(book,p,{"kind":"SOURCE_REFERENCE","component_id":component,
         "evidence_url":"https://example.org/reference","as_of":"2026-10-10"})
    book=record_evidence(book,p,{"kind":"RECEIVING_OBSERVATION","component_id":component,
         "observed_revision":"Sample B","quantity_received":2,"as_of":"2026-10-10"})
    docs=json.loads((ROOT/"catalog/manufacturer_document_references.v1.json").read_text())
    return build_receiving_reconciliation(p,book,docs)


def main():
    for name in ("brake_first_trail_core","x1_compact_electric_study"):
        actual=json.loads(subprocess.check_output(
            ["node","tools/generate_receiving_reconciliation.mjs",name],cwd=ROOT,text=True))
        expected=fixture(name)
        assert actual==expected, f"Receiving reconciliation cross-runtime mismatch for {name}"
        assert expected["confirmation"]["physical_qualification"]=="NOT_QUALIFIED"
        assert not any(expected["authority"].values())
        print(f"Receiving reconciliation parity PASS {name}: {len(expected['rows'])} parts")


if __name__=="__main__":
    main()
