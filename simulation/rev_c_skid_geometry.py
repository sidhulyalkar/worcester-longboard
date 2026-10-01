#!/usr/bin/env python3
"""Geometric clearance study for Worcester X1 skid / armor candidates.

This is a rigid 2D geometry calculation only. It does not include tire
compression, truck roll, deck flex, suspension, terrain compliance, dynamic
pitch, rider motion, or impact deformation, so it cannot qualify trail
clearance by itself.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SkidGeometry:
    wheelbase_mm: float
    skid_x_from_front_axle_mm: float
    vulnerable_component_clearance_mm: float
    skid_drop_below_component_mm: float

    def validate(self) -> None:
        vals = (
            self.wheelbase_mm,
            self.skid_x_from_front_axle_mm,
            self.vulnerable_component_clearance_mm,
            self.skid_drop_below_component_mm,
        )
        if not all(math.isfinite(v) for v in vals):
            raise ValueError("all geometry inputs must be finite")
        if self.wheelbase_mm <= 0:
            raise ValueError("wheelbase_mm must be positive")
        if not 0 < self.skid_x_from_front_axle_mm < self.wheelbase_mm:
            raise ValueError(
                "skid_x_from_front_axle_mm must lie between the axles"
            )
        if self.vulnerable_component_clearance_mm <= 0:
            raise ValueError(
                "vulnerable_component_clearance_mm must be positive"
            )
        if self.skid_drop_below_component_mm < 0:
            raise ValueError(
                "skid_drop_below_component_mm cannot be negative"
            )
        if self.skid_clearance_mm <= 0:
            raise ValueError(
                "skid_drop_below_component_mm consumes all ground clearance"
            )

    @property
    def skid_clearance_mm(self) -> float:
        return (
            self.vulnerable_component_clearance_mm
            - self.skid_drop_below_component_mm
        )

    def _breakover_deg(self, clearance_mm: float) -> float:
        front_run = self.skid_x_from_front_axle_mm
        rear_run = self.wheelbase_mm - self.skid_x_from_front_axle_mm
        return math.degrees(
            math.atan2(clearance_mm, front_run)
            + math.atan2(clearance_mm, rear_run)
        )

    @property
    def component_breakover_deg(self) -> float:
        return self._breakover_deg(self.vulnerable_component_clearance_mm)

    @property
    def skid_breakover_deg(self) -> float:
        return self._breakover_deg(self.skid_clearance_mm)

    def as_dict(self) -> dict:
        self.validate()
        component = self.component_breakover_deg
        skid = self.skid_breakover_deg
        return {
            "wheelbase_mm": self.wheelbase_mm,
            "skid_x_from_front_axle_mm": self.skid_x_from_front_axle_mm,
            "vulnerable_component_clearance_mm": (
                self.vulnerable_component_clearance_mm
            ),
            "skid_drop_below_component_mm": (
                self.skid_drop_below_component_mm
            ),
            "skid_clearance_mm": round(self.skid_clearance_mm, 3),
            "rigid_2d_component_breakover_deg": round(component, 3),
            "rigid_2d_skid_breakover_deg": round(skid, 3),
            "rigid_2d_breakover_loss_deg": round(component - skid, 3),
            "clearance_consumed_fraction": round(
                self.skid_drop_below_component_mm
                / self.vulnerable_component_clearance_mm,
                4,
            ),
            "physical_authority": False,
            "impact_authority": False,
            "warning": (
                "Rigid 2D geometry only. Re-evaluate using measured loaded tire "
                "radius, deck flex/lean, steering state, and physical surrogate "
                "testing before any trail-clearance decision."
            ),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheelbase-mm", type=float, required=True)
    parser.add_argument("--skid-x-mm", type=float, required=True)
    parser.add_argument("--component-clearance-mm", type=float, required=True)
    parser.add_argument("--skid-drop-mm", type=float, required=True)
    args = parser.parse_args()

    report = SkidGeometry(
        wheelbase_mm=args.wheelbase_mm,
        skid_x_from_front_axle_mm=args.skid_x_mm,
        vulnerable_component_clearance_mm=args.component_clearance_mm,
        skid_drop_below_component_mm=args.skid_drop_mm,
    ).as_dict()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
