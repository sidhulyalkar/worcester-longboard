import hashlib
import json
from pathlib import Path

import pytest

from tools.init_x1_cart_a_checkout import initialize as init_checkout
from tools.init_x1_cart_a_receiving import initialize as init_receiving
from tools.init_x1_fit_pilot_hardware_selection import initialize as init_selection
from tools.validate_x1_cart_a_checkout import validate as validate_checkout
from tools.validate_x1_cart_a_receiving import validate as validate_receiving
from tools.validate_x1_fit_pilot_hardware_selection import validate as validate_selection

ROOT = Path(__file__).resolve().parents[1]


def _inventory(*, owned_sensors=False):
    data = json.loads(
        (ROOT / "hardware/x1_physical_kickoff_inventory_template.json").read_text()
    )
    data["inventory_checked_at_utc"] = "2026-10-02T12:00:00-07:00"
    for row in data["items"]:
        row["status"] = "NEED_BUY"
        if owned_sensors and row["id"] in {"LC-3135", "ADC-HX711"}:
            row["status"] = "OWNED_EXACT_UNUSED"
            row["qty_owned_verified"] = 2
            row["exact_part_match"] = True
            row["unused_or_known_history"] = True
            row["notes"] = "Two exact unused units physically verified."
    return data


def _prepare_checkout(tmp_path: Path, *, owned_sensors=False, ordered=True):
    inventory = _inventory(owned_sensors=owned_sensors)
    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    checkout_path = tmp_path / "checkout.json"
    checkout = init_checkout(checkout_path, inventory_path, "CART-A-TEST")
    checkout["status"] = "ORDERED" if ordered else "READY_TO_ORDER"
    checkout["checkout_at_utc"] = "2026-10-02T12:30:00-07:00"

    merchandise = 0.0
    for row in checkout["items"]:
        if row["resolution"] != "ORDER":
            continue
        row["stock_confirmed_at_checkout"] = True
        if row["source_snapshot_required"]:
            row["source_rechecked_at_checkout"] = True
        if row["unit_price_usd"] is None:
            row["unit_price_usd"] = 1.0
        merchandise += row["ordered_qty"] * float(row["unit_price_usd"])
        if ordered:
            row["order_confirmation_ref"] = f"private-{row['id']}"

    checkout["merchandise_total_usd"] = round(merchandise, 2)
    if ordered:
        checkout["shipping_usd"] = 5.0
        checkout["tax_usd"] = 4.0
        checkout["order_total_usd"] = round(merchandise + 9.0, 2)
    checkout_path.write_text(json.dumps(checkout, indent=2), encoding="utf-8")

    authority = validate_checkout(checkout, inventory)
    assert authority["valid"] is True
    authority_path = tmp_path / "checkout_authority.json"
    authority_path.write_text(json.dumps(authority, indent=2), encoding="utf-8")
    return inventory_path, checkout_path, authority_path, inventory, checkout, authority


def _unit(hardware_id, role):
    return {
        "hardware_id": hardware_id,
        "role": role,
        "exact_part_match": True,
        "visible_damage_observed": False,
        "packaging_and_markings_recorded": True,
        "condition_note": "Expected markings; no visible damage.",
    }


def _prepare_receiving(tmp_path: Path, checkout_path, authority_path, checkout, authority):
    receiving_path = tmp_path / "receiving.json"
    receiving = init_receiving(
        receiving_path,
        checkout_path,
        authority_path,
        "RECEIVE-TEST",
    )
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
                _unit("MCU-PILOT-A", "PILOT_ACTIVE_CANDIDATE")
            ]
    receiving_path.write_text(json.dumps(receiving, indent=2), encoding="utf-8")

    report = validate_receiving(receiving, checkout, authority)
    assert report["valid"] is True
    assert report["receiving_complete"] is True
    authority_out = tmp_path / "receiving_authority.json"
    authority_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return receiving_path, authority_out, receiving, report


def test_received_hardware_selection_binds_active_and_untouched_spares(tmp_path: Path):
    (
        inventory_path,
        checkout_path,
        checkout_authority_path,
        inventory,
        checkout,
        checkout_authority,
    ) = _prepare_checkout(tmp_path)
    receiving_path, receiving_authority_path, receiving, receiving_authority = (
        _prepare_receiving(
            tmp_path,
            checkout_path,
            checkout_authority_path,
            checkout,
            checkout_authority,
        )
    )

    selection_path = tmp_path / "selection.json"
    selection = init_selection(
        selection_path,
        inventory_path,
        checkout_path,
        checkout_authority_path,
        "PILOT-HW-A",
        "2026-10-03T12:30:00-07:00",
        receiving_path=receiving_path,
        receiving_authority_path=receiving_authority_path,
        mcu_id="MCU-PILOT-A",
    )
    report = validate_selection(
        selection,
        inventory,
        checkout,
        checkout_authority,
        receiving=receiving,
        receiving_authority=receiving_authority,
    )

    assert report["valid"] is True
    assert report["exact_evidence_hardware_verified"] is True
    assert report["untouched_spares_preserved"] is True
    assert report["hardware"]["load_cell"]["active_hardware_id"] == "LC-PILOT-A"
    assert report["hardware"]["load_cell"]["spare_hardware_id"] == "LC-SPARE-A"
    assert report["hardware"]["hx711"]["active_hardware_id"] == "ADC-PILOT-A"
    assert report["hardware"]["hx711"]["spare_hardware_id"] == "ADC-SPARE-A"
    assert report["physical_qualification_authority"] is False
    assert report["four_zone_duplication_authorized"] is False
    assert report["powered_operation_authorized"] is False
    assert len(report["authority_fingerprint_sha256"]) == 64


