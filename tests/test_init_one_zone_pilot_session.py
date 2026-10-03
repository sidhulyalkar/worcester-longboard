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
        "checkout_authority_fingerprint_sha256": selection["checkout_authority_fingerprint_sha256"],
        "inventory_record_sha256": selection["inventory_record_sha256"],
        "receiving_id": selection["receiving_id"],
        "receiving_authority_fingerprint_sha256": selection["receiving_authority_fingerprint_sha256"],
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


def _mass_reference_and_authority():
    record = {
        "schema_version": 1,
        "scope": "x1_fit_pilot_mass_reference_record",
        "issue": 61,
        "reference_set_id": "MASS-REF-TEST",
        "measured_at_utc": "2026-10-03T13:00:00-07:00",
        "method": "INDEPENDENT_SCALE_MANUFACTURER_SPEC",
        "uncertainty_policy": {
            "max_relative_uncertainty_fraction": 0.005,
            "rationale": "synthetic",
        },
        "instrument": {},
        "masses": [],
        "nist_traceability_claimed": False,
        "commercial_legal_metrology_claimed": False,
        "physical_sensor_qualification_authority": False,
        "four_zone_duplication_authorized": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
    }
    summaries = [
        {
            "mass_id": "M1P997",
            "role": "CALIBRATION",
            "accepted_mass_kg": 1.997,
            "declared_expanded_uncertainty_kg": 0.005,
            "relative_uncertainty_fraction": 0.005 / 1.997,
        },
        {
            "mass_id": "M5P013",
            "role": "CALIBRATION",
            "accepted_mass_kg": 5.013,
            "declared_expanded_uncertainty_kg": 0.005,
            "relative_uncertainty_fraction": 0.005 / 5.013,
        },
        {
            "mass_id": "M10P021",
            "role": "CALIBRATION",
            "accepted_mass_kg": 10.021,
            "declared_expanded_uncertainty_kg": 0.005,
            "relative_uncertainty_fraction": 0.005 / 10.021,
        },
        {
            "mass_id": "M7P486",
            "role": "VALIDATION",
            "accepted_mass_kg": 7.486,
            "declared_expanded_uncertainty_kg": 0.005,
            "relative_uncertainty_fraction": 0.005 / 7.486,
        },
    ]
    authority = {
        "schema_version": 1,
        "authority": "x1_fit_pilot_mass_reference",
        "scope": "issue4_mass_reference_only",
        "valid": True,
        "errors": [],
        "reference_set_id": record["reference_set_id"],
        "mass_reference_record_sha256": _digest(record),
        "method": record["method"],
        "calibration_masses_kg": [1.997, 5.013, 10.021],
        "validation_mass_kg": 7.486,
        "mass_summaries": summaries,
        "max_relative_uncertainty_fraction": max(x["relative_uncertainty_fraction"] for x in summaries),
        "nist_traceability_claimed": False,
        "commercial_legal_metrology_claimed": False,
        "physical_sensor_qualification_authority": False,
        "four_zone_duplication_authorized": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": "synthetic mass authority",
    }
    authority["authority_fingerprint_sha256"] = _digest(authority)
    return record, authority


def _args():
    return argparse.Namespace(
        pod_id="POD-A",
        zone_pad_id="PAD-A",
        channel="left_heel",
        sps=10,
    )


def _build():
    selection, selection_authority = _selection_and_authority()
    mass_ref, mass_authority = _mass_reference_and_authority()
    return build_manifest(
        _args(),
        selection,
        selection_authority,
        mass_ref,
        mass_authority,
    )


def test_initializer_manifest_starts_safely_unqualified():
    m = _build()
    assert m["hardware_ids"]["load_cell_id"] == "LC-PILOT-A"
    assert m["hardware_ids"]["hx711_id"] == "ADC-PILOT-A"
    assert m["hardware_ids"]["mcu_id"] == "MCU-PILOT-A"
    assert m["spare_hardware_ids"]["load_cell_id"] == "LC-SPARE-A"
    assert m["spare_hardware_ids"]["hx711_id"] == "ADC-SPARE-A"
    assert m["hardware_selection"]["selection_id"] == "PILOT-HW-TEST"
    assert m["mass_reference"]["reference_set_id"] == "MASS-REF-TEST"
    assert m["hx711_sps"] == 10
    assert m["acquisition"]["rate_jumper_verified"] is False
    assert m["mechanical"]["vendor_pattern_verified"] is False


def test_initializer_uses_authority_mass_sequence_and_uncertainty():
    m = _build()
    kinds = [row["kind"] for row in m["observations"]]
    assert kinds == [
        "zero_pre", "load_up", "load_up", "load_up",
        "load_down", "load_down", "zero_post",
    ]
    ups = [row for row in m["observations"] if row["kind"] == "load_up"]
    assert [row["mass_kg"] for row in ups] == [1.997, 5.013, 10.021]
    assert [row["mass_id"] for row in ups] == ["M1P997", "M5P013", "M10P021"]
    assert all(row["reference_uncertainty_kg"] == 0.005 for row in ups)
    assert m["validation"][0]["mass_kg"] == 7.486
    assert m["validation"][0]["mass_id"] == "M7P486"
    assert m["validation"][0]["reference_uncertainty_kg"] == 0.005


def test_initializer_rejects_tampered_hardware_selection_authority():
    selection, authority = _selection_and_authority()
    mass_ref, mass_authority = _mass_reference_and_authority()
    authority["hardware"]["load_cell"]["active_hardware_id"] = "LC-OTHER"
    with pytest.raises(ValueError, match="fingerprint is invalid"):
        build_manifest(_args(), selection, authority, mass_ref, mass_authority)


def test_initializer_rejects_tampered_mass_reference_authority():
    selection, authority = _selection_and_authority()
    mass_ref, mass_authority = _mass_reference_and_authority()
    mass_authority["validation_mass_kg"] = 8.0
    with pytest.raises(ValueError, match="mass reference authority fingerprint is invalid"):
        build_manifest(_args(), selection, authority, mass_ref, mass_authority)


def test_initializer_rejects_mass_reference_record_mismatch():
    selection, authority = _selection_and_authority()
    mass_ref, mass_authority = _mass_reference_and_authority()
    mass_ref["reference_set_id"] = "TAMPERED"
    with pytest.raises(ValueError, match="does not match mass reference record"):
        build_manifest(_args(), selection, authority, mass_ref, mass_authority)
