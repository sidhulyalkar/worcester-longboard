import copy
import json
from pathlib import Path

from tools.init_x1_cart_a_checkout import initialize as init_checkout
from tools.init_x1_cart_a_receiving import initialize as init_receiving
from tools.validate_x1_cart_a_checkout import validate as validate_checkout
from tools.validate_x1_cart_a_receiving import validate as validate_receiving

ROOT = Path(__file__).resolve().parents[1]


def _inventory():
    data = json.loads(
        (ROOT / "hardware/x1_physical_kickoff_inventory_template.json").read_text()
    )
    data["inventory_checked_at_utc"] = "2026-10-02T12:00:00-07:00"
    for row in data["items"]:
        row["status"] = "NEED_BUY"
    return data


def _ordered_checkout(tmp_path: Path):
    inventory = _inventory()
    inventory_path = tmp_path / "owned_inventory.json"
    inventory_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    checkout_path = tmp_path / "checkout.json"
    checkout = init_checkout(
        checkout_path,
        inventory_path,
        "CART-A-ORDERED",
    )
    checkout["status"] = "ORDERED"
    checkout["checkout_at_utc"] = "2026-10-02T12:30:00-07:00"
    for row in checkout["items"]:
        if row["resolution"] != "ORDER":
            continue
        row["stock_confirmed_at_checkout"] = True
        if row["source_snapshot_required"]:
            row["source_rechecked_at_checkout"] = True
        if row["unit_price_usd"] is None:
            row["unit_price_usd"] = 1.0
        row["order_confirmation_ref"] = f"private-order-{row['id']}"

    merchandise = sum(
        row["ordered_qty"] * float(row["unit_price_usd"])
        for row in checkout["items"]
        if row["resolution"] == "ORDER"
    )
    checkout["merchandise_total_usd"] = round(merchandise, 2)
    checkout["shipping_usd"] = 5.0
    checkout["tax_usd"] = 4.0
    checkout["order_total_usd"] = round(merchandise + 9.0, 2)
    checkout_path.write_text(json.dumps(checkout, indent=2), encoding="utf-8")

    authority = validate_checkout(checkout, inventory)
    assert authority["valid"] is True
    assert authority["order_record_complete"] is True
    authority_path = tmp_path / "checkout_authority.json"
    authority_path.write_text(json.dumps(authority, indent=2), encoding="utf-8")
    return checkout_path, authority_path, checkout, authority


def _unit(hardware_id, role):
    return {
        "hardware_id": hardware_id,
        "role": role,
        "exact_part_match": True,
        "visible_damage_observed": False,
        "packaging_and_markings_recorded": True,
        "condition_note": "Received clean with expected markings and no visible damage.",
    }


def _complete_receiving(receiving):
    receiving["status"] = "COMPLETE"
    receiving["received_at_utc"] = "2026-10-03T12:00:00-07:00"
    for row in receiving["items"]:
        row["qty_received"] = row["expected_qty"]
        row["package_sku_observed"] = row["expected_sku"]
        row["substitution_observed"] = False
        row["visible_damage_observed"] = False
        if row["id"] == "LC-3135":
            row["hardware_units"] = [
                _unit("LC-PILOT-A", "PILOT_ACTIVE_CANDIDATE"),
                _unit("LC-SPARE-A", "SPARE_UNTOUCHED"),
            ]
        elif row["id"] == "ADC-HX711":
            row["hardware_units"] = [
                _unit("ADC-PILOT-A", "PILOT_ACTIVE_CANDIDATE"),
                _unit("ADC-SPARE-A", "SPARE_UNTOUCHED"),
            ]
        elif row["id"] == "MCU-ESP32S3":
            row["hardware_units"] = [
                _unit("MCU-PILOT-A", "PILOT_ACTIVE_CANDIDATE"),
            ]
    return receiving


def test_complete_receiving_reconciles_order_without_qualifying_hardware(tmp_path: Path):
    checkout_path, authority_path, checkout, authority = _ordered_checkout(tmp_path)
    receiving_path = tmp_path / "receiving.json"
    receiving = init_receiving(
        receiving_path,
        checkout_path,
        authority_path,
        "RECEIVE-A",
    )
    _complete_receiving(receiving)

    report = validate_receiving(receiving, checkout, authority)
    assert report["valid"] is True
    assert report["receiving_complete"] is True
    assert report["issue4_materials_accounted_for"] is True
    assert report["physical_qualification_authority"] is False
    assert report["fabrication_authority"] is False
    assert report["powered_operation_authorized"] is False
    assert set(report["tracked_hardware_item_ids_ready"]) == {
        "LC-3135",
        "ADC-HX711",
        "MCU-ESP32S3",
    }


