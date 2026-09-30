#!/usr/bin/env python3
"""Sweep front-vs-rear 2WD traction sensitivity for Rev-C topology screening.

This deliberately uses dimensionless CG ratios instead of rider-specific values.
It is a rejection/sensitivity tool only. It cannot qualify a drivetrain, tire,
terrain, brake topology, or powered ride.

The sweep asks a narrow question:
    as uphill grade and longitudinal load transfer increase, how much friction
    coefficient would front- versus rear-driven axles require?

Use the result to decide which physical topology deserves expensive packaging
work. Do not use it to infer actual trail friction.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from simulation.front_drive_traction import analyze_scenario


@dataclass(frozen=True)
class SweepConfig:
    wheelbase_m: float = 0.94
    total_mass_kg: float = 1.0
    cg_from_rear_fraction: float = 0.50
    cg_height_to_wheelbase: float = 0.75
    rolling_resistance_coeff: float = 0.04
    acceleration_mps2: float = 0.50

    def base_config(self) -> dict:
        if self.wheelbase_m <= 0:
            raise ValueError("wheelbase_m must be positive")
        if self.total_mass_kg <= 0:
            raise ValueError("total_mass_kg must be positive")
        if not 0 < self.cg_from_rear_fraction < 1:
            raise ValueError("cg_from_rear_fraction must be in (0, 1)")
        if self.cg_height_to_wheelbase <= 0:
            raise ValueError("cg_height_to_wheelbase must be positive")
        if not 0 <= self.rolling_resistance_coeff < 0.5:
            raise ValueError("rolling_resistance_coeff must be in [0, 0.5)")
        if self.acceleration_mps2 < 0:
            raise ValueError("acceleration_mps2 must be nonnegative")
        return {
            "schema_version": 1,
            "scope": "front_drive_traction_sensitivity",
            "total_mass_kg": self.total_mass_kg,
            "wheelbase_m": self.wheelbase_m,
            "cg_from_rear_m": self.wheelbase_m * self.cg_from_rear_fraction,
            "cg_height_m": self.wheelbase_m * self.cg_height_to_wheelbase,
            "rolling_resistance_coeff": self.rolling_resistance_coeff,
        }


def sweep(config: SweepConfig, grades: list[float]) -> dict:
    if not grades:
        raise ValueError("at least one grade is required")
    if any(g < 0 for g in grades):
        raise ValueError("grades must be nonnegative")

    base = config.base_config()
    rows = []
    for grade in grades:
        result = analyze_scenario(
            base,
            {
                "name": f"grade_{grade:.3f}",
                "grade": grade,
                "acceleration_mps2": config.acceleration_mps2,
                "compare_mu": [],
            },
        )
        front_mu = result["required_mu"]["front_drive"]
        rear_mu = result["required_mu"]["rear_drive"]
        rows.append(
            {
                "grade": grade,
                "grade_angle_deg": round(result["grade_angle_deg"], 2),
                "front_load_fraction": round(result["front_load_fraction"], 4),
                "rear_load_fraction": round(result["rear_load_fraction"], 4),
                "required_mu_front_2wd": None if front_mu is None else round(front_mu, 3),
                "required_mu_rear_2wd": None if rear_mu is None else round(rear_mu, 3),
                "front_to_rear_mu_ratio": (
                    None
                    if front_mu is None or rear_mu is None or rear_mu <= 0
                    else round(front_mu / rear_mu, 3)
                ),
            }
        )

    return {
        "schema_version": 1,
        "scope": "rev_c_topology_traction_sweep",
        "physical_authority": False,
        "interpretation": (
            "A larger required_mu means that axle needs more tire/terrain friction "
            "to deliver the same uphill propulsion demand. This is topology screening, "
            "not a terrain-friction measurement."
        ),
        "inputs": {
            "wheelbase_m": config.wheelbase_m,
            "normalization_mass_kg": config.total_mass_kg,
            "cg_from_rear_fraction": config.cg_from_rear_fraction,
            "cg_height_to_wheelbase": config.cg_height_to_wheelbase,
            "rolling_resistance_coeff": config.rolling_resistance_coeff,
            "acceleration_mps2": config.acceleration_mps2,
        },
        "rows": rows,
    }


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wheelbase-m", type=float, default=0.94)
    p.add_argument("--mass-kg", type=float, default=1.0, help="normalization mass; required-mu ratios are mass invariant")
    p.add_argument("--cg-from-rear-fraction", type=float, default=0.50)
    p.add_argument("--cg-height-to-wheelbase", type=float, default=0.75)
    p.add_argument("--rolling-resistance", type=float, default=0.04)
    p.add_argument("--acceleration", type=float, default=0.50)
    p.add_argument("--grades", type=float, nargs="+", default=[0.0, 0.10, 0.20, 0.30])
    return p


def main() -> None:
    args = _parser().parse_args()
    report = sweep(
        SweepConfig(
            wheelbase_m=args.wheelbase_m,
            total_mass_kg=args.mass_kg,
            cg_from_rear_fraction=args.cg_from_rear_fraction,
            cg_height_to_wheelbase=args.cg_height_to_wheelbase,
            rolling_resistance_coeff=args.rolling_resistance,
            acceleration_mps2=args.acceleration,
        ),
        args.grades,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
