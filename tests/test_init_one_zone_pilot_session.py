import argparse
import hashlib
import json

import pytest

from tools.init_one_zone_pilot_session import build_manifest
from tools.validate_x1_fit_pilot_mass_reference import validate as validate_mass


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


def _mass_item(mass_id, role, mass, uncertainty):
    return {
        "mass_id": mass_id,
        "role": role,
        "evidence_type": "REFERENCE_MASS",
        "declared_mass_kg": mass,
        "declared_uncertainty_kg": uncertainty,
        "reference_mass_evidence": {
            "source_reference": f"synthetic-{mass_id}",
            "documented_mass_kg": mass,
            "documented_uncertainty_kg": uncertainty,
        },
        "independent_scale_evidence": {
            "scale_manufacturer": "",
            "scale_model": "",
            "capacity_kg": None,
            "resolution_kg": None,
            "stated_accuracy_source": "",
            "conservative_accuracy_limit_kg": None,
            "zero_check_before": True,
            "zero_check_after": True,
            "repeated_readings_kg": [],
            "measurement_notes": "",
        },
        "notes": "",
    }


def _mass_record_and_authority():
    record = {
        "schema_version": 1,
        "scope": "x1_fit_pilot_mass_reference_record",
        "issue": 61,
        "reference_set_id": "MASS-REF-TEST",
        "measured_at_utc": "2026-10-03T12:45:00-07:00",
        "purpose": "Issue #4 synthetic test",
        "screening_policy": {
            "max_mass_kg": 20.0,
            "min_calibration_mass_count": 3,
            "validation_mass_count": 1,
            "max_relative_reference_uncertainty": 0.005,
            "uncertainty_policy_note": "synthetic",
        },
        "masses": [
            _mass_item("CAL-1P997", "CALIBRATION", 1.997, 0.002),
            _mass_item("CAL-5P013", "CALIBRATION", 5.013, 0.005),
            _mass_item("CAL-10P021", "CALIBRATION", 10.021, 0.010),
            _mass_item("VAL-7P486", "VALIDATION", 7.486, 0.007),
        ],
        "claims": {
            "nist_traceable": False,
            "legal_metrology": False,
            "commercial_measurement_authority": False,
            "load_cell_performance_authority": False,
            "four_zone_duplication_authorized": False,
            "fabrication_authority": False,
            "powered_operation_authorized": False,
            "public_operation_authorized": False,
            "dog_accompanied_operation_authorized": False,
        },
    }
    authority = validate_mass(record)
    assert authority["valid"] is True
    return record, authority


def _args():
    return argparse.Namespace(
        pod_id="POD-A",
        zone_pad_id="PAD-A",
        channel="left_heel",
        sps=10,
    )


def _build():
    selection, authority = _selection_and_authority()
    mass_record, mass_authority = _mass_record_and_authority()
    return build_manifest(
        _args(),
        selection,
        authority,
        mass_record,
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
    assert len(m["mass_reference"]["authority_fingerprint_sha256"]) == 64
    assert m["hx711_sps"] == 10
    assert m["acquisition"]["rate_jumper_verified"] is False
    assert m["mechanical"]["vendor_pattern_verified"] is False
    assert m["mechanical"]["stop_gap_unloaded_mm"] is None


def test_initializer_uses_authority_sorted_mass_sequence_and_uncertainty():
    m = _build()
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
    ups = [row for row in m["observations"] if row["kind"] == "load_up"]
    downs = [row for row in m["observations"] if row["kind"] == "load_down"]
    assert [row["mass_kg"] for row in ups] == [1.997, 5.013, 10.021]
    assert [row["mass_reference_id"] for row in ups] == [
        "CAL-1P997",
        "CAL-5P013",
        "CAL-10P021",
    ]
    assert [row["mass_uncertainty_kg"] for row in ups] == [0.002, 0.005, 0.01]
    assert [row["mass_kg"] for row in downs] == [5.013, 1.997]
    assert m["validation"][0]["mass_kg"] == 7.486
    assert m["validation"][0]["mass_reference_id"] == "VAL-7P486"
    assert m["validation"][0]["mass_uncertainty_kg"] == 0.007
    assert m["validation"][0]["log"] == "raw/validation_7p486kg.csv"


def test_initializer_rejects_tampered_hardware_selection_authority():
    selection, authority = _selection_and_authority()
    mass_record, mass_authority = _mass_record_and_authority()
    authority["hardware"]["load_cell"]["active_hardware_id"] = "LC-OTHER"
    with pytest.raises(ValueError, match="fingerprint is invalid"):
        build_manifest(
            _args(),
            selection,
            authority,
            mass_record,
            mass_authority,
        )


def test_initializer_rejects_selection_without_untouched_spares():
    selection, authority = _selection_and_authority()
    mass_record, mass_authority = _mass_record_and_authority()
    unsigned = dict(authority)
    unsigned.pop("authority_fingerprint_sha256")
    unsigned["untouched_spares_preserved"] = False
    unsigned["authority_fingerprint_sha256"] = _digest(unsigned)
    with pytest.raises(ValueError, match="preserve untouched spares"):
        build_manifest(
            _args(),
            selection,
            unsigned,
            mass_record,
            mass_authority,
        )


def test_initializer_rejects_tampered_mass_reference_authority():
    selection, authority = _selection_and_authority()
    mass_record, mass_authority = _mass_record_and_authority()
    mass_authority["calibration_masses"][0]["mass_kg"] = 2.5
    with pytest.raises(ValueError, match="mass reference authority fingerprint is invalid"):
        build_manifest(
            _args(),
            selection,
            authority,
            mass_record,
            mass_authority,
        )


def test_initializer_rejects_mass_authority_not_matching_record():
    selection, authority = _selection_and_authority()
    mass_record, mass_authority = _mass_record_and_authority()
    mass_record["masses"][0]["declared_mass_kg"] = 2.1
    with pytest.raises(ValueError, match="does not match mass record"):
        build_manifest(
            _args(),
            selection,
            authority,
            mass_record,
            mass_authority,
        )
