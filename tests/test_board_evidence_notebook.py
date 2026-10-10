"""Independent Python regressions for the unverified receiving and sourcing ledger."""
import copy
import json
from pathlib import Path
import pytest

from configurator.platform_engine import load_platform_bundle, generate_board_design_space
from configurator.build_passport import build_build_passport, propose_passport_revision_change
from configurator.evidence_notebook import (
    empty_evidence_notebook, record_evidence, restore_evidence_notebook, evaluate_evidence_notebook
)

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = load_platform_bundle()
PROFILE = json.loads((ROOT / "configurator/examples/trail_rider_profile.json").read_text())
CANDIDATES = {x["id"]: x for x in generate_board_design_space(PROFILE, BUNDLE)["candidates"]}
RECEIVING = {
    "kind": "RECEIVING_OBSERVATION", "component_id": "DONOR-COMP95",
    "observed_revision": "Rev B - label", "quantity_received": 1,
    "as_of": "2026-10-10", "note": "Photo of carton retained locally",
}


def passport(name="brake_first_trail_core"):
    return build_build_passport(CANDIDATES[name], BUNDLE)


def test_receiving_never_unlocks_order_quantity_or_assembly():
    p = passport()
    book = record_evidence(empty_evidence_notebook(p), p, RECEIVING)
    review = evaluate_evidence_notebook(p, book)
    assert book["records"][0]["quantity_received"] == 1
    assert book["records"][0]["review_status"] == "USER_RECORDED_NOT_INDEPENDENTLY_VERIFIED"
    assert p["parts"][0]["price"]["assembly_required_qty"] is None
    assert review["invalidated_interface_ids"] == sorted(x["id"] for x in p["interface_claims"])
    assert review["assembly_quantities_authorized"] == 0
    assert review["stock_confirmed"] == 0
    assert review["physical_qualification"] == "NOT_QUALIFIED"
    assert not any(book["authority"].values()) and not any(review["authority"].values())


def test_source_manual_citations_are_unverified_even_when_https():
    p = passport()
    book = empty_evidence_notebook(p)
    book = record_evidence(book, p, {"kind": "SOURCE_REFERENCE", "component_id": "BRAKE-V5",
        "evidence_url": "https://www.mbs.com/shop/parts/brakes", "as_of": "2026-10-10"})
    book = record_evidence(book, p, {"kind": "MANUFACTURER_INSTRUCTIONS_CANDIDATE",
        "component_id": "BRAKE-V5", "observed_revision": "v5-marked",
        "evidence_url": "https://www.mbs.com/manual.pdf", "as_of": "2026-10-10"})
    review = evaluate_evidence_notebook(p, book)
    assert review["instruction_candidates_part_ids"] == ["BRAKE-V5"]
    assert review["manufacturer_manuals_independently_verified"] == 0
    assert review["stock_confirmed"] == 0


def test_interface_note_retains_unknown_state():
    p = passport("x1_compact_electric_study")
    claim = next(c for c in p["interface_claims"] if c["reference_state"] in ("UNKNOWN", "MEASURE_FIRST"))
    id_of_part = next(i for i in claim["component_ids"] if i in {p["component_id"] for p in p["parts"]})
    book = record_evidence(empty_evidence_notebook(p), p, {
        "kind": "INTERFACE_MEASUREMENT_NOTE", "component_id": id_of_part,
        "interface_id": claim["id"], "note": "Calibrated axle measurement still required"
    })
    review = evaluate_evidence_notebook(p, book)
    assert claim["id"] in review["unresolved_interface_ids"]
    assert claim["id"] in review["noted_interface_ids"]


@pytest.mark.parametrize("changes", [
    {"quantity_received": 0}, {"quantity_received": 1.5},
    {"quantity_received": 501}, {"as_of": "2026-02-31"},
    {"component_id": "FAKE"}, {"kind": "PROMOTE_AUTHORITY"},
    {"evidence_url": "javascript:alert(1)"},
    {"evidence_url": "https://user:pass@example.org"},
    {"observed_revision": "x\n<script>alert(1)</script>"},
])
def test_invalid_untrusted_fields(changes):
    p = passport()
    with pytest.raises(ValueError):
        record_evidence(empty_evidence_notebook(p), p, {**RECEIVING, **changes})


def test_forged_and_stale_records_fail_closed():
    p = passport()
    book = record_evidence(empty_evidence_notebook(p), p, RECEIVING)
    forged = copy.deepcopy(book)
    forged["records"][0]["review_status"] = "VERIFIED"
    forged["records"][0]["usable_for_qualification"] = True
    forged["authority"]["procurement_authorized"] = True
    restored = restore_evidence_notebook(p, forged)
    assert restored["records"][0]["review_status"] == "USER_RECORDED_NOT_INDEPENDENTLY_VERIFIED"
    assert restored["records"][0]["usable_for_qualification"] is False
    assert not any(restored["authority"].values())
    stale = copy.deepcopy(book)
    stale["study_identity_key"] = "other-source"
    assert restore_evidence_notebook(p, stale)["records"] == []
    changed = propose_passport_revision_change(p, "BRAKE-V5", "revision-C")
    assert restore_evidence_notebook(changed, book)["records"] == []


def test_restore_preserves_valid_history():
    p = passport()
    book = record_evidence(empty_evidence_notebook(p), p, {
        "kind": "SOURCE_REFERENCE", "component_id": "DONOR-COMP95",
        "evidence_url": "https://www.mbs.com/shop/p/example", "as_of": "2026-10-10"
    })
    book = record_evidence(book, p, RECEIVING)
    assert restore_evidence_notebook(p, json.dumps(book)) == book
