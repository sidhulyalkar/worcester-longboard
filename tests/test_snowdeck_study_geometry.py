from cad.snowdeck_study_geometry import DEFAULT


def test_snowdeck_study_is_fail_closed():
    report = DEFAULT.authority_report()

    assert DEFAULT.validate() == []
    assert report["fabrication_authority"] is False
    assert report["ride_authority"] is False
    assert report["powered_operation_authorized"] is False
    assert report["structural_deck_interface_verified"] is False
    assert report["rider_retention_verified"] is False
    assert report["ride_load_path_verified"] is False


def test_snowdeck_reuses_fit_rig_plate_coordinate_envelope():
    from cad.fit_rig_geometry import DEFAULT as FIT_RIG

    assert DEFAULT.plate_length_mm == FIT_RIG.footplate_length_mm
    assert DEFAULT.plate_width_mm == FIT_RIG.footplate_width_mm
    assert DEFAULT.plate_thickness_mm == FIT_RIG.footplate_thickness_mm


def test_study_angles_stay_inside_visual_bounds():
    assert max(DEFAULT.cant_study_angles_deg) <= DEFAULT.viewer_cant_max_deg
    assert DEFAULT.viewer_stance_min_mm < DEFAULT.viewer_stance_max_mm
