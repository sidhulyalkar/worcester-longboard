import copy
import json
from pathlib import Path

from tools.evaluate_x1_lifecycle_health import evaluate

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = json.loads(
    (ROOT / "hardware/rev_c_lifecycle_health_snapshot_2026-10-01.json").read_text()
)
EVENT_TEMPLATE = json.loads(
    (ROOT / "hardware/x1_health_event_template.json").read_text()
)


def _component(
    component_id="DECK-A",
    role="structural_deck",
    *,
    interval_km=None,
    interval_hours=None,
    interval_days=None,
    source_type="",
    source_reference="",
    installed_at="2026-10-01T12:00:00Z",
    installed_km=0.0,
    installed_hours=0.0,
):
    return {
        "component_id": component_id,
        "subsystem": role,
        "role": role,
        "manufacturer": "Synthetic",
        "model": f"Model-{component_id}",
        "revision": "A",
        "serial_or_private_identifier": "",
        "active": True,
        "installed_at_utc": installed_at,
        "installed_odometer_km": installed_km,
        "installed_ride_hours": installed_hours,
        "service_policy": {
            "source_type": source_type,
            "source_reference": source_reference,
            "interval_km": interval_km,
            "interval_hours": interval_hours,
            "interval_days": interval_days,
            "notes": "",
        },
    }


def _registry(components=None):
    return {
        "schema_version": 1,
        "scope": "x1_vehicle_component_registry",
        "board_id": "X1-TEST-A",
        "configuration_id": "CFG-A",
        "created_at_utc": "2026-10-01T12:00:00Z",
        "upstream_authorities": {},
        "components": components or [_component()],
        "configuration_notes": "",
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
    }


def _event(
    event_id,
    timestamp,
    event_type,
    *,
    config="CFG-A",
    odometer=0.0,
    hours=0.0,
):
    data = copy.deepcopy(EVENT_TEMPLATE)
    data.update(
        {
            "event_id": event_id,
            "board_id": "X1-TEST-A",
            "configuration_id": config,
            "timestamp_utc": timestamp,
            "event_type": event_type,
            "activity_type": "UNPOWERED_CONTROLLED_TEST",
            "odometer_km": odometer,
            "ride_hours": hours,
        }
    )
    for check in data["checks"].values():
        check["status"] = "NA"
    return data


def _pass_preflight(
    event_id="PREFLIGHT-01",
    timestamp="2026-10-01T12:10:00Z",
    *,
    config="CFG-A",
    odometer=0.0,
    hours=0.0,
    lights=False,
):
    data = _event(
        event_id,
        timestamp,
        "PREFLIGHT",
        config=config,
        odometer=odometer,
        hours=hours,
    )
    for check_id in SNAPSHOT["required_preflight_checks"]:
        data["checks"][check_id]["status"] = "PASS"
    data["activity_requirements"]["lights_required"] = lights
    if lights:
        data["checks"]["lights_and_reflective_visibility"]["status"] = "PASS"
    return data


def test_clean_preflight_is_ready_but_never_authorizes_operation():
    report = evaluate(_registry(), [_pass_preflight()], SNAPSHOT)

    assert report["valid"] is True
    assert report["health_state"] == "READY_FOR_ALLOWED_ACTIVITY"
    assert report["ready_for_allowed_activity"] is True
    assert report["powered_operation_authorized"] is False
    assert report["public_operation_authorized"] is False
    assert report["dog_accompanied_operation_authorized"] is False
    assert len(report["authority_fingerprint_sha256"]) == 64


def test_no_event_or_non_preflight_latest_event_requires_inspection():
    report = evaluate(_registry(), [], SNAPSHOT)
    assert report["valid"] is True
    assert report["health_state"] == "INSPECTION_REQUIRED"
    assert report["ready_for_allowed_activity"] is False
    assert "no health events recorded" in report["preflight_blockers"]

    post = _event(
        "POST-01",
        "2026-10-01T12:20:00Z",
        "POST_ACTIVITY",
        odometer=0.2,
        hours=0.1,
    )
    report = evaluate(_registry(), [_pass_preflight(), post], SNAPSHOT)
    assert report["health_state"] == "INSPECTION_REQUIRED"
    assert "latest event is not a PREFLIGHT" in report["preflight_blockers"]


