from tools.analyze_brake_repeat_stops import analyze


def _series():
    return {
        "schema_version": 1,
        "scope": "unpowered_repeated_stop_thermal_series",
        "plan_frozen_before_data": True,
        "powered_test": False,
        "test_plan": {
            "target_start_speed_mps": 3.0,
            "start_speed_tolerance_mps": 0.15,
            "baseline_stop_count": 2,
            "minimum_stop_count": 5,
            "max_deceleration_loss_fraction": 0.20,
            "max_rotor_peak_temp_c": 90.0,
        },
        "stops": [
            {"start_speed_mps": 3.0, "stop_distance_m": 2.0, "ambient_temp_c": 20.0, "rotor_temp_start_c": 20.0, "rotor_temp_peak_c": 30.0},
            {"start_speed_mps": 3.0, "stop_distance_m": 2.1, "ambient_temp_c": 20.0, "rotor_temp_start_c": 25.0, "rotor_temp_peak_c": 38.0},
            {"start_speed_mps": 3.0, "stop_distance_m": 2.2, "ambient_temp_c": 20.0, "rotor_temp_start_c": 31.0, "rotor_temp_peak_c": 48.0},
            {"start_speed_mps": 3.0, "stop_distance_m": 2.25, "ambient_temp_c": 20.0, "rotor_temp_start_c": 38.0, "rotor_temp_peak_c": 58.0},
            {"start_speed_mps": 3.0, "stop_distance_m": 2.3, "ambient_temp_c": 20.0, "rotor_temp_start_c": 46.0, "rotor_temp_peak_c": 68.0},
        ],
    }


def test_clean_predeclared_series_passes_analysis_only():
    report = analyze(_series())
    assert report["valid"] is True
    assert report["analysis_passed"] is True
    assert report["physical_authority"] is False
    assert report["checks"]["deceleration_retention_passed"] is True
    assert report["checks"]["rotor_peak_temperature_passed"] is True


def test_thresholds_must_be_frozen_before_data():
    data = _series()
    data["plan_frozen_before_data"] = False
    report = analyze(data)
    assert report["valid"] is False


def test_deceleration_fade_can_fail_without_invalidating_schema():
    data = _series()
    data["stops"][-1]["stop_distance_m"] = 3.2
    report = analyze(data)
    assert report["valid"] is True
    assert report["analysis_passed"] is False
    assert report["checks"]["deceleration_retention_passed"] is False


def test_rotor_temperature_limit_can_fail():
    data = _series()
    data["stops"][-1]["rotor_temp_peak_c"] = 105.0
    report = analyze(data)
    assert report["valid"] is True
    assert report["analysis_passed"] is False
    assert report["checks"]["rotor_peak_temperature_passed"] is False


def test_speed_outside_predeclared_tolerance_is_invalid_evidence():
    data = _series()
    data["stops"][3]["start_speed_mps"] = 3.5
    report = analyze(data)
    assert report["valid"] is False


def test_peak_temperature_cannot_be_below_start_temperature():
    data = _series()
    data["stops"][2]["rotor_temp_peak_c"] = 25.0
    data["stops"][2]["rotor_temp_start_c"] = 30.0
    report = analyze(data)
    assert report["valid"] is False


def test_powered_test_is_outside_this_analyzer_scope():
    data = _series()
    data["powered_test"] = True
    report = analyze(data)
    assert report["valid"] is False
