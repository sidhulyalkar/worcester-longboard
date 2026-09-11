from dataclasses import replace

from cad.fit_rig_geometry import DEFAULT
from cad.generate_one_zone_pilot import PILOT, carrier_plate, pilot_pod


def test_default_pilot_geometry_is_reference_ready_but_not_four_zone_authority():
    assert DEFAULT.sensor_mount_pilot_ready is True
    assert DEFAULT.sensor_mount_fabrication_ready is False
    assert PILOT.validate(DEFAULT) == []


def test_pilot_carrier_has_positive_volume():
    assert carrier_plate(PILOT).val().Volume() > 0
    assert pilot_pod(DEFAULT, PILOT).val().Volume() > 0


def test_pod_mount_holes_keep_sensor_body_clearance():
    too_close = replace(PILOT, pod_mount_y_mm=7.0)
    assert any("sensor body" in err for err in too_close.validate(DEFAULT))


def test_loaded_end_mount_holes_stay_clear_of_overload_towers():
    too_close = replace(PILOT, pod_mount_x_mm=27.0)
    assert any("overload towers" in err for err in too_close.validate(DEFAULT))


def test_carrier_must_have_margin_around_pod():
    too_small = replace(PILOT, carrier_length_mm=100.0)
    assert any("longitudinal margin" in err for err in too_small.validate(DEFAULT))