def test_stop_finding_survives_later_green_preflight_until_explicit_service_closure():
    impact = _event(
        "IMPACT-01",
        "2026-10-01T12:20:00Z",
        "IMPACT",
        odometer=0.2,
        hours=0.1,
    )
    impact["observed_triggers"] = ["critical_witness_mark_movement"]
    impact["findings_opened"] = [
        {
            "finding_id": "F-STOP-01",
            "component_id": "DECK-A",
            "severity": "STOP",
            "trigger": "critical_witness_mark_movement",
            "source_check_id": "",
            "description": "Critical retention witness mark moved after impact.",
            "evidence_ref": "private/photo-01",
        }
    ]

    later_preflight = _pass_preflight(
        "PREFLIGHT-02",
        "2026-10-01T12:30:00Z",
        odometer=0.2,
        hours=0.1,
    )
    report = evaluate(
        _registry(),
        [_pass_preflight(), impact, later_preflight],
        SNAPSHOT,
    )
    assert report["valid"] is True
    assert report["health_state"] == "STOP_USE"
    assert report["ready_for_allowed_activity"] is False
    assert report["open_findings"][0]["finding_id"] == "F-STOP-01"

    service = _event(
        "SERVICE-01",
        "2026-10-01T12:40:00Z",
        "SERVICE",
        odometer=0.2,
        hours=0.1,
    )
    service["findings_closed"] = [
        {
            "finding_id": "F-STOP-01",
            "closure_action": "Disassembled and inspected retention stack; replaced damaged locking hardware.",
            "verification": "Reassembled to selected procedure and re-established witness mark.",
        }
    ]
    service["service_actions"] = [
        {
            "component_id": "DECK-A",
            "action": "retention joint inspection and hardware replacement",
            "resets_service_interval": False,
            "source_reference": "Issue-41 synthetic fixture",
            "notes": "",
        }
    ]

    report = evaluate(
        _registry(),
        [_pass_preflight(), impact, later_preflight, service],
        SNAPSHOT,
    )
    assert report["health_state"] == "INSPECTION_REQUIRED"
    assert report["open_findings"] == []

    fresh = _pass_preflight(
        "PREFLIGHT-03",
        "2026-10-01T12:50:00Z",
        odometer=0.2,
        hours=0.1,
    )
    report = evaluate(
        _registry(),
        [_pass_preflight(), impact, later_preflight, service, fresh],
        SNAPSHOT,
    )
    assert report["health_state"] == "READY_FOR_ALLOWED_ACTIVITY"


def test_failed_preflight_check_requires_explicit_finding():
    data = _pass_preflight()
    data["checks"]["mechanical_brake_function"]["status"] = "FAIL"

    report = evaluate(_registry(), [data], SNAPSHOT)
    assert report["valid"] is False
    assert report["ready_for_allowed_activity"] is False
    assert any(
        "failed check mechanical_brake_function requires an INSPECT-or-higher finding"
        in error
        for error in report["errors"]
    )


def test_trigger_cannot_be_recorded_below_minimum_severity():
    data = _event("FAULT-01", "2026-10-01T12:10:00Z", "FAULT")
    data["observed_triggers"] = ["brake_unavailable_or_materially_degraded"]
    data["findings_opened"] = [
        {
            "finding_id": "F-BRAKE",
            "component_id": "DECK-A",
            "severity": "INSPECT",
            "trigger": "brake_unavailable_or_materially_degraded",
            "source_check_id": "",
            "description": "Synthetic brake fault.",
            "evidence_ref": "",
        }
    ]

    report = evaluate(_registry(), [data], SNAPSHOT)
    assert report["valid"] is False
    assert any(
        "requires a finding at severity STOP or higher" in error
        for error in report["errors"]
    )


def test_sourced_distance_interval_becomes_service_required_and_can_be_reset():
    brake = _component(
        "BRAKE-A",
        "mechanical_brake",
        interval_km=10.0,
        source_type="selected_component_manufacturer",
        source_reference="manufacturer-manual-rev-a",
    )
    registry = _registry([_component(), brake])

    due_preflight = _pass_preflight(
        "PREFLIGHT-DUE",
        "2026-10-01T13:00:00Z",
        odometer=10.0,
        hours=0.5,
    )
    report = evaluate(registry, [due_preflight], SNAPSHOT)
    assert report["valid"] is True
    assert report["health_state"] == "SERVICE_REQUIRED"
    assert any("BRAKE-A: interval_km reached" in item for item in report["service_due"])

    service = _event(
        "SERVICE-BRAKE",
        "2026-10-01T13:10:00Z",
        "SERVICE",
        odometer=10.0,
        hours=0.5,
    )
    service["service_actions"] = [
        {
            "component_id": "BRAKE-A",
            "action": "manufacturer-specified service",
            "resets_service_interval": True,
            "source_reference": "manufacturer-manual-rev-a",
            "notes": "",
        }
    ]
    fresh = _pass_preflight(
        "PREFLIGHT-AFTER-SERVICE",
        "2026-10-01T13:20:00Z",
        odometer=11.0,
        hours=0.6,
    )
    report = evaluate(registry, [due_preflight, service, fresh], SNAPSHOT)
    assert report["valid"] is True
    assert report["service_due"] == []
    assert report["health_state"] == "READY_FOR_ALLOWED_ACTIVITY"