def test_receiving_initializer_binds_exact_checkout_fingerprint(tmp_path: Path):
    checkout_path, authority_path, checkout, authority = _ordered_checkout(tmp_path)
    receiving = init_receiving(
        tmp_path / "receiving.json",
        checkout_path,
        authority_path,
        "RECEIVE-A",
    )
    assert (
        receiving["checkout_authority_fingerprint_sha256"]
        == authority["authority_fingerprint_sha256"]
    )
    assert receiving["checkout_id"] == checkout["checkout_id"]


def test_partial_backorder_can_be_valid_but_is_not_complete(tmp_path: Path):
    checkout_path, authority_path, checkout, authority = _ordered_checkout(tmp_path)
    receiving = init_receiving(
        tmp_path / "receiving.json",
        checkout_path,
        authority_path,
        "RECEIVE-PARTIAL",
    )
    receiving["status"] = "PARTIAL"
    receiving["received_at_utc"] = "2026-10-03T12:00:00-07:00"

    for row in receiving["items"]:
        if row["id"] == "LC-3135":
            row["qty_received"] = 1
            row["package_sku_observed"] = row["expected_sku"]
            row["hardware_units"] = [
                _unit("LC-PILOT-A", "PILOT_ACTIVE_CANDIDATE")
            ]
            row["missing_or_backorder_note"] = "One unit backordered."
        else:
            row["qty_received"] = row["expected_qty"]
            row["package_sku_observed"] = row["expected_sku"]
            if row["id"] == "ADC-HX711":
                row["hardware_units"] = [
                    _unit("ADC-PILOT-A", "PILOT_ACTIVE_CANDIDATE"),
                    _unit("ADC-SPARE-A", "SPARE_UNTOUCHED"),
                ]
            elif row["id"] == "MCU-ESP32S3":
                row["hardware_units"] = [
                    _unit("MCU-PILOT-A", "PILOT_ACTIVE_CANDIDATE")
                ]

    report = validate_receiving(receiving, checkout, authority)
    assert report["valid"] is True
    assert report["receiving_complete"] is False
    assert report["issue4_materials_accounted_for"] is False
    assert report["incomplete_item_ids"] == ["LC-3135"]


def test_exact_source_substitution_is_rejected(tmp_path: Path):
    checkout_path, authority_path, checkout, authority = _ordered_checkout(tmp_path)
    receiving = init_receiving(
        tmp_path / "receiving.json",
        checkout_path,
        authority_path,
        "RECEIVE-SUB",
    )
    _complete_receiving(receiving)
    row = next(x for x in receiving["items"] if x["id"] == "ADC-HX711")
    row["package_sku_observed"] = "NOT-SEN-13879"
    row["substitution_observed"] = True

    report = validate_receiving(receiving, checkout, authority)
    assert report["valid"] is False
    assert any("observed package SKU does not match" in error for error in report["errors"])
    assert any("cannot be substituted" in error for error in report["errors"])


def test_damaged_complete_shipment_is_rejected(tmp_path: Path):
    checkout_path, authority_path, checkout, authority = _ordered_checkout(tmp_path)
    receiving = init_receiving(
        tmp_path / "receiving.json",
        checkout_path,
        authority_path,
        "RECEIVE-DAMAGE",
    )
    _complete_receiving(receiving)
    row = next(x for x in receiving["items"] if x["id"] == "LC-3135")
    row["visible_damage_observed"] = True

    report = validate_receiving(receiving, checkout, authority)
    assert report["valid"] is False
    assert any("damaged shipment cannot be COMPLETE" in error for error in report["errors"])


def test_required_active_and_untouched_spare_roles_are_enforced(tmp_path: Path):
    checkout_path, authority_path, checkout, authority = _ordered_checkout(tmp_path)
    receiving = init_receiving(
        tmp_path / "receiving.json",
        checkout_path,
        authority_path,
        "RECEIVE-ROLES",
    )
    _complete_receiving(receiving)
    cell = next(x for x in receiving["items"] if x["id"] == "LC-3135")
    cell["hardware_units"][1]["role"] = "PILOT_ACTIVE_CANDIDATE"

    report = validate_receiving(receiving, checkout, authority)
    assert report["valid"] is False
    assert any("must assign roles" in error for error in report["errors"])


def test_checkout_fingerprint_mismatch_is_rejected(tmp_path: Path):
    checkout_path, authority_path, checkout, authority = _ordered_checkout(tmp_path)
    receiving = init_receiving(
        tmp_path / "receiving.json",
        checkout_path,
        authority_path,
        "RECEIVE-FP",
    )
    _complete_receiving(receiving)
    receiving["checkout_authority_fingerprint_sha256"] = "0" * 64

    report = validate_receiving(receiving, checkout, authority)
    assert report["valid"] is False
    assert "receiving record does not link exact checkout authority" in report["errors"]
