import copy
import hashlib
import json
from pathlib import Path

from tools.qualify_rev_c_powered_commissioning_stage import qualify

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = json.loads(
    (
        ROOT / "hardware/rev_c_powered_commissioning_snapshot_2026-10-01.json"
    ).read_text()
)
TEMPLATE = json.loads(
    (
        ROOT / "hardware/rev_c_powered_commissioning_stage_template.json"
    ).read_text()
)


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


def _power_architecture():
    return _stamp(
        {
            "schema_version": 1,
            "authority": "x1_power_architecture",
            "qualified": True,
        }
    )


def _health(timestamp, *, board="X1-A", config="CFG-A"):
    return _stamp(
        {
            "schema_version": 1,
            "authority": "x1_lifecycle_health_state",
            "valid": True,
            "errors": [],
            "board_id": board,
            "current_configuration_id": config,
            "active_component_ids": ["DECK-A", "BRAKE-A"],
            "event_count": 2,
            "latest_event_id": f"PREFLIGHT-{timestamp}",
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
    )


def _venue():
    return _stamp(
        {
            "schema_version": 1,
            "authority": "x1_powered_test_venue_evidence",
            "qualified": True,
            "errors": [],
            "venue_id": "PRIVATE-A",
            "venue_name": "Synthetic private controlled venue",
            "venue_permission_qualified": True,
            "vehicle_operation_legality_verified_recorded": False,
            "vehicle_powered_operation_authority": False,
            "public_operation_authority": False,
            "dog_accompanied_operation_authority": False,
            "interpretation_boundary": "synthetic",
        }
    )


def _stage(stage_id):
    return next(x for x in SNAPSHOT["stages"] if x["stage_id"] == stage_id)


def _manifest(
    stage_id,
    power,
    pre_health,
    *,
    previous=None,
    post_health=None,
    venue=None,
    started="2026-10-01T12:00:00Z",
    completed="2026-10-01T12:01:00Z",
):
    spec = _stage(stage_id)
    data = copy.deepcopy(TEMPLATE)
    data.update(
        {
            "session_id": f"session-{stage_id.lower()}",
            "board_id": "X1-A",
            "configuration_id": "CFG-A",
            "stage_id": stage_id,
            "started_at_utc": started,
            "completed_at_utc": completed,
            "power_architecture_fingerprint_sha256": power[
                "authority_fingerprint_sha256"
            ],
            "pre_lifecycle_health_fingerprint_sha256": pre_health[
                "authority_fingerprint_sha256"
            ],
            "post_lifecycle_health_fingerprint_sha256": (
                post_health["authority_fingerprint_sha256"]
                if post_health is not None
                else pre_health["authority_fingerprint_sha256"]
            ),
            "previous_stage_fingerprint_sha256": (
                previous["authority_fingerprint_sha256"]
                if previous is not None
                else ""
            ),
            "venue_authority_fingerprint_sha256": (
                venue["authority_fingerprint_sha256"]
                if venue is not None
                else ""
            ),
            "energized": spec["energized"],
            "free_ground_travel": spec["free_ground_travel"],
            "rider_present": spec["rider_present"],
            "dog_present": spec["dog_present"],
            "public_area": False,
            "independent_mechanical_brake_available": True,
            "emergency_power_removal_available": True,
            "declared_stage_limits": {
                "source_reference": "final power architecture / commissioning plan",
                "max_commanded_speed_mps": 2.0,
                "max_motor_phase_current_a": 10.0,
                "max_battery_current_a": 5.0,
                "max_pack_voltage_v": 60.0,
                "max_motor_erpm": 10000.0,
                "max_motor_temperature_c": 60.0,
                "max_controller_temperature_c": 60.0,
            },
            "checks": {
                check: {"status": "PASS", "notes": "synthetic"}
                for check in spec["required_checks"]
            },
            "measurements": [
                {
                    "metric_id": metric,
                    "value": 1.0,
                    "unit": "synthetic-unit",
                    "source": "synthetic fixture",
                    "evidence_ref": "",
                }
                for metric in spec["required_measurements"]
            ],
            "stop_conditions_observed": [],
            "anomalies": [],
            "notes": "",
        }
    )
    if spec["post_stage_ready_health_required"]:
        for key in data["post_stage"]:
            data["post_stage"][key] = True
    return data


def _qualify_stage(
    stage_id,
    power,
    pre_health,
    *,
    previous=None,
    post_health=None,
    venue=None,
    started="2026-10-01T12:00:00Z",
    completed="2026-10-01T12:01:00Z",
):
    manifest = _manifest(
        stage_id,
        power,
        pre_health,
        previous=previous,
        post_health=post_health,
        venue=venue,
        started=started,
        completed=completed,
    )
    return qualify(
        manifest,
        power,
        pre_health,
        previous_stage=previous,
        post_health=post_health,
        venue=venue,
        snapshot=SNAPSHOT,
    )


def test_stage_zero_can_qualify_but_never_authorizes_operation():
    power = _power_architecture()
    health = _health("2026-10-01T11:59:00Z")

    report = _qualify_stage("BENCH_READINESS", power, health)

    assert report["qualified"] is True
    assert report["stage_index"] == 0
    assert report["energized_stage_completed"] is False
    assert report["free_ground_travel_stage_completed"] is False
    assert report["rider_stage_completed"] is False
    assert report["general_powered_operation_authorized"] is False
    assert report["public_operation_authorized"] is False
    assert report["dog_accompanied_operation_authorized"] is False
    assert len(report["authority_fingerprint_sha256"]) == 64


def test_stage_one_requires_previous_stage_and_new_post_health():
    power = _power_architecture()
    pre = _health("2026-10-01T11:59:00Z")
    stage0 = _qualify_stage("BENCH_READINESS", power, pre)
    post = _health("2026-10-01T12:04:00Z")

    report = _qualify_stage(
        "SECURED_UNLOADED_SPIN",
        power,
        pre,
        previous=stage0,
        post_health=post,
        started="2026-10-01T12:02:00Z",
        completed="2026-10-01T12:03:00Z",
    )

    assert report["qualified"] is True
    assert report["stage_index"] == 1
    assert report["energized_stage_completed"] is True
    assert report["free_ground_travel_stage_completed"] is False
    assert (
        report["pre_lifecycle_health_fingerprint_sha256"]
        == stage0["post_lifecycle_health_fingerprint_sha256"]
    )
    assert (
        report["post_lifecycle_health_fingerprint_sha256"]
        != report["pre_lifecycle_health_fingerprint_sha256"]
    )


def test_stage_cannot_be_skipped():
    power = _power_architecture()
    pre = _health("2026-10-01T11:59:00Z")
    stage0 = _qualify_stage("BENCH_READINESS", power, pre)
    post = _health("2026-10-01T12:04:00Z")

    report = _qualify_stage(
        "RESTRAINED_LOADED_BENCH",
        power,
        pre,
        previous=stage0,
        post_health=post,
        started="2026-10-01T12:02:00Z",
        completed="2026-10-01T12:03:00Z",
    )

    assert report["qualified"] is False
    assert any("previous stage index must be 1" in x for x in report["errors"])


def test_energized_stage_rejects_stale_or_missing_post_health():
    power = _power_architecture()
    pre = _health("2026-10-01T11:59:00Z")
    stage0 = _qualify_stage("BENCH_READINESS", power, pre)

    manifest = _manifest(
        "SECURED_UNLOADED_SPIN",
        power,
        pre,
        previous=stage0,
        post_health=None,
        started="2026-10-01T12:02:00Z",
        completed="2026-10-01T12:03:00Z",
    )
    report = qualify(
        manifest,
        power,
        pre,
        previous_stage=stage0,
        post_health=None,
        snapshot=SNAPSHOT,
    )
    assert report["qualified"] is False
    assert "post-health READY state is required" in report["errors"]

    stale = _health("2026-10-01T12:03:00Z")
    report = _qualify_stage(
        "SECURED_UNLOADED_SPIN",
        power,
        pre,
        previous=stage0,
        post_health=stale,
        started="2026-10-01T12:02:00Z",
        completed="2026-10-01T12:03:00Z",
    )
    assert report["qualified"] is False
    assert any("post-health latest event must be after stage completion" in x for x in report["errors"])


def test_stop_condition_or_unresolved_anomaly_blocks_stage():
    power = _power_architecture()
    health = _health("2026-10-01T11:59:00Z")
    manifest = _manifest("BENCH_READINESS", power, health)
    manifest["stop_conditions_observed"] = ["mechanical brake unavailable"]
    manifest["anomalies"] = ["unexpected sensor mapping"]

    report = qualify(manifest, power, health, snapshot=SNAPSHOT)
    assert report["qualified"] is False
    assert "stage cannot qualify with observed stop conditions" in report["errors"]
    assert "stage cannot qualify with unresolved anomalies" in report["errors"]


def test_required_check_and_measurement_cannot_be_omitted():
    power = _power_architecture()
    pre = _health("2026-10-01T11:59:00Z")
    stage0 = _qualify_stage("BENCH_READINESS", power, pre)
    post = _health("2026-10-01T12:04:00Z")
    manifest = _manifest(
        "SECURED_UNLOADED_SPIN",
        power,
        pre,
        previous=stage0,
        post_health=post,
        started="2026-10-01T12:02:00Z",
        completed="2026-10-01T12:03:00Z",
    )
    manifest["checks"].pop("motor_direction_correct")
    manifest["measurements"] = [
        m for m in manifest["measurements"]
        if m["metric_id"] != "pack_voltage_v"
    ]

    report = qualify(
        manifest,
        power,
        pre,
        previous_stage=stage0,
        post_health=post,
        snapshot=SNAPSHOT,
    )
    assert report["qualified"] is False
    assert "required stage check not PASS: motor_direction_correct" in report["errors"]
    assert "required measurement missing: pack_voltage_v" in report["errors"]


def test_ground_stage_requires_fingerprinted_venue_and_no_rider():
    power = _power_architecture()
    h0 = _health("2026-10-01T11:50:00Z")
    s0 = _qualify_stage("BENCH_READINESS", power, h0)

    h1 = _health("2026-10-01T12:04:00Z")
    s1 = _qualify_stage(
        "SECURED_UNLOADED_SPIN",
        power,
        h0,
        previous=s0,
        post_health=h1,
        started="2026-10-01T12:02:00Z",
        completed="2026-10-01T12:03:00Z",
    )
    h2 = _health("2026-10-01T12:09:00Z")
    s2 = _qualify_stage(
        "RESTRAINED_LOADED_BENCH",
        power,
        h1,
        previous=s1,
        post_health=h2,
        started="2026-10-01T12:07:00Z",
        completed="2026-10-01T12:08:00Z",
    )

    post = _health("2026-10-01T12:14:00Z")
    venue = _venue()
    report = _qualify_stage(
        "RIDER_FREE_CONTROLLED_GROUND",
        power,
        h2,
        previous=s2,
        post_health=post,
        venue=venue,
        started="2026-10-01T12:12:00Z",
        completed="2026-10-01T12:13:00Z",
    )
    assert report["qualified"] is True
    assert report["free_ground_travel_stage_completed"] is True
    assert report["rider_stage_completed"] is False

    tampered = dict(venue)
    tampered["venue_name"] = "tampered"
    report = _qualify_stage(
        "RIDER_FREE_CONTROLLED_GROUND",
        power,
        h2,
        previous=s2,
        post_health=post,
        venue=tampered,
        started="2026-10-01T12:12:00Z",
        completed="2026-10-01T12:13:00Z",
    )
    assert report["qualified"] is False
    assert "venue authority fingerprint is invalid" in report["errors"]


def test_rider_only_stage_still_does_not_grant_general_powered_operation():
    power = _power_architecture()
    venue = _venue()

    h0 = _health("2026-10-01T11:50:00Z")
    s0 = _qualify_stage("BENCH_READINESS", power, h0)
    h1 = _health("2026-10-01T12:04:00Z")
    s1 = _qualify_stage(
        "SECURED_UNLOADED_SPIN", power, h0, previous=s0, post_health=h1,
        started="2026-10-01T12:02:00Z", completed="2026-10-01T12:03:00Z"
    )
    h2 = _health("2026-10-01T12:09:00Z")
    s2 = _qualify_stage(
        "RESTRAINED_LOADED_BENCH", power, h1, previous=s1, post_health=h2,
        started="2026-10-01T12:07:00Z", completed="2026-10-01T12:08:00Z"
    )
    h3 = _health("2026-10-01T12:14:00Z")
    s3 = _qualify_stage(
        "RIDER_FREE_CONTROLLED_GROUND", power, h2, previous=s2,
        post_health=h3, venue=venue,
        started="2026-10-01T12:12:00Z", completed="2026-10-01T12:13:00Z"
    )
    h4 = _health("2026-10-01T12:19:00Z")
    s4 = _qualify_stage(
        "RIDER_ONLY_VERY_LOW_SPEED", power, h3, previous=s3,
        post_health=h4, venue=venue,
        started="2026-10-01T12:17:00Z", completed="2026-10-01T12:18:00Z"
    )

    assert s4["qualified"] is True
    assert s4["rider_stage_completed"] is True
    assert s4["general_powered_operation_authorized"] is False
    assert s4["public_operation_authorized"] is False
    assert s4["dog_accompanied_operation_authorized"] is False


def test_configuration_or_power_architecture_lineage_mismatch_fails():
    power = _power_architecture()
    pre = _health("2026-10-01T11:59:00Z")
    stage0 = _qualify_stage("BENCH_READINESS", power, pre)
    post = _health("2026-10-01T12:04:00Z", config="CFG-B")

    manifest = _manifest(
        "SECURED_UNLOADED_SPIN",
        power,
        pre,
        previous=stage0,
        post_health=post,
        started="2026-10-01T12:02:00Z",
        completed="2026-10-01T12:03:00Z",
    )
    report = qualify(
        manifest,
        power,
        pre,
        previous_stage=stage0,
        post_health=post,
        snapshot=SNAPSHOT,
    )
    assert report["qualified"] is False
    assert "post-health configuration_id mismatch" in report["errors"]

    tampered_power = dict(power)
    tampered_power["qualified"] = False
    report = qualify(
        _manifest("BENCH_READINESS", power, pre),
        tampered_power,
        pre,
        snapshot=SNAPSHOT,
    )
    assert report["qualified"] is False
    assert "power architecture must be qualified" in report["errors"]
    assert "power architecture fingerprint is invalid" in report["errors"]