def test_declared_interval_without_source_is_invalid():
    component = _component("BEARING-A", "wheel_bearing", interval_hours=5.0)
    report = evaluate(_registry([component]), [_pass_preflight()], SNAPSHOT)

    assert report["valid"] is False
    assert any(
        "sourced service intervals require an accepted source_type" in error
        for error in report["errors"]
    )
    assert any(
        "sourced service intervals require source_reference" in error
        for error in report["errors"]
    )


def test_missing_counter_for_declared_interval_fails_closed_to_inspection():
    component = _component(
        "BEARING-A",
        "wheel_bearing",
        interval_km=10.0,
        source_type="qualified_x1_physical_evidence",
        source_reference="future-qualified-bearing-program",
        installed_km=None,
    )
    preflight = _pass_preflight()
    preflight["odometer_km"] = None

    report = evaluate(_registry([component]), [preflight], SNAPSHOT)
    assert report["valid"] is True
    assert report["health_state"] == "INSPECTION_REQUIRED"
    assert any(
        "BEARING-A: interval_km due state unknown" in item
        for item in report["service_due_state_unknown"]
    )


def test_remote_and_lighting_checks_are_conditionally_required():
    registry = _registry(
        [
            _component(),
            _component("REMOTE-A", "traction_remote"),
        ]
    )
    preflight = _pass_preflight(lights=True)
    preflight["checks"]["remote_deadman_function"]["status"] = "UNSET"

    report = evaluate(registry, [preflight], SNAPSHOT)
    assert report["valid"] is True
    assert report["health_state"] == "INSPECTION_REQUIRED"
    assert any("remote_deadman_function" in x for x in report["preflight_blockers"])

    preflight["checks"]["remote_deadman_function"]["status"] = "PASS"
    report = evaluate(registry, [preflight], SNAPSHOT)
    assert report["health_state"] == "READY_FOR_ALLOWED_ACTIVITY"


def test_component_replacement_creates_new_configuration_lineage():
    registry = _registry(
        [
            _component(),
            _component("BRAKE-A", "mechanical_brake"),
        ]
    )
    replacement = _event(
        "REPLACE-01",
        "2026-10-01T13:00:00Z",
        "COMPONENT_REPLACEMENT",
        odometer=1.0,
        hours=0.2,
    )
    replacement["configuration_change"] = {
        "applied": True,
        "new_configuration_id": "CFG-B",
        "component_changes": [
            {
                "action": "REMOVE",
                "component_id": "BRAKE-A",
            },
            {
                "action": "INSTALL",
                "component": _component(
                    "BRAKE-B",
                    "mechanical_brake",
                    installed_at="2026-10-01T13:00:00Z",
                    installed_km=1.0,
                    installed_hours=0.2,
                ),
            },
        ],
    }

    fresh = _pass_preflight(
        "PREFLIGHT-CFG-B",
        "2026-10-01T13:10:00Z",
        config="CFG-B",
        odometer=1.0,
        hours=0.2,
    )
    report = evaluate(registry, [replacement, fresh], SNAPSHOT)

    assert report["valid"] is True
    assert report["current_configuration_id"] == "CFG-B"
    assert "BRAKE-A" not in report["active_component_ids"]
    assert "BRAKE-B" in report["active_component_ids"]
    assert report["health_state"] == "READY_FOR_ALLOWED_ACTIVITY"


def test_odometer_and_ride_hours_cannot_go_backwards():
    first = _pass_preflight(
        "PREFLIGHT-01",
        "2026-10-01T12:10:00Z",
        odometer=10.0,
        hours=2.0,
    )
    second = _pass_preflight(
        "PREFLIGHT-02",
        "2026-10-01T12:20:00Z",
        odometer=9.0,
        hours=1.5,
    )
    report = evaluate(_registry(), [first, second], SNAPSHOT)

    assert report["valid"] is False
    assert any("odometer_km decreased" in x for x in report["errors"])
    assert any("ride_hours decreased" in x for x in report["errors"])
