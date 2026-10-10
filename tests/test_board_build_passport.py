"""Build Passport revision and sourcing evidence regressions."""
import pytest

from configurator.platform_engine import generate_board_design_space, load_platform_bundle
from configurator.build_passport import build_build_passport, propose_passport_revision_change

BUNDLE = load_platform_bundle()
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PROFILE = json.loads((ROOT / "configurator/examples/trail_rider_profile.json").read_text())
CANDIDATES = {row["id"]: row for row in generate_board_design_space(PROFILE, BUNDLE)["candidates"]}


def passport(name):
    return build_build_passport(CANDIDATES[name], BUNDLE)


def test_revision_sku_and_stock_are_independent():
    p = passport("brake_first_trail_core")
    donor = next(row for row in p["parts"] if row["component_id"] == "DONOR-COMP95")
    assert donor["sku_text"] == "10303"
    assert donor["catalog_revision"] is None
    assert donor["revision_status"] == "EXACT_VARIANT_REVISION_UNVERIFIED"
    assert donor["supplier"]["source_health"] == "REFRESH_DUE"
    assert donor["supplier"]["verified_current_stock"] is False
    assert donor["manufacturer_instructions_url"] is None
    assert donor["price"]["assembly_required_qty"] is None
    assert not any(p["authority"].values())


def test_electric_planning_price_is_not_vendor_quote():
    p = passport("x1_compact_electric_study")
    battery = next(row for row in p["parts"] if row["category"] == "battery")
    assert battery["price"]["price_basis"] == "UNSOURCED_PLANNING_ESTIMATE_USD"
    assert p["sourcing"]["unsourced_planning_usd_estimate"]["min"] > 0
    assert p["sourcing"]["sourced_usd_snapshot"]["min"] > 0
    assert p["sourcing"]["all_in_total_usd"] is None
    assert p["assembly"]["powered"] is True
    assert next(x for x in p["assembly"]["stages"] if x["id"] == "electrical")["status"] == "POWER_GATED"


def test_catalog_reference_compatibility_not_physical_qualification():
    p = passport("brake_first_trail_core")
    assert p["interface_claims"]
    assert all(not row["valid_for_physical_build"] for row in p["interface_claims"])
    assert p["physical_qualification"] == "NOT_QUALIFIED"
    assert p["assembly"]["receiving_inspection_complete"] is False


def test_variant_revision_change_invalidates_every_attached_claim():
    p = passport("brake_first_trail_core")
    initial = json.dumps(p)
    proposed = propose_passport_revision_change(p, "BRAKE-V5", "new-2026-RevB")
    expected = sorted(x["id"] for x in p["interface_claims"] if "BRAKE-V5" in x["component_ids"])
    assert proposed["change_receipt"]["invalidated_interface_ids"] == expected
    assert expected
    assert proposed["study_identity_key"] != p["study_identity_key"]
    assert all(x["revision_evidence_state"] == "INVALIDATED_BY_REVISION_CHANGE"
               for x in proposed["interface_claims"] if "BRAKE-V5" in x["component_ids"])
    assert not any(proposed["authority"].values())
    assert json.dumps(p) == initial


def test_missing_and_invalid_revisions_are_rejected():
    p = passport("brake_first_trail_core")
    with pytest.raises(ValueError, match="Choose a component"):
        propose_passport_revision_change(p, "UNKNOWN-ID", "rev1")
    with pytest.raises(ValueError, match="bounded"):
        propose_passport_revision_change(p, "BRAKE-V5", "")
    with pytest.raises(ValueError, match="bounded"):
        propose_passport_revision_change(p, "BRAKE-V5", "z" * 121)
    with pytest.raises(ValueError, match="Missing catalog part"):
        build_build_passport({**CANDIDATES["brake_first_trail_core"],
                             "bom": [{"component_id": "NO-SUCH-PART"}]}, BUNDLE)



def test_ceiling_is_upper_bound_not_exact_sourced_quote():
    sample = {**CANDIDATES["brake_first_trail_core"],
              "bom": [{"component_id": "TRUCK-M3-400"}]}
    packet = build_build_passport(sample, BUNDLE)
    part = packet["parts"][0]
    assert part["price"]["kind"] == "ceiling"
    assert part["price"]["min_usd"] is None
    assert part["price"]["max_usd"] == 124.95
    assert part["price"]["price_basis"] == "DATED_SOURCE_CEILING_USD"
    assert packet["sourcing"]["ceiling_only_ids"] == ["TRUCK-M3-400"]
    assert packet["sourcing"]["all_in_total_usd"] is None
