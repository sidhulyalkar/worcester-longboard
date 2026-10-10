#!/usr/bin/env python3
"""Compare the complete Python/JavaScript evidence-ledger outputs for two actual builds."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from configurator.platform_engine import generate_board_design_space, load_platform_bundle
from configurator.build_passport import build_build_passport
from configurator.evidence_notebook import (
    empty_evidence_notebook, record_evidence, evaluate_evidence_notebook
)


def python_report(name):
    bundle = load_platform_bundle()
    profile = json.loads((ROOT / "configurator/examples/trail_rider_profile.json").read_text())
    generated = generate_board_design_space(profile, bundle)
    selected = next(x for x in generated["candidates"] if x["id"] == name)
    passport = build_build_passport(selected, bundle)
    book = empty_evidence_notebook(passport)
    first = passport["parts"][0]
    book = record_evidence(book, passport, {
        "kind": "SOURCE_REFERENCE", "component_id": first["component_id"],
        "evidence_url": "https://example.org/catalog/source-record", "as_of": "2026-10-10",
    })
    book = record_evidence(book, passport, {
        "kind": "RECEIVING_OBSERVATION", "component_id": first["component_id"],
        "observed_revision": "Test Rev A", "quantity_received": 1, "as_of": "2026-10-10",
        "note": "Synthetic first-piece receiving note",
    })
    manual = next((p for p in passport["parts"] if p["component_id"] == "BRAKE-V5"), first)
    book = record_evidence(book, passport, {
        "kind": "MANUFACTURER_INSTRUCTIONS_CANDIDATE", "component_id": manual["component_id"],
        "observed_revision": "Test Rev A", "evidence_url": "https://example.org/not-verified/manual",
        "as_of": "2026-10-10",
    })
    claim = next((c for c in passport["interface_claims"] if first["component_id"] in c["component_ids"]), None)
    if claim:
        book = record_evidence(book, passport, {
            "kind": "INTERFACE_MEASUREMENT_NOTE", "component_id": first["component_id"],
            "interface_id": claim["id"], "note": "Missing actual tolerance stack measurements",
        })
    return {"notebook": book, "review": evaluate_evidence_notebook(passport, book)}


def main():
    for name in ("brake_first_trail_core", "x1_compact_electric_study"):
        browser = json.loads(subprocess.check_output(
            ["node", "tools/generate_evidence_notebook.mjs", name],
            cwd=ROOT, text=True
        ))
        python = python_report(name)
        assert python == browser, (
            "Cross-runtime evidence mismatch in " + name +
            "\nPython: " + json.dumps(python, indent=2) +
            "\nBrowser: " + json.dumps(browser, indent=2)
        )
        assert python["review"]["physical_qualification"] == "NOT_QUALIFIED"
        assert not any(python["notebook"]["authority"].values())
        assert not any(python["review"]["authority"].values())
        assert python["review"]["manufacturer_manuals_independently_verified"] == 0
        print(f"Evidence notebook parity PASS {name}: {len(python['notebook']['records'])} records")


if __name__ == "__main__":
    main()
