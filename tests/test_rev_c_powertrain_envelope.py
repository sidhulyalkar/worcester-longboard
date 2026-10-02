import copy
import math

from simulation.rev_c_powertrain_envelope import analyze, sweep_pinions


def _config(topology="rear"):
    return {
        "schema_version": 1,
        "scope": "rev_c_powertrain_envelope",
        "vehicle": {
            "total_mass_kg": 80.0,
            "wheelbase_m": 0.94,
            "cg_from_rear_m": 0.47,
            "cg_height_m": 0.35,
            "wheel_diameter_m": 0.20,
            "rolling_resistance_coeff": 0.03,
            "aero_drag_area_m2": 0.0,
            "air_density_kg_m3": 1.225,
        },
        "candidate": {
            "id": "SYNTHETIC-2WD",
            "topology": topology,
            "motor_count": 2,
            "motor_kv_rpm_per_v": 120.0,
            "motor_pole_pairs": 7,
            "wheel_gear_teeth": 64,
            "motor_gear_teeth": 15,
            "nominal_voltage_v": 50.4,
            "full_voltage_v": 58.8,
            "speed_voltage_basis": "nominal",
            "phase_current_limit_a_per_motor": 80.0,
            "battery_current_limit_a_total": 60.0,
            "electrical_power_limit_w_total": 3000.0,
            "erpm_limit": 100000.0,
            "drivetrain_efficiency": 0.90,
            "electrical_efficiency": 0.92,
        },
        "scenarios": [
            {
                "name": "flat_cruise",
                "grade": 0.0,
                "target_speed_mps": 5.0,
                "acceleration_mps2": 0.2,
                "assumed_mu": 0.7,
            },
            {
                "name": "trail_climb",
                "grade": 0.20,
                "target_speed_mps": 4.0,
                "acceleration_mps2": 0.2,
                "assumed_mu": 0.7,
            },
        ],
        "physical_authority": False,
        "procurement_authority": False,
        "controller_configuration_authority": False,
        "battery_configuration_authority": False,
        "powered_operation_authorized": False,
    }


def _scenario(report, name):
    return next(x for x in report["scenarios"] if x["name"] == name)


def test_steeper_grade_raises_required_phase_and_battery_current():
    report = analyze(_config())
    assert report["valid"] is True

    flat = _scenario(report, "flat_cruise")
    climb = _scenario(report, "trail_climb")

    assert (
        climb["drivetrain"]["ideal_phase_current_a_per_motor"]
        > flat["drivetrain"]["ideal_phase_current_a_per_motor"]
    )
    assert (
        climb["power"]["estimated_battery_current_a_at_nominal_voltage"]
        > flat["power"]["estimated_battery_current_a_at_nominal_voltage"]
    )
    assert (
        climb["force_components_n"]["grade"]
        > flat["force_components_n"]["grade"]
    )


def test_smaller_pinion_reduces_phase_current_but_raises_erpm_and_lowers_no_load_speed():
    config = _config()
    sweep = sweep_pinions(config, [13, 15, 17])
    assert sweep["valid"] is True
    rows = {row["motor_gear_teeth"]: row for row in sweep["pinion_results"]}

    r13 = _scenario(
        {"scenarios": rows[13]["scenario_results"]},
        "trail_climb",
    )
    r17 = _scenario(
        {"scenarios": rows[17]["scenario_results"]},
        "trail_climb",
    )

    assert rows[13]["ratio_wheel_over_motor"] > rows[17]["ratio_wheel_over_motor"]
    assert (
        r13["drivetrain"]["ideal_phase_current_a_per_motor"]
        < r17["drivetrain"]["ideal_phase_current_a_per_motor"]
    )
    assert r13["speed_electrical"]["erpm"] > r17["speed_electrical"]["erpm"]
    assert (
        r13["speed_electrical"]["no_load_speed_nominal_mps"]
        < r17["speed_electrical"]["no_load_speed_nominal_mps"]
    )

    # Same wheel force/speed and declared efficiencies means the first-order
    # battery-power estimate is ratio-independent even though phase current is not.
    assert math.isclose(
        r13["power"]["estimated_battery_input_power_w"],
        r17["power"]["estimated_battery_input_power_w"],
        rel_tol=0,
        abs_tol=1e-9,
    )


