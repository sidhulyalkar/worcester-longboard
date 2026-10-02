#!/usr/bin/env python3
"""Evaluate longitudinal Worcester X1 lifecycle health.

This tool evaluates maintenance/inspection state only. A READY result means
ready for an activity that is independently allowed elsewhere. It never grants
powered, public, wet, or dog-accompanied operation authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "hardware/rev_c_lifecycle_health_snapshot_2026-10-01.json"

ALLOWED_SOURCE_TYPES = {
    "selected_component_manufacturer",
    "selected_system_integrator_or_battery_builder",
    "qualified_x1_physical_evidence",
}
ALLOWED_EVENT_TYPES = {
    "BASELINE",
    "PREFLIGHT",
    "POST_ACTIVITY",
    "INSPECTION",
    "SERVICE",
    "COMPONENT_REPLACEMENT",
    "CONTAMINATION_EXPOSURE",
    "IMPACT",
    "FAULT",
    "CONFIGURATION_CHANGE",
}
ALLOWED_CHECK_STATUS = {"PASS", "FAIL", "NA", "UNSET"}
ALLOWED_SEVERITY = {"INFO", "INSPECT", "SERVICE", "STOP"}
SEVERITY_RANK = {"INFO": 0, "INSPECT": 1, "SERVICE": 2, "STOP": 3}
CLOSURE_EVENT_TYPES = {
    "INSPECTION",
    "SERVICE",
    "COMPONENT_REPLACEMENT",
    "CONFIGURATION_CHANGE",
}


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _valid_authority(data: dict, expected: str) -> bool:
    if data.get("authority") != expected or data.get("qualified") is not True:
        return False
    if data.get("powered_operation_authorized") is not False:
        return False
    actual = data.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        return False
    unsigned = dict(data)
    unsigned.pop("authority_fingerprint_sha256", None)
    try:
        return actual == _digest(unsigned)
    except (TypeError, ValueError):
        return False


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _finite_nonnegative(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) >= 0
    )


def _optional_counter(errors: list[str], label: str, value: Any) -> None:
    if value is not None and not _finite_nonnegative(value):
        errors.append(f"{label} must be null or a finite nonnegative number")


def _parse_timestamp(errors: list[str], label: str, value: Any) -> datetime | None:
    if not _nonempty(value):
        errors.append(f"{label} must be a nonempty ISO-8601 timestamp")
        return None
    raw = value.strip()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label} is not valid ISO-8601")
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        errors.append(f"{label} must include a timezone offset")
        return None
    return dt.astimezone(timezone.utc)


def _validate_service_policy(
    errors: list[str],
    component_id: str,
    policy: Any,
) -> None:
    if not isinstance(policy, dict):
        errors.append(f"{component_id}: service_policy must be an object")
        return

    intervals = {
        "interval_km": policy.get("interval_km"),
        "interval_hours": policy.get("interval_hours"),
        "interval_days": policy.get("interval_days"),
    }
    has_interval = False
    for key, value in intervals.items():
        if value is not None:
            has_interval = True
            if not (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(float(value))
                and float(value) > 0
            ):
                errors.append(f"{component_id}: service_policy.{key} must be null or positive")

    source_type = policy.get("source_type")
    source_reference = policy.get("source_reference")
    if has_interval:
        if source_type not in ALLOWED_SOURCE_TYPES:
            errors.append(
                f"{component_id}: sourced service intervals require an accepted source_type"
            )
        if not _nonempty(source_reference):
            errors.append(
                f"{component_id}: sourced service intervals require source_reference"
            )
    else:
        if source_type not in ("", None) and source_type not in ALLOWED_SOURCE_TYPES:
            errors.append(f"{component_id}: invalid service_policy.source_type")


def _validate_component(
    errors: list[str],
    component: Any,
    label: str,
) -> str | None:
    if not isinstance(component, dict):
        errors.append(f"{label} must be an object")
        return None

    component_id = component.get("component_id")
    if not _nonempty(component_id):
        errors.append(f"{label}.component_id must be nonempty")
        return None

    for key in ("subsystem", "role", "manufacturer", "model", "revision"):
        if not _nonempty(component.get(key)):
            errors.append(f"{component_id}: {key} must be nonempty")

    if component.get("active") is not True:
        errors.append(f"{component_id}: baseline/installed component must have active=true")

    _parse_timestamp(errors, f"{component_id}.installed_at_utc", component.get("installed_at_utc"))
    _optional_counter(
        errors,
        f"{component_id}.installed_odometer_km",
        component.get("installed_odometer_km"),
    )
    _optional_counter(
        errors,
        f"{component_id}.installed_ride_hours",
        component.get("installed_ride_hours"),
    )
    _validate_service_policy(errors, component_id, component.get("service_policy"))
    return component_id


def _required_preflight_checks(snapshot: dict, active_components: dict, event: dict) -> list[str]:
    required = list(snapshot["required_preflight_checks"])
    roles = {
        c.get("role")
        for c in active_components.values()
        if c.get("active") is True
    }
    for rule in snapshot["conditional_preflight_checks"]:
        role = rule.get("applies_when_component_role_present")
        if role and role in roles:
            required.append(rule["check_id"])
        if (
            rule.get("applies_when_activity_declares_required") is True
            and event.get("activity_requirements", {}).get("lights_required") is True
        ):
            required.append(rule["check_id"])
    return sorted(set(required))


def _component_due_state(
    component: dict,
    installed_at: datetime | None,
    installed_km: float | None,
    installed_hours: float | None,
    last_reset_at: datetime | None,
    last_reset_km: float | None,
    last_reset_hours: float | None,
    current_at: datetime | None,
    current_km: float | None,
    current_hours: float | None,
) -> tuple[list[str], list[str]]:
    due: list[str] = []
    unknown: list[str] = []
    policy = component.get("service_policy", {})
    component_id = component.get("component_id", "<unknown>")

    baseline_at = last_reset_at or installed_at
    baseline_km = last_reset_km if last_reset_km is not None else installed_km
    baseline_hours = (
        last_reset_hours if last_reset_hours is not None else installed_hours
    )

    interval_km = policy.get("interval_km")
    if interval_km is not None:
        if current_km is None or baseline_km is None:
            unknown.append(f"{component_id}: interval_km due state unknown")
        elif current_km - baseline_km >= float(interval_km):
            due.append(f"{component_id}: interval_km reached")

    interval_hours = policy.get("interval_hours")
    if interval_hours is not None:
        if current_hours is None or baseline_hours is None:
            unknown.append(f"{component_id}: interval_hours due state unknown")
        elif current_hours - baseline_hours >= float(interval_hours):
            due.append(f"{component_id}: interval_hours reached")

    interval_days = policy.get("interval_days")
    if interval_days is not None:
        if current_at is None or baseline_at is None:
            unknown.append(f"{component_id}: interval_days due state unknown")
        else:
            elapsed_days = (current_at - baseline_at).total_seconds() / 86400.0
            if elapsed_days >= float(interval_days):
                due.append(f"{component_id}: interval_days reached")

    return due, unknown


def evaluate(
    registry: dict,
    events: list[dict],
    chassis_authority: dict,
    snapshot: dict | None = None,
) -> dict:
    snapshot = snapshot or json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    errors: list[str] = []

    if registry.get("schema_version") != 1:
        errors.append("registry schema_version must be 1")
    if registry.get("scope") != "x1_vehicle_component_registry":
        errors.append("wrong component registry scope")

    if not _valid_authority(chassis_authority, "x1_rolling_chassis_physical"):
        errors.append(
            "linked rolling-chassis authority must be qualified, "
            "fingerprint-valid, and non-powered"
        )

    upstream = registry.get("upstream_authorities")
    if not isinstance(upstream, dict):
        errors.append("registry upstream_authorities must be an object")
        upstream = {}
    if (
        upstream.get("rolling_chassis_fingerprint_sha256")
        != chassis_authority.get("authority_fingerprint_sha256")
    ):
        errors.append(
            "registry does not link the supplied rolling-chassis authority"
        )

    board_id = registry.get("board_id")
    current_configuration_id = registry.get("configuration_id")
    if not _nonempty(board_id):
        errors.append("registry board_id must be nonempty")
    if not _nonempty(current_configuration_id):
        errors.append("registry configuration_id must be nonempty")

    registry_created_at = _parse_timestamp(
        errors,
        "registry.created_at_utc",
        registry.get("created_at_utc"),
    )

    for key in (
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if registry.get(key) is not False:
            errors.append(f"registry {key} must be false")

    components = registry.get("components")
    if not isinstance(components, list) or not components:
        errors.append("registry components must be a nonempty list")
        components = []

    active_components: dict[str, dict] = {}
    known_component_ids: set[str] = set()
    install_times: dict[str, datetime | None] = {}
    install_km: dict[str, float | None] = {}
    install_hours: dict[str, float | None] = {}
    last_service_at: dict[str, datetime | None] = {}
    last_service_km: dict[str, float | None] = {}
    last_service_hours: dict[str, float | None] = {}

    for index, component in enumerate(components):
        cid = _validate_component(errors, component, f"registry.components[{index}]")
        if cid is None:
            continue
        if cid in known_component_ids:
            errors.append(f"duplicate component_id: {cid}")
            continue
        known_component_ids.add(cid)
        active_components[cid] = dict(component)
        install_times[cid] = _parse_timestamp(
            errors,
            f"{cid}.installed_at_utc",
            component.get("installed_at_utc"),
        )
        install_km[cid] = (
            float(component["installed_odometer_km"])
            if _finite_nonnegative(component.get("installed_odometer_km"))
            else None
        )
        install_hours[cid] = (
            float(component["installed_ride_hours"])
            if _finite_nonnegative(component.get("installed_ride_hours"))
            else None
        )
        last_service_at[cid] = None
        last_service_km[cid] = None
        last_service_hours[cid] = None

    parsed_events: list[tuple[datetime, dict]] = []
    event_ids: set[str] = set()
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"event {index} must be an object")
            continue
        if event.get("schema_version") != 1:
            errors.append(f"event {index}: schema_version must be 1")
        if event.get("scope") != "x1_vehicle_health_event":
            errors.append(f"event {index}: wrong health event scope")

        event_id = event.get("event_id")
        if not _nonempty(event_id):
            errors.append(f"event {index}: event_id must be nonempty")
        elif event_id in event_ids:
            errors.append(f"duplicate event_id: {event_id}")
        else:
            event_ids.add(event_id)

        if event.get("board_id") != board_id:
            errors.append(f"{event_id or index}: board_id does not match registry")

        event_type = event.get("event_type")
        if event_type not in ALLOWED_EVENT_TYPES:
            errors.append(f"{event_id or index}: unsupported event_type")
        if not _nonempty(event.get("activity_type")):
            errors.append(f"{event_id or index}: activity_type must be nonempty")

        for key in (
            "powered_operation_authorized",
            "public_operation_authorized",
            "dog_accompanied_operation_authorized",
        ):
            if event.get(key) is not False:
                errors.append(f"{event_id or index}: {key} must be false")

        _optional_counter(errors, f"{event_id or index}.odometer_km", event.get("odometer_km"))
        _optional_counter(errors, f"{event_id or index}.ride_hours", event.get("ride_hours"))

        dt = _parse_timestamp(
            errors,
            f"{event_id or index}.timestamp_utc",
            event.get("timestamp_utc"),
        )
        if dt is not None:
            if registry_created_at is not None and dt < registry_created_at:
                errors.append(f"{event_id or index}: event predates registry creation")
            parsed_events.append((dt, event))

    parsed_events.sort(key=lambda pair: pair[0])
    for (prev_dt, _), (cur_dt, _) in zip(parsed_events, parsed_events[1:]):
        if cur_dt <= prev_dt:
            errors.append("event timestamps must be unique and strictly increasing")

    open_findings: dict[str, dict] = {}
    all_findings: set[str] = set()
    baseline_event_ids: list[str] = []
    last_seen_km: float | None = None
    last_seen_hours: float | None = None
    latest_event: dict | None = None
    latest_at: datetime | None = None
    latest_km: float | None = None
    latest_hours: float | None = None

    escalation = {
        item["trigger"]: item["minimum_severity"]
        for item in snapshot["automatic_event_escalations"]
    }

    for dt, event in parsed_events:
        latest_event = event
        latest_at = dt
        event_id = event.get("event_id", "<unknown>")
        event_type = event.get("event_type")
        event_config = event.get("configuration_id")
        if event_type == "BASELINE":
            baseline_event_ids.append(event_id)

        if event_config != current_configuration_id:
            errors.append(
                f"{event_id}: configuration_id={event_config!r} does not match "
                f"active configuration {current_configuration_id!r}"
            )

        for cid, installed_at in install_times.items():
            if cid in active_components and installed_at is not None and installed_at > dt:
                errors.append(
                    f"{event_id}: active component {cid} is recorded before its installation timestamp"
                )

        km = event.get("odometer_km")
        hours = event.get("ride_hours")
        current_km = float(km) if _finite_nonnegative(km) else None
        current_hours = float(hours) if _finite_nonnegative(hours) else None

        if current_km is not None:
            if last_seen_km is not None and current_km < last_seen_km:
                errors.append(f"{event_id}: odometer_km decreased")
            last_seen_km = current_km
            latest_km = current_km
        if current_hours is not None:
            if last_seen_hours is not None and current_hours < last_seen_hours:
                errors.append(f"{event_id}: ride_hours decreased")
            last_seen_hours = current_hours
            latest_hours = current_hours

        checks = event.get("checks")
        if not isinstance(checks, dict):
            errors.append(f"{event_id}: checks must be an object")
            checks = {}
        for check_id, entry in checks.items():
            if not isinstance(entry, dict):
                errors.append(f"{event_id}: check {check_id} must be an object")
                continue
            if entry.get("status") not in ALLOWED_CHECK_STATUS:
                errors.append(f"{event_id}: check {check_id} has invalid status")

        findings_opened = event.get("findings_opened")
        if not isinstance(findings_opened, list):
            errors.append(f"{event_id}: findings_opened must be a list")
            findings_opened = []

        opened_by_check: dict[str, list[dict]] = {}
        opened_by_trigger: dict[str, list[dict]] = {}
        for finding in findings_opened:
            if not isinstance(finding, dict):
                errors.append(f"{event_id}: finding must be an object")
                continue
            finding_id = finding.get("finding_id")
            if not _nonempty(finding_id):
                errors.append(f"{event_id}: finding_id must be nonempty")
                continue
            if finding_id in all_findings:
                errors.append(f"{event_id}: duplicate finding_id {finding_id}")
                continue
            all_findings.add(finding_id)

            severity = finding.get("severity")
            if severity not in ALLOWED_SEVERITY:
                errors.append(f"{event_id}/{finding_id}: invalid severity")
                continue

            component_id = finding.get("component_id")
            if component_id not in (None, "", "BOARD") and component_id not in active_components:
                errors.append(
                    f"{event_id}/{finding_id}: unknown or inactive component_id {component_id}"
                )
            if not _nonempty(finding.get("description")):
                errors.append(f"{event_id}/{finding_id}: description must be nonempty")

            source_check = finding.get("source_check_id")
            if _nonempty(source_check):
                opened_by_check.setdefault(source_check, []).append(finding)
            trigger = finding.get("trigger")
            if _nonempty(trigger):
                opened_by_trigger.setdefault(trigger, []).append(finding)

            open_findings[finding_id] = dict(finding)

        for check_id, entry in checks.items():
            if isinstance(entry, dict) and entry.get("status") == "FAIL":
                linked = opened_by_check.get(check_id, [])
                if not linked or max(SEVERITY_RANK.get(x.get("severity"), -1) for x in linked) < SEVERITY_RANK["INSPECT"]:
                    errors.append(
                        f"{event_id}: failed check {check_id} requires an INSPECT-or-higher finding"
                    )

        observed_triggers = event.get("observed_triggers")
        if not isinstance(observed_triggers, list):
            errors.append(f"{event_id}: observed_triggers must be a list")
            observed_triggers = []
        for trigger in observed_triggers:
            if trigger not in escalation:
                errors.append(f"{event_id}: unknown observed trigger {trigger}")
                continue
            linked = opened_by_trigger.get(trigger, [])
            min_rank = SEVERITY_RANK[escalation[trigger]]
            if not linked or max(SEVERITY_RANK.get(x.get("severity"), -1) for x in linked) < min_rank:
                errors.append(
                    f"{event_id}: trigger {trigger} requires a finding at severity "
                    f"{escalation[trigger]} or higher"
                )

        findings_closed = event.get("findings_closed")
        if not isinstance(findings_closed, list):
            errors.append(f"{event_id}: findings_closed must be a list")
            findings_closed = []
        if findings_closed and event_type not in CLOSURE_EVENT_TYPES:
            errors.append(
                f"{event_id}: findings may close only during inspection/service/"
                "component-replacement/configuration-change events"
            )
        for closure in findings_closed:
            if not isinstance(closure, dict):
                errors.append(f"{event_id}: finding closure must be an object")
                continue
            finding_id = closure.get("finding_id")
            if finding_id not in open_findings:
                errors.append(
                    f"{event_id}: cannot close non-open finding {finding_id!r}"
                )
                continue
            if not _nonempty(closure.get("closure_action")):
                errors.append(
                    f"{event_id}/{finding_id}: closure_action must be nonempty"
                )
            if not _nonempty(closure.get("verification")):
                errors.append(
                    f"{event_id}/{finding_id}: verification must be nonempty"
                )
            open_findings.pop(finding_id, None)

        service_actions = event.get("service_actions")
        if not isinstance(service_actions, list):
            errors.append(f"{event_id}: service_actions must be a list")
            service_actions = []
        for action in service_actions:
            if not isinstance(action, dict):
                errors.append(f"{event_id}: service action must be an object")
                continue
            component_id = action.get("component_id")
            if component_id not in active_components:
                errors.append(
                    f"{event_id}: service action references unknown/inactive component {component_id}"
                )
                continue
            if not _nonempty(action.get("action")):
                errors.append(f"{event_id}: service action requires action text")
            if action.get("resets_service_interval") is True:
                policy = active_components[component_id].get("service_policy", {})
                has_sourced_interval = any(
                    policy.get(key) is not None
                    for key in ("interval_km", "interval_hours", "interval_days")
                )
                if not has_sourced_interval:
                    errors.append(
                        f"{event_id}: cannot reset service interval for "
                        f"{component_id} because no interval is declared"
                    )
                if not _nonempty(action.get("source_reference")):
                    errors.append(
                        f"{event_id}: resetting service interval for "
                        f"{component_id} requires source_reference"
                    )
                last_service_at[component_id] = dt
                last_service_km[component_id] = current_km
                last_service_hours[component_id] = current_hours

        change = event.get("configuration_change")
        if not isinstance(change, dict):
            errors.append(f"{event_id}: configuration_change must be an object")
            change = {"applied": False}

        if change.get("applied") is True:
            if event_type not in {"CONFIGURATION_CHANGE", "COMPONENT_REPLACEMENT"}:
                errors.append(
                    f"{event_id}: configuration changes require CONFIGURATION_CHANGE "
                    "or COMPONENT_REPLACEMENT event_type"
                )
            new_config = change.get("new_configuration_id")
            if not _nonempty(new_config) or new_config == current_configuration_id:
                errors.append(
                    f"{event_id}: configuration change requires a new nonempty configuration_id"
                )
            component_changes = change.get("component_changes")
            if not isinstance(component_changes, list) or not component_changes:
                errors.append(
                    f"{event_id}: applied configuration change requires component_changes"
                )
                component_changes = []

            for cindex, item in enumerate(component_changes):
                if not isinstance(item, dict):
                    errors.append(
                        f"{event_id}: component change {cindex} must be an object"
                    )
                    continue
                action = item.get("action")
                if action == "REMOVE":
                    cid = item.get("component_id")
                    if cid not in active_components:
                        errors.append(
                            f"{event_id}: cannot remove unknown/inactive component {cid}"
                        )
                    else:
                        active_components.pop(cid, None)
                elif action == "INSTALL":
                    component = item.get("component")
                    cid = _validate_component(
                        errors,
                        component,
                        f"{event_id}.component_changes[{cindex}].component",
                    )
                    if cid is None:
                        continue
                    if cid in known_component_ids:
                        errors.append(
                            f"{event_id}: installed component_id has already existed: {cid}"
                        )
                        continue
                    known_component_ids.add(cid)
                    active_components[cid] = dict(component)
                    install_times[cid] = _parse_timestamp(
                        errors,
                        f"{cid}.installed_at_utc",
                        component.get("installed_at_utc"),
                    )
                    if install_times[cid] is not None and install_times[cid] > dt:
                        errors.append(
                            f"{event_id}: installed component {cid} has an installation "
                            "timestamp after the configuration-change event"
                        )
                    install_km[cid] = (
                        float(component["installed_odometer_km"])
                        if _finite_nonnegative(component.get("installed_odometer_km"))
                        else current_km
                    )
                    install_hours[cid] = (
                        float(component["installed_ride_hours"])
                        if _finite_nonnegative(component.get("installed_ride_hours"))
                        else current_hours
                    )
                    last_service_at[cid] = None
                    last_service_km[cid] = None
                    last_service_hours[cid] = None
                else:
                    errors.append(
                        f"{event_id}: component change action must be INSTALL or REMOVE"
                    )
            if _nonempty(new_config):
                current_configuration_id = new_config
        else:
            if change.get("component_changes") not in ([], None):
                errors.append(
                    f"{event_id}: component_changes must be empty when applied=false"
                )

    baseline_errors: list[str] = []
    if len(baseline_event_ids) == 0:
        baseline_errors.append("BASELINE event is required before READY state")
    elif len(baseline_event_ids) > 1:
        errors.append(
            f"exactly one BASELINE event is allowed, found {len(baseline_event_ids)}"
        )
    elif parsed_events and parsed_events[0][1].get("event_type") != "BASELINE":
        errors.append("BASELINE must be the first health event")

    current_at = latest_at
    due_items: list[str] = []
    due_unknown: list[str] = []
    for cid, component in active_components.items():
        due, unknown = _component_due_state(
            component,
            install_times.get(cid),
            install_km.get(cid),
            install_hours.get(cid),
            last_service_at.get(cid),
            last_service_km.get(cid),
            last_service_hours.get(cid),
            current_at,
            latest_km,
            latest_hours,
        )
        due_items.extend(due)
        due_unknown.extend(unknown)

    preflight_errors: list[str] = list(baseline_errors)
    preflight_complete = False
    if latest_event is None:
        preflight_errors.append("no health events recorded")
    elif latest_event.get("event_type") != "PREFLIGHT":
        preflight_errors.append("latest event is not a PREFLIGHT")
    elif latest_event.get("configuration_id") != current_configuration_id:
        preflight_errors.append("latest PREFLIGHT is not for the current configuration")
    else:
        required = _required_preflight_checks(
            snapshot,
            active_components,
            latest_event,
        )
        checks = latest_event.get("checks", {})
        for check_id in required:
            status = checks.get(check_id, {}).get("status")
            if status != "PASS":
                preflight_errors.append(
                    f"required preflight check not PASS: {check_id}"
                )
        preflight_complete = not preflight_errors

    open_blockers = [
        finding
        for finding in open_findings.values()
        if finding.get("severity") in {"INSPECT", "SERVICE", "STOP"}
    ]
    max_open_rank = max(
        (SEVERITY_RANK[f["severity"]] for f in open_blockers),
        default=0,
    )

    if errors:
        health_state = None
        ready = False
    elif max_open_rank >= SEVERITY_RANK["STOP"]:
        health_state = "STOP_USE"
        ready = False
    elif max_open_rank >= SEVERITY_RANK["SERVICE"] or due_items:
        health_state = "SERVICE_REQUIRED"
        ready = False
    elif (
        max_open_rank >= SEVERITY_RANK["INSPECT"]
        or due_unknown
        or not preflight_complete
    ):
        health_state = "INSPECTION_REQUIRED"
        ready = False
    else:
        health_state = "READY_FOR_ALLOWED_ACTIVITY"
        ready = True

    report = {
        "schema_version": 1,
        "authority": "x1_lifecycle_health_state",
        "valid": not errors,
        "errors": errors,
        "board_id": board_id,
        "rolling_chassis_fingerprint_sha256": chassis_authority.get(
            "authority_fingerprint_sha256"
        ),
        "current_configuration_id": current_configuration_id,
        "active_component_ids": sorted(active_components),
        "event_count": len(parsed_events),
        "baseline_recorded": len(baseline_event_ids) == 1,
        "baseline_event_id": (
            baseline_event_ids[0] if len(baseline_event_ids) == 1 else None
        ),
        "latest_event_id": (
            latest_event.get("event_id") if latest_event is not None else None
        ),
        "latest_event_timestamp_utc": (
            latest_at.isoformat().replace("+00:00", "Z")
            if latest_at is not None
            else None
        ),
        "latest_odometer_km": latest_km,
        "latest_ride_hours": latest_hours,
        "open_findings": sorted(
            open_findings.values(),
            key=lambda x: (
                -SEVERITY_RANK.get(x.get("severity"), -1),
                x.get("finding_id", ""),
            ),
        ),
        "service_due": sorted(due_items),
        "service_due_state_unknown": sorted(due_unknown),
        "preflight_complete": preflight_complete,
        "preflight_blockers": preflight_errors,
        "health_state": health_state,
        "ready_for_allowed_activity": ready,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": (
            "READY_FOR_ALLOWED_ACTIVITY means only that lifecycle health checks "
            "passed for the current recorded configuration. The intended activity "
            "must still be independently permitted by Worcester X1 build, venue, "
            "public-use, environmental, and companion authorities."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", type=Path)
    parser.add_argument("--event", type=Path, action="append", default=[])
    parser.add_argument("--rolling-chassis-authority", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    events = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in args.event
    ]
    chassis_authority = json.loads(
        args.rolling_chassis_authority.read_text(encoding="utf-8")
    )
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    report = evaluate(registry, events, chassis_authority, snapshot)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
