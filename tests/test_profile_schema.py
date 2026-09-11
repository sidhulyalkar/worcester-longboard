from fit.profile_schema import RiderProfile


def test_independent_feet_and_system_mass():
    p=RiderProfile.from_dict({
        "mass_kg": 50,
        "height_mm": 1575,
        "board_mass_kg": 20,
        "left_foot": {"shoe_size_label":"example-left"},
        "right_foot": {"shoe_size_label":"example-right"},
    })
    assert p.system_mass_kg == 70
    assert p.left_foot.shoe_size_label != p.right_foot.shoe_size_label
    assert not p.validate()
    assert "left_foot.length_mm" in p.measurement_gaps()


def test_bad_cant_is_rejected():
    p=RiderProfile.from_dict({"left_foot":{"cant_deg":12}})
    assert any("cant_deg" in e for e in p.validate())
