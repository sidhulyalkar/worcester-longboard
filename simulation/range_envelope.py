#!/usr/bin/env python3
"""Conservative planning envelope for Worcester X1 range.

This is deliberately not a physics-perfect vehicle model. It converts nominal
pack energy, reserve policy, and measured/planning Wh/mi into an auditable trip
range. Replace planning consumption with X1 telemetry as soon as qualified ride
data exists.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class RangeEnvelope:
    nominal_wh: float
    reserve_fraction: float
    wh_per_mile_low: float
    wh_per_mile_high: float

    def validate(self) -> None:
        if self.nominal_wh <= 0:
            raise ValueError("nominal_wh must be positive")
        if not 0 <= self.reserve_fraction < 1:
            raise ValueError("reserve_fraction must be in [0, 1)")
        if self.wh_per_mile_low <= 0 or self.wh_per_mile_high <= 0:
            raise ValueError("Wh/mi values must be positive")
        if self.wh_per_mile_low > self.wh_per_mile_high:
            raise ValueError("wh_per_mile_low cannot exceed wh_per_mile_high")

    @property
    def usable_wh(self) -> float:
        self.validate()
        return self.nominal_wh * (1.0 - self.reserve_fraction)

    @property
    def conservative_miles(self) -> float:
        return self.usable_wh / self.wh_per_mile_high

    @property
    def optimistic_miles(self) -> float:
        return self.usable_wh / self.wh_per_mile_low

    def as_dict(self) -> dict:
        return {
            "nominal_wh": self.nominal_wh,
            "reserve_fraction": self.reserve_fraction,
            "usable_wh": round(self.usable_wh, 1),
            "wh_per_mile": [self.wh_per_mile_low, self.wh_per_mile_high],
            "range_miles": [
                round(self.conservative_miles, 1),
                round(self.optimistic_miles, 1),
            ],
        }


PLANNING_CASES = {
    "mixed": (22.0, 30.0),
    "trail": (32.0, 45.0),
}


def planning_envelope(
    nominal_wh: float,
    terrain: str,
    reserve_fraction: float = 0.20,
) -> RangeEnvelope:
    if terrain not in PLANNING_CASES:
        raise ValueError(f"unknown terrain {terrain!r}; choose {sorted(PLANNING_CASES)}")
    low, high = PLANNING_CASES[terrain]
    return RangeEnvelope(
        nominal_wh=nominal_wh,
        reserve_fraction=reserve_fraction,
        wh_per_mile_low=low,
        wh_per_mile_high=high,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack-wh", type=float, required=True)
    parser.add_argument("--terrain", choices=sorted(PLANNING_CASES), required=True)
    parser.add_argument("--reserve", type=float, default=0.20)
    return parser


def main() -> None:
    args = _parser().parse_args()
    report = planning_envelope(args.pack_wh, args.terrain, args.reserve).as_dict()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
