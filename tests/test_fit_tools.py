from fit.static_load import summarize

def test_static_load_summary():
    rows=[
      {"left_heel":"20","left_forefoot":"20","right_heel":"30","right_forefoot":"30"},
      {"left_heel":"22","left_forefoot":"18","right_heel":"28","right_forefoot":"32"},
    ]
    out=summarize(rows)
    assert abs(out["left_load_fraction"]-0.4)<1e-9
    assert abs(out["right_load_fraction"]-0.6)<1e-9
