#!/usr/bin/env python3
"""Summarize SnowDeck compliant-cartridge bench curves without approving a material."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Callable

EXPECTED_SCOPE = "x1_snowdeck_compliance_bench_trial"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _finite_nonnegative(value: Any, label: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(label + " must be finite and nonnegative")
    return result


def _origin_slope(points: list[tuple[float, float]], label: str) -> float:
    denominator = sum(x * x for x, _ in points)
    if denominator <= 0:
        raise ValueError(label + " requires nonzero displacement/angle")
    return sum(x * y for x, y in points) / denominator


def _path_work(points: list[tuple[float, float]]) -> float:
    total = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        total += 0.5 * (y0 + y1) * (x1 - x0)
    return total


def _summary(values: list[float]) -> dict[str, float]:
    return {
        "mean": mean(values),
        "sd": pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def _curve_points(
    raw: list[dict[str, Any]],
    *,
    x_key: str,
    y_key: str,
    x_transform: Callable[[float], float] = lambda value: value,
) -> list[tuple[float, float]]:
    if len(raw) < 3:
        raise ValueError("each loading/unloading curve requires at least three points")
    points: list[tuple[float, float]] = []
    for index, point in enumerate(raw):
        x = x_transform(_finite_nonnegative(point.get(x_key), x_key + "[" + str(index) + "]"))
        y = _finite_nonnegative(point.get(y_key), y_key + "[" + str(index) + "]")
        points.append((x, y))
    return points


def _normal_cycle(cycle: dict[str, Any]) -> dict[str, float]:
    loading = _curve_points(
        cycle.get("loading", []),
        x_key="displacement_mm",
        y_key="force_n",
    )
    unloading = _curve_points(
        cycle.get("unloading", []),
        x_key="displacement_mm",
        y_key="force_n",
    )
    return {
        "stiffness_loading_n_per_mm": _origin_slope(loading, "normal loading"),
        "stiffness_unloading_n_per_mm": _origin_slope(unloading, "normal unloading"),
        "hysteresis_loop_mj": abs(_path_work(loading) + _path_work(unloading)),
        "zero_return_mm": _finite_nonnegative(cycle.get("zero_return_mm"), "zero_return_mm"),
        "settling_time_s": _finite_nonnegative(cycle.get("settling_time_s"), "settling_time_s"),
        "peak_force_n": max(y for _, y in loading),
        "peak_displacement_mm": max(x for x, _ in loading),
    }


def _torsion_cycle(cycle: dict[str, Any]) -> dict[str, float]:
    radians = lambda degrees: math.radians(degrees)
    loading = _curve_points(
        cycle.get("loading", []),
        x_key="angle_deg",
        y_key="moment_nm",
        x_transform=radians,
    )
    unloading = _curve_points(
        cycle.get("unloading", []),
        x_key="angle_deg",
        y_key="moment_nm",
        x_transform=radians,
    )
    return {
        "stiffness_loading_nm_per_rad": _origin_slope(loading, "torsion loading"),
        "stiffness_unloading_nm_per_rad": _origin_slope(unloading, "torsion unloading"),
        "hysteresis_loop_j": abs(_path_work(loading) + _path_work(unloading)),
        "zero_return_deg": _finite_nonnegative(cycle.get("zero_return_deg"), "zero_return_deg"),
        "settling_time_s": _finite_nonnegative(cycle.get("settling_time_s"), "settling_time_s"),
        "peak_moment_nm": max(y for _, y in loading),
        "peak_angle_deg": math.degrees(max(x for x, _ in loading)),
    }


def _rejects(observations: dict[str, Any]) -> list[str]:
    mapping = (
        ("unexpected_rocking_observed", "unexpected rocking"),
        ("insert_migration_observed", "insert migration"),
        ("fastener_migration_observed", "fastener migration"),
        ("visible_damage_observed", "visible damage"),
        ("persistent_deformation_observed", "persistent deformation"),
    )
    return [label for key, label in mapping if observations.get(key) is True]


def summarize(data: dict[str, Any], source_sha256: str | None = None) -> dict[str, Any]:
    if data.get("scope") != EXPECTED_SCOPE:
        raise ValueError("wrong SnowDeck compliance trial scope")
    for key in (
        "physical_authority",
        "fabrication_authority",
        "ride_authority",
        "powered_operation_authorized",
    ):
        if data.get(key) is not False:
            raise ValueError(key + " must remain false")

    normal_raw = data.get("normal_cycles", [])
    torsion_raw = data.get("torsion_cycles", [])
    if len(normal_raw) < 2 or len(torsion_raw) < 2:
        raise ValueError("compliance study requires at least two normal and two torsion cycles")

    normal = [_normal_cycle(cycle) for cycle in normal_raw]
    torsion = [_torsion_cycle(cycle) for cycle in torsion_raw]
    rejects = _rejects(data.get("observations", {}))
    synthetic = bool(data.get("synthetic_fixture"))

    normal_keys = (
        "stiffness_loading_n_per_mm",
        "stiffness_unloading_n_per_mm",
        "hysteresis_loop_mj",
        "zero_return_mm",
        "settling_time_s",
    )
    torsion_keys = (
        "stiffness_loading_nm_per_rad",
        "stiffness_unloading_nm_per_rad",
        "hysteresis_loop_j",
        "zero_return_deg",
        "settling_time_s",
    )

    return {
        "schema_version": 1,
        "scope": "x1_snowdeck_compliance_signature",
        "condition_id": data.get("condition_id"),
        "synthetic_fixture": synthetic,
        "physical_evidence_eligible": not synthetic,
        "source_trial_sha256": source_sha256,
        "normal_cycle_count": len(normal),
        "torsion_cycle_count": len(torsion),
        "normal_response": {
            key: _summary([cycle[key] for cycle in normal])
            for key in normal_keys
        },
        "torsion_response": {
            key: _summary([cycle[key] for cycle in torsion])
            for key in torsion_keys
        },
        "mechanical_rejects": rejects,
        "eligible_for_further_bench_study": not rejects,
        "interpretation": (
            "Descriptive stiffness/hysteresis/return response only. "
            "No material, thickness, or ride setting is approved."
        ),
        "physical_authority": False,
        "fabrication_authority": False,
        "ride_authority": False,
        "powered_operation_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trial", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    data = json.loads(args.trial.read_text(encoding="utf-8"))
    report = summarize(data, _sha256(args.trial))
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
