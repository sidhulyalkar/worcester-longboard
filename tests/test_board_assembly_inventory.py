"""Quantity, package inclusion, stock and retrofit audit regressions."""
import copy
import json
from pathlib import Path
import pytest
from configurator.platform_engine import generate_board_design_space, load_platform_bundle
from configurator.build_passport import build_build_passport, propose_passport_revision_change
from configurator.assembly_inventory import audit_assembly_inventory

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = load_platform_bundle()
PROFILE = json.loads((ROOT / "configurator/examples/trail_rider_profile.json").read_text())
CANDIDATES = {c["id"]: c for c in generate_board_design_space(PROFILE, BUNDLE)["candidates"]}


def passport(name="brake_first_trail_core"):
    return build_build_passport(CANDIDATES[name], BUNDLE)


def synthetic(ids):
    candidate = {**CANDIDATES["brake_first_trail_core"], "bom": [{"component_id": x} for x in ids]}
    return build_build_passport(candidate, BUNDLE)


def test_donor_package_contents_do_not_establish_counts_or_prices():
    p = passport()
    a = p["assembly_inventory_audit"]
    donor = next(x for x in a["package_claims"] if x["package_id"] == "DONOR-COMP95")
    assert donor["snapshot_binding_status"] == "BOUND_TO_REFERENCE_SNAPSHOT"
    assert donor["exact_received_contents_verified"] is False
    assert donor["order_unit_quantity"] is None
    assert any(x["inclusion_token"] == "f5_bindings" for x in a["unmapped_inclusion_worklist"])
    assert all(x["actual_supplier_order_quantity"] is None for x in a["order_lines"])
    assert a["costs"]["overlap_adjusted_total_usd"] is None
    assert not any(a["authority"].values())


def test_donor_hub_and_truck_potential_double_count_stays_undiscounted():
    p = synthetic(["DONOR-COMP95", "HUB-RSII", "TRUCK-M3-400", "BRAKE-V5"])
    a = p["assembly_inventory_audit"]
    assert [x["component_id"] for x in a["overlap_worklist"]] == ["HUB-RSII", "TRUCK-M3-400"]
    assert all(x["classification"] == "POSSIBLE_DOUBLE_COUNT" for x in a["overlap_worklist"])
    assert a["costs"]["existing_bom_subtotal_has_possible_double_count"] is True
    assert p["sourcing"]["sourced_usd_snapshot"]["min"] > 0
    assert a["costs"]["confirmed_quote_total_usd"] is None


def test_retrofits_remain_measure_first():
    p = synthetic(["DONOR-COMP95", "AXLE-M3-70", "DRIVE-G1-DUAL"])
    a = p["assembly_inventory_audit"]
    assert [x["component_id"] for x in a["retrofit_worklist"]] == ["AXLE-M3-70", "DRIVE-G1-DUAL"]
    assert not a["eligibility"]["mechanical_interfaces_qualified"]
    assert not a["eligibility"]["electrical_integration_qualified"]


def test_stale_mapping_invalidation_and_revision_change():
    packet = passport()
    changed = copy.deepcopy(packet)
    next(x for x in changed["parts"] if x["component_id"] == "DONOR-COMP95")["supplier"]["snapshot_id"] = "new-listing"
    result = audit_assembly_inventory(changed, BUNDLE["packageInclusions"])
    assert result["package_claims"][0]["snapshot_binding_status"] == "STALE_OR_CHANGED_SOURCE_HOLD"
    assert any(x["reason"] == "STALE_OR_CHANGED_SOURCE_HOLD" for x in result["unmapped_inclusion_worklist"])
    revision = propose_passport_revision_change(packet, "DONOR-COMP95", "rev-new")
    assert revision["assembly_inventory_audit"] is None
    assert revision["physical_qualification"] == "NOT_QUALIFIED"


def test_mismatched_inclusion_claims_and_duplicate_bom_rejected():
    packet = passport()
    registry = copy.deepcopy(BUNDLE["packageInclusions"])
    registry["packages"][0]["inclusions"].pop()
    with pytest.raises(ValueError, match="included token mismatch"):
        audit_assembly_inventory(packet, registry)
    duplicated = copy.deepcopy(packet)
    duplicated["parts"].append(copy.deepcopy(duplicated["parts"][0]))
    with pytest.raises(ValueError, match="Duplicate BOM"):
        audit_assembly_inventory(duplicated, BUNDLE["packageInclusions"])


def test_new_unmapped_donor_fails_closed():
    packet = passport()
    packet["parts"][0]["component_id"] = "DONOR-UNKNOWN-REF"
    report = audit_assembly_inventory(packet, BUNDLE["packageInclusions"])
    assert report["package_claims"][0]["snapshot_binding_status"] == "UNMAPPED_BUNDLE_HOLD"
    assert len(report["unmapped_inclusion_worklist"]) >= 5
    assert report["costs"]["all_in_assembly_total_usd"] is None
