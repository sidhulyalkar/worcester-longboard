import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _snapshot():
    return json.loads(
        (
            ROOT / "hardware/rev_c_powertrain_reference_snapshot_2026-10-01.json"
        ).read_text()
    )


def test_g1_reference_keeps_64t_axle_and_mount_facts_without_selecting_g1():
    data = _snapshot()
    g1 = data["mbs_g1"]
    assert g1["selected_for_x1"] is False
    assert g1["wheel_gear_teeth"] == 64
    assert "70 mm axles" in g1["compatible_truck_requirement"]
    assert "44 mm diagonal" in g1["motor_mount_pattern"]
    assert g1["motors_sold_separately"] is True
    assert g1["motor_gears_sold_separately"] is True


def test_agent_reference_preserves_unknown_motor_controller_values():
    agent = _snapshot()["mbs_agent_reference"]
    assert agent["selected_for_x1"] is False
    assert agent["stock_motor_gear_teeth"] == 15
    assert agent["stock_wheel_gear_teeth"] == 64
    assert agent["alternate_official_motor_gears_teeth"] == [13, 17]
    assert agent["maximum_pack_voltage_v"] == 75.6
    assert agent["motor_kv_rpm_per_v"].startswith("NOT_PUBLISHED")
    assert agent["motor_pole_pairs"].startswith("NOT_PUBLISHED")
    assert agent["motor_current_limit_a"].startswith("NOT_PUBLISHED")
    assert agent["controller_erpm_limit"].startswith("NOT_PUBLISHED")


def test_vesc_reference_keeps_motor_and_battery_current_distinct():
    boundary = _snapshot()["vesc_modeling_boundary"]
    assert boundary["motor_current_and_battery_current_are_distinct"] is True
    assert (
        boundary["low_speed_high_motor_current_can_coexist_with_lower_battery_current"]
        is True
    )
    assert boundary["erpm_equals_mechanical_rpm_times_pole_pairs"] is True
    assert boundary["hardware_erpm_limit_varies_by_controller"] is True


def test_reference_snapshot_never_grants_powertrain_authority():
    authority = _snapshot()["output_authority"]
    assert authority == {
        "physical_authority": False,
        "procurement_authority": False,
        "controller_configuration_authority": False,
        "battery_configuration_authority": False,
        "thermal_qualification": False,
        "powered_operation_authorized": False,
    }
