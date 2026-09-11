from fit.profile_schema import RiderProfile
from fit.stance_optimizer import recommend


def test_optimizer_refuses_to_infer_from_shoe_size():
    p=RiderProfile.from_dict({
        "height_mm": 1575,
        "mass_kg": 50,
        "left_foot": {"shoe_size_label":"A"},
        "right_foot": {"shoe_size_label":"B"},
    })
    r=recommend(p)
    assert r.status == "measurement_gated"
    assert r.left["foot_length_mm"] is None
    assert r.right["foot_length_mm"] is None


def test_measured_stance_is_clamped_to_rig_envelope():
    p=RiderProfile.from_dict({
        "height_mm": 1575,
        "mass_kg": 50,
        "stance_width_mm": 900,
        "left_foot": {"length_mm":220,"width_mm":85,"natural_yaw_deg":-10},
        "right_foot": {"length_mm":225,"width_mm":87,"natural_yaw_deg":10},
    })
    r=recommend(p)
    assert r.stance_width_mm == 560.0
