import math

from simulation.front_drive_traction import analyze, analyze_scenario


def _config():
    return {
        "schema_version": 1,
        "scope": "front_drive_traction_sensitivity",
        "total_mass_kg": 70.0,
        "wheelbase_m": 0.94,
        "cg_from_rear_m": 0.47,
        "cg_height_m": 0.70,
        "rolling_resistance_coeff": 0.03,
        "scenarios": [
            {"name": "level", "grade": 0.0, "acceleration_mps2": 0.0, "compare_mu": [0.3, 0.6]},
        ],
    }


def test_level_static_load_is_centered_for_centered_cg():
    cfg = _config()
    cfg["rolling_resistance_coeff"] = 0.0
    result = analyze_scenario(cfg, cfg["scenarios"][0])
    assert math.isclose(result["front_load_fraction"], 0.5, abs_tol=1e-12)
    assert math.isclose(result["rear_load_fraction"], 0.5, abs_tol=1e-12)


def test_forward_acceleration_unloads_front_axle():
    cfg = _config()
    base = analyze_scenario(cfg, {"name": "base", "grade": 0.0, "acceleration_mps2": 0.0, "compare_mu": []})
    accel = analyze_scenario(cfg, {"name": "accel", "grade": 0.0, "acceleration_mps2": 1.5, "compare_mu": []})
    assert accel["front_load_fraction"] < base["front_load_fraction"]
    assert accel["required_mu"]["front_drive"] > accel["required_mu"]["rear_drive"]


def test_uphill_grade_unloads_front_and_increases_required_mu():
    cfg = _config()
    flat = analyze_scenario(cfg, {"name": "flat", "grade": 0.0, "acceleration_mps2": 0.5, "compare_mu": []})
    hill = analyze_scenario(cfg, {"name": "hill", "grade": 0.25, "acceleration_mps2": 0.5, "compare_mu": []})
    assert hill["front_load_fraction"] < flat["front_load_fraction"]
    assert hill["required_mu"]["front_drive"] > flat["required_mu"]["front_drive"]


def test_awd_required_mu_is_lower_than_two_wheel_axles_when_contacts_positive():
    cfg = _config()
    result = analyze_scenario(cfg, {"name": "hill", "grade": 0.15, "acceleration_mps2": 0.5, "compare_mu": []})
    assert result["required_mu"]["awd"] < result["required_mu"]["front_drive"]
    assert result["required_mu"]["awd"] < result["required_mu"]["rear_drive"]


def test_invalid_cg_position_fails_closed():
    cfg = _config()
    cfg["cg_from_rear_m"] = 1.1
    report = analyze(cfg)
    assert report["valid"] is False
    assert report["physical_authority"] is False


def test_model_never_claims_physical_authority():
    report = analyze(_config())
    assert report["valid"] is True
    assert report["physical_authority"] is False
