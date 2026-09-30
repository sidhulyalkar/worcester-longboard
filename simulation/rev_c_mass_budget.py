#!/usr/bin/env python3
"""Rev-C finished-mass budget helper.

This is a bookkeeping tool, not a structural or performance model. It makes
mass assumptions explicit and reports how much target mass remains for
unbudgeted subsystems.

Reference masses below are current published commercial benchmarks only. Their
presence does not imply compatibility or selection.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

LB_PER_KG = 2.2046226218

REFERENCE_MASS_LB = {
    "comp95_unpowered": 14.6,
    "pro_warren_iii_unpowered": 15.9,
    "mbs_agent_540_battery": 15.0,
    "mbs_agent_1080_battery": 20.0,
}

TARGET_MASS_LB = {
    "trail": 35.0,
    "range": 45.0,
}


@dataclass(frozen=True)
class MassBudget:
    target_mass_lb: float
    known_components_lb: dict[str, float]

    @property
    def known_mass_lb(self) -> float:
        return sum(self.known_components_lb.values())

    @property
    def remaining_headroom_lb(self) -> float:
        return self.target_mass_lb - self.known_mass_lb

    @property
    def target_exceeded_by_known_parts(self) -> bool:
        return self.remaining_headroom_lb < 0

    def as_dict(self) -> dict:
        return {
            "target_mass_lb": round(self.target_mass_lb, 2),
            "known_components_lb": {
                key: round(value, 2) for key, value in self.known_components_lb.items()
            },
            "known_mass_lb": round(self.known_mass_lb, 2),
            "remaining_headroom_lb": round(self.remaining_headroom_lb, 2),
            "target_exceeded_by_known_parts": self.target_exceeded_by_known_parts,
            "interpretation": (
                "Remaining headroom must still cover every omitted subsystem. "
                "A positive number does not prove the finished target is achievable."
            ),
        }


def reference_budget(configuration: str, chassis: str = "comp95") -> MassBudget:
    chassis_key = {
        "comp95": "comp95_unpowered",
        "pro_warren_iii": "pro_warren_iii_unpowered",
    }.get(chassis)
    if chassis_key is None:
        raise ValueError("chassis must be 'comp95' or 'pro_warren_iii'")

    if configuration == "trail":
        battery_key = "mbs_agent_540_battery"
        battery_label = "mbs_540_battery_reference"
    elif configuration == "range":
        battery_key = "mbs_agent_1080_battery"
        battery_label = "mbs_1080_battery_reference"
    else:
        raise ValueError("configuration must be 'trail' or 'range'")

    components = {
        f"unpowered_{chassis}_reference": REFERENCE_MASS_LB[chassis_key],
        battery_label: REFERENCE_MASS_LB[battery_key],
    }
    return MassBudget(
        target_mass_lb=TARGET_MASS_LB[configuration],
        known_components_lb=components,
    )


def custom_budget(target_mass_lb: float, components: dict[str, float]) -> MassBudget:
    if target_mass_lb <= 0:
        raise ValueError("target_mass_lb must be positive")
    if not components:
        raise ValueError("at least one component mass is required")
    for name, value in components.items():
        if not name or value < 0:
            raise ValueError("component names must be nonempty and masses nonnegative")
    return MassBudget(target_mass_lb=target_mass_lb, known_components_lb=components)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--configuration",
        choices=("trail", "range"),
        help="emit the current commercial-reference lower-bound budget",
    )
    parser.add_argument(
        "--chassis",
        choices=("comp95", "pro_warren_iii"),
        default="comp95",
        help="published complete unpowered chassis mass reference",
    )
    parser.add_argument("--target-lb", type=float)
    parser.add_argument(
        "--component",
        action="append",
        default=[],
        help="custom component as NAME=MASS_LB; may be repeated",
    )
    args = parser.parse_args()

    if args.configuration:
        budget = reference_budget(args.configuration, args.chassis)
    else:
        if args.target_lb is None or not args.component:
            parser.error("use --configuration or provide --target-lb plus --component")
        components: dict[str, float] = {}
        for raw in args.component:
            if "=" not in raw:
                parser.error("--component must be NAME=MASS_LB")
            name, raw_value = raw.split("=", 1)
            components[name] = float(raw_value)
        budget = custom_budget(args.target_lb, components)

    print(json.dumps(budget.as_dict(), indent=2))


if __name__ == "__main__":
    main()
