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
    assert report["buy_now_maximum_usd"] <= report["buy_now_ceiling_usd"]


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
