import json
from pathlib import Path

from cad.rolling_chassis_geometry import (
    BRAKE_FIRST,
    DRIVE_CLEARANCE,
    BRAKE_HANGER_70MM_TOPOLOGY_STUDY,
)
from tools.validate_mechanical_architecture import validate

ROOT = Path(__file__).resolve().parents[1]


def _load(path):
    return json.loads((ROOT / path).read_text())


def test_comp95_reference_geometry_is_internally_consistent():
    assert BRAKE_FIRST.wheel.diameter_mm == 194.0
    assert BRAKE_FIRST.wheel.width_mm == 51.0
    assert BRAKE_FIRST.wheelbase_mm == 940.0
    assert BRAKE_FIRST.deck_length_mm == 950.0
    assert BRAKE_FIRST.deck_max_width_mm == 251.0
    assert BRAKE_FIRST.derived_overall_length_mm == 1134.0
    assert abs(BRAKE_FIRST.derived_overall_length_mm - BRAKE_FIRST.published_overall_length_mm) <= 20.0
    assert BRAKE_FIRST.wheel_center_lateral_mm == 175.0
    assert BRAKE_FIRST.estimated_outer_wheel_envelope_width_mm == 401.0
    assert BRAKE_FIRST.validate() == []
    assert BRAKE_FIRST.vendor_envelopes_verified is False
    assert BRAKE_FIRST.fabrication_ready is False


def test_drive_and_topology_study_references_do_not_fake_brake_compatibility():
    assert DRIVE_CLEARANCE.truck.total_width_mm == 420.0
    assert DRIVE_CLEARANCE.truck.drive_reference_compatible is True
    assert DRIVE_CLEARANCE.truck.brake_reference_compatible is False
    assert BRAKE_HANGER_70MM_TOPOLOGY_STUDY.truck.total_width_mm == 440.0
    assert BRAKE_HANGER_70MM_TOPOLOGY_STUDY.truck.drive_reference_compatible is True
    assert BRAKE_HANGER_70MM_TOPOLOGY_STUDY.truck.brake_reference_compatible is False


def test_mechanical_architecture_registry_validates():
    errors = validate(
        _load("hardware/mechanical_reference_benchmarks_2026-09-11.json"),
        _load("hardware/mechanical_risk_register.json"),
        _load("hardware/build_authority.json"),
        _load("hardware/planned_system_bom.json"),
    )
    assert errors == []


def test_high_severity_risks_have_physical_verification_and_release_gate():
    register = _load("hardware/mechanical_risk_register.json")
    high = [risk for risk in register["risks"] if risk["severity"] == 5]
    assert high
    for risk in high:
        assert risk["verification"]
        assert risk["must_close_before"]
        assert risk["status"] != "CLOSED"
