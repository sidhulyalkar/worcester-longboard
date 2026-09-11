from fit.fit_score import score_trials
from fit.profile_schema import RiderProfile
from fit.rev_b_gate import evaluate
from fit.trial_summary import summarize_neutral_trial


def rows(left_fraction=0.40, roll=0.10):
    total = 500.0
    left = total * left_fraction
    right = total - left
    return [
        {
            "t_s": i / 50.0,
            "left_heel_N": left * 0.45,
            "left_forefoot_N": left * 0.55,
            "right_heel_N": right * 0.50,
            "right_forefoot_N": right * 0.50,
            "roll_deg": roll + (0.02 if i % 2 else -0.02),
        }
        for i in range(100)
    ]


def complete_profile():
    return RiderProfile.from_dict({
        "schema_version": 2,
        "mass_kg": 50.0,
        "height_mm": 1575.0,
        "board_mass_kg": 20.0,
        "stance_width_mm": 390.0,
        "left_foot": {"length_mm": 220.0, "width_mm": 82.0, "natural_yaw_deg": 12.0},
        "right_foot": {"length_mm": 228.0, "width_mm": 86.0, "natural_yaw_deg": -10.0},
        "symmetric_trucks_default": True,
    })


def good_raw_quality():
    base = {
        "duration_s": 20.5,
        "monotonic_time": True,
        "complete_force_fraction": 1.0,
        "channel_valid_fraction": {
            "left_heel": 1.0,
            "left_forefoot": 1.0,
            "right_heel": 1.0,
            "right_forefoot": 1.0,
        },
        "imu_valid_fraction": 1.0,
        "warnings": [],
    }
    return [dict(base, trial_id=f"remount-{i}") for i in (1, 2, 3)]


def stable_trials():
    return [
        summarize_neutral_trial(rows(0.40, 0.10), stance_width_mm=390, left_yaw_deg=12, right_yaw_deg=-10),
        summarize_neutral_trial(rows(0.41, 0.08), stance_width_mm=391, left_yaw_deg=12.5, right_yaw_deg=-10),
        summarize_neutral_trial(rows(0.40, 0.12), stance_width_mm=389, left_yaw_deg=12, right_yaw_deg=-10.5),
    ]


def test_stable_asymmetric_session_can_pass_fit_gate_with_qualified_raw_logs():
    score = score_trials(stable_trials())
    gate = evaluate(complete_profile(), score, good_raw_quality())
    assert gate["ready_for_rev_b_fit_cad"] is True
    assert score["left_load_mean"] < 0.5


def test_missing_raw_quality_blocks_rev_b_even_when_fit_statistics_are_good():
    gate = evaluate(complete_profile(), score_trials(stable_trials()))
    assert gate["ready_for_rev_b_fit_cad"] is False
    assert any("raw quality reports" in blocker for blocker in gate["blockers"])


def test_force_channel_dropout_blocks_rev_b():
    quality = good_raw_quality()
    quality[1]["complete_force_fraction"] = 0.90
    quality[1]["channel_valid_fraction"] = dict(quality[1]["channel_valid_fraction"])
    quality[1]["channel_valid_fraction"]["right_forefoot"] = 0.90
    gate = evaluate(complete_profile(), score_trials(stable_trials()), quality)
    assert gate["ready_for_rev_b_fit_cad"] is False
    assert any("right_forefoot" in blocker for blocker in gate["blockers"])


def test_short_or_nonmonotonic_raw_trial_blocks_rev_b():
    quality = good_raw_quality()
    quality[0]["duration_s"] = 10.0
    quality[2]["monotonic_time"] = False
    gate = evaluate(complete_profile(), score_trials(stable_trials()), quality)
    assert gate["ready_for_rev_b_fit_cad"] is False
    assert any("duration" in blocker for blocker in gate["blockers"])
    assert any("monotonic" in blocker for blocker in gate["blockers"])


def test_missing_direct_foot_measurement_blocks_rev_b():
    profile = complete_profile()
    profile.left_foot.length_mm = None
    gate = evaluate(profile, score_trials(stable_trials()), good_raw_quality())
    assert gate["ready_for_rev_b_fit_cad"] is False
    assert "missing measurement: left_foot.length_mm" in gate["blockers"]


def test_large_neutral_roll_bias_blocks_rev_b():
    trials = [
        summarize_neutral_trial(rows(0.40, 1.5), stance_width_mm=390, left_yaw_deg=12, right_yaw_deg=-10),
        summarize_neutral_trial(rows(0.40, 1.4), stance_width_mm=390, left_yaw_deg=12, right_yaw_deg=-10),
        summarize_neutral_trial(rows(0.40, 1.6), stance_width_mm=390, left_yaw_deg=12, right_yaw_deg=-10),
    ]
    gate = evaluate(complete_profile(), score_trials(trials), good_raw_quality())
    assert gate["ready_for_rev_b_fit_cad"] is False
    assert any("roll" in blocker for blocker in gate["blockers"])
