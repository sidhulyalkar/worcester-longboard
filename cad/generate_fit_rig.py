#!/usr/bin/env python3
"""Generate non-riding Worcester X1 Fit Rig v0.3 parts.

The current Phidgets 3135 drawing provides a two-hole, 40 mm center-spacing
single-point load-cell pattern. X1 uses that vendor pattern for a one-zone pilot,
then requires physical verification before four final pods are duplicated.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cadquery as cq

try:
    from cad.fit_rig_geometry import DEFAULT, FitRigGeometry
except ModuleNotFoundError:
    from fit_rig_geometry import DEFAULT, FitRigGeometry

BINDING_SLOT_L = 34.0
BINDING_SLOT_W = 6.5


def capsule_slot(length: float, width: float, depth: float):
    straight = length - width
    shape = cq.Workplane("XY").rect(straight, width).extrude(depth)
    shape = shape.union(cq.Workplane("XY").center(-straight / 2, 0).circle(width / 2).extrude(depth))
    shape = shape.union(cq.Workplane("XY").center(straight / 2, 0).circle(width / 2).extrude(depth))
    return shape


def footplate(g: FitRigGeometry):
    p = (
        cq.Workplane("XY")
        .box(g.footplate_length_mm, g.footplate_width_mm, g.footplate_thickness_mm,
             centered=(True, True, False))
        .edges("|Z").fillet(8)
    )
    for y in (-g.rail_offset_y_mm, g.rail_offset_y_mm):
        p = p.cut(capsule_slot(g.rail_slot_length_mm, g.rail_slot_width_mm,
                               g.footplate_thickness_mm + 2).translate((0, y, 0)))
    for x in (-78, 78):
        for y in (-26, 26):
            p = p.cut(capsule_slot(BINDING_SLOT_L, BINDING_SLOT_W,
                                   g.footplate_thickness_mm + 2).translate((x, y, 0)))
    return p.cut(cq.Workplane("XY").circle(1.25).extrude(g.footplate_thickness_mm + 2))


def cant_wedge(g: FitRigGeometry, angle_deg: float):
    rise = g.footplate_width_mm * math.tan(math.radians(angle_deg))
    pts = [(-g.footplate_width_mm / 2, 0), (g.footplate_width_mm / 2, 0),
           (g.footplate_width_mm / 2, rise), (-g.footplate_width_mm / 2, 0)]
    return cq.Workplane("YZ").polyline(pts).close().extrude(g.footplate_length_mm / 2, both=True)


def fixture_base(g: FitRigGeometry):
    base = cq.Workplane("XY").box(g.base_length_mm, g.base_width_mm, g.base_thickness_mm,
                                   centered=(True, True, False))
    for sx in (-180.0, 180.0):
        for y in (-g.rail_offset_y_mm, g.rail_offset_y_mm):
            base = base.cut(capsule_slot(150.0, 6.5, g.base_thickness_mm + 2).translate((sx, y, 0)))
    for x in (-55.0, 55.0):
        base = base.cut(capsule_slot(30.0, 5.5, g.base_thickness_mm + 2).translate((x, -120, 0)))
    return base


def load_cell_reference(g: FitRigGeometry):
    cell = cq.Workplane("XY").box(g.load_cell.length_mm, g.load_cell.width_mm,
                                   g.load_cell.height_mm, centered=(True, True, False))
    for x, y in (g.load_cell.fixed_hole_xy_mm, g.load_cell.loaded_hole_xy_mm):
        cell = cell.cut(cq.Workplane("XY").center(x, y).circle(2.5).extrude(g.load_cell.height_mm + 2))
    return cell


def load_cell_pod(g: FitRigGeometry):
    """Base-side pod: one M5 clearance hole fixes the wire end of the cell."""
    base = (
        cq.Workplane("XY")
        .box(g.load_cell_pod_length_mm, g.load_cell_pod_width_mm,
             g.load_cell_pod_thickness_mm, centered=(True, True, False))
        .edges("|Z").fillet(3)
    )
    if g.sensor_mount_pilot_ready:
        x, y = g.load_cell.fixed_hole_xy_mm
        base = base.cut(cq.Workplane("XY").center(x, y).circle(2.75)
                        .extrude(g.load_cell_pod_thickness_mm + 2))

    # Towers start at the pod bottom. Their top must sit `gap` below the nominal
    # zone-pad bottom, not merely `cell height + gap` above Z=0.
    stop_h = g.nominal_overload_stop_top_z_mm
    loaded_x = g.load_cell.loaded_hole_xy_mm[0]
    for y in (-12.0, 12.0):
        base = base.union(cq.Workplane("XY").center(loaded_x, y)
                          .circle(g.overload_stop_diameter_mm / 2).extrude(stop_h))
    return base


def zone_pad(g: FitRigGeometry):
    """Heel/forefoot platform bolted directly to the loaded/free sensor end."""
    pad = (
        cq.Workplane("XY")
        .box(g.zone_pad_length_mm, g.zone_pad_width_mm, g.zone_pad_thickness_mm,
             centered=(True, True, False))
        .edges("|Z").fillet(6)
    )
    if g.sensor_mount_pilot_ready:
        x, y = g.load_cell.loaded_hole_xy_mm
        pad = pad.cut(cq.Workplane("XY").center(x, y).circle(2.75)
                      .extrude(g.zone_pad_thickness_mm + 2))
    return pad


def electronics_box(g: FitRigGeometry):
    L, W, H, wall = (g.electronics_box_length_mm, g.electronics_box_width_mm,
                     g.electronics_box_height_mm, g.electronics_wall_mm)
    outer = cq.Workplane("XY").box(L, W, H, centered=(True, True, False)).edges("|Z").fillet(5)
    inner = cq.Workplane("XY").workplane(offset=wall).box(L - 2 * wall, W - 2 * wall, H,
                                                               centered=(True, True, False))
    box = outer.cut(inner)
    for x in (-60.0, -20.0, 20.0, 60.0):
        box = box.cut(cq.Workplane("XZ").center(x, H / 2).rect(12, 10).extrude(W, both=True))
    return box


def alignment_jig(g: FitRigGeometry):
    margin = 8.0
    length = g.load_cell.length_mm + 2 * margin
    width = g.load_cell.width_mm + 2 * margin
    jig = cq.Workplane("XY").box(length, width, 4.0, centered=(True, True, False))
    pocket = cq.Workplane("XY").box(g.load_cell.length_mm + 0.4,
                                      g.load_cell.width_mm + 0.4, 3.0,
                                      centered=(True, True, False)).translate((0, 0, 1.5))
    return jig.cut(pocket)


def load_geometry(verification: Path | None) -> FitRigGeometry:
    if verification is None:
        return DEFAULT
    data = json.loads(verification.read_text(encoding="utf-8"))
    cell = data.get("load_cell") or {}
    fixed = cell.get("fixed_hole_xy_mm")
    loaded = cell.get("loaded_hole_xy_mm")
    if fixed is None or loaded is None:
        return DEFAULT
    return DEFAULT.with_load_cell_verification({
        "fixed_hole_xy_mm": fixed,
        "loaded_hole_xy_mm": loaded,
    })


def export(out: Path, name: str, shape):
    cq.exporters.export(shape, str(out / f"{name}.step"))
    cq.exporters.export(shape, str(out / f"{name}.stl"), tolerance=0.12, angularTolerance=0.15)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--measurements", type=Path,
                   help="private verification JSON for one physical 3135 load cell")
    p.add_argument("--out", type=Path,
                   default=Path(__file__).resolve().parent / "generated_fit")
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

    report = g.authority_report()
    (args.out / "fit_rig_authority.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    state = "FOUR-POD READY" if g.sensor_mount_fabrication_ready else "ONE-ZONE PILOT READY"
    print(f"Generated unpowered Fit Rig v0.3 parts in {args.out} [{state}]")


if __name__ == "__main__":
    main()
