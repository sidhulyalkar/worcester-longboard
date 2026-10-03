import copy
import json
from pathlib import Path

from tools.validate_x1_fit_pilot_mass_reference import validate


def _record():
    return {
        "schema_version": 1,
        "scope": "x1_fit_pilot_mass_reference_record",
        "issue": 61,
        "reference_set_id": "MASS-REF-A",
        "measured_at_utc": "2026-10-03T13:00:00-07:00",
        "method": "INDEPENDENT_SCALE_MANUFACTURER_SPEC",
        "uncertainty_policy": {
            "max_relative_uncertainty_fraction": 0.005,
            "rationale": "synthetic test fixture",
        },
        "instrument": {
            "manufacturer": "Synthetic",
            "model": "BenchScale-A",
            "private_identifier": "",
            "capacity_kg": 20.0,
            "resolution_kg": 0.001,
            "stated_accuracy_abs_kg": 0.005,
            "accuracy_source_reference": "manufacturer-spec-fixture",
            "calibration_certificate_reference": "",
            "certificate_expanded_uncertainty_kg": None,
            "zero_checks_kg": [0.0, 0.001, 0.0],
        },
        "masses": [
            {
                "mass_id": "M2",
                "role": "CALIBRATION",
                "object_description": "synthetic 2 kg object",
                "nominal_label_kg": 2.0,
                "repeat_measurements_kg": [2.000, 2.001, 1.999, 2.000, 2.000],
                "accepted_mass_kg": 2.0,
                "declared_expanded_uncertainty_kg": 0.005,
                "source_reference": "scale-session-a",
            },
            {
                "mass_id": "M5",
                "role": "CALIBRATION",
                "object_description": "synthetic 5 kg object",
                "nominal_label_kg": 5.0,
                "repeat_measurements_kg": [5.000, 5.001, 4.999, 5.000, 5.000],
                "accepted_mass_kg": 5.0,
                "declared_expanded_uncertainty_kg": 0.005,
                "source_reference": "scale-session-a",
            },
            {
                "mass_id": "M10",
                "role": "CALIBRATION",
                "object_description": "synthetic 10 kg object",
                "nominal_label_kg": 10.0,
                "repeat_measurements_kg": [10.000, 10.001, 9.999, 10.000, 10.000],
                "accepted_mass_kg": 10.0,
                "declared_expanded_uncertainty_kg": 0.005,
                "source_reference": "scale-session-a",
            },
            {
                "mass_id": "M7P5",
                "role": "VALIDATION",
                "object_description": "synthetic independent 7.5 kg object",
                "nominal_label_kg": 7.5,
                "repeat_measurements_kg": [7.500, 7.501, 7.499, 7.500, 7.500],
                "accepted_mass_kg": 7.5,
                "declared_expanded_uncertainty_kg": 0.005,
                "source_reference": "scale-session-a",
            },
        ],
        "nist_traceability_claimed": False,
        "commercial_legal_metrology_claimed": False,
        "physical_sensor_qualification_authority": False,
        "four_zone_duplication_authorized": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
    }


def test_independent_scale_reference_can_qualify_without_traceability_claim():
    report = validate(_record())
    assert report["valid"] is True
    assert report["authority"] == "x1_fit_pilot_mass_reference"
    assert report["calibration_masses_kg"] == [2.0, 5.0, 10.0]
    assert report["validation_mass_kg"] == 7.5
    assert report["max_relative_uncertainty_fraction"] == 0.0025
    assert report["nist_traceability_claimed"] is False
    assert report["commercial_legal_metrology_claimed"] is False
    assert report["physical_sensor_qualification_authority"] is False
    assert report["four_zone_duplication_authorized"] is False
    assert report["powered_operation_authorized"] is False
    assert len(report["authority_fingerprint_sha256"]) == 64


def test_nominal_labels_without_repeat_measurements_are_not_mass_authority():
    data = _record()
    data["masses"][0]["repeat_measurements_kg"] = []
    report = validate(data)
    assert report["valid"] is False
    assert any("requires at least five repeat measurements" in e for e in report["errors"])


def test_declared_uncertainty_cannot_be_smaller_than_scale_accuracy():
    data = _record()
    data["masses"][0]["declared_expanded_uncertainty_kg"] = 0.001
    report = validate(data)
    assert report["valid"] is False
    assert any("below conservative floor" in e for e in report["errors"])


def test_reference_uncertainty_above_half_percent_is_rejected():
    data = _record()
    data["instrument"]["stated_accuracy_abs_kg"] = 0.02
    data["masses"][0]["declared_expanded_uncertainty_kg"] = 0.02
    report = validate(data)
    assert report["valid"] is False
    assert any("relative uncertainty" in e for e in report["errors"])


def test_validation_mass_must_be_distinct():
    data = _record()
    data["masses"][-1]["accepted_mass_kg"] = 5.0
    data["masses"][-1]["repeat_measurements_kg"] = [5.0] * 5
    report = validate(data)
    assert report["valid"] is False
    assert any("all accepted mass values must be unique" in e for e in report["errors"])
    assert any("validation mass must be independent" in e for e in report["errors"])


def test_traceability_or_legal_metrology_claims_are_forbidden():
    data = _record()
    data["nist_traceability_claimed"] = True
    data["commercial_legal_metrology_claimed"] = True
    report = validate(data)
    assert report["valid"] is False
    assert "nist_traceability_claimed must be false" in report["errors"]
    assert "commercial_legal_metrology_claimed must be false" in report["errors"]


def test_calibrated_reference_path_requires_certificate_uncertainty_and_reference():
    data = _record()
    data["method"] = "CALIBRATED_REFERENCE_MASSES"
    data["instrument"]["stated_accuracy_abs_kg"] = None
    data["instrument"]["accuracy_source_reference"] = ""
    data["instrument"]["certificate_expanded_uncertainty_kg"] = 0.001
    data["instrument"]["calibration_certificate_reference"] = "private-cert-ref"
    for row in data["masses"]:
        row["repeat_measurements_kg"] = []
        row["declared_expanded_uncertainty_kg"] = 0.001
    report = validate(data)
    assert report["valid"] is True

    broken = copy.deepcopy(data)
    broken["instrument"]["calibration_certificate_reference"] = ""
    report = validate(broken)
    assert report["valid"] is False
    assert any("calibration_certificate_reference" in e for e in report["errors"])
