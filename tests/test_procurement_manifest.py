import json
from copy import deepcopy
from pathlib import Path

from tools.validate_procurement_manifest import validate_manifest


def _manifest():
    return json.loads(Path("hardware/procurement_manifest.json").read_text())


def test_manifest_is_valid_and_power_hardware_stays_blocked():
    report = validate_manifest(_manifest())
    assert report["valid"] is True
    assert report["power_gated_authorized"] is False
    assert report["buy_now_maximum_usd"] == 120.9
    assert report["buy_now_maximum_usd"] <= report["buy_now_ceiling_usd"]


def test_rev_c_holds_expensive_chassis_while_retaining_comp95_reference():
    data = _manifest()
    assert data["rules"]["preferred_chassis_strategy"] == "REV_C_HOLD_COMPACT_MATRIX_REFERENCE"
    assert data["rules"]["preferred_chassis_item_id"] == "DONOR-COMP95"
    assert data["rules"]["rev_c_expensive_procurement_hold"] == "evidence_gated"
    assert data["rules"]["rev_c_chassis_release_gate"] == "rev_c_chassis_release_qualified"
    items = {item["id"]: item for item in data["items"]}
    assert items["DONOR-COMP95"]["purchase_strategy"] == "leading_compact_reference_not_yet_authorized"
    assert items["DONOR-COMP95"]["requires_gate"] == "rev_c_chassis_release_qualified"
    assert items["BRAKE-V5"]["requires_gate"] == "rev_c_chassis_release_qualified"
    assert items["TRUCK-M3-400"]["alternative_to"] == "DONOR-COMP95"
    assert items["HUB-RSII"]["alternative_to"] == "DONOR-COMP95"
    assert items["AXLE-M3-70"]["purchase_strategy"] == "deferred_interface_study"
    assert "BATTERY-PRO-MODULAR" in items


def test_power_gate_cannot_be_promoted_in_this_tranche():
    data = _manifest()
    data["rules"]["power_gated_authorized"] = True
    report = validate_manifest(data)
    assert report["valid"] is False
    assert any("power-gated procurement" in err for err in report["errors"])


def test_buy_now_budget_is_hard_gated():
    data = _manifest()
    data["rules"]["buy_now_max_total_usd"] = 1.0
    report = validate_manifest(data)
    assert report["valid"] is False
    assert any("BUY_NOW ceiling exceeded" in err for err in report["errors"])


def test_duplicate_sku_authority_id_is_rejected():
    data = _manifest()
    duplicate = deepcopy(data["items"][0])
    data["items"].append(duplicate)
    report = validate_manifest(data)
    assert report["valid"] is False
    assert any("duplicate" in err for err in report["errors"])


def test_missing_preferred_or_alternative_targets_are_rejected():
    data = _manifest()
    data["rules"]["preferred_chassis_item_id"] = "NOT-REAL"
    data["items"][12]["alternative_to"] = "ALSO-NOT-REAL"
    report = validate_manifest(data)
    assert report["valid"] is False
    assert any("preferred chassis item does not exist" in err for err in report["errors"])
    assert any("alternative target does not exist" in err for err in report["errors"])
