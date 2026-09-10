from fit.pressure_calibration import from_known_mass, calibrate_sample, total_force_newtons
from fit.ruview_adapter import normalize_pose, COCO17
from fit.fit_score import score_trials
from fit.session_sync import synchronize


def test_load_cell_known_mass_calibration():
    cal = {name: from_known_mass(1000, 2000, 10.0) for name in (
        "left_heel", "left_forefoot", "right_heel", "right_forefoot")}
    sample = calibrate_sample({name: 1500 for name in cal}, cal)
    assert abs(total_force_newtons(sample) - 4 * 5.0 * 9.80665) < 1e-6


def test_ruview_normalization_preserves_17_keypoints_without_metric_claim():
    raw = [[float(i), float(i + 1), float(i + 2), 0.9] for i in range(17)]
    out = normalize_pose({"keypoints": raw})
    assert set(out["keypoints"]) == set(COCO17)
    assert out["missing_keypoints"] == []
    assert out["metric_geometry_authoritative"] is False


def test_fit_score_does_not_penalize_stable_asymmetric_loading():
    asymmetric = [
        {"left_load_fraction": 0.40, "deck_roll_mean_deg": 0.1, "deck_roll_rms_deg": 0.2,
         "stance_width_mm": 390, "left_yaw_deg": 12, "right_yaw_deg": -10},
        {"left_load_fraction": 0.40, "deck_roll_mean_deg": 0.1, "deck_roll_rms_deg": 0.2,
         "stance_width_mm": 390, "left_yaw_deg": 12, "right_yaw_deg": -10},
        {"left_load_fraction": 0.40, "deck_roll_mean_deg": 0.1, "deck_roll_rms_deg": 0.2,
         "stance_width_mm": 390, "left_yaw_deg": 12, "right_yaw_deg": -10},
    ]
    balanced = [dict(r, left_load_fraction=0.50) for r in asymmetric]
    assert score_trials(asymmetric)["score_lower_is_better"] == score_trials(balanced)["score_lower_is_better"]


def test_session_sync_rejects_large_timestamp_mismatch():
    ref = [{"t_s": 1.0}, {"t_s": 2.0}]
    imu = [{"t_s": 1.01, "roll": 0.1}, {"t_s": 2.2, "roll": 0.2}]
    out = synchronize(ref, {"imu": imu}, tolerance_s=0.05)
    assert len(out) == 1
    assert out[0]["reference"]["t_s"] == 1.0
