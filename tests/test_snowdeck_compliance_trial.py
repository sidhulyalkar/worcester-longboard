from tools.summarize_snowdeck_compliance_trial import summarize


def _normal_cycle(scale=1.0):
    return {
        "loading": [
            {"displacement_mm": 0.0, "force_n": 0.0},
            {"displacement_mm": 1.0, "force_n": 20.0 * scale},
            {"displacement_mm": 2.0, "force_n": 40.0 * scale},
        ],
        "unloading": [
            {"displacement_mm": 2.0, "force_n": 36.0 * scale},
            {"displacement_mm": 1.0, "force_n": 16.0 * scale},
            {"displacement_mm": 0.0, "force_n": 0.0},
        ],
        "zero_return_mm": 0.1,
        "settling_time_s": 0.4,
    }


def _torsion_cycle(scale=1.0):
    return {
        "loading": [
            {"angle_deg": 0.0, "moment_nm": 0.0},
            {"angle_deg": 2.0, "moment_nm": 1.0 * scale},
            {"angle_deg": 4.0, "moment_nm": 2.0 * scale},
        ],
        "unloading": [
            {"angle_deg": 4.0, "moment_nm": 1.8 * scale},
            {"angle_deg": 2.0, "moment_nm": 0.8 * scale},
            {"angle_deg": 0.0, "moment_nm": 0.0},
        ],
        "zero_return_deg": 0.2,
        "settling_time_s": 0.5,
    }


def _trial():
    return {
        "scope": "x1_snowdeck_compliance_bench_trial",
        "condition_id": "C1",
        "synthetic_fixture": False,
        "normal_cycles": [_normal_cycle(), _normal_cycle(1.05)],
        "torsion_cycles": [_torsion_cycle(), _torsion_cycle(1.05)],
        "observations": {
            "unexpected_rocking_observed": False,
            "insert_migration_observed": False,
            "fastener_migration_observed": False,
            "visible_damage_observed": False,
            "persistent_deformation_observed": False,
        },
        "physical_authority": False,
        "fabrication_authority": False,
        "ride_authority": False,
        "powered_operation_authorized": False,
    }


def test_compliance_signature_is_descriptive_and_non_authoritative():
    report = summarize(_trial(), "a" * 64)

    assert report["normal_cycle_count"] == 2
    assert report["torsion_cycle_count"] == 2
    assert report["normal_response"]["stiffness_loading_n_per_mm"]["mean"] > 0
    assert report["normal_response"]["hysteresis_loop_mj"]["mean"] > 0
    assert report["torsion_response"]["stiffness_loading_nm_per_rad"]["mean"] > 0
    assert report["torsion_response"]["hysteresis_loop_j"]["mean"] > 0
    assert report["eligible_for_further_bench_study"] is True
    assert report["physical_authority"] is False
    assert report["fabrication_authority"] is False
    assert report["ride_authority"] is False
    assert report["powered_operation_authorized"] is False


def test_compliance_mechanical_reject_stays_separate_from_response():
    trial = _trial()
    trial["observations"]["insert_migration_observed"] = True

    report = summarize(trial)

    assert report["eligible_for_further_bench_study"] is False
    assert "insert migration" in report["mechanical_rejects"]
    assert "normal_response" in report
    assert "torsion_response" in report


def test_compliance_refuses_authority_promotion():
    trial = _trial()
    trial["ride_authority"] = True

    try:
        summarize(trial)
    except ValueError as exc:
        assert "ride_authority must remain false" in str(exc)
    else:
        raise AssertionError("ride authority must be rejected")
