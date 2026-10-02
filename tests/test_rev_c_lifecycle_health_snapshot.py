import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _snapshot():
    return json.loads(
        (
            ROOT / "hardware/rev_c_lifecycle_health_snapshot_2026-10-01.json"
        ).read_text()
    )


def test_health_states_never_create_operation_authority():
    data = _snapshot()
    assert data["authority"] == "REFERENCE_ONLY"
    assert data["powered_operation_authorized"] is False
    assert data["public_operation_authorized"] is False
    assert data["dog_accompanied_operation_authorized"] is False
    assert all(
        state["authorization_effect"] == "NONE"
        for state in data["health_states"]
    )


def test_ready_state_is_bounded_to_independently_allowed_activity():
    boundaries = _snapshot()["hard_boundaries"]
    assert "health state never authorizes powered operation" in boundaries
    assert "health state never authorizes public operation" in boundaries
    assert "health state never authorizes dog-accompanied operation" in boundaries
    assert (
        "READY_FOR_ALLOWED_ACTIVITY means ready only for an activity independently permitted elsewhere"
        in boundaries
    )


def test_service_intervals_must_be_sourced_not_invented():
    policy = _snapshot()["service_interval_policy"]
    assert policy["project_default_fixed_intervals"] is False
    assert "Do not invent mileage" in policy["rule"]
    assert policy["accepted_sources"] == [
        "selected_component_manufacturer",
        "selected_system_integrator_or_battery_builder",
        "qualified_x1_physical_evidence",
    ]


def test_critical_retention_and_brake_triggers_escalate_to_stop():
    rules = {
        item["trigger"]: item["minimum_severity"]
        for item in _snapshot()["automatic_event_escalations"]
    }
    assert rules["critical_witness_mark_movement"] == "STOP"
    assert rules["wheel_retention_change_or_new_axial_play"] == "STOP"
    assert rules["new_structural_crack_or_permanent_deformation"] == "STOP"
    assert rules["brake_unavailable_or_materially_degraded"] == "STOP"
    assert rules["steering_binding_or_uncommanded_interference"] == "STOP"


def test_core_preflight_covers_mechanical_environmental_and_harness_health():
    checks = set(_snapshot()["required_preflight_checks"])
    assert "tire_pressure_and_visible_condition" in checks
    assert "mechanical_brake_function" in checks
    assert "critical_witness_marks" in checks
    assert "guard_skid_retention_and_clearance" in checks
    assert "drainage_and_contamination_paths" in checks
    assert "harness_hose_and_connector_condition" in checks
