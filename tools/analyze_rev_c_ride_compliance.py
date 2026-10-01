#!/usr/bin/env python3
"""Analyze low-energy Worcester X1 ride-compliance trials.

The tool is intentionally non-authoritative. It compares repeated, speed-matched
unpowered trials using objective IMU/speed metrics. It does not infer comfort,
safety, or a preferred configuration.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any

REQUIRED_COLUMNS = (
    "time_s",
    "speed_mps",
    "accel_z_mps2",
    "gyro_roll_dps",
    "gyro_yaw_dps",
)

REQUIRED_OBSERVATION_COLUMNS = (
    "run_id",
    "config_id",
    "carve_response",
    "trail_chatter",
    "recentering",
    "steering_effort",
    "stability",
    "foot_fatigue",
    "confidence",
    "emergency_stepoff_ok",
)

SETTING_KEYS = (
    "chassis_id",
    "tire_family",
    "tire_pressure_front_kpa",
    "tire_pressure_rear_kpa",
    "shock_block_id",
    "shock_block_position",
    "wheelbase_mm",
    "deck_id",
    "footbed_id",
)

PRIMARY_VARIABLE_SETTINGS = {
    "tire_pressure": {"tire_pressure_front_kpa", "tire_pressure_rear_kpa"},
    "shock_block_position": {"shock_block_position"},
    "shock_block_hardness": {"shock_block_id"},
    "wheelbase": {"wheelbase_mm"},
    "tire_family": {"tire_family"},
    "footbed": {"footbed_id"},
}


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _rms(values: list[float]) -> float:
    return math.sqrt(sum(v * v for v in values) / len(values))


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _median(values: list[float]) -> float:
    return float(statistics.median(values))


def _correlation(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or len(a) < 2:
        return None
    mean_a = statistics.fmean(a)
    mean_b = statistics.fmean(b)
    da = [x - mean_a for x in a]
    db = [x - mean_b for x in b]
    denom_a = math.sqrt(sum(x * x for x in da))
    denom_b = math.sqrt(sum(x * x for x in db))
    if denom_a == 0 or denom_b == 0:
        return None
    return sum(x * y for x, y in zip(da, db)) / (denom_a * denom_b)


def _pct_delta(value: float, baseline: float) -> float | None:
    if baseline == 0:
        return None
    return round((value / baseline - 1.0) * 100.0, 2)


def _load_csv(path: Path) -> tuple[list[dict[str, float]], list[str]]:
    errors: list[str] = []
    rows: list[dict[str, float]] = []
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                return [], [f"{path}: missing CSV header"]
            missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
            if missing:
                return [], [f"{path}: missing columns {', '.join(missing)}"]
            for line_no, raw in enumerate(reader, start=2):
                parsed: dict[str, float] = {}
                for column in REQUIRED_COLUMNS:
                    try:
                        value = float(raw[column])
                    except (TypeError, ValueError):
                        errors.append(f"{path}:{line_no}: invalid {column}")
                        break
                    if not math.isfinite(value):
                        errors.append(f"{path}:{line_no}: non-finite {column}")
                        break
                    parsed[column] = value
                else:
                    rows.append(parsed)
    except OSError as exc:
        errors.append(f"{path}: {exc}")
    return rows, errors


def _load_observations(path: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    errors: list[str] = []
    observations: dict[str, dict[str, str]] = {}
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                return {}, [f"{path}: missing CSV header"]
            missing = [
                column
                for column in REQUIRED_OBSERVATION_COLUMNS
                if column not in reader.fieldnames
            ]
            if missing:
                return {}, [
                    f"{path}: missing observation columns {', '.join(missing)}"
                ]
            for line_no, row in enumerate(reader, start=2):
                run_id = str(row.get("run_id", "")).strip()
                if not run_id:
                    errors.append(f"{path}:{line_no}: missing run_id")
                    continue
                if run_id in observations:
                    errors.append(f"{path}:{line_no}: duplicate run_id {run_id}")
                    continue
                observations[run_id] = {
                    key: str(row.get(key, "")).strip()
                    for key in reader.fieldnames
                    if key is not None
                }
    except OSError as exc:
        errors.append(f"{path}: {exc}")
    return observations, errors


def _analyze_run(
    run: dict,
    *,
    base_dir: Path,
    target_speed_mps: float,
    speed_tolerance_fraction: float,
    minimum_samples: int,
    minimum_duration_s: float,
    max_within_run_speed_std_fraction: float,
) -> dict:
    errors: list[str] = []
    csv_path = base_dir / str(run.get("csv_path", ""))
    rows, csv_errors = _load_csv(csv_path)
    errors.extend(csv_errors)

    if len(rows) < minimum_samples:
        errors.append(
            f"run {run.get('id')}: {len(rows)} samples < minimum {minimum_samples}"
        )

    if rows:
        times = [row["time_s"] for row in rows]
        if any(b <= a for a, b in zip(times, times[1:])):
            errors.append(f"run {run.get('id')}: time_s must be strictly increasing")
        duration = times[-1] - times[0]
        if duration < minimum_duration_s:
            errors.append(
                f"run {run.get('id')}: duration {duration:.3f}s < "
                f"minimum {minimum_duration_s:.3f}s"
            )
    else:
        duration = 0.0

    if not rows:
        return {
            "id": run.get("id"),
            "config_id": run.get("config_id"),
            "valid": False,
            "errors": errors,
        }

    speed = [row["speed_mps"] for row in rows]
    mean_speed = statistics.fmean(speed)
    speed_std = statistics.pstdev(speed)
    speed_low = target_speed_mps * (1.0 - speed_tolerance_fraction)
    speed_high = target_speed_mps * (1.0 + speed_tolerance_fraction)
    if not speed_low <= mean_speed <= speed_high:
        errors.append(
            f"run {run.get('id')}: mean speed {mean_speed:.3f} m/s outside "
            f"{speed_low:.3f}-{speed_high:.3f} m/s"
        )
    max_speed_std = target_speed_mps * max_within_run_speed_std_fraction
    if speed_std > max_speed_std:
        errors.append(
            f"run {run.get('id')}: speed std {speed_std:.3f} m/s exceeds "
            f"{max_speed_std:.3f} m/s"
        )

    accel = [row["accel_z_mps2"] for row in rows]
    accel_mean = statistics.fmean(accel)
    accel_centered = [value - accel_mean for value in accel]
    accel_abs = [abs(value) for value in accel_centered]
    roll = [row["gyro_roll_dps"] for row in rows]
    yaw = [row["gyro_yaw_dps"] for row in rows]
    roll_rms = _rms(roll)
    yaw_rms = _rms(yaw)
    yaw_to_roll = None if roll_rms == 0 else yaw_rms / roll_rms
    roll_yaw_corr = _correlation(roll, yaw)

    return {
        "id": run.get("id"),
        "config_id": run.get("config_id"),
        "valid": not errors,
        "errors": errors,
        "sample_count": len(rows),
        "duration_s": round(duration, 3),
        "mean_speed_mps": round(mean_speed, 4),
        "speed_std_mps": round(speed_std, 4),
        "vertical_accel_rms_mps2": round(_rms(accel_centered), 4),
        "vertical_accel_p95_abs_mps2": round(_percentile(accel_abs, 0.95), 4),
        "vertical_accel_peak_abs_mps2": round(max(accel_abs), 4),
        "roll_rate_rms_dps": round(roll_rms, 4),
        "yaw_rate_rms_dps": round(yaw_rms, 4),
        "yaw_to_roll_rms_ratio": (
            None if yaw_to_roll is None else round(yaw_to_roll, 4)
        ),
        "roll_yaw_correlation": (
            None if roll_yaw_corr is None else round(roll_yaw_corr, 4)
        ),
    }


def analyze(manifest: dict, base_dir: Path) -> dict:
    errors: list[str] = []

    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if manifest.get("scope") != "rev_c_unpowered_ride_compliance_trials":
        errors.append("wrong trial scope")
    if manifest.get("powered_operation_authorized") is not False:
        errors.append("ride-compliance analysis cannot authorize powered operation")
    if manifest.get("unpowered_test") is not True:
        errors.append("unpowered_test must be true")
    if manifest.get("dog_or_leash_present") is not False:
        errors.append("dog_or_leash_present must be false")

    for key in (
        "session_id",
        "course_id",
        "surface_description",
        "imu_source_id",
        "imu_mount_id",
        "speed_source_id",
        "rider_observations_csv",
    ):
        value = manifest.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{key} must be a nonempty string")
    if manifest.get("speed_source_calibrated") is not True:
        errors.append("speed_source_calibrated must be true")
    if manifest.get("sensor_timebase_aligned") is not True:
        errors.append("sensor_timebase_aligned must be true")
    if manifest.get("same_course_for_all_runs") is not True:
        errors.append("same_course_for_all_runs must be true")
    if manifest.get("imu_mount_unchanged") is not True:
        errors.append("imu_mount_unchanged must be true")

    pressure_range = manifest.get("tire_pressure_approved_range_kpa")
    pressure_min = pressure_max = None
    if (
        not isinstance(pressure_range, list)
        or len(pressure_range) != 2
        or not all(_finite(value) for value in pressure_range)
        or float(pressure_range[0]) <= 0
        or float(pressure_range[1]) <= float(pressure_range[0])
    ):
        errors.append(
            "tire_pressure_approved_range_kpa must contain positive [min, max]"
        )
    else:
        pressure_min = float(pressure_range[0])
        pressure_max = float(pressure_range[1])

    target_speed = manifest.get("target_speed_mps")
    tolerance = manifest.get("speed_tolerance_fraction")
    minimum_samples = manifest.get("minimum_samples_per_run")
    minimum_duration = manifest.get("minimum_duration_s")
    minimum_repeats = manifest.get("minimum_repeats_per_config")
    max_within_run_speed_std_fraction = manifest.get(
        "max_within_run_speed_std_fraction"
    )
    max_config_speed_delta_fraction = manifest.get(
        "max_config_median_speed_delta_fraction"
    )

    if not _finite(target_speed) or float(target_speed) <= 0:
        errors.append("target_speed_mps must be positive")
    if (
        not _finite(tolerance)
        or float(tolerance) <= 0
        or float(tolerance) > 0.25
    ):
        errors.append("speed_tolerance_fraction must be in (0, 0.25]")
    if not isinstance(minimum_samples, int) or minimum_samples < 10:
        errors.append("minimum_samples_per_run must be an integer >= 10")
    if not _finite(minimum_duration) or float(minimum_duration) <= 0:
        errors.append("minimum_duration_s must be positive")
    if not isinstance(minimum_repeats, int) or minimum_repeats < 3:
        errors.append("minimum_repeats_per_config must be an integer >= 3")
    if (
        not _finite(max_within_run_speed_std_fraction)
        or float(max_within_run_speed_std_fraction) <= 0
        or float(max_within_run_speed_std_fraction) > 0.25
    ):
        errors.append(
            "max_within_run_speed_std_fraction must be in (0, 0.25]"
        )
    if (
        not _finite(max_config_speed_delta_fraction)
        or float(max_config_speed_delta_fraction) <= 0
        or float(max_config_speed_delta_fraction) > 0.25
    ):
        errors.append(
            "max_config_median_speed_delta_fraction must be in (0, 0.25]"
        )

    configs = manifest.get("configs", [])
    if not isinstance(configs, list) or not configs:
        errors.append("configs must be a nonempty list")
        configs = []

    config_ids = [
        config.get("id")
        for config in configs
        if isinstance(config, dict) and isinstance(config.get("id"), str)
        and config.get("id").strip()
    ]
    if len(config_ids) != len(set(config_ids)) or len(config_ids) != len(configs):
        errors.append("configs must contain unique nonempty ids")

    baseline_id = manifest.get("baseline_config_id")
    if baseline_id not in config_ids:
        errors.append("baseline_config_id must reference a declared config")

    config_map = {
        config["id"]: config
        for config in configs
        if isinstance(config, dict)
        and isinstance(config.get("id"), str)
        and config.get("id").strip()
    }

    for config_id, config in config_map.items():
        settings = config.get("settings")
        if not isinstance(settings, dict):
            errors.append(f"{config_id}: settings must be an object")
            continue
        missing_settings = [key for key in SETTING_KEYS if key not in settings]
        if missing_settings:
            errors.append(
                f"{config_id}: missing settings {', '.join(missing_settings)}"
            )
            continue

        for key in ("tire_pressure_front_kpa", "tire_pressure_rear_kpa", "wheelbase_mm"):
            value = settings.get(key)
            if value is not None and (not _finite(value) or float(value) <= 0):
                errors.append(f"{config_id}: {key} must be positive when provided")
        if pressure_min is not None and pressure_max is not None:
            for key in ("tire_pressure_front_kpa", "tire_pressure_rear_kpa"):
                value = settings.get(key)
                if _finite(value) and not pressure_min <= float(value) <= pressure_max:
                    errors.append(
                        f"{config_id}: {key} lies outside approved pressure range"
                    )

        for key in ("chassis_id", "tire_family", "shock_block_id", "shock_block_position", "deck_id", "footbed_id"):
            value = settings.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{config_id}: {key} must be a nonempty string")

    experiment_blocks = {
        config.get("experiment_block")
        for config in config_map.values()
        if isinstance(config.get("experiment_block"), str)
        and config.get("experiment_block").strip()
    }
    if len(experiment_blocks) != 1 or len(experiment_blocks) != len(
        {
            config.get("experiment_block")
            for config in config_map.values()
        }
    ):
        errors.append("all configs must share one nonempty experiment_block")

    baseline_config = config_map.get(baseline_id)
    if baseline_config is not None and isinstance(baseline_config.get("settings"), dict):
        baseline_settings = baseline_config["settings"]
        if baseline_config.get("primary_variable") != "baseline":
            errors.append("baseline config primary_variable must be 'baseline'")
        for config_id, config in config_map.items():
            if config_id == baseline_id or not isinstance(config.get("settings"), dict):
                continue
            primary = config.get("primary_variable")
            allowed_keys = PRIMARY_VARIABLE_SETTINGS.get(primary)
            if allowed_keys is None:
                errors.append(
                    f"{config_id}: primary_variable must be one of "
                    + ", ".join(sorted(PRIMARY_VARIABLE_SETTINGS))
                )
                continue

            settings = config["settings"]
            changed = {
                key
                for key in SETTING_KEYS
                if settings.get(key) != baseline_settings.get(key)
            }
            if not changed:
                errors.append(f"{config_id}: no setting differs from baseline")
            elif not changed.issubset(allowed_keys):
                errors.append(
                    f"{config_id}: changed settings {sorted(changed)} exceed "
                    f"primary variable {primary}"
                )

            if primary == "tire_pressure":
                front = settings.get("tire_pressure_front_kpa")
                rear = settings.get("tire_pressure_rear_kpa")
                baseline_front = baseline_settings.get("tire_pressure_front_kpa")
                baseline_rear = baseline_settings.get("tire_pressure_rear_kpa")
                if front != rear or baseline_front != baseline_rear:
                    errors.append(
                        f"{config_id}: initial tire-pressure experiments must use "
                        "symmetric front/rear pressure in baseline and candidate"
                    )

    if errors:
        return {
            "schema_version": 1,
            "authority": "x1_rev_c_ride_compliance_analysis",
            "valid": False,
            "errors": errors,
            "physical_authority": False,
            "procurement_authority": False,
            "powered_operation_authorized": False,
        }

    runs = manifest.get("runs", [])
    if not isinstance(runs, list) or not runs:
        errors.append("runs must be a nonempty list")
        runs = []

    run_ids = [
        run.get("id")
        for run in runs
        if isinstance(run, dict)
        and isinstance(run.get("id"), str)
        and run.get("id").strip()
    ]
    if len(run_ids) != len(set(run_ids)) or len(run_ids) != len(runs):
        errors.append("runs must contain unique nonempty ids")

    for run in runs:
        if not isinstance(run, dict):
            continue
        if run.get("rider_observation_recorded") is not True:
            errors.append(
                f"run {run.get('id')}: rider_observation_recorded must be true"
            )

    observation_path = base_dir / str(manifest.get("rider_observations_csv", ""))
    observations, observation_errors = _load_observations(observation_path)
    errors.extend(observation_errors)

    expected_run_ids = set(run_ids)
    actual_observation_ids = set(observations)
    if expected_run_ids != actual_observation_ids:
        missing = sorted(expected_run_ids - actual_observation_ids)
        extra = sorted(actual_observation_ids - expected_run_ids)
        if missing:
            errors.append(
                "rider observations missing runs: " + ", ".join(missing)
            )
        if extra:
            errors.append(
                "rider observations contain unknown runs: " + ", ".join(extra)
            )

    for run in runs:
        if not isinstance(run, dict):
            continue
        run_id = run.get("id")
        observation = observations.get(run_id)
        if observation is None:
            continue
        if observation.get("config_id") != run.get("config_id"):
            errors.append(
                f"run {run_id}: rider observation config_id does not match"
            )
        for key in REQUIRED_OBSERVATION_COLUMNS:
            if key in {"run_id", "config_id"}:
                continue
            if not observation.get(key):
                errors.append(
                    f"run {run_id}: rider observation missing {key}"
                )
        if observation.get("emergency_stepoff_ok", "").lower() not in {
            "true",
            "yes",
            "pass",
            "1",
        }:
            errors.append(
                f"run {run_id}: emergency step-off was not accepted"
            )

    if errors:
        return {
            "schema_version": 1,
            "authority": "x1_rev_c_ride_compliance_analysis",
            "valid": False,
            "errors": errors,
            "physical_authority": False,
            "procurement_authority": False,
            "powered_operation_authorized": False,
        }

    analyzed_runs = [
        _analyze_run(
            run,
            base_dir=base_dir,
            target_speed_mps=float(target_speed),
            speed_tolerance_fraction=float(tolerance),
            minimum_samples=minimum_samples,
            minimum_duration_s=float(minimum_duration),
            max_within_run_speed_std_fraction=float(
                max_within_run_speed_std_fraction
            ),
        )
        for run in runs
        if isinstance(run, dict)
    ]

    for run in analyzed_runs:
        if run.get("config_id") not in config_ids:
            run["valid"] = False
            run.setdefault("errors", []).append("run references unknown config")

    aggregate: dict[str, dict] = {}
    metric_names = (
        "mean_speed_mps",
        "vertical_accel_rms_mps2",
        "vertical_accel_p95_abs_mps2",
        "vertical_accel_peak_abs_mps2",
        "roll_rate_rms_dps",
        "yaw_rate_rms_dps",
        "yaw_to_roll_rms_ratio",
        "roll_yaw_correlation",
    )
    for config_id in config_ids:
        valid_runs = [
            run
            for run in analyzed_runs
            if run.get("config_id") == config_id and run.get("valid") is True
        ]
        config_errors: list[str] = []
        if len(valid_runs) < minimum_repeats:
            config_errors.append(
                f"{len(valid_runs)} valid repeats < required {minimum_repeats}"
            )

        medians = {
            metric: (
                round(_median([float(run[metric]) for run in valid_runs]), 4)
                if valid_runs
                else None
            )
            for metric in metric_names
        }
        aggregate[config_id] = {
            "valid_for_comparison": not config_errors,
            "errors": config_errors,
            "valid_repeat_count": len(valid_runs),
            "median_metrics": medians,
        }

    baseline = aggregate.get(baseline_id, {})
    baseline_metrics = baseline.get("median_metrics", {})
    baseline_speed = baseline_metrics.get("mean_speed_mps")

    if baseline_speed is not None:
        max_delta = float(baseline_speed) * float(max_config_speed_delta_fraction)
        for config_id, entry in aggregate.items():
            config_speed = entry["median_metrics"].get("mean_speed_mps")
            if config_speed is None:
                continue
            if abs(float(config_speed) - float(baseline_speed)) > max_delta:
                entry["errors"].append(
                    "median configuration speed differs too much from baseline"
                )
                entry["valid_for_comparison"] = False

    for config_id, entry in aggregate.items():
        deltas: dict[str, float | None] = {}
        for metric in metric_names:
            value = entry["median_metrics"].get(metric)
            base = baseline_metrics.get(metric)
            if metric == "roll_yaw_correlation":
                deltas["roll_yaw_correlation_delta_vs_baseline"] = (
                    round(float(value) - float(base), 4)
                    if value is not None and base is not None
                    else None
                )
            else:
                deltas[f"{metric}_pct_vs_baseline"] = (
                    _pct_delta(float(value), float(base))
                    if value is not None and base is not None
                    else None
                )
        entry["relative_to_baseline"] = deltas

    valid = (
        all(run.get("valid") is True for run in analyzed_runs)
        and bool(analyzed_runs)
        and all(entry["valid_for_comparison"] for entry in aggregate.values())
    )

    return {
        "schema_version": 1,
        "authority": "x1_rev_c_ride_compliance_analysis",
        "valid": valid,
        "errors": [] if valid else ["one or more runs/configurations failed comparison gates"],
        "physical_authority": False,
        "procurement_authority": False,
        "powered_operation_authorized": False,
        "baseline_config_id": baseline_id,
        "sensor_provenance": {
            "imu_source_id": manifest.get("imu_source_id"),
            "imu_mount_id": manifest.get("imu_mount_id"),
            "speed_source_id": manifest.get("speed_source_id"),
            "speed_source_calibrated": manifest.get("speed_source_calibrated") is True,
            "sensor_timebase_aligned": manifest.get("sensor_timebase_aligned") is True,
        },
        "run_results": analyzed_runs,
        "config_results": aggregate,
        "interpretation_boundary": (
            "Lower vibration metrics do not automatically mean better handling. "
            "Yaw-to-roll ratio and roll/yaw correlation are only descriptive lean-to-turn "
            "proxies, not stability or quality scores. Use them alongside separate "
            "rider-control observations; do not collapse the outputs into a single winner score."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = analyze(manifest, args.manifest.parent)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
