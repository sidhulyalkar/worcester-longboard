from fit.pressure_analysis import summarize_trials


def test_repeatable_asymmetric_loading_is_preserved():
    rows=[
        {"left_heel":15,"left_forefoot":25,"right_heel":25,"right_forefoot":35},
        {"left_heel":16,"left_forefoot":24,"right_heel":24,"right_forefoot":36},
        {"left_heel":14,"left_forefoot":26,"right_heel":26,"right_forefoot":34},
    ]
    s=summarize_trials(rows)
    assert abs(s.left_fraction-0.4) < 1e-9
    assert abs(s.right_fraction-0.6) < 1e-9
    assert s.repeatability_ok