def test_front_drive_loses_uphill_traction_margin_relative_to_rear_drive():
    rear = _config("rear")
    front = _config("front")
    for config in (rear, front):
        config["scenarios"] = [
            {
                "name": "uphill_accel",
                "grade": 0.20,
                "target_speed_mps": 3.0,
                "acceleration_mps2": 0.5,
                "assumed_mu": 0.55,
            }
        ]

    rear_result = analyze(rear)["scenarios"][0]
    front_result = analyze(front)["scenarios"][0]

    assert (
        front_result["normal_loads_n"]["driven"]
        < rear_result["normal_loads_n"]["driven"]
    )
    assert (
        front_result["traction"]["required_mu"]
        > rear_result["traction"]["required_mu"]
    )
    assert rear_result["checks"]["traction"]["passed"] is True
    assert front_result["checks"]["traction"]["passed"] is False


def test_battery_current_is_not_equated_to_phase_current():
    report = analyze(_config())
    climb = _scenario(report, "trail_climb")

    phase = climb["drivetrain"]["ideal_phase_current_a_per_motor"]
    battery = climb["power"]["estimated_battery_current_a_at_nominal_voltage"]

    assert phase > battery
    assert not math.isclose(phase, battery, rel_tol=0, abs_tol=1e-6)


def test_declared_erpm_limit_rejects_candidate_without_inventing_thermal_result():
    config = _config()
    config["candidate"]["erpm_limit"] = 20000.0
    config["scenarios"] = [
        {
            "name": "fast",
            "grade": 0.0,
            "target_speed_mps": 8.0,
            "acceleration_mps2": 0.0,
            "assumed_mu": 0.8,
        }
    ]

    report = analyze(config)
    result = report["scenarios"][0]

    assert report["valid"] is True
    assert result["checks"]["erpm"]["passed"] is False
    assert "erpm" in result["rejection_reasons"]
    assert result["thermal_qualification"] is False
    assert report["thermal_qualification"] is False


def test_geometric_no_load_speed_can_reject_impossible_target():
    config = _config()
    config["candidate"]["motor_kv_rpm_per_v"] = 40.0
    config["scenarios"] = [
        {
            "name": "too_fast",
            "grade": 0.0,
            "target_speed_mps": 8.0,
            "acceleration_mps2": 0.0,
            "assumed_mu": 0.8,
        }
    ]

    report = analyze(config)
    result = report["scenarios"][0]
    assert result["checks"]["geometric_speed"]["passed"] is False
    assert "geometric_speed" in result["rejection_reasons"]


def test_battery_power_and_current_limits_are_independent_rejection_reasons():
    config = _config()
    config["candidate"]["battery_current_limit_a_total"] = 10.0
    config["candidate"]["electrical_power_limit_w_total"] = 400.0

    report = analyze(config)
    climb = _scenario(report, "trail_climb")
    assert climb["checks"]["battery_current"]["passed"] is False
    assert climb["checks"]["electrical_power"]["passed"] is False
    assert "battery_current" in climb["rejection_reasons"]
    assert "electrical_power" in climb["rejection_reasons"]


def test_invalid_motor_or_controller_limits_fail_validation():
    for field, value in (
        ("motor_kv_rpm_per_v", None),
        ("phase_current_limit_a_per_motor", 0),
        ("battery_current_limit_a_total", -1),
        ("erpm_limit", 0),
    ):
        config = _config()
        config["candidate"][field] = value
        report = analyze(config)
        assert report["valid"] is False
        assert any(field in error for error in report["errors"])


def test_analysis_never_creates_hardware_or_operation_authority():
    report = analyze(_config())
    assert report["valid"] is True
    assert report["physical_authority"] is False
    assert report["procurement_authority"] is False
    assert report["controller_configuration_authority"] is False
    assert report["battery_configuration_authority"] is False
    assert report["thermal_qualification"] is False
    assert report["powered_operation_authorized"] is False

    for scenario in report["scenarios"]:
        assert scenario["physical_authority"] is False
        assert scenario["procurement_authority"] is False
        assert scenario["controller_configuration_authority"] is False
        assert scenario["battery_configuration_authority"] is False
        assert scenario["thermal_qualification"] is False
        assert scenario["powered_operation_authorized"] is False
