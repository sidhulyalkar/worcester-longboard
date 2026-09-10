from dataclasses import replace

from cad.fit_rig_geometry import DEFAULT, LoadCellEnvelope


def test_default_fit_rig_geometry_is_valid_but_sensor_mount_is_gated():
    assert DEFAULT.validate() == []
    assert DEFAULT.sensor_mount_fabrication_ready is False
    report = DEFAULT.authority_report()
    assert report["fixture_type"] == "unpowered_fit_rig_only"
    assert set(report["measurement_gates"]) == {
        "load_cell.fixed_hole_spacing_mm",
        "load_cell.load_hole_spacing_mm",
    }


def test_measured_sensor_hole_spacing_can_close_mount_gate_without_other_changes():
    measured = replace(
        DEFAULT,
        load_cell=LoadCellEnvelope(
            fixed_hole_spacing_mm=15.0,
            load_hole_spacing_mm=15.0,
        ),
    )
    assert measured.validate() == []
    assert measured.sensor_mount_fabrication_ready is True
    assert measured.authority_report()["measurement_gates"] == []


def test_overload_stop_gap_has_conservative_bounds():
    too_small = replace(DEFAULT, overload_stop_gap_mm=0.1)
    too_large = replace(DEFAULT, overload_stop_gap_mm=3.0)
    assert any("overload stop gap" in e for e in too_small.validate())
    assert any("overload stop gap" in e for e in too_large.validate())


def test_fixture_base_has_adjustment_clearance():
    too_short = replace(DEFAULT, base_length_mm=550.0)
    too_narrow = replace(DEFAULT, base_width_mm=190.0)
    assert any("too short" in e for e in too_short.validate())
    assert any("too narrow" in e for e in too_narrow.validate())
