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


def _analyze_run(
    run: dict,
    *,
    base_dir: Path,
    target_speed_mps: float,
    speed_tolerance_fraction: float,
    minimum_samples: int,
    minimum_duration_s: float,
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
    speed_low = target_speed_mps * (1.0 - speed_tolerance_fraction)
    speed_high = target_speed_mps * (1.0 + speed_tolerance_fraction)
    if not speed_low <= mean_speed <= speed_high:
        errors.append(
            f"run {run.get('id')}: mean speed {mean_speed:.3f} m/s outside "
            f"{speed_low:.3f}-{speed_high:.3f} m/s"
        )

    accel = [row["accel_z_mps2"] for row in rows]
    accel_mean = statistics.fmean(accel)
    accel_centered = [value - accel_mean for value in accel]
    accel_abs = [abs(value) for value in accel_centered]
    roll = [row["gyro_roll_dps"] for row in rows]
    yaw = [row["gyro_yaw_dps"] for row in rows]

    return {
        "id": run.get("id"),
        "config_id": run.get("config_id"),
        "valid": not errors,
        "errors": errors,
        "sample_count": len(rows),
        "duration_s": round(duration, 3),
        "mean_speed_mps": round(mean_speed, 4),
        "speed_std_mps": round(statistics.pstdev(speed), 4),
        "vertical_accel_rms_mps2": round(_rms(accel_centered), 4),
        "vertical_accel_p95_abs_mps2": round(_percentile(accel_abs, 0.95), 4),
        "vertical_accel_peak_abs_mps2": round(max(accel_abs), 4),
        "roll_rate_rms_dps": round(_rms(roll), 4),
        "yaw_rate_rms_dps": round(_rms(yaw), 4),
    }


def analyze(manifest: dict, base_dir: Path) -> dict:
    errors: list[str] = []

    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if manifest.get("scope") != "rev_c_unpowered_ride_compliance_trials":
        errors.append("wrong trial scope")
    if manifest.get("powered_operation_authorized") is not False:
        errors.append("ride-compliance analysis cannot authorize powered operation")
    if manifest.get("same_course_for_all_runs") is not True:
        errors.append("same_course_for_all_runs must be true")
    if manifest.get("imu_mount_unchanged") is not True:
        errors.append("imu_mount_unchanged must be true")

    target_speed = manifest.get("target_speed_mps")
    tolerance = manifest.get("speed_tolerance_fraction")
    minimum_samples = manifest.get("minimum_samples_per_run")
    minimum_duration = manifest.get("minimum_duration_s")
    minimum_repeats = manifest.get("minimum_repeats_per_config")

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

    configs = manifest.get("configs", [])
    config_ids = [
        config.get("id")
        for config in configs
        if isinstance(config, dict) and isinstance(config.get("id"), str)
    ]
    if len(config_ids) != len(set(config_ids)) or not config_ids:
        errors.append("configs must contain unique nonempty ids")

    baseline_id = manifest.get("baseline_config_id")
    if baseline_id not in config_ids:
        errors.append("baseline_config_id must reference a declared config")

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
    analyzed_runs = [
        _analyze_run(
            run,
            base_dir=base_dir,
            target_speed_mps=float(target_speed),
            speed_tolerance_fraction=float(tolerance),
            minimum_samples=minimum_samples,
            minimum_duration_s=float(minimum_duration),
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
    for config_id, entry in aggregate.items():
        deltas: dict[str, float | None] = {}
        for metric in metric_names:
            value = entry["median_metrics"].get(metric)
            base = baseline_metrics.get(metric)
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
        "run_results": analyzed_runs,
        "config_results": aggregate,
        "interpretation_boundary": (
            "Lower vibration metrics do not automatically mean better handling, "
            "and higher roll/yaw activity does not automatically mean better carve. "
            "Use these results alongside separate rider-control observations; do not "
            "collapse them into a single winner score."
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
