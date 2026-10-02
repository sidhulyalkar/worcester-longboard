import copy
import json
from pathlib import Path

from tools.qualify_powered_test_venue import qualify

ROOT = Path(__file__).resolve().parents[1]


def _manifest():
    data = json.loads(
        (ROOT / "hardware/powered_test_venue_template.json").read_text()
    )
    data.update(
        {
            "session_id": "venue-test-01",
            "venue_id": "PRIVATE-COURSE-A",
            "venue_name": "Controlled private test course",
            "venue_type": "private_property",
            "owner_or_jurisdiction": "property owner",
            "permission_basis": "written owner permission",
            "permission_source_or_record": "private/venue_permission_record.pdf",
            "permission_checked_date": "2026-10-01",
            "public_access_controlled": True,
            "course_boundary_defined": True,
            "surface_description": "closed mixed-surface loop",
            "pedestrian_vehicle_separation_method": "closed gate and spotter",
            "emergency_stop_plan": "mechanical stop and clear runoff zone",
            "maximum_planned_speed_mps": 2.0,
            "applicable_restrictions": ["no public access during test"],
            "mechanical_brake_required": True,
            "dog_present": False,
            "leash_attachment_to_board": False,
            "worcester_park": False,
            "venue_permission_verified": True,
            "vehicle_operation_legality_verified": False,
            "vehicle_powered_operation_authority": False,
            "dog_accompanied_operation_authority": False,
        }
    )
    return data


def test_private_controlled_venue_record_can_qualify_without_vehicle_authority():
    report = qualify(_manifest())
    assert report["qualified"] is True
    assert report["venue_permission_qualified"] is True
    assert report["vehicle_operation_legality_verified_recorded"] is False
    assert report["vehicle_powered_operation_authority"] is False
    assert report["public_operation_authority"] is False
    assert report["dog_accompanied_operation_authority"] is False
    assert len(report["authority_fingerprint_sha256"]) == 64


def test_worcester_park_is_blocked_by_current_dated_qualifier():
    data = _manifest()
    data["venue_id"] = "WORCESTER-PARK"
    data["venue_name"] = "Worcester Park"
    data["worcester_park"] = True
    report = qualify(data)
    assert report["qualified"] is False
    assert any("Worcester Park is blocked" in error for error in report["errors"])


def test_initial_powered_venue_record_must_be_dog_free():
    data = _manifest()
    data["dog_present"] = True
    report = qualify(data)
    assert report["qualified"] is False
    assert "dog_present must be false for initial powered test venue qualification" in report["errors"]


def test_venue_record_cannot_self_authorize_vehicle_power():
    data = _manifest()
    data["vehicle_powered_operation_authority"] = True
    report = qualify(data)
    assert report["qualified"] is False
    assert "vehicle_powered_operation_authority must be false" in report["errors"]


def test_permission_and_controlled_access_are_required():
    data = _manifest()
    data["venue_permission_verified"] = False
    data["public_access_controlled"] = False
    report = qualify(data)
    assert report["qualified"] is False
    assert "venue_permission_verified must be true" in report["errors"]
    assert "public_access_controlled must be true" in report["errors"]
