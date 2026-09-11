from dataclasses import replace

import pytest

from cad.fit_rig_geometry import DEFAULT, LoadCellEnvelope


def test_default_uses_vendor_pattern_but_stays_physical_verification_gated():
    assert DEFAULT.validate() == []
    assert DEFAULT.sensor_mount_pilot_ready is True
    assert DEFAULT.sensor_mount_fabrication_ready is False
    report = DEFAULT.authority_report()
    assert report["fixture_type"] == "unpowered_fit_rig_only"
    assert report["schema_version"] == 3
    assert report["sensor_mount_pilot_ready"] is True
    assert len(report["measurement_gates"]) == 3


def test_vendor_pattern_matches_current_40mm_two_hole_drawing():
    cell = DEFAULT.load_cell
    assert cell.fixed_hole_xy_mm == (-20.0, 0.0)
    assert cell.loaded_hole_xy_mm == (20.0, 0.0)
    assert cell.loaded_hole_xy_mm[0] - cell.fixed_hole_xy_mm[0] == 40.0
    assert cell.thread == "M5x0.8 THRU"


def test_physical_verification_closes_four_pod_gate():
    measured = DEFAULT.with_load_cell_verification({
        "fixed_hole_xy_mm": [-20.1, 0.1],
        "loaded_hole_xy_mm": [19.9, 0.1],
    })
    assert measured.validate() == []
    assert measured.sensor_mount_fabrication_ready is True
    assert measured.authority_report()["measurement_gates"] == []


def test_large_physical_disagreement_is_rejected_not_silently_accepted():
    with pytest.raises(ValueError, match="vendor pattern"):
        DEFAULT.with_load_cell_verification({
            "fixed_hole_xy_mm": [-18.0, 0.0],
            "loaded_hole_xy_mm": [20.0, 0.0],
        })


def test_wrong_vendor_pattern_fails_geometry_validation():
    wrong = replace(
        DEFAULT,
        load_cell=LoadCellEnvelope(
            fixed_hole_xy_mm=(20.0, 0.0),
            loaded_hole_xy_mm=(30.0, 0.0),
        ),
    )
    errors = wrong.validate()
    assert any("fixed hole x" in e for e in errors)
    assert any("outside sensor envelope" in e for e in errors)
    assert wrong.sensor_mount_fabrication_ready is False


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