def test_exact_owned_sensor_path_can_select_stable_active_and_spare_ids(tmp_path: Path):
    (
        inventory_path,
        checkout_path,
        checkout_authority_path,
        inventory,
        checkout,
        checkout_authority,
    ) = _prepare_checkout(tmp_path, owned_sensors=True, ordered=False)

    selection_path = tmp_path / "selection.json"
    selection = init_selection(
        selection_path,
        inventory_path,
        checkout_path,
        checkout_authority_path,
        "PILOT-HW-OWNED",
        "2026-10-02T13:00:00-07:00",
        owned_load_cell_active_id="LC-OWNED-A",
        owned_load_cell_spare_id="LC-OWNED-SPARE",
        owned_hx711_active_id="ADC-OWNED-A",
        owned_hx711_spare_id="ADC-OWNED-SPARE",
    )
    report = validate_selection(
        selection,
        inventory,
        checkout,
        checkout_authority,
    )
    assert report["valid"] is True
    assert report["receiving_authority_fingerprint_sha256"] is None
    assert report["hardware"]["load_cell"]["source_kind"] == "OWNED_EXACT_UNUSED"
    assert report["hardware"]["hx711"]["source_kind"] == "OWNED_EXACT_UNUSED"


def test_received_selection_rejects_swapping_active_and_spare_roles(tmp_path: Path):
    (
        inventory_path,
        checkout_path,
        checkout_authority_path,
        inventory,
        checkout,
        checkout_authority,
    ) = _prepare_checkout(tmp_path)
    receiving_path, receiving_authority_path, receiving, receiving_authority = (
        _prepare_receiving(
            tmp_path,
            checkout_path,
            checkout_authority_path,
            checkout,
            checkout_authority,
        )
    )
    selection_path = tmp_path / "selection.json"
    selection = init_selection(
        selection_path,
        inventory_path,
        checkout_path,
        checkout_authority_path,
        "PILOT-HW-A",
        "2026-10-03T12:30:00-07:00",
        receiving_path=receiving_path,
        receiving_authority_path=receiving_authority_path,
    )
    selection["hardware"]["load_cell"]["active_hardware_id"] = "LC-SPARE-A"
    selection["hardware"]["load_cell"]["spare_hardware_id"] = "LC-PILOT-A"

    report = validate_selection(
        selection,
        inventory,
        checkout,
        checkout_authority,
        receiving=receiving,
        receiving_authority=receiving_authority,
    )
    assert report["valid"] is False
    assert any("active ID is not the received PILOT_ACTIVE_CANDIDATE" in x for x in report["errors"])
    assert any("spare ID is not the received SPARE_UNTOUCHED" in x for x in report["errors"])


def test_selection_rejects_duplicate_hardware_ids(tmp_path: Path):
    (
        inventory_path,
        checkout_path,
        checkout_authority_path,
        inventory,
        checkout,
        checkout_authority,
    ) = _prepare_checkout(tmp_path, owned_sensors=True, ordered=False)

    with pytest.raises(ValueError, match="globally unique"):
        init_selection(
            tmp_path / "selection.json",
            inventory_path,
            checkout_path,
            checkout_authority_path,
            "PILOT-HW-BAD",
            "2026-10-02T13:00:00-07:00",
            owned_load_cell_active_id="SAME-ID",
            owned_load_cell_spare_id="LC-SPARE",
            owned_hx711_active_id="SAME-ID",
            owned_hx711_spare_id="ADC-SPARE",
        )


def test_selection_rejects_tampered_receiving_authority(tmp_path: Path):
    (
        inventory_path,
        checkout_path,
        checkout_authority_path,
        inventory,
        checkout,
        checkout_authority,
    ) = _prepare_checkout(tmp_path)
    receiving_path, receiving_authority_path, receiving, receiving_authority = (
        _prepare_receiving(
            tmp_path,
            checkout_path,
            checkout_authority_path,
            checkout,
            checkout_authority,
        )
    )
    tampered = dict(receiving_authority)
    tampered["receiving_complete"] = False
    receiving_authority_path.write_text(json.dumps(tampered), encoding="utf-8")

    with pytest.raises(ValueError, match="fingerprint-invalid"):
        init_selection(
            tmp_path / "selection.json",
            inventory_path,
            checkout_path,
            checkout_authority_path,
            "PILOT-HW-TAMPER",
            "2026-10-03T12:30:00-07:00",
            receiving_path=receiving_path,
            receiving_authority_path=receiving_authority_path,
        )
