#!/usr/bin/env python3
"""Generate Worcester X1 unpowered rolling-chassis packaging references."""
from __future__ import annotations

import json
from pathlib import Path

import cadquery as cq

from cad.generate_fit_rig import export
from cad.rolling_chassis_geometry import BRAKE_FIRST, DRIVE_CLEARANCE, ChassisEnvelope


def deck_reference(g: ChassisEnvelope):
    return (
        cq.Workplane("XY")
        .box(g.deck_length_mm, g.deck_max_width_mm, g.deck_reference_thickness_mm,
             centered=(True, True, False))
        .edges("|Z").fillet(18)
        .translate((0, 0, g.static_ground_clearance_mm))
    )


def rider_keepout(g: ChassisEnvelope):
    return cq.Workplane("XY").box(
        g.rider_interface_keepout_length_mm,
        g.rider_interface_keepout_width_mm,
        4.0,
        centered=(True, True, False),
    ).translate((0, 0, g.static_ground_clearance_mm + g.deck_reference_thickness_mm + 2.0))


def ground_reference(g: ChassisEnvelope):
    return cq.Workplane("XY").box(
        g.deck_length_mm + 300.0,
        g.truck.total_width_mm + g.wheel.width_mm + 100.0,
        1.0,
        centered=(True, True, False),
    )


def truck_reference(g: ChassisEnvelope, x: float):
    return cq.Workplane("XY").box(
        28.0,
        g.truck.total_width_mm,
        18.0,
        centered=(True, True, False),
    ).translate((x, 0, g.static_ground_clearance_mm - 18.0))


def wheel_reference(g: ChassisEnvelope, x: float, y: float, steer_deg: float):
    # Ground is Z=0 and wheel center is one radius above ground. Wheel axis lies
    # along Y; yaw is a conservative plan-view packaging reference.
    wheel = (
        cq.Workplane("XZ")
        .circle(g.wheel_radius_mm)
        .extrude(g.wheel.width_mm / 2.0, both=True)
    )
    return wheel.rotate((0, 0, 0), (0, 0, 1), steer_deg).translate((x, y, g.wheel_radius_mm))


def rotor_reference(g: ChassisEnvelope, x: float, y: float, steer_deg: float):
    rotor = (
        cq.Workplane("XZ")
        .circle(g.brake_rotor_reference_diameter_mm / 2.0)
        .circle(g.brake_rotor_reference_diameter_mm / 2.0 - 3.0)
        .extrude(1.0, both=True)
    )
    return rotor.rotate((0, 0, 0), (0, 0, 1), steer_deg).translate((x, y, g.wheel_radius_mm))


def assembly(g: ChassisEnvelope, steer_deg: float = 0.0):
    result = ground_reference(g).union(deck_reference(g)).union(rider_keepout(g))
    axle_x = g.wheelbase_mm / 2.0
    wheel_y = g.truck.total_width_mm / 2.0
    for x in (-axle_x, axle_x):
        result = result.union(truck_reference(g, x))
        axle_sign = -1 if x < 0 else 1
        for y in (-wheel_y, wheel_y):
            wheel_steer = axle_sign * steer_deg
            result = result.union(wheel_reference(g, x, y, wheel_steer))
            if g.truck.brake_reference_compatible:
                result = result.union(rotor_reference(g, x, y, wheel_steer))
    return result


def sweep_envelope(g: ChassisEnvelope):
    # Union neutral and both steering extremes to create a deliberately chunky
    # keep-out volume useful for interference analysis.
    out = assembly(g, 0.0)
    for angle in (-g.truck.max_steer_deg, g.truck.max_steer_deg):
        out = out.union(assembly(g, angle))
    return out


def main() -> None:
    out = Path(__file__).resolve().parent / "generated_chassis"
    out.mkdir(parents=True, exist_ok=True)
    for name, geometry in (
        ("brake_first_400mm", BRAKE_FIRST),
        ("drive_clearance_420mm", DRIVE_CLEARANCE),
    ):
        errors = geometry.validate()
        if errors:
            raise SystemExit(f"{name}: " + "; ".join(errors))
        export(out, f"x1_chassis_{name}_neutral", assembly(geometry, 0.0))
        export(out, f"x1_chassis_{name}_sweep", sweep_envelope(geometry))
        (out / f"x1_chassis_{name}_authority.json").write_text(
            json.dumps(geometry.authority_report(), indent=2) + "\n", encoding="utf-8"
        )
    print(f"Generated unpowered rolling-chassis references in {out} [NOT FABRICATION READY]")


if __name__ == "__main__":
    main()
