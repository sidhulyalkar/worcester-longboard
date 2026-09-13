import copy
import hashlib
import json
from types import SimpleNamespace
from pathlib import Path

from tools.init_chassis_session import build_manifest
from tools.qualify_rolling_chassis import qualify

ROOT = Path(__file__).resolve().parents[1]


def _stamp(doc):
    payload = json.dumps(doc, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    out = dict(doc)
    out["authority_fingerprint_sha256"] = hashlib.sha256(payload).hexdigest()
    return out


def _args():
    return SimpleNamespace(
        donor_id="DONOR-A",
        deck_id="DECK-A",
        front_truck_id="TRUCK-F-A",
        rear_truck_id="TRUCK-R-A",
        wheel_fl_id="WHEEL-FL-A",
        wheel_fr_id="WHEEL-FR-A",
        wheel_rl_id="WHEEL-RL-A",
        wheel_rr_id="WHEEL-RR-A",
        brake_id="BRAKE-V5-A",
    )


def _brake():
    return _stamp(
        {
            "schema_version": 1,
            "authority": "x1_mechanical_brake_interface",
            "scope": "unpowered_mechanical_brake_interface_only",
            "qualified": True,
            "errors": [],
            "brake_interface_verified": True,
            "powered_operation_authorized": False,
            "hardware_ids": {"brake": "BRAKE-V5-A"},
        }
    )


def _joint_contract():
    return json.loads((ROOT / "hardware/critical_joint_register_v1.json").read_text())


def _complete_manifest():
    data = build_manifest(_args())
    data["measurements_mm"].update(
        {
            "deck_tip_to_tip": 950.0,
            "deck_max_width": 251.0,
            "axle_to_axle": 940.0,
            "front_truck_total_width": 400.0,
            "rear_truck_total_width": 400.0,
            "static_ground_clearance_min": 70.0,
            "loaded_ground_clearance_min": 58.0,
        }
    )
    data["measurements_mm"]["wheel_diameter"] = {pos: 194.0 for pos in ("fl", "fr", "rl", "rr")}
    data["measurements_mm"]["wheel_width"] = {pos: 51.0 for pos in ("fl", "fr", "rl", "rr")}
    data["measurements_mm"]["wheel_axial_play"] = {pos: 0.25 for pos in ("fl", "fr", "rl", "rr")}
    data["measurement_context"]["tire_pressure"] = {pos: 20.0 for pos in ("fl", "fr", "rl", "rr")}
    data["measurement_context"]["loaded_clearance_test_mass_kg"] = 55.0
    data["measurement_context"]["measurement_tools"] = ["CALIPER-A", "TAPE-A", "PRESSURE-A"]
    for key in data["stock_baseline"]:
        data["stock_baseline"][key] = True
    for key in data["brake_installed_chassis"]:
        if key != "brake_authority_path":
            data["brake_installed_chassis"][key] = True
    data["brake_installed_chassis"]["brake_authority_path"] = "brake_authority.json"
    for row in data["retention"]["joints"]:
        row.update(
            {
                "hardware_description": f"received hardware for {row['id']}",
                "assembly_state": "manufacturer-style received/serviced state",
                "locking_method": "positive locking method recorded from received assembly",
                "witness_method": "paint witness mark",
                "pre_test_inspection_passed": True,
                "post_test_inspection_passed": True,
                "movement_detected": False,
            }
        )
    return data


def test_complete_physical_chassis_manifest_qualifies():
    report = qualify(_complete_manifest(), _brake(), _joint_contract())
    assert report["qualified"] is True
    assert report["authority"] == "x1_rolling_chassis_physical"
    assert report["powered_operation_authorized"] is False
    unsigned = dict(report)
    fingerprint = unsigned.pop("authority_fingerprint_sha256")
    expected = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    assert fingerprint == expected


def test_any_joint_movement_fails_chassis():
    data = _complete_manifest()
    data["retention"]["joints"][0]["movement_detected"] = True
    report = qualify(data, _brake(), _joint_contract())
    assert report["qualified"] is False
    assert any("retention movement" in error for error in report["errors"])


def test_power_or_drive_presence_fails_unpowered_scope():
    for field in ("drivetrain_installed", "traction_battery_installed", "powered_test_performed"):
        data = _complete_manifest()
        data["configuration"][field] = True
        report = qualify(data, _brake(), _joint_contract())
        assert report["qualified"] is False
        assert any(field in error for error in report["errors"])


def test_tampered_brake_authority_is_rejected():
    brake = _brake()
    brake["brake_interface_verified"] = False
    report = qualify(_complete_manifest(), brake, _joint_contract())
    assert report["qualified"] is False
    assert any("brake authority" in error for error in report["errors"])


def test_missing_critical_joint_is_rejected():
    data = _complete_manifest()
    data["retention"]["joints"] = data["retention"]["joints"][:-1]
    report = qualify(data, _brake(), _joint_contract())
    assert report["qualified"] is False
    assert any("missing critical joint" in error for error in report["errors"])


def test_catalog_like_but_unmeasured_manifest_fails_closed():
    data = build_manifest(_args())
    report = qualify(data, _brake(), _joint_contract())
    assert report["qualified"] is False
    assert len(report["errors"]) > 10
