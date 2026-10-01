#!/usr/bin/env python3
"""Plan Worcester X1 mission energy and ideal charge-time lower bounds.

This is a planning tool, not battery or charger qualification.

Range uses the repository's planning Wh/mi cases plus an explicit reserve.
Charge time is only the ideal energy / charger-power lower bound. Real charging
will be longer and depends on the selected pack, BMS, charger, taper, temperature,
cell balance, and manufacturer limits.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass

from simulation.range_envelope import PLANNING_CASES, planning_envelope


@dataclass(frozen=True)
class MissionPlan:
    distance_miles: float
    terrain: str
    reserve_fraction: float
    pack_wh: float

    def validate(self) -> None:
        if self.distance_miles <= 0:
            raise ValueError("distance_miles must be positive")
        if self.pack_wh <= 0:
            raise ValueError("pack_wh must be positive")
        if self.terrain not in PLANNING_CASES:
            raise ValueError(f"unknown terrain {self.terrain!r}")
        if not 0 <= self.reserve_fraction < 1:
            raise ValueError("reserve_fraction must be in [0, 1)")

    def as_dict(self) -> dict:
        self.validate()
        low, high = PLANNING_CASES[self.terrain]
        required_usable_low = self.distance_miles * low
        required_usable_high = self.distance_miles * high
        required_nominal_low = required_usable_low / (1 - self.reserve_fraction)
        required_nominal_high = required_usable_high / (1 - self.reserve_fraction)

        envelope = planning_envelope(
            self.pack_wh, self.terrain, self.reserve_fraction
        ).as_dict()

        packs_conservative = math.ceil(required_nominal_high / self.pack_wh)
        packs_optimistic = math.ceil(required_nominal_low / self.pack_wh)

        return {
            "distance_miles": self.distance_miles,
            "terrain": self.terrain,
            "reserve_fraction": self.reserve_fraction,
            "pack_wh": self.pack_wh,
            "pack_range_envelope_miles": envelope["range_miles"],
            "required_nominal_wh_for_mission": [
                round(required_nominal_low, 1),
                round(required_nominal_high, 1),
            ],
            "single_pack_covers_conservative_case": (
                self.pack_wh >= required_nominal_high
            ),
            "single_pack_covers_optimistic_case": (
                self.pack_wh >= required_nominal_low
            ),
            "packs_needed": {
                "optimistic_consumption_case": packs_optimistic,
                "conservative_consumption_case": packs_conservative,
            },
            "cold_swaps_needed": {
                "optimistic_consumption_case": max(0, packs_optimistic - 1),
                "conservative_consumption_case": max(0, packs_conservative - 1),
            },
        }


def ideal_charge_lower_bound(
    *,
    pack_wh: float,
    charger_power_w: float,
    start_soc_fraction: float = 0.0,
    target_soc_fraction: float = 1.0,
) -> dict:
    for name, value in (
        ("pack_wh", pack_wh),
        ("charger_power_w", charger_power_w),
    ):
        if value <= 0 or not math.isfinite(value):
            raise ValueError(f"{name} must be finite and positive")

    for name, value in (
        ("start_soc_fraction", start_soc_fraction),
        ("target_soc_fraction", target_soc_fraction),
    ):
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be in [0, 1]")

    if target_soc_fraction <= start_soc_fraction:
        raise ValueError("target SOC must exceed start SOC")

    energy_wh = pack_wh * (target_soc_fraction - start_soc_fraction)
    ideal_hours = energy_wh / charger_power_w
    return {
        "pack_wh": pack_wh,
        "charger_power_w": charger_power_w,
        "start_soc_fraction": start_soc_fraction,
        "target_soc_fraction": target_soc_fraction,
        "energy_added_wh": round(energy_wh, 1),
        "ideal_lower_bound_hours": round(ideal_hours, 3),
        "ideal_lower_bound_minutes": round(ideal_hours * 60.0, 1),
        "actual_charge_time_claimed": False,
        "compatibility_claimed": False,
        "warning": (
            "Ideal energy/power lower bound only. Actual charging is longer and "
            "must use a charger explicitly approved for the selected battery system."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distance-miles", type=float)
    parser.add_argument("--terrain", choices=sorted(PLANNING_CASES))
    parser.add_argument("--pack-wh", type=float)
    parser.add_argument("--reserve", type=float, default=0.20)
    parser.add_argument("--charger-w", type=float)
    parser.add_argument("--start-soc", type=float, default=0.0)
    parser.add_argument("--target-soc", type=float, default=1.0)
    args = parser.parse_args()

    report: dict[str, object] = {
        "schema_version": 1,
        "authority": "x1_rev_c_energy_planning",
        "physical_authority": False,
        "procurement_authority": False,
        "powered_operation_authorized": False,
    }

    if args.distance_miles is not None:
        if args.terrain is None or args.pack_wh is None:
            parser.error("--distance-miles requires --terrain and --pack-wh")
        report["mission"] = MissionPlan(
            distance_miles=args.distance_miles,
            terrain=args.terrain,
            reserve_fraction=args.reserve,
            pack_wh=args.pack_wh,
        ).as_dict()

    if args.charger_w is not None:
        if args.pack_wh is None:
            parser.error("--charger-w requires --pack-wh")
        report["charge"] = ideal_charge_lower_bound(
            pack_wh=args.pack_wh,
            charger_power_w=args.charger_w,
            start_soc_fraction=args.start_soc,
            target_soc_fraction=args.target_soc,
        )

    if "mission" not in report and "charge" not in report:
        parser.error("request a mission plan, charge bound, or both")

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
