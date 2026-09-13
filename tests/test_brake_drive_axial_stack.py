from tools.analyze_brake_drive_axial_stack import analyze, interval_gap


def _config():
    return {
        "schema_version": 1,
        "scope": "brake_drive_axial_stack_analysis",
        "datum": "rear hanger outer face, outward positive",
        "components": [
            {"id": "pad_window", "start_mm": 18.0, "end_mm": 24.0},
            {"id": "rotor", "start_mm": 20.0, "end_mm": 22.0},
            {"id": "drive_coupler", "start_mm": 30.0, "end_mm": 42.0},
            {"id": "brake_arm_sweep", "start_mm": 10.0, "end_mm": 26.0},
        ],
        "containment_rules": [
            {"child": "rotor", "container": "pad_window", "minimum_edge_margin_mm": 1.0},
        ],
        "separation_rules": [
            {"a": "rotor", "b": "drive_coupler", "minimum_gap_mm": 5.0},
            {"a": "brake_arm_sweep", "b": "drive_coupler", "minimum_gap_mm": 2.0},
        ],
    }


def test_gap_returns_positive_separation_and_negative_overlap():
    assert interval_gap((0.0, 5.0), (8.0, 10.0)) == 3.0
    assert interval_gap((0.0, 5.0), (4.0, 10.0)) == -1.0
    assert interval_gap((0.0, 5.0), (5.0, 10.0)) == 0.0


def test_clean_stack_passes_analysis_only():
    report = analyze(_config())
    assert report["valid"] is True
    assert report["analysis_passed"] is True
    assert report["physical_authority"] is False


def test_rotor_outside_pad_window_fails_rule():
    cfg = _config()
    for component in cfg["components"]:
        if component["id"] == "rotor":
            component["start_mm"] = 23.5
            component["end_mm"] = 25.5
    report = analyze(cfg)
    assert report["valid"] is True
    assert report["analysis_passed"] is False
    assert report["containment_results"][0]["passed"] is False


def test_drive_overlap_is_reported_with_depth():
    cfg = _config()
    for component in cfg["components"]:
        if component["id"] == "drive_coupler":
            component["start_mm"] = 21.0
            component["end_mm"] = 35.0
    report = analyze(cfg)
    assert report["analysis_passed"] is False
    rotor_rule = report["separation_results"][0]
    assert rotor_rule["overlap_depth_mm"] == 1.0


def test_unknown_component_reference_fails_config():
    cfg = _config()
    cfg["separation_rules"].append({"a": "rotor", "b": "ghost", "minimum_gap_mm": 1.0})
    report = analyze(cfg)
    assert report["valid"] is False


def test_no_rules_is_invalid_not_an_implicit_pass():
    cfg = _config()
    cfg["containment_rules"] = []
    cfg["separation_rules"] = []
    report = analyze(cfg)
    assert report["valid"] is False
    assert report["analysis_passed"] is False
