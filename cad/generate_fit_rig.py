#!/usr/bin/env python3
"""Generate non-riding Worcester X1 Fit Rig v0.3 parts.

These outputs are calibration-fixture geometry only. The load-cell mounting-hole
locations are measurement-gated. Without an explicit measurement JSON, generated
pod geometry is a reference/mock-up and must not be treated as fabrication-ready.

Example after measuring a physical load cell:

    python cad/generate_fit_rig.py \
      --measurements rider/private/fit_rig_measurements.json \
      --out rider/private/generated_fit_v03
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cadquery as cq

try:
    from cad.fit_rig_geometry import DEFAULT, FitRigGeometry
except ModuleNotFoundError:  # direct execution from cad/
    from fit_rig_geometry import DEFAULT, FitRigGeometry


BINDING_SLOT_L = 34.0
BINDING_SLOT_W = 6.5


def capsule_slot(length: float, width: float, depth: float):
    straight = length - width
    shape = cq.Workplane("XY").rect(straight, width).extrude(depth)
    shape = shape.union(
        cq.Workplane("XY").center(-straight / 2, 0).circle(width / 2).extrude(depth)
    )
    shape = shape.union(
        cq.Workplane("XY").center(straight / 2, 0).circle(width / 2).extrude(depth)
    )
    return shape


def footplate(g: FitRigGeometry):
    p = (
        cq.Workplane("XY")
        .box(
            g.footplate_length_mm,
            g.footplate_width_mm,
            g.footplate_thickness_mm,
            centered=(True, True, False),
        )
        .edges("|Z")
        .fillet(8)
    )
    for y in (-g.rail_offset_y_mm, g.rail_offset_y_mm):
        p = p.cut(
            capsule_slot(
                g.rail_slot_length_mm,
                g.rail_slot_width_mm,
                g.footplate_thickness_mm + 2,
            ).translate((0, y, 0))
        )
    for x in (-78, 78):
        for y in (-26, 26):
            p = p.cut(
                capsule_slot(
                    BINDING_SLOT_L,
                    BINDING_SLOT_W,
                    g.footplate_thickness_mm + 2,
                ).translate((x, y, 0))
            )
    p = p.cut(cq.Workplane("XY").circle(1.25).extrude(g.footplate_thickness_mm + 2))
    return p


def cant_wedge(g: FitRigGeometry, angle_deg: float):
    rise = g.footplate_width_mm * math.tan(math.radians(angle_deg))
    pts = [
        (-g.footplate_width_mm / 2, 0),
        (g.footplate_width_mm / 2, 0),
        (g.footplate_width_mm / 2, rise),
        (-g.footplate_width_mm / 2, 0),
    ]
    return cq.Workplane("YZ").polyline(pts).close().extrude(
        g.footplate_length_mm / 2, both=True
    )


def fixture_base(g: FitRigGeometry):
    """Reference base with longitudinal adjustment slots for each footplate."""
    base = cq.Workplane("XY").box(
        g.base_length_mm,
        g.base_width_mm,
        g.base_thickness_mm,
        centered=(True, True, False),
    )
    station_x = 180.0
    for sx in (-station_x, station_x):
        for y in (-g.rail_offset_y_mm, g.rail_offset_y_mm):
            base = base.cut(
                capsule_slot(150.0, 6.5, g.base_thickness_mm + 2).translate((sx, y, 0))
            )
    for x in (-55.0, 55.0):
        base = base.cut(
            capsule_slot(30.0, 5.5, g.base_thickness_mm + 2).translate((x, -120, 0))
        )
    return base


def load_cell_reference(g: FitRigGeometry):
    return cq.Workplane("XY").box(
        g.load_cell.length_mm,
        g.load_cell.width_mm,
        g.load_cell.height_mm,
        centered=(True, True, False),
    )


def _cut_measured_fixed_holes(base, g: FitRigGeometry):
    """Cut clearance holes corresponding only to explicitly measured fixed-end holes."""
    if not g.sensor_mount_fabrication_ready:
        return base
    # M5 threaded holes live in the sensor. The pod receives conservative 5.5 mm
    # clearance holes so fasteners pass through the fixture into the load cell.
    for x, y in g.load_cell.fixed_holes_xy_mm or ():
        base = base.cut(
            cq.Workplane("XY")
            .center(x, y)
            .circle(2.75)
            .extrude(g.load_cell_pod_thickness_mm + 2)
        )
    return base


def load_cell_pod(g: FitRigGeometry):
    """Pod base with overload stops and optional measured fixed-end mounting holes."""
    base = (
        cq.Workplane("XY")
        .box(
            g.load_cell_pod_length_mm,
            g.load_cell_pod_width_mm,
            g.load_cell_pod_thickness_mm,
            centered=(True, True, False),
        )
        .edges("|Z")
        .fillet(3)
    )
    base = _cut_measured_fixed_holes(base, g)

    stop_h = g.load_cell.height_mm + g.overload_stop_gap_mm
    loaded_x = g.load_cell_pod_length_mm / 2 - 16.0
    for y in (-12.0, 12.0):
        tower = (
            cq.Workplane("XY")
            .center(loaded_x, y)
            .circle(g.overload_stop_diameter_mm / 2)
            .extrude(stop_h)
        )
        base = base.union(tower)
    return base


def zone_pad(g: FitRigGeometry):
    """Heel/forefoot force-transfer pad with an underside loading button."""
    pad = (
        cq.Workplane("XY")
        .box(
            g.zone_pad_length_mm,
            g.zone_pad_width_mm,
            g.zone_pad_thickness_mm,
            centered=(True, True, False),
        )
        .edges("|Z")
        .fillet(6)
    )
    button = (
        cq.Workplane("XY")
        .circle(g.force_button_diameter_mm / 2)
        .extrude(g.force_button_height_mm)
        .translate((0, 0, -g.force_button_height_mm))
    )
    pad = pad.union(button)

    # Loaded/free-end sensor holes are represented as small datum holes in the pad
    # only after they have been measured. They are NOT assumed from nominal spacing.
    if g.sensor_mount_fabrication_ready:
        for x, y in g.load_cell.loaded_holes_xy_mm or ():
            # Convert global sensor x to pad-local coordinates with loaded end centered
            # beneath the pad. This is a datum/fixture feature, not a binding fastener.
            local_x = x - g.load_cell.length_mm / 4
            pad = pad.cut(
                cq.Workplane("XY")
                .center(local_x, y)
                .circle(2.75)
                .extrude(g.zone_pad_thickness_mm + 2)
            )
    return pad


def electronics_box(g: FitRigGeometry):
    L, W, H, wall = (
        g.electronics_box_length_mm,
        g.electronics_box_width_mm,
        g.electronics_box_height_mm,
        g.electronics_wall_mm,
    )
    outer = (
        cq.Workplane("XY")
        .box(L, W, H, centered=(True, True, False))
        .edges("|Z")
        .fillet(5)
    )
    inner = (
        cq.Workplane("XY")
        .workplane(offset=wall)
        .box(L - 2 * wall, W - 2 * wall, H, centered=(True, True, False))
    )
    box = outer.cut(inner)
    for x in (-60.0, -20.0, 20.0, 60.0):
        cut = cq.Workplane("XZ").center(x, H / 2).rect(12, 10).extrude(W, both=True)
        box = box.cut(cut)
    return box


def alignment_jig(g: FitRigGeometry):
    """Pocket gauge for repeatable sensor-envelope placement during mock-up."""
    margin = 8.0
    length = g.load_cell.length_mm + 2 * margin
    width = g.load_cell.width_mm + 2 * margin
    jig = cq.Workplane("XY").box(length, width, 4.0, centered=(True, True, False))
    pocket = (
        cq.Workplane("XY")
        .box(
            g.load_cell.length_mm + 0.4,
            g.load_cell.width_mm + 0.4,
            3.0,
            centered=(True, True, False),
        )
        .translate((0, 0, 1.5))
    )
    return jig.cut(pocket)


def load_geometry(measurements: Path | None) -> FitRigGeometry:
    if measurements is None:
        return DEFAULT
    data = json.loads(measurements.read_text(encoding="utf-8"))
    load_cell = data.get("load_cell") or {}
    fixed = load_cell.get("fixed_holes_xy_mm")
    loaded = load_cell.get("loaded_holes_xy_mm")
    if not fixed or not loaded:
        return DEFAULT
    return DEFAULT.with_load_cell_measurements(
        {"fixed_holes_xy_mm": fixed, "loaded_holes_xy_mm": loaded}
    )


def export(out: Path, name: str, shape):
    cq.exporters.export(shape, str(out / f"{name}.step"))
    cq.exporters.export(
        shape,
        str(out / f"{name}.stl"),
        tolerance=0.12,
        angularTolerance=0.15,
    )


def write_authority_report(out: Path, g: FitRigGeometry):
    (out / "fit_rig_authority.json").write_text(
        json.dumps(g.authority_report(), indent=2) + "\n", encoding="utf-8"
    )


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--measurements",
        type=Path,
        help="private JSON containing directly measured load-cell hole centers",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "generated_fit",
    )
    return p.parse_args()


def main():
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    g = load_geometry(args.measurements)
    errors = g.validate()
    if errors:
        raise SystemExit("Invalid fit-rig geometry: " + "; ".join(errors))

    export(args.out, "fit_fixture_base_reference", fixture_base(g))
    export(args.out, "fit_footplate_universal", footplate(g))
    export(args.out, "fit_zone_pad", zone_pad(g))
    export(args.out, "fit_load_cell_pod_reference", load_cell_pod(g))
    export(args.out, "fit_load_cell_envelope_reference", load_cell_reference(g))
    export(args.out, "fit_electronics_box_reference", electronics_box(g))
    export(args.out, "fit_load_cell_alignment_jig", alignment_jig(g))
    for deg in (1, 2, 3, 4):
        export(args.out, f"fit_cant_wedge_{deg}deg", cant_wedge(g, float(deg)))
    write_authority_report(args.out, g)

    state = "FABRICATION READY" if g.sensor_mount_fabrication_ready else "MEASUREMENT GATED"
    print(f"Generated unpowered Fit Rig v0.3 parts in {args.out} [{state}]")


if __name__ == "__main__":
    main()
