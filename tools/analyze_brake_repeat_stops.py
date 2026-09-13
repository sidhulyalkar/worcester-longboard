#!/usr/bin/env python3
"""Analyze predeclared low-energy Worcester X1 repeated-stop brake data.

This is a thermal/fade screening analysis, not powered-operation authority. The
test plan and thresholds must be frozen before data collection. Performance is
compared using equivalent constant deceleration v^2/(2d), which reduces the
sensitivity of raw stopping distance to small start-speed differences.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def analyze(data: dict) -> dict:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("scope") != "unpowered_repeated_stop_thermal_series":
        errors.append("wrong repeated-stop scope")
    if data.get("plan_frozen_before_data") is not True:
        errors.append("test plan must be frozen before data collection")
    if data.get("powered_test") is not False:
        errors.append("this analyzer is scoped to unpowered/low-energy external-motion testing")

    plan = data.get("test_plan", {})
    target_speed = plan.get("target_start_speed_mps")
    speed_tol = plan.get("start_speed_tolerance_mps")
    baseline_count = plan.get("baseline_stop_count")
    max_decel_loss = plan.get("max_deceleration_loss_fraction")
    max_peak_temp = plan.get("max_rotor_peak_temp_c")
    minimum_stops = plan.get("minimum_stop_count")

    if not _finite(target_speed) or float(target_speed) <= 0:
        errors.append("target_start_speed_mps must be positive")
    if not _finite(speed_tol) or float(speed_tol) <= 0:
        errors.append("start_speed_tolerance_mps must be positive")
    if not isinstance(baseline_count, int) or baseline_count < 2:
        errors.append("baseline_stop_count must be an integer >= 2")
    if not _finite(max_decel_loss) or not 0 <= float(max_decel_loss) < 1:
        errors.append("max_deceleration_loss_fraction must be in [0, 1)")
    if not _finite(max_peak_temp):
        errors.append("max_rotor_peak_temp_c must be finite")
    if not isinstance(minimum_stops, int) or minimum_stops < 3:
        errors.append("minimum_stop_count must be an integer >= 3")

    stops = data.get("stops")
    if not isinstance(stops, list):
        errors.append("stops must be a list")
        stops = []
    if isinstance(minimum_stops, int) and len(stops) < minimum_stops:
        errors.append("insufficient stops for frozen test plan")
    if isinstance(baseline_count, int) and len(stops) <= baseline_count:
        errors.append("series must include at least one stop after the baseline window")

    rows = []
    for index, stop in enumerate(stops, start=1):
        if not isinstance(stop, dict):
            errors.append(f"stop {index} must be an object")
            continue
        speed = stop.get("start_speed_mps")
        distance = stop.get("stop_distance_m")
        ambient = stop.get("ambient_temp_c")
        rotor_start = stop.get("rotor_temp_start_c")
        rotor_peak = stop.get("rotor_temp_peak_c")
        if not _finite(speed) or float(speed) <= 0:
            errors.append(f"stop {index}: invalid start speed")
            continue
        if not _finite(distance) or float(distance) <= 0:
            errors.append(f"stop {index}: invalid stop distance")
            continue
        if not all(_finite(x) for x in (ambient, rotor_start, rotor_peak)):
            errors.append(f"stop {index}: invalid temperature data")
            continue
        speed = float(speed)
        distance = float(distance)
        ambient = float(ambient)
        rotor_start = float(rotor_start)
        rotor_peak = float(rotor_peak)
        if rotor_peak < rotor_start:
            errors.append(f"stop {index}: rotor peak below start temperature")
        if _finite(target_speed) and _finite(speed_tol):
            if abs(speed - float(target_speed)) > float(speed_tol):
                errors.append(f"stop {index}: start speed outside frozen tolerance")
        decel = speed * speed / (2.0 * distance)
        rows.append(
            {
                "index": index,
                "start_speed_mps": speed,
                "stop_distance_m": distance,
                "equivalent_deceleration_mps2": decel,
                "ambient_temp_c": ambient,
                "rotor_temp_start_c": rotor_start,
                "rotor_temp_peak_c": rotor_peak,
                "peak_temp_rise_above_ambient_c": rotor_peak - ambient,
            }
        )

    baseline_decel = None
    if isinstance(baseline_count, int) and len(rows) >= baseline_count:
        baseline_decel = statistics.median(
            row["equivalent_deceleration_mps2"] for row in rows[:baseline_count]
        )
        for row in rows:
            row["deceleration_loss_fraction_vs_baseline"] = (
                1.0 - row["equivalent_deceleration_mps2"] / baseline_decel
                if baseline_decel > 0
                else None
            )

    checks = {
        "deceleration_retention_passed": False,
        "rotor_peak_temperature_passed": False,
    }
    if baseline_decel is not None and _finite(max_decel_loss):
        checks["deceleration_retention_passed"] = all(
            row["deceleration_loss_fraction_vs_baseline"] <= float(max_decel_loss)
            for row in rows[baseline_count:]
        )
    if rows and _finite(max_peak_temp):
        checks["rotor_peak_temperature_passed"] = max(row["rotor_temp_peak_c"] for row in rows) <= float(max_peak_temp)

    valid = not errors
    passed = valid and all(checks.values())
    return {
        "schema_version": 1,
        "scope": "unpowered_repeated_stop_thermal_analysis",
        "valid": valid,
        "errors": errors,
        "analysis_passed": passed,
        "physical_authority": False,
        "test_plan": plan,
        "baseline_equivalent_deceleration_mps2": baseline_decel,
        "checks": checks,
        "stops": rows,
        "limitations": [
            "does not reproduce powered downhill energy without an appropriate low-energy surrogate protocol",
            "does not authorize powered hill testing",
            "temperature sensor placement and response time must be documented separately",
            "brake wear and cable condition still require physical inspection",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("series", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    report = analyze(json.loads(args.series.read_text(encoding="utf-8")))
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
