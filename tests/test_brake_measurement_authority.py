import argparse

from tools.init_brake_measurement_session import build_manifest
from tools.qualify_brake_interface import qualify


def _args():
    return argparse.Namespace(
        truck_id="TRUCK-A", brake_kit_id="BRAKE-A", hub_id="HUB-A",
        tire_id="TIRE-A", tube_id="TUBE-A"
    )


def _passing_manifest():
    m = build_manifest(_args())
    m["measurements_mm"].update({
        "rotor_outer_diameter": 160.0,
        "rotor_inner_diameter": 80.0,
        "rotor_thickness": 2.0,
        "rotor_bolt_circle_diameter": 120.0,
        "rotor_to_hub_axial_offset": -4.0,
        "brake_arm_pivot_thread_major_diameter": 8.0,
        "brake_arm_pivot_axis_to_axle_x": -18.0,
        "brake_arm_pivot_axis_to_axle_z": 12.0,
        "spring_pin_offset_x": 0.0,
        "spring_pin_offset_z": 9.0,
        "pad_radial_center": 70.0,
        "released_arm_max_extent": 42.0,
        "applied_arm_max_extent": 47.0,
        "cable_min_bend_radius": 35.0,
        "inflated_tire_max_diameter": 220.0,
        "inflated_tire_max_width": 55.0,
    })
    for key in m["checks"]:
        m["checks"][key] = True
    m["static_brake_test"].update({
        "wheel_radius_m": 0.11,
        "applied_tangential_force_n": 100.0,
        "brake_torque_nm": 11.0,
    })
    return m


def test_initializer_starts_unqualified_and_unpowered():
    m = build_manifest(_args())
    assert m["authority"]["brake_interface_verified"] is False
    assert m["authority"]["powered_operation_authorized"] is False
    assert all(v is None for v in m["measurements_mm"].values())


def test_complete_unpowered_evidence_can_verify_brake_interface():
    report = qualify(_passing_manifest())
    assert report["qualified"] is True
    assert report["brake_interface_verified"] is True
    assert report["powered_operation_authorized"] is False


def test_signed_and_zero_datums_are_allowed():
    m = _passing_manifest()
    m["measurements_mm"]["rotor_to_hub_axial_offset"] = -6.0
    m["measurements_mm"]["spring_pin_offset_x"] = 0.0
    assert qualify(m)["qualified"] is True


def test_missing_geometry_blocks_qualification():
    m = _passing_manifest()
    m["measurements_mm"]["rotor_outer_diameter"] = None
    report = qualify(m)
    assert report["qualified"] is False
    assert any("rotor_outer_diameter" in err for err in report["errors"])


def test_impossible_rotor_geometry_blocks_qualification():
    m = _passing_manifest()
    m["measurements_mm"]["rotor_inner_diameter"] = 170.0
    report = qualify(m)
    assert report["qualified"] is False
    assert any("outer diameter must exceed" in err for err in report["errors"])


def test_bad_torque_consistency_blocks_qualification():
    m = _passing_manifest()
    m["static_brake_test"]["brake_torque_nm"] = 25.0
    report = qualify(m)
    assert report["qualified"] is False
    assert any("torque inconsistent" in err for err in report["errors"])


def test_wrong_wheel_radius_blocks_qualification():
    m = _passing_manifest()
    m["static_brake_test"]["wheel_radius_m"] = 0.15
    m["static_brake_test"]["brake_torque_nm"] = 15.0
    report = qualify(m)
    assert report["qualified"] is False
    assert any("wheel radius inconsistent" in err for err in report["errors"])


def test_brake_authority_never_promotes_power():
    m = _passing_manifest()
    m["authority"]["powered_operation_authorized"] = True
    report = qualify(m)
    assert report["qualified"] is False
    assert report["powered_operation_authorized"] is False
