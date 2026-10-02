import hashlib
import json
from pathlib import Path

import pytest

from tools.init_rev_c_powered_commissioning_stage import initialize


def _stamp(doc):
    payload = json.dumps(
        doc,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    out = dict(doc)
    out["authority_fingerprint_sha256"] = hashlib.sha256(payload).hexdigest()
    return out


def _write(path: Path, doc: dict) -> Path:
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return path


def _power(tmp_path: Path):
    return _write(
        tmp_path / "power.json",
        _stamp(
            {
                "schema_version": 1,
                "authority": "x1_power_architecture",
                "qualified": True,
            }
        ),
    )


def _health(tmp_path: Path, name: str, timestamp: str):
    return _write(
        tmp_path / name,
        _stamp(
            {
                "schema_version": 1,
                "authority": "x1_lifecycle_health_state",
                "valid": True,
                "errors": [],
                "board_id": "X1-A",
                "current_configuration_id": "CFG-A",
                "active_component_ids": ["DECK-A"],
                "event_count": 2,
                "latest_event_id": "PREFLIGHT",
                "latest_event_timestamp_utc": timestamp,
                "latest_odometer_km": 0.0,
                "latest_ride_hours": 0.0,
                "open_findings": [],
                "service_due": [],
                "service_due_state_unknown": [],
                "preflight_complete": True,
                "preflight_blockers": [],
                "health_state": "READY_FOR_ALLOWED_ACTIVITY",
                "ready_for_allowed_activity": True,
                "powered_operation_authorized": False,
                "public_operation_authorized": False,
                "dog_accompanied_operation_authorized": False,
                "interpretation_boundary": "synthetic",
            }
        ),
    )


def _stage(tmp_path: Path, index: int, stage_id: str, health_fp: str):
    return _write(
        tmp_path / f"stage-{index}.json",
        _stamp(
            {
                "schema_version": 1,
                "authority": "x1_powered_commissioning_stage",
                "qualified": True,
                "issue": 45,
                "stage_index": index,
                "stage_id": stage_id,
                "stage_name": "synthetic",
                "session_id": f"stage-{index}",
                "board_id": "X1-A",
                "configuration_id": "CFG-A",
                "started_at_utc": "2026-10-01T12:00:00Z",
                "completed_at_utc": "2026-10-01T12:01:00Z",
                "power_architecture_fingerprint_sha256": "power-fp",
                "pre_lifecycle_health_fingerprint_sha256": health_fp,
                "post_lifecycle_health_fingerprint_sha256": health_fp,
                "previous_stage_fingerprint_sha256": None,
                "venue_authority_fingerprint_sha256": None,
                "commissioning_stage_completed": True,
                "energized_stage_completed": index > 0,
                "free_ground_travel_stage_completed": index >= 3,
                "rider_stage_completed": index >= 4,
                "general_powered_operation_authorized": False,
                "public_operation_authorized": False,
                "dog_accompanied_operation_authorized": False,
                "interpretation_boundary": "synthetic",
            }
        ),
    )


def _venue(tmp_path: Path):
    return _write(
        tmp_path / "venue.json",
        _stamp(
            {
                "schema_version": 1,
                "authority": "x1_powered_test_venue_evidence",
                "qualified": True,
                "errors": [],
                "venue_id": "PRIVATE-A",
                "venue_name": "Synthetic private venue",
                "venue_permission_qualified": True,
                "vehicle_operation_legality_verified_recorded": False,
                "vehicle_powered_operation_authority": False,
                "public_operation_authority": False,
                "dog_accompanied_operation_authority": False,
                "interpretation_boundary": "synthetic",
            }
        ),
    )


def test_stage_zero_initializer_creates_unset_evidence_scaffold(tmp_path: Path):
    power = _power(tmp_path)
    health = _health(tmp_path, "health.json", "2026-10-01T11:59:00Z")
    workspace = tmp_path / "commissioning"

    report = initialize(
        workspace,
        "BENCH_READINESS",
        "X1-A",
        "CFG-A",
        power,
        health,
    )

    assert report["stage_index"] == 0
    assert report["general_powered_operation_authority"] is False

    manifest = json.loads((workspace / "commissioning_manifest.json").read_text())
    assert manifest["energized"] is False
    assert manifest["free_ground_travel"] is False
    assert manifest["rider_present"] is False
    assert manifest["dog_present"] is False
    assert manifest["checks"]
    assert all(item["status"] == "UNSET" for item in manifest["checks"].values())


def test_ground_stage_requires_previous_stage_and_venue(tmp_path: Path):
    power = _power(tmp_path)
    health_path = _health(tmp_path, "health.json", "2026-10-01T12:10:00Z")
    health = json.loads(health_path.read_text())
    previous = _stage(
        tmp_path,
        2,
        "RESTRAINED_LOADED_BENCH",
        health["authority_fingerprint_sha256"],
    )
    venue = _venue(tmp_path)

    workspace = tmp_path / "commissioning"
    report = initialize(
        workspace,
        "RIDER_FREE_CONTROLLED_GROUND",
        "X1-A",
        "CFG-A",
        power,
        health_path,
        previous,
        venue,
    )
    assert report["stage_index"] == 3

    manifest = json.loads((workspace / "commissioning_manifest.json").read_text())
    assert manifest["energized"] is True
    assert manifest["free_ground_travel"] is True
    assert manifest["rider_present"] is False
    assert manifest["venue_authority_fingerprint_sha256"]


def test_initializer_rejects_missing_ground_venue(tmp_path: Path):
    power = _power(tmp_path)
    health_path = _health(tmp_path, "health.json", "2026-10-01T12:10:00Z")
    health = json.loads(health_path.read_text())
    previous = _stage(
        tmp_path,
        2,
        "RESTRAINED_LOADED_BENCH",
        health["authority_fingerprint_sha256"],
    )

    with pytest.raises(ValueError, match="venue authority"):
        initialize(
            tmp_path / "commissioning",
            "RIDER_FREE_CONTROLLED_GROUND",
            "X1-A",
            "CFG-A",
            power,
            health_path,
            previous,
        )


def test_initializer_rejects_health_not_matching_previous_stage(tmp_path: Path):
    power = _power(tmp_path)
    health_path = _health(tmp_path, "health.json", "2026-10-01T12:10:00Z")
    previous = _stage(
        tmp_path,
        0,
        "BENCH_READINESS",
        "different-health-fingerprint",
    )

    with pytest.raises(ValueError, match="pre-health must match"):
        initialize(
            tmp_path / "commissioning",
            "SECURED_UNLOADED_SPIN",
            "X1-A",
            "CFG-A",
            power,
            health_path,
            previous,
        )


def test_initializer_refuses_to_overwrite_existing_session(tmp_path: Path):
    power = _power(tmp_path)
    health = _health(tmp_path, "health.json", "2026-10-01T11:59:00Z")
    workspace = tmp_path / "commissioning"
    workspace.mkdir()
    marker = workspace / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        initialize(
            workspace,
            "BENCH_READINESS",
            "X1-A",
            "CFG-A",
            power,
            health,
        )

    assert marker.read_text(encoding="utf-8") == "keep"
