#!/usr/bin/env python3
"""First-order traction sensitivity for Worcester X1 topology decisions.

This model is intentionally a rejection/sensitivity tool, not physical authority.
It estimates quasi-static front/rear normal load on a grade while accelerating
along the deck plane, then reports the tire/terrain friction coefficient required
for front-, rear-, or all-wheel propulsion.

Coordinate convention:
- rear contact line x = 0
- front contact line x = wheelbase
- CG x is measured forward from the rear contact line
- CG height is normal to the road plane
- positive grade and acceleration point uphill/forward

It neglects suspension transients, individual-wheel load transfer, tire sinkage,
aero, steering angle, and torque-vectoring effects. Those omissions make it a
screening model rather than a topology qualification.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

G = 9.80665


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def validate_config(config: dict) -> list[str]:
    errors: list[str] = []
    if config.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if config.get("scope") != "front_drive_traction_sensitivity":
        errors.append("wrong traction-model scope")

    for key in ("total_mass_kg", "wheelbase_m", "cg_from_rear_m", "cg_height_m"):
        value = config.get(key)
        if not _finite_number(value) or float(value) <= 0:
            errors.append(f"{key} must be finite and positive")

    wheelbase = config.get("wheelbase_m")
    cg_x = config.get("cg_from_rear_m")
    if _finite_number(wheelbase) and _finite_number(cg_x):
        if not 0 < float(cg_x) < float(wheelbase):
            errors.append("cg_from_rear_m must lie between rear and front contact lines")

    crr = config.get("rolling_resistance_coeff", 0.0)
    if not _finite_number(crr) or not 0 <= float(crr) < 0.5:
        errors.append("rolling_resistance_coeff must be in [0, 0.5)")

    scenarios = config.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        errors.append("at least one scenario is required")
    else:
        names: set[str] = set()
        for index, scenario in enumerate(scenarios):
            if not isinstance(scenario, dict):
                errors.append(f"scenario {index} must be an object")
                continue
            name = scenario.get("name")
            if not isinstance(name, str) or not name.strip():
                errors.append(f"scenario {index} requires name")
            elif name in names:
                errors.append(f"duplicate scenario name: {name}")
            else:
                names.add(name)
            grade = scenario.get("grade")
            accel = scenario.get("acceleration_mps2")
            if not _finite_number(grade) or float(grade) < 0:
                errors.append(f"{name or index}: grade must be finite and nonnegative")
            if not _finite_number(accel) or float(accel) < 0:
                errors.append(f"{name or index}: acceleration_mps2 must be finite and nonnegative")
            mus = scenario.get("compare_mu", [])
            if not isinstance(mus, list):
                errors.append(f"{name or index}: compare_mu must be a list")
            else:
                for mu in mus:
                    if not _finite_number(mu) or float(mu) <= 0:
                        errors.append(f"{name or index}: compare_mu entries must be positive")
    return errors


def analyze_scenario(config: dict, scenario: dict) -> dict:
    mass = float(config["total_mass_kg"])
    wheelbase = float(config["wheelbase_m"])
    cg_x = float(config["cg_from_rear_m"])
    cg_h = float(config["cg_height_m"])
    crr = float(config.get("rolling_resistance_coeff", 0.0))
    grade = float(scenario["grade"])
    accel = float(scenario["acceleration_mps2"])
    theta = math.atan(grade)

    normal_total = mass * G * math.cos(theta)
    uphill_inertial_plus_gravity = mass * (G * math.sin(theta) + accel)

    # Moment balance about the rear contact line. Positive forward acceleration
    # and positive uphill grade both unload the front axle.
    front_normal = (
        mass * G * math.cos(theta) * cg_x
        - mass * (G * math.sin(theta) + accel) * cg_h
    ) / wheelbase
    rear_normal = normal_total - front_normal

    rolling_force = crr * normal_total
    required_propulsion = uphill_inertial_plus_gravity + rolling_force

    def required_mu(normal: float) -> float | None:
        if normal <= 0:
            return None
        return required_propulsion / normal

    mu_front = required_mu(front_normal)
    mu_rear = required_mu(rear_normal)
    mu_awd = required_mu(normal_total)

    comparisons = []
    for mu in scenario.get("compare_mu", []):
        mu = float(mu)
        comparisons.append(
            {
                "mu": mu,
                "front_drive_force_margin_n": mu * front_normal - required_propulsion,
                "rear_drive_force_margin_n": mu * rear_normal - required_propulsion,
                "awd_force_margin_n": mu * normal_total - required_propulsion,
                "front_drive_meets_required_force": front_normal > 0 and mu * front_normal >= required_propulsion,
                "rear_drive_meets_required_force": rear_normal > 0 and mu * rear_normal >= required_propulsion,
                "awd_meets_required_force": mu * normal_total >= required_propulsion,
            }
        )

    return {
        "name": scenario["name"],
        "grade": grade,
        "grade_angle_deg": math.degrees(theta),
        "acceleration_mps2": accel,
        "required_propulsion_force_n": required_propulsion,
        "front_normal_force_n": front_normal,
        "rear_normal_force_n": rear_normal,
        "front_load_fraction": front_normal / normal_total if normal_total > 0 else None,
        "rear_load_fraction": rear_normal / normal_total if normal_total > 0 else None,
        "required_mu": {
            "front_drive": mu_front,
            "rear_drive": mu_rear,
            "awd": mu_awd,
        },
        "front_contact_positive": front_normal > 0,
        "rear_contact_positive": rear_normal > 0,
        "comparisons": comparisons,
    }


def analyze(config: dict) -> dict:
    errors = validate_config(config)
    if errors:
        return {
            "schema_version": 1,
            "scope": "front_drive_traction_sensitivity_analysis",
            "valid": False,
            "errors": errors,
            "physical_authority": False,
        }
    return {
        "schema_version": 1,
        "scope": "front_drive_traction_sensitivity_analysis",
        "valid": True,
        "errors": [],
        "physical_authority": False,
        "assumptions": [
            "quasi-static pitch/load transfer",
            "single front and rear axle normal-load result",
            "no lateral load transfer",
            "no tire sinkage or transient suspension dynamics",
            "traction limited by mu times axle normal load",
        ],
        "inputs": {
            key: config[key]
            for key in ("total_mass_kg", "wheelbase_m", "cg_from_rear_m", "cg_height_m")
        }
        | {"rolling_resistance_coeff": config.get("rolling_resistance_coeff", 0.0)},
        "scenarios": [analyze_scenario(config, scenario) for scenario in config["scenarios"]],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("config", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    report = analyze(json.loads(args.config.read_text(encoding="utf-8")))
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
