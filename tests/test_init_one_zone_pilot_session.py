import argparse
import hashlib
import json

import pytest

from tools.init_one_zone_pilot_session import build_manifest


def _digest(data):
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _selection_and_authority():
    selection = {
        "schema_version": 1,
        "scope": "x1_fit_pilot_hardware_selection_record",
        "issue": 59,
        "selection_id": "PILOT-HW-TEST",
        "selected_at_utc": "2026-10-03T12:30:00-07:00",
        "checkout_id": "CART-A-TEST",
        "checkout_authority_fingerprint_sha256": "a" * 64,
        "inventory_record_sha256": "b" * 64,
        "receiving_id": "RECEIVE-TEST",
        "receiving_authority_fingerprint_sha256": "c" * 64,
        "hardware": {
            "load_cell": {
                "item_id": "LC-3135",
                "source_kind": "RECEIVED_ORDER",
                "active_hardware_id": "LC-PILOT-A",
                "spare_hardware_id": "LC-SPARE-A",
            },
            "hx711": {
                "item_id": "ADC-HX711",
                "source_kind": "RECEIVED_ORDER",
                "active_hardware_id": "ADC-PILOT-A",
                "spare_hardware_id": "ADC-SPARE-A",
            },
            "mcu": {
                "item_id": "MCU-ESP32S3",
                "source_kind": "RECEIVED_ORDER",
                "active_hardware_id": "MCU-PILOT-A",
            },
        },
        "notes": "",
        "physical_qualification_authority": False,
        "four_zone_duplication_authorized": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
    }
    authority = {
        "schema_version": 1,
        "authority": "x1_fit_pilot_hardware_selection",
        "valid": True,
        "errors": [],
        "selection_id": selection["selection_id"],
        "selection_record_sha256": _digest(selection),
        "checkout_id": selection["checkout_id"],
        "checkout_authority_fingerprint_sha256": selection[
            "checkout_authority_fingerprint_sha256"
        ],
        "inventory_record_sha256": selection["inventory_record_sha256"],
        "receiving_id": selection["receiving_id"],
        "receiving_authority_fingerprint_sha256": selection[
            "receiving_authority_fingerprint_sha256"
        ],
        "hardware": selection["hardware"],
        "exact_evidence_hardware_verified": True,
        "untouched_spares_preserved": True,
        "physical_qualification_authority": False,
        "four_zone_duplication_authorized": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": "synthetic selection authority",
    }
    authority["authority_fingerprint_sha256"] = _digest(authority)
    return selection, authority


def _args():
    return argparse.Namespace(
        pod_id="POD-A",
        zone_pad_id="PAD-A",
        channel="left_heel",
        sps=10,
        calibration_mass_kg=[5.013, 1.997, 10.021],
        validation_mass_kg=7.486,
    )


def test_initializer_manifest_starts_safely_unqualified():
    selection, authority = _selection_and_authority()
    m = build_manifest(_args(), selection, authority)
    assert m["hardware_ids"]["load_cell_id"] == "LC-PILOT-A"
    assert m["hardware_ids"]["hx711_id"] == "ADC-PILOT-A"
    assert m["hardware_ids"]["mcu_id"] == "MCU-PILOT-A"
    assert m["spare_hardware_ids"]["load_cell_id"] == "LC-SPARE-A"
    assert m["spare_hardware_ids"]["hx711_id"] == "ADC-SPARE-A"
    assert m["hardware_selection"]["selection_id"] == "PILOT-HW-TEST"
    assert m["hx711_sps"] == 10
    assert m["acquisition"]["rate_jumper_verified"] is False
    assert m["mechanical"]["vendor_pattern_verified"] is False
    assert m["mechanical"]["stop_gap_unloaded_mm"] is None


def test_initializer_uses_actual_sorted_mass_sequence():
    selection, authority = _selection_and_authority()
    m = build_manifest(_args(), selection, authority)
    kinds = [row["kind"] for row in m["observations"]]
    assert kinds == [
        "zero_pre",
        "load_up",
        "load_up",
        "load_up",
        "load_down",
        "load_down",
        "zero_post",
    ]
    ups = [row["mass_kg"] for row in m["observations"] if row["kind"] == "load_up"]
    downs = [row["mass_kg"] for row in m["observations"] if row["kind"] == "load_down"]
    assert ups == [1.997, 5.013, 10.021]
    assert downs == [5.013, 1.997]
    assert m["validation"][0]["mass_kg"] == 7.486
    assert m["validation"][0]["log"] == "raw/validation_7p486kg.csv"


def test_initializer_requires_three_unique_masses():
    selection, authority = _selection_and_authority()
    args = _args()
    args.calibration_mass_kg = [2.0, 5.0]
    with pytest.raises(ValueError, match="at least three"):
        build_manifest(args, selection, authority)
    args.calibration_mass_kg = [2.0, 5.0, 5.0]
    with pytest.raises(ValueError, match="unique"):
        build_manifest(args, selection, authority)


def test_initializer_rejects_nonindependent_or_oversize_validation():
    selection, authority = _selection_and_authority()
    args = _args()
    args.validation_mass_kg = 5.013
    with pytest.raises(ValueError, match="independent"):
        build_manifest(args, selection, authority)
    args = _args()
    args.validation_mass_kg = 20.1
    with pytest.raises(ValueError, match="hard 20 kg"):
        build_manifest(args, selection, authority)


def test_initializer_rejects_tampered_hardware_selection_authority():
    selection, authority = _selection_and_authority()
    authority["hardware"]["load_cell"]["active_hardware_id"] = "LC-OTHER"
    with pytest.raises(ValueError, match="fingerprint is invalid"):
        build_manifest(_args(), selection, authority)


def test_initializer_rejects_selection_without_untouched_spares():
    selection, authority = _selection_and_authority()
    unsigned = dict(authority)
    unsigned.pop("authority_fingerprint_sha256")
    unsigned["untouched_spares_preserved"] = False
    unsigned["authority_fingerprint_sha256"] = _digest(unsigned)
    with pytest.raises(ValueError, match="preserve untouched spares"):
        build_manifest(_args(), selection, unsigned)
