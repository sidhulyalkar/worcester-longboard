from dataclasses import replace

from cad.rolling_chassis_geometry import BRAKE_FIRST, DRIVE_CLEARANCE


def test_reference_chassis_is_valid_but_not_fabrication_ready():
    assert BRAKE_FIRST.validate() == []
    assert BRAKE_FIRST.fabrication_ready is False
    assert BRAKE_FIRST.vendor_envelopes_verified is False


def test_brake_and_drive_reference_conflict_is_explicit():
    assert BRAKE_FIRST.truck.brake_reference_compatible is True
    assert BRAKE_FIRST.truck.drive_reference_compatible is False
    assert DRIVE_CLEARANCE.truck.brake_reference_compatible is False
    assert DRIVE_CLEARANCE.truck.drive_reference_compatible is True


def test_compressed_clearance_gate_tracks_suspension_travel():
    too_much_travel = replace(BRAKE_FIRST, suspension_vertical_travel_allowance_mm=25.0)
    assert any("compressed ground-clearance" in err for err in too_much_travel.validate())


def test_rider_keepout_cannot_be_consumed_by_chassis_packaging():
    oversized = replace(BRAKE_FIRST, rider_interface_keepout_length_mm=900.0)
    assert any("end packaging" in err for err in oversized.validate())


def test_wheel_sweep_grows_with_steering_angle():
    straight = replace(BRAKE_FIRST, truck=replace(BRAKE_FIRST.truck, max_steer_deg=0.0))
    assert BRAKE_FIRST.steered_wheel_half_extent_x_mm > straight.steered_wheel_half_extent_x_mm


def test_authority_stays_nonfabrication_until_vendor_interfaces_verified():
    report = BRAKE_FIRST.authority_report()
    assert report["scope"] == "unpowered_rolling_chassis_geometry_only"
    assert report["fabrication_ready"] is False
    assert len(report["gates"]) == 6
    verified = BRAKE_FIRST.with_component_verification()
    assert verified.vendor_envelopes_verified is True
    assert verified.fabrication_ready is True
