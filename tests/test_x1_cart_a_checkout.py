import copy
import json
from pathlib import Path

from tools.init_x1_cart_a_checkout import initialize
from tools.validate_x1_cart_a_checkout import validate

ROOT = Path(__file__).resolve().parents[1]


def _inventory():
    data = json.loads(
        (ROOT / "hardware/x1_physical_kickoff_inventory_template.json").read_text()
    )
    data["inventory_checked_at_utc"] = "2026-10-02T12:00:00-07:00"
    for row in data["items"]:
        row["status"] = "NEED_BUY"
    return data


def _write_inventory(tmp_path: Path, data=None):
    path = tmp_path / "owned_inventory.json"
    path.write_text(json.dumps(data or _inventory(), indent=2), encoding="utf-8")
    return path


def _complete_checkout_fields(checkout, *, status="READY_TO_ORDER", checkout_at="2026-10-02T12:30:00-07:00"):
    checkout["status"] = status
    checkout["checkout_at_utc"] = checkout_at

    for row in checkout["items"]:
        if row["resolution"] == "ORDER":
            row["stock_confirmed_at_checkout"] = True
            if row["source_snapshot_required"]:
                row["source_rechecked_at_checkout"] = True
            if row["unit_price_usd"] is None:
                row["unit_price_usd"] = 1.0
            if status == "ORDERED":
                row["order_confirmation_ref"] = f"private-order-{row['id']}"

    merchandise = sum(
        row["ordered_qty"] * float(row["unit_price_usd"])
        for row in checkout["items"]
        if row["resolution"] == "ORDER"
    )
    checkout["merchandise_total_usd"] = round(merchandise, 2)
    if status == "ORDERED":
        checkout["shipping_usd"] = 5.0
        checkout["tax_usd"] = 4.0
        checkout["order_total_usd"] = round(merchandise + 9.0, 2)
    return checkout


def _initialized(tmp_path: Path, inventory=None):
    inv_data = inventory or _inventory()
    inv_path = _write_inventory(tmp_path, inv_data)
    checkout_path = tmp_path / "cart_a_checkout.json"
    checkout = initialize(checkout_path, inv_path, "CART-A-TEST")
    return checkout, inv_data


def test_ready_cart_a_checkout_is_valid_but_creates_no_new_authority(tmp_path: Path):
    checkout, inventory = _initialized(tmp_path)
    _complete_checkout_fields(checkout)
    report = validate(checkout, inventory)

    assert report["valid"] is True
    assert report["checkout_ready"] is True
    assert report["order_record_complete"] is False
    assert report["checkout_within_existing_buy_now_authority"] is True
    assert report["merchandise_total_usd"] <= report["buy_now_ceiling_usd"]
    assert report["procurement_authority"] is False
    assert report["physical_qualification_authority"] is False
    assert report["fabrication_authority"] is False
    assert report["powered_operation_authorized"] is False
    assert "DONOR-COMP95" not in report["ordered_item_ids"]
    assert "BATTERY-PRO-MODULAR" not in report["ordered_item_ids"]


def test_ordered_checkout_requires_confirmation_and_total_reconciliation(tmp_path: Path):
    checkout, inventory = _initialized(tmp_path)
    _complete_checkout_fields(checkout, status="ORDERED")
    report = validate(checkout, inventory)
    assert report["valid"] is True
    assert report["order_record_complete"] is True

    broken = copy.deepcopy(checkout)
    ordered = next(row for row in broken["items"] if row["resolution"] == "ORDER")
    ordered["order_confirmation_ref"] = ""
    broken["order_total_usd"] += 10.0
    report = validate(broken, inventory)
    assert report["valid"] is False
    assert any("order_confirmation_ref" in error for error in report["errors"])
    assert "order_total_usd does not match merchandise + shipping + tax" in report["errors"]


def test_refreshed_exact_sources_expire_after_declared_freshness_window(tmp_path: Path):
    checkout, inventory = _initialized(tmp_path)
    _complete_checkout_fields(
        checkout,
        checkout_at="2026-10-10T12:30:00-07:00",
    )
    report = validate(checkout, inventory)

    assert report["valid"] is False
    assert any("refresh snapshot before checkout" in error for error in report["errors"])


def test_price_change_on_refreshed_source_forces_snapshot_refresh(tmp_path: Path):
    checkout, inventory = _initialized(tmp_path)
    _complete_checkout_fields(checkout)
    load_cell = next(row for row in checkout["items"] if row["id"] == "LC-3135")
    load_cell["unit_price_usd"] = 6.5
    checkout["merchandise_total_usd"] = round(
        sum(
            row["ordered_qty"] * float(row["unit_price_usd"])
            for row in checkout["items"]
            if row["resolution"] == "ORDER"
        ),
        2,
    )

    report = validate(checkout, inventory)
    assert report["valid"] is False
    assert any("checkout price changed; refresh source snapshot" in error for error in report["errors"])


def test_blocked_item_injection_is_rejected(tmp_path: Path):
    checkout, inventory = _initialized(tmp_path)
    _complete_checkout_fields(checkout)
    checkout["items"].append(
        {
            "id": "DONOR-COMP95",
            "required_qty": 1,
            "optional_if_owned": False,
            "resolution": "ORDER",
            "owned_qty_verified": 0,
            "ordered_qty": 1,
            "seller": "MBS",
            "sku": "10303",
            "source_url": "",
            "source_last_verified_as_of": "",
            "source_snapshot_required": False,
            "source_rechecked_at_checkout": True,
            "stock_confirmed_at_checkout": True,
            "unit_price_usd": 499.95,
            "order_confirmation_ref": "",
            "notes": "",
        }
    )
    report = validate(checkout, inventory)
    assert report["valid"] is False
    assert any("only orderable BUY_NOW ids" in error for error in report["errors"])


def test_exact_owned_required_evidence_can_avoid_duplicate_purchase(tmp_path: Path):
    inventory = _inventory()
    cell = next(row for row in inventory["items"] if row["id"] == "LC-3135")
    cell.update(
        {
            "status": "OWNED_EXACT_UNUSED",
            "qty_owned_verified": 2,
            "exact_part_match": True,
            "unused_or_known_history": True,
        }
    )
    checkout, inventory = _initialized(tmp_path, inventory)
    row = next(row for row in checkout["items"] if row["id"] == "LC-3135")
    assert row["resolution"] == "USE_OWNED_EXACT"

    _complete_checkout_fields(checkout)
    report = validate(checkout, inventory)
    assert report["valid"] is True
    assert "LC-3135" in report["owned_item_ids"]
    assert "LC-3135" not in report["ordered_item_ids"]


def test_vague_owned_equivalent_cannot_satisfy_required_load_cell(tmp_path: Path):
    inventory = _inventory()
    cell = next(row for row in inventory["items"] if row["id"] == "LC-3135")
    cell.update(
        {
            "status": "OWNED_EQUIVALENT",
            "qty_owned_verified": 2,
            "exact_part_match": False,
            "unused_or_known_history": True,
        }
    )
    checkout, inventory = _initialized(tmp_path, inventory)
    row = next(row for row in checkout["items"] if row["id"] == "LC-3135")
    assert row["resolution"] == "UNRESOLVED"

    _complete_checkout_fields(checkout)
    report = validate(checkout, inventory)
    assert report["valid"] is False
    assert "LC-3135" in report["unresolved_item_ids"]
