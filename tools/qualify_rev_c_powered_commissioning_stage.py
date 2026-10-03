#!/usr/bin/env python3
"""Qualify one staged Worcester X1 powered-commissioning step.

The output qualifies only the declared commissioning stage. Even Stage 4 does
not authorize general powered operation, public operation, or dog-accompanied
operation.
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
SNAPSHOT = ROOT / "hardware/rev_c_powered_commissioning_snapshot_2026-10-01.json"

LIMIT_KEYS = (
    "max_commanded_speed_mps",
    "max_motor_phase_current_a",
    "max_battery_current_a",
    "max_pack_voltage_v",
    "max_motor_erpm",
    "max_motor_temperature_c",
    "max_controller_temperature_c",
)

POST_STAGE_TRUE = (
    "critical_witness_marks_unchanged",
    "wheel_retention_unchanged",
    "structural_damage_absent",
    "harness_brake_guard_clearance_intact",
    "abnormal_heat_or_odor_absent",
    "fresh_lifecycle_health_recorded",
)


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _valid_fp(data: dict) -> bool:
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


def _positive(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0
    )


def _parse_timestamp(errors: list[str], label: str, value: Any) -> datetime | None:
    if not _nonempty(value):
        errors.append(f"{label} must be a nonempty ISO-8601 timestamp")
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label} is not valid ISO-8601")
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        errors.append(f"{label} must include a timezone offset")
        return None
    return dt.astimezone(timezone.utc)


def _stage_map(snapshot: dict) -> dict[str, dict]:
    return {
        stage["stage_id"]: stage
        for stage in snapshot.get("stages", [])
        if isinstance(stage, dict) and _nonempty(stage.get("stage_id"))
    }


def _validate_power_architecture(errors: list[str], data: dict) -> None:
    if data.get("authority") != "x1_power_architecture":
        errors.append("power architecture authority must be x1_power_architecture")
    if data.get("qualified") is not True:
        errors.append("power architecture must be qualified")
    if not _valid_fp(data):
        errors.append("power architecture fingerprint is invalid")


def _validate_health(
    errors: list[str],
    data: dict,
    *,
    board_id: str,
    configuration_id: str,
    label: str,
) -> None:
    if data.get("authority") != "x1_lifecycle_health_state":
        errors.append(f"{label} must be x1_lifecycle_health_state")
    if data.get("valid") is not True:
        errors.append(f"{label} must be valid")
    if data.get("health_state") != "READY_FOR_ALLOWED_ACTIVITY":
        errors.append(f"{label} health_state must be READY_FOR_ALLOWED_ACTIVITY")
    if data.get("ready_for_allowed_activity") is not True:
        errors.append(f"{label} must be ready_for_allowed_activity")
    if data.get("board_id") != board_id:
        errors.append(f"{label} board_id mismatch")
    if data.get("current_configuration_id") != configuration_id:
        errors.append(f"{label} configuration_id mismatch")
    if data.get("powered_operation_authorized") is not False:
        errors.append(f"{label} cannot authorize powered operation")
    if data.get("public_operation_authorized") is not False:
        errors.append(f"{label} cannot authorize public operation")
    if data.get("dog_accompanied_operation_authorized") is not False:
        errors.append(f"{label} cannot authorize dog-accompanied operation")
    if not _valid_fp(data):
        errors.append(f"{label} fingerprint is invalid")


def _validate_previous_stage(
    errors: list[str],
    data: dict,
    *,
    expected_index: int,
    board_id: str,
    configuration_id: str,
    power_arch_fp: str,
) -> None:
    if data.get("authority") != "x1_powered_commissioning_stage":
        errors.append("previous stage authority has wrong type")
    if data.get("qualified") is not True:
        errors.append("previous commissioning stage is not qualified")
    if data.get("stage_index") != expected_index:
        errors.append(
            f"previous stage index must be {expected_index}, "
            f"found {data.get('stage_index')!r}"
        )
    if data.get("board_id") != board_id:
        errors.append("previous stage board_id mismatch")
    if data.get("configuration_id") != configuration_id:
        errors.append("previous stage configuration_id mismatch")
    if data.get("power_architecture_fingerprint_sha256") != power_arch_fp:
        errors.append("previous stage power-architecture lineage mismatch")
    if data.get("general_powered_operation_authorized") is not False:
        errors.append("previous stage cannot authorize general powered operation")
    if not _valid_fp(data):
        errors.append("previous stage fingerprint is invalid")


def _validate_venue(errors: list[str], data: dict) -> None:
    if data.get("authority") != "x1_powered_test_venue_evidence":
        errors.append("venue authority has wrong type")
    if data.get("qualified") is not True:
        errors.append("venue authority is not qualified")
    if data.get("venue_permission_qualified") is not True:
        errors.append("venue permission is not qualified")
    if data.get("vehicle_powered_operation_authority") is not False:
        errors.append("venue evidence cannot authorize powered operation")
    if data.get("public_operation_authority") is not False:
        errors.append("venue evidence cannot authorize public operation")
    if data.get("dog_accompanied_operation_authority") is not False:
        errors.append("venue evidence cannot authorize dog-accompanied operation")
    if not _valid_fp(data):
        errors.append("venue authority fingerprint is invalid")


def _validate_telemetry_replay(
    errors: list[str],
    data: dict,
    *,
    board_id: str,
    configuration_id: str,
    stage_id: str,
    power_arch_fp: str,
    required_metrics: list[str],
) -> None:
    if data.get("authority") != "x1_commissioning_telemetry_replay":
        errors.append("telemetry replay has wrong authority type")
    if data.get("qualified") is not True:
        errors.append("telemetry replay is not qualified")
    if data.get("board_id") != board_id:
        errors.append("telemetry replay board_id mismatch")
    if data.get("configuration_id") != configuration_id:
        errors.append("telemetry replay configuration_id mismatch")
    if data.get("commissioning_stage_id") != stage_id:
        errors.append("telemetry replay stage_id mismatch")
    if data.get("power_architecture_fingerprint_sha256") != power_arch_fp:
        errors.append("telemetry replay power-architecture lineage mismatch")
    if data.get("powered_operation_authorized") is not False:
        errors.append("telemetry replay cannot authorize powered operation")
    if data.get("public_operation_authorized") is not False:
        errors.append("telemetry replay cannot authorize public operation")
    if data.get("dog_accompanied_operation_authorized") is not False:
        errors.append("telemetry replay cannot authorize dog-accompanied operation")
    if data.get("synthetic_fixture") is True:
        errors.append("synthetic telemetry replay cannot qualify physical commissioning")
    if data.get("physical_evidence_eligible") is not True:
        errors.append("telemetry replay is not eligible as physical evidence")
    if not _valid_fp(data):
        errors.append("telemetry replay fingerprint is invalid")

    metric_ids = set(data.get("metric_ids", []))
    missing = sorted(set(required_metrics) - metric_ids)
    if missing:
        errors.append(f"telemetry replay missing required metrics: {missing}")


def _validate_measurements(
    errors: list[str],
    measurements: Any,
    required: list[str],
    telemetry_replay: dict | None = None,
) -> None:
    if not isinstance(measurements, list):
        errors.append("measurements must be a list")
        return

    by_id: dict[str, dict] = {}
    for index, item in enumerate(measurements):
        if not isinstance(item, dict):
            errors.append(f"measurement {index} must be an object")
            continue
        metric_id = item.get("metric_id")
        if not _nonempty(metric_id):
            errors.append(f"measurement {index} requires metric_id")
            continue
        if metric_id in by_id:
            errors.append(f"duplicate measurement metric_id: {metric_id}")
            continue
        by_id[metric_id] = item
        if not _nonempty(item.get("unit")):
            errors.append(f"{metric_id}: measurement unit must be nonempty")
        if not _nonempty(item.get("source")):
            errors.append(f"{metric_id}: measurement source must be nonempty")

        value = item.get("value")
        evidence_ref = item.get("evidence_ref")
        numeric_ok = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )
        if not numeric_ok and not _nonempty(evidence_ref):
            errors.append(
                f"{metric_id}: measurement requires finite value or evidence_ref"
            )

    replay_by_id = {}
    if telemetry_replay is not None:
        replay_by_id = {
            item.get("metric_id"): item
            for item in telemetry_replay.get("metrics", [])
            if isinstance(item, dict) and _nonempty(item.get("metric_id"))
        }

    for metric_id in required:
        if metric_id not in by_id:
            errors.append(f"required measurement missing: {metric_id}")
            continue

        if telemetry_replay is None:
            continue

        replay_item = replay_by_id.get(metric_id)
        if replay_item is None:
            errors.append(
                f"required measurement has no telemetry replay metric: {metric_id}"
            )
            continue

        item = by_id[metric_id]
        if item.get("source") != "x1_commissioning_telemetry_replay":
            errors.append(
                f"{metric_id}: measurement source must be x1_commissioning_telemetry_replay"
            )
        if item.get("evidence_ref") != replay_item.get("evidence_ref"):
            errors.append(
                f"{metric_id}: measurement evidence_ref does not match telemetry replay"
            )
        if item.get("unit") != replay_item.get("unit"):
            errors.append(
                f"{metric_id}: measurement unit does not match telemetry replay"
            )

        replay_value = replay_item.get("value")
        value = item.get("value")
        if (
            replay_value is not None
            and isinstance(replay_value, (int, float))
            and not isinstance(replay_value, bool)
            and math.isfinite(float(replay_value))
        ):
            if not (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(float(value))
                and math.isclose(
                    float(value),
                    float(replay_value),
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                )
            ):
                errors.append(
                    f"{metric_id}: measurement value does not match telemetry replay"
                )


def qualify(
    manifest: dict,
    power_architecture: dict,
    pre_health: dict,
    *,
    previous_stage: dict | None = None,
    post_health: dict | None = None,
    venue: dict | None = None,
    telemetry_replay: dict | None = None,
    snapshot: dict | None = None,
) -> dict:
    snapshot = snapshot or json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    errors: list[str] = []

    if manifest.get("schema_version") != 1:
        errors.append("manifest schema_version must be 1")
    if manifest.get("scope") != "rev_c_powered_commissioning_stage_trial":
        errors.append("wrong powered commissioning manifest scope")

    stages = _stage_map(snapshot)
    stage_id = manifest.get("stage_id")
    stage = stages.get(stage_id)
    if stage is None:
        errors.append(f"unknown stage_id: {stage_id!r}")
        stage = {
            "stage_index": -1,
            "required_checks": [],
            "required_measurements": [],
            "energized": False,
            "free_ground_travel": False,
            "rider_present": False,
            "dog_present": False,
            "venue_authority_required": False,
            "previous_stage_required": False,
            "post_stage_ready_health_required": False,
        }

    for key in ("session_id", "board_id", "configuration_id"):
        if not _nonempty(manifest.get(key)):
            errors.append(f"{key} must be a nonempty string")

    board_id = manifest.get("board_id")
    configuration_id = manifest.get("configuration_id")

    started = _parse_timestamp(errors, "started_at_utc", manifest.get("started_at_utc"))
    completed = _parse_timestamp(
        errors, "completed_at_utc", manifest.get("completed_at_utc")
    )
    if started is not None and completed is not None and completed < started:
        errors.append("completed_at_utc must not precede started_at_utc")

    for key in (
        "general_powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if manifest.get(key) is not False:
            errors.append(f"{key} must be false")

    if manifest.get("public_area") is not False:
        errors.append("public_area must be false")
    if manifest.get("independent_mechanical_brake_available") is not True:
        errors.append("independent_mechanical_brake_available must be true")
    if manifest.get("emergency_power_removal_available") is not True:
        errors.append("emergency_power_removal_available must be true")

    for key in ("energized", "free_ground_travel", "rider_present", "dog_present"):
        if manifest.get(key) is not stage.get(key):
            errors.append(
                f"{key} must be {stage.get(key)!r} for stage {stage_id}"
            )

    if manifest.get("dog_present") is not False:
        errors.append("dog_present must remain false for all commissioning stages")

    _validate_power_architecture(errors, power_architecture)
    power_fp = power_architecture.get("authority_fingerprint_sha256")
    if manifest.get("power_architecture_fingerprint_sha256") != power_fp:
        errors.append("manifest power_architecture_fingerprint_sha256 mismatch")

    _validate_health(
        errors,
        pre_health,
        board_id=board_id,
        configuration_id=configuration_id,
        label="pre-health",
    )
    pre_fp = pre_health.get("authority_fingerprint_sha256")
    if manifest.get("pre_lifecycle_health_fingerprint_sha256") != pre_fp:
        errors.append("manifest pre-health fingerprint mismatch")

    pre_health_time = _parse_timestamp(
        errors,
        "pre-health latest_event_timestamp_utc",
        pre_health.get("latest_event_timestamp_utc"),
    )
    if pre_health_time is not None and started is not None and pre_health_time > started:
        errors.append("pre-health event timestamp cannot be after stage start")

    stage_index = int(stage.get("stage_index", -1))
    previous_required = stage.get("previous_stage_required") is True
    if previous_required:
        if previous_stage is None:
            errors.append("previous stage authority is required")
        else:
            _validate_previous_stage(
                errors,
                previous_stage,
                expected_index=stage_index - 1,
                board_id=board_id,
                configuration_id=configuration_id,
                power_arch_fp=power_fp,
            )
            previous_fp = previous_stage.get("authority_fingerprint_sha256")
            if manifest.get("previous_stage_fingerprint_sha256") != previous_fp:
                errors.append("manifest previous-stage fingerprint mismatch")
            expected_pre = previous_stage.get(
                "post_lifecycle_health_fingerprint_sha256"
            )
            if expected_pre != pre_fp:
                errors.append(
                    "pre-health fingerprint must equal previous stage post-health"
                )
    else:
        if previous_stage is not None:
            errors.append("Stage 0 must not supply a previous stage authority")
        if manifest.get("previous_stage_fingerprint_sha256") not in ("", None):
            errors.append("Stage 0 previous_stage_fingerprint_sha256 must be empty")

    venue_required = stage.get("venue_authority_required") is True
    if venue_required:
        if venue is None:
            errors.append("qualified venue authority is required")
        else:
            _validate_venue(errors, venue)
            venue_fp = venue.get("authority_fingerprint_sha256")
            if manifest.get("venue_authority_fingerprint_sha256") != venue_fp:
                errors.append("manifest venue-authority fingerprint mismatch")
    else:
        if venue is not None:
            errors.append(f"venue authority is not used by stage {stage_id}")
        if manifest.get("venue_authority_fingerprint_sha256") not in ("", None):
            errors.append(
                f"venue_authority_fingerprint_sha256 must be empty for stage {stage_id}"
            )

    limits = manifest.get("declared_stage_limits")
    if not isinstance(limits, dict):
        errors.append("declared_stage_limits must be an object")
    else:
        if not _nonempty(limits.get("source_reference")):
            errors.append("declared_stage_limits.source_reference must be nonempty")
        for key in LIMIT_KEYS:
            if not _positive(limits.get(key)):
                errors.append(f"declared_stage_limits.{key} must be positive")

    checks = manifest.get("checks")
    if not isinstance(checks, dict):
        errors.append("checks must be an object")
        checks = {}
    for check_id in stage.get("required_checks", []):
        item = checks.get(check_id)
        if not isinstance(item, dict) or item.get("status") != "PASS":
            errors.append(f"required stage check not PASS: {check_id}")

    required_measurements = list(stage.get("required_measurements", []))
    telemetry_required = stage.get("telemetry_replay_required") is True
    if telemetry_required:
        if telemetry_replay is None:
            errors.append("fingerprinted telemetry replay is required for this stage")
        else:
            _validate_telemetry_replay(
                errors,
                telemetry_replay,
                board_id=board_id,
                configuration_id=configuration_id,
                stage_id=stage_id,
                power_arch_fp=power_fp,
                required_metrics=required_measurements,
            )
            replay_fp = telemetry_replay.get("authority_fingerprint_sha256")
            if manifest.get("telemetry_replay_fingerprint_sha256") != replay_fp:
                errors.append("manifest telemetry replay fingerprint mismatch")
    else:
        if telemetry_replay is not None:
            errors.append("Stage 0 must not supply telemetry replay evidence")
        if manifest.get("telemetry_replay_fingerprint_sha256") not in ("", None):
            errors.append(
                "Stage 0 telemetry_replay_fingerprint_sha256 must be empty"
            )

    _validate_measurements(
        errors,
        manifest.get("measurements"),
        required_measurements,
        telemetry_replay=telemetry_replay if telemetry_required else None,
    )

    stop_conditions = manifest.get("stop_conditions_observed")
    if not isinstance(stop_conditions, list):
        errors.append("stop_conditions_observed must be a list")
    elif stop_conditions:
        errors.append("stage cannot qualify with observed stop conditions")

    anomalies = manifest.get("anomalies")
    if not isinstance(anomalies, list):
        errors.append("anomalies must be a list")
    elif anomalies:
        errors.append("stage cannot qualify with unresolved anomalies")

    post_required = stage.get("post_stage_ready_health_required") is True
    post = manifest.get("post_stage")
    if not isinstance(post, dict):
        errors.append("post_stage must be an object")
        post = {}

    if post_required:
        for key in POST_STAGE_TRUE:
            if post.get(key) is not True:
                errors.append(f"post_stage.{key} must be true")

        if post_health is None:
            errors.append("post-health READY state is required")
            post_fp = None
        else:
            _validate_health(
                errors,
                post_health,
                board_id=board_id,
                configuration_id=configuration_id,
                label="post-health",
            )
            post_fp = post_health.get("authority_fingerprint_sha256")
            if manifest.get("post_lifecycle_health_fingerprint_sha256") != post_fp:
                errors.append("manifest post-health fingerprint mismatch")
            if post_fp == pre_fp:
                errors.append("post-health fingerprint must differ from pre-health")

            post_health_time = _parse_timestamp(
                errors,
                "post-health latest_event_timestamp_utc",
                post_health.get("latest_event_timestamp_utc"),
            )
            if (
                post_health_time is not None
                and completed is not None
                and post_health_time <= completed
            ):
                errors.append(
                    "post-health latest event must be after stage completion"
                )
    else:
        if post_health is not None:
            errors.append("Stage 0 does not require a separate post-health report")
        post_fp = pre_fp
        if manifest.get("post_lifecycle_health_fingerprint_sha256") not in (
            "",
            None,
            pre_fp,
        ):
            errors.append(
                "Stage 0 post-health fingerprint must be empty or equal pre-health"
            )

    qualified = not errors
    report = {
        "schema_version": 1,
        "authority": "x1_powered_commissioning_stage",
        "qualified": qualified,
        "errors": errors,
        "issue": 45,
        "stage_index": stage_index,
        "stage_id": stage_id,
        "stage_name": stage.get("name"),
        "session_id": manifest.get("session_id"),
        "board_id": board_id,
        "configuration_id": configuration_id,
        "started_at_utc": manifest.get("started_at_utc"),
        "completed_at_utc": manifest.get("completed_at_utc"),
        "power_architecture_fingerprint_sha256": power_fp,
        "pre_lifecycle_health_fingerprint_sha256": pre_fp,
        "post_lifecycle_health_fingerprint_sha256": post_fp,
        "previous_stage_fingerprint_sha256": (
            previous_stage.get("authority_fingerprint_sha256")
            if previous_stage is not None
            else None
        ),
        "venue_authority_fingerprint_sha256": (
            venue.get("authority_fingerprint_sha256")
            if venue is not None
            else None
        ),
        "telemetry_replay_fingerprint_sha256": (
            telemetry_replay.get("authority_fingerprint_sha256")
            if telemetry_replay is not None
            else None
        ),
        "telemetry_session_fingerprint_sha256": (
            telemetry_replay.get("telemetry_session_fingerprint_sha256")
            if telemetry_replay is not None
            else None
        ),
        "commissioning_stage_completed": qualified,
        "energized_stage_completed": qualified and stage.get("energized") is True,
        "free_ground_travel_stage_completed": (
            qualified and stage.get("free_ground_travel") is True
        ),
        "rider_stage_completed": (
            qualified and stage.get("rider_present") is True
        ),
        "general_powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": (
            "A passing report qualifies only this staged commissioning activity "
            "for the exact recorded configuration lineage. It does not authorize "
            "normal powered riding, public operation, or dog-accompanied operation."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--power-architecture", type=Path, required=True)
    parser.add_argument("--pre-health-state", type=Path, required=True)
    parser.add_argument("--previous-stage", type=Path)
    parser.add_argument("--post-health-state", type=Path)
    parser.add_argument("--venue-authority", type=Path)
    parser.add_argument("--telemetry-replay", type=Path)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    def load(path: Path | None) -> dict | None:
        if path is None:
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    report = qualify(
        load(args.manifest),
        load(args.power_architecture),
        load(args.pre_health_state),
        previous_stage=load(args.previous_stage),
        post_health=load(args.post_health_state),
        venue=load(args.venue_authority),
        telemetry_replay=load(args.telemetry_replay),
        snapshot=load(args.snapshot),
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["qualified"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
