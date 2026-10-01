import math

import pytest

from simulation.rev_c_skid_geometry import SkidGeometry


def test_centered_skid_matches_symmetric_breakover_formula():
    study = SkidGeometry(
        wheelbase_mm=940.0,
        skid_x_from_front_axle_mm=470.0,
        vulnerable_component_clearance_mm=100.0,
        skid_drop_below_component_mm=10.0,
    )
    report = study.as_dict()
    expected_component = math.degrees(2 * math.atan2(100.0, 470.0))
    expected_skid = math.degrees(2 * math.atan2(90.0, 470.0))
    assert report["rigid_2d_component_breakover_deg"] == pytest.approx(
        expected_component, abs=1e-3
    )
    assert report["rigid_2d_skid_breakover_deg"] == pytest.approx(
        expected_skid, abs=1e-3
    )
    assert report["rigid_2d_breakover_loss_deg"] > 0
    assert report["clearance_consumed_fraction"] == 0.1
    assert report["physical_authority"] is False
    assert report["impact_authority"] is False


def test_more_skid_drop_always_reduces_rigid_breakover_for_same_location():
    shallow = SkidGeometry(940, 470, 100, 5).as_dict()
    deep = SkidGeometry(940, 470, 100, 20).as_dict()
    assert deep["skid_clearance_mm"] < shallow["skid_clearance_mm"]
    assert (
        deep["rigid_2d_skid_breakover_deg"]
        < shallow["rigid_2d_skid_breakover_deg"]
    )
    assert (
        deep["rigid_2d_breakover_loss_deg"]
        > shallow["rigid_2d_breakover_loss_deg"]
    )


def test_off_center_skid_uses_front_and_rear_runs():
    report = SkidGeometry(940, 300, 100, 10).as_dict()
    expected = math.degrees(
        math.atan2(90.0, 300.0) + math.atan2(90.0, 640.0)
    )
    assert report["rigid_2d_skid_breakover_deg"] == pytest.approx(
        expected, abs=1e-3
    )


@pytest.mark.parametrize(
    "study",
    [
        SkidGeometry(0, 100, 100, 5),
        SkidGeometry(940, 0, 100, 5),
        SkidGeometry(940, 940, 100, 5),
        SkidGeometry(940, 470, 0, 5),
        SkidGeometry(940, 470, 100, -1),
        SkidGeometry(940, 470, 100, 100),
    ],
)
def test_invalid_skid_geometry_fails_closed(study):
    with pytest.raises(ValueError):
        study.validate()
