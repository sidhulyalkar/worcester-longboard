from fit.landmarks import analyze


def test_landmark_asymmetry_metrics_keep_sign():
    lm={
        "left_ankle":(-80,0,0), "right_ankle":(90,0,5),
        "left_knee":(-70,0,400), "right_knee":(85,0,410),
        "left_hip":(-60,0,800), "right_hip":(70,0,815),
        "left_shoulder":(-120,0,1250), "right_shoulder":(145,0,1270),
    }
    out=analyze(lm)
    assert out["hip_height_delta_mm"] == 15
    assert out["shoulder_height_delta_mm"] == 20
    assert out["pelvis_width_mm"] > 0
    assert out["shoulder_width_mm"] > out["pelvis_width_mm"]
