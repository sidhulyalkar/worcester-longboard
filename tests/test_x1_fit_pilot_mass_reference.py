import copy

import pytest

from tools.validate_x1_fit_pilot_mass_reference import validate


def _reference_item(mass_id, role, mass, uncertainty):
    return {
        "mass_id": mass_id,
        "role": role,
        "evidence_type": "REFERENCE_MASS",
        "declared_mass_kg": mass,
        "declared_uncertainty_kg": uncertainty,
        "reference_mass_evidence": {
            "source_reference": f"reference-document-{mass_id}",
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


def _record():
    return {
        "schema_version": 1,
        "scope": "x1_fit_pilot_mass_reference_record",
        "issue": 61,
        "reference_set_id": "MASS-REF-TEST",
        "measured_at_utc": "2026-10-02T18:00:00-07:00",
        "purpose": "Issue #4 one-zone fit-pilot calibration and independent validation masses",
        "screening_policy": {
            "max_mass_kg": 20.0,
            "min_calibration_mass_count": 3,
            "validation_mass_count": 1,
            "max_relative_reference_uncertainty": 0.005,
            "uncertainty_policy_note": "synthetic test",
        },
        "masses": [
            _reference_item("CAL-2", "CALIBRATION", 2.0, 0.002),
            _reference_item("CAL-5", "CALIBRATION", 5.0, 0.005),
            _reference_item("CAL-10", "CALIBRATION", 10.0, 0.010),
            _reference_item("VAL-7P5", "VALIDATION", 7.5, 0.0075),
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


def test_documented_reference_mass_set_qualifies_without_metrology_claims():
    report = validate(_record())
    assert report["valid"] is True
    assert report["errors"] == []
    assert report["authority"] == "x1_fit_pilot_mass_reference"
    assert len(report["calibration_masses"]) == 3
    assert len(report["validation_masses"]) == 1
    assert report["nist_traceable"] is False
    assert report["legal_metrology"] is False
    assert report["load_cell_performance_authority"] is False
    assert report["four_zone_duplication_authorized"] is False
    assert report["powered_operation_authorized"] is False
    assert len(report["authority_fingerprint_sha256"]) == 64


def test_independent_scale_path_uses_conservative_uncertainty_floor():
    record = _record()
    item = record["masses"][1]
    item["evidence_type"] = "INDEPENDENT_SCALE"
    item["reference_mass_evidence"] = {
        "source_reference": "",
        "documented_mass_kg": None,
        "documented_uncertainty_kg": None,
    }
    item["declared_mass_kg"] = 5.000333333333333
    item["declared_uncertainty_kg"] = 0.006
    item["independent_scale_evidence"] = {
        "scale_manufacturer": "SyntheticScale",
        "scale_model": "S-10",
        "capacity_kg": 10.0,
        "resolution_kg": 0.001,
        "stated_accuracy_source": "manufacturer manual",
        "conservative_accuracy_limit_kg": 0.005,
        "zero_check_before": True,
        "zero_check_after": True,
        "repeated_readings_kg": [5.000, 5.001, 5.000],
        "measurement_notes": "synthetic",
    }

    report = validate(record)
    assert report["valid"] is True
    mass = next(x for x in report["calibration_masses"] if x["mass_id"] == "CAL-5")
    assert mass["evidence_type"] == "INDEPENDENT_SCALE"
    assert mass["evidence_summary"]["reading_count"] == 3
    assert mass["evidence_summary"]["repeatability_half_range_kg"] == pytest.approx(0.0005)
    assert mass["evidence_summary"]["uncertainty_floor_kg"] == pytest.approx(0.006)


def test_nominal_label_without_reference_evidence_is_not_authority():
    record = _record()
    item = record["masses"][0]
    item["reference_mass_evidence"]["source_reference"] = ""
    item["reference_mass_evidence"]["documented_uncertainty_kg"] = None

    report = validate(record)
    assert report["valid"] is False
    assert any("requires source_reference" in error for error in report["errors"])
    assert any("documented_uncertainty_kg" in error for error in report["errors"])


def test_declared_uncertainty_cannot_be_smaller_than_scale_floor():
    record = _record()
    item = record["masses"][0]
    item["evidence_type"] = "INDEPENDENT_SCALE"
    item["reference_mass_evidence"] = {
        "source_reference": "",
        "documented_mass_kg": None,
        "documented_uncertainty_kg": None,
    }
    item["declared_mass_kg"] = 2.0
    item["declared_uncertainty_kg"] = 0.002
    item["independent_scale_evidence"] = {
        "scale_manufacturer": "SyntheticScale",
        "scale_model": "S-10",
        "capacity_kg": 10.0,
        "resolution_kg": 0.001,
        "stated_accuracy_source": "manufacturer manual",
        "conservative_accuracy_limit_kg": 0.003,
        "zero_check_before": True,
        "zero_check_after": True,
        "repeated_readings_kg": [1.999, 2.001, 2.000],
        "measurement_notes": "",
    }

    report = validate(record)
    assert report["valid"] is False
    assert any(
        "smaller than conservative scale uncertainty floor" in error
        for error in report["errors"]
    )


def test_reference_uncertainty_must_not_dominate_issue4_validation_gate():
    record = _record()
    record["masses"][0]["declared_uncertainty_kg"] = 0.02
    record["masses"][0]["reference_mass_evidence"][
        "documented_uncertainty_kg"
    ] = 0.02

    report = validate(record)
    assert report["valid"] is False
    assert any(
        "relative reference uncertainty exceeds 0.500%" in error
        for error in report["errors"]
    )


def test_validation_mass_must_be_independent_and_mass_ids_unique():
    record = _record()
    record["masses"][-1]["declared_mass_kg"] = 5.0
    record["masses"][-1]["reference_mass_evidence"]["documented_mass_kg"] = 5.0
    record["masses"][-1]["mass_id"] = "CAL-5"

    report = validate(record)
    assert report["valid"] is False
    assert any("duplicate mass_id" in error for error in report["errors"])
    assert "validation mass must be independent of calibration masses" in report["errors"]


def test_claims_cannot_be_promoted_by_mass_record():
    record = _record()
    record["claims"]["nist_traceable"] = True
    record["claims"]["four_zone_duplication_authorized"] = True

    report = validate(record)
    assert report["valid"] is False
    assert "claims.nist_traceable must be false" in report["errors"]
    assert "claims.four_zone_duplication_authorized must be false" in report["errors"]
