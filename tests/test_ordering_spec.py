import copy
import json
from pathlib import Path

from tools.validate_ordering_spec import validate

ROOT = Path(__file__).resolve().parents[1]


def _procurement():
    return json.loads((ROOT / "hardware/procurement_manifest.json").read_text())


def _sources():
    return json.loads((ROOT / "hardware/order_sources_2026-10-01.json").read_text())


def _planned():
    return json.loads((ROOT / "hardware/planned_system_bom.json").read_text())


def test_ordering_spec_is_consistent():
    report = validate(_procurement(), _sources(), _planned())
    assert report["valid"] is True, report["errors"]


def test_power_source_cannot_be_recommended():
    sources = copy.deepcopy(_sources())
    drive = next(x for x in sources["sources"] if x["manifest_id"] == "DRIVE-G1-DUAL")
    drive["recommended"] = True
    report = validate(_procurement(), sources, _planned())
    assert report["valid"] is False
    assert any("POWER_GATED" in error for error in report["errors"])


def test_source_price_drift_is_detected():
    sources = copy.deepcopy(_sources())
    load_cell = next(x for x in sources["sources"] if x["manifest_id"] == "LC-3135")
    load_cell["unit_price_usd"] = 99.0
    report = validate(_procurement(), sources, _planned())
    assert report["valid"] is False
    assert any("disagrees with manifest" in error for error in report["errors"])


def test_9in_caveat_cannot_be_silently_removed():
    procurement = copy.deepcopy(_procurement())
    tire = next(x for x in procurement["items"] if x["id"] == "TIRE-T2-9")
    tire.pop("defer_until")
    tire["notes"] = "optional tire"
    report = validate(procurement, _sources(), _planned())
    assert report["valid"] is False
    assert any("TIRE-T2-9" in error for error in report["errors"])


def test_powered_subsystems_stay_non_orderable():
    planned = copy.deepcopy(_planned())
    drive = next(x for x in planned["subsystems"] if x["id"] == "DRIVE")
    drive["status"] = "ORDER_NOW"
    report = validate(_procurement(), _sources(), planned)
    assert report["valid"] is False
    assert any("DRIVE" in error for error in report["errors"])


def test_october_refresh_scope_is_exact_and_fresh():
    sources = _sources()
    assert sources["as_of"] == "2026-10-01"
    assert sources["refresh_scope"] == "ISSUE_4_CART_A_EXACT_EVIDENCE_HARDWARE"
    assert sources["refresh_scope_manifest_ids"] == [
        "LC-3135",
        "ADC-HX711",
        "MCU-ESP32S3",
    ]
    rows = {item["manifest_id"]: item for item in sources["sources"]}
    for item_id in sources["refresh_scope_manifest_ids"]:
        assert rows[item_id]["last_verified_as_of"] == "2026-10-01"
        assert rows[item_id]["availability_status"] == "IN_STOCK"


def test_scoped_refresh_cannot_claim_stale_required_source_is_fresh():
    sources = copy.deepcopy(_sources())
    row = next(x for x in sources["sources"] if x["manifest_id"] == "ADC-HX711")
    row["last_verified_as_of"] = "2026-09-11"
    report = validate(_procurement(), sources, _planned())
    assert report["valid"] is False
    assert any("scoped refresh entry must be verified" in error for error in report["errors"])


def test_scoped_refresh_requires_recorded_in_stock_state():
    sources = copy.deepcopy(_sources())
    row = next(x for x in sources["sources"] if x["manifest_id"] == "LC-3135")
    row["availability_status"] = "UNKNOWN"
    report = validate(_procurement(), sources, _planned())
    assert report["valid"] is False
    assert any("must record IN_STOCK availability" in error for error in report["errors"])
