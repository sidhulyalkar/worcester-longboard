from tools.qualify_rev_c_inert_pack_envelope import qualify


def _manifest():
    return {
        "schema_version": 1,
        "scope": "rev_c_pre_purchase_inert_pack_envelope",
        "chassis_candidate_id": "compact_matrix_reference",
        "available_mount_envelope_mm": {
            "length": 520,
            "width": 210,
            "height": 95,
        },
        "minimum_vulnerable_component_ground_keepout_mm": 25,
        "pack_candidates": {
            "trail": {
                "nominal_wh": 575,
                "envelope_mm": {"length": 360, "width": 170, "height": 70},
                "inert_target_mass_kg": 3.5,
                "placement": "top",
            },
            "range": {
                "nominal_wh": 1050,
                "envelope_mm": {"length": 500, "width": 205, "height": 90},
                "inert_target_mass_kg": 6.5,
                "placement": "top",
            },
        },
        "checks": {
            "rider_stance_keepout_clear": True,
            "steering_sweep_keepout_clear": True,
            "deck_flex_keepout_clear": True,
            "service_removal_direction_defined": True,
            "positive_retention_concept_defined": True,
            "sacrificial_skid_or_impact_path_defined": True,
            "no_live_battery_used": True,
        },
        "powered_operation_authorized": False,
    }


def test_valid_inert_envelope_qualifies_without_authorizing_power():
    report = qualify(_manifest())
    assert report["qualified"] is True
    assert report["authority"] == "x1_rev_c_inert_pack_envelope"
    assert report["range_pack_inert_envelope_plausible"] is True
    assert report["powered_operation_authorized"] is False


def test_range_pack_must_fit_declared_available_envelope():
    data = _manifest()
    data["pack_candidates"]["range"]["envelope_mm"]["length"] = 600
    report = qualify(data)
    assert report["qualified"] is False
    assert report["range_pack_inert_envelope_plausible"] is False
    assert any("range: pack envelope exceeds" in e for e in report["errors"])


def test_energy_classes_cannot_silently_drift():
    data = _manifest()
    data["pack_candidates"]["trail"]["nominal_wh"] = 900
    report = qualify(data)
    assert report["qualified"] is False
    assert any("trail: nominal_wh must remain" in e for e in report["errors"])


def test_live_battery_use_fails_closed():
    data = _manifest()
    data["checks"]["no_live_battery_used"] = False
    report = qualify(data)
    assert report["qualified"] is False
    assert any("no_live_battery_used" in e for e in report["errors"])


def test_missing_clearance_or_service_checks_fail_closed():
    data = _manifest()
    data["checks"]["steering_sweep_keepout_clear"] = False
    data["checks"]["service_removal_direction_defined"] = False
    report = qualify(data)
    assert report["qualified"] is False
    assert any("steering_sweep_keepout_clear" in e for e in report["errors"])
    assert any("service_removal_direction_defined" in e for e in report["errors"])
