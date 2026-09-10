#!/usr/bin/env python3
"""Generate non-riding Worcester X1 Fit Rig v0.3 parts.

These outputs are calibration-fixture geometry only.  The load-cell mounting-hole
locations are intentionally measurement-gated.  Until physical sensors are
measured, generated pod geometry is a reference/mock-up and must not be treated as
fabrication-authoritative.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cadquery as cq

try:
    from cad.fit_rig_geometry import DEFAULT as G
except ModuleNotFoundError:  # direct execution from cad/
    from fit_rig_geometry import DEFAULT as G


OUT = Path(__file__).resolve().parent / "generated_fit"
OUT.mkdir(parents=True, exist_ok=True)

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


def footplate():
    p = (
        cq.Workplane("XY")
        .box(G.footplate_length_mm, G.footplate_width_mm, G.footplate_thickness_mm,
             centered=(True, True, False))
        .edges("|Z")
        .fillet(8)
    )
    for y in (-G.rail_offset_y_mm, G.rail_offset_y_mm):
        p = p.cut(
            capsule_slot(G.rail_slot_length_mm, G.rail_slot_width_mm,
                         G.footplate_thickness_mm + 2).translate((0, y, 0))
        )
    for x in (-78, 78):
        for y in (-26, 26):
            p = p.cut(
                capsule_slot(BINDING_SLOT_L, BINDING_SLOT_W,
                             G.footplate_thickness_mm + 2).translate((x, y, 0))
            )
    # Small center datum hole, not a riding fastener.
    p = p.cut(cq.Workplane("XY").circle(1.25).extrude(G.footplate_thickness_mm + 2))
    return p


def cant_wedge(angle_deg: float):
    rise = G.footplate_width_mm * math.tan(math.radians(angle_deg))
    pts = [
        (-G.footplate_width_mm / 2, 0),
        (G.footplate_width_mm / 2, 0),
        (G.footplate_width_mm / 2, rise),
        (-G.footplate_width_mm / 2, 0),
    ]
    return cq.Workplane("YZ").polyline(pts).close().extrude(G.footplate_length_mm / 2, both=True)


def fixture_base():
    """Reference base with longitudinal adjustment slots for each footplate."""
    base = cq.Workplane("XY").box(
        G.base_length_mm, G.base_width_mm, G.base_thickness_mm, centered=(True, True, False)
    )
    # Two left/right stance stations.  Long slots make the rig adjustable before
    # rider-specific stance width is known.
    station_x = 180.0
    for sx in (-station_x, station_x):
        for y in (-G.rail_offset_y_mm, G.rail_offset_y_mm):
            base = base.cut(
                capsule_slot(150.0, 6.5, G.base_thickness_mm + 2).translate((sx, y, 0))
            )
    # Electronics-box reference mounting slots along rear edge.
    for x in (-55.0, 55.0):
        base = base.cut(capsule_slot(30.0, 5.5, G.base_thickness_mm + 2).translate((x, -120, 0)))
    return base


def load_cell_reference():
    """Non-manufacturing envelope for collision/alignment visualization only."""
    return cq.Workplane("XY").box(
        G.load_cell.length_mm, G.load_cell.width_mm, G.load_cell.height_mm,
        centered=(True, True, False),
    )


def load_cell_pod():
    """Pod base with overload stops and a load-cell reference envelope.

    Mounting holes are intentionally omitted until the physical sensor hole centers
    are measured.  The returned assembly-like solid is for placement/clearance
    review and print mock-ups, not final sensor mounting.
    """
    base = (
        cq.Workplane("XY")
        .box(G.load_cell_pod_length_mm, G.load_cell_pod_width_mm,
             G.load_cell_pod_thickness_mm, centered=(True, True, False))
        .edges("|Z")
        .fillet(3)
    )
    # Hard-stop towers flank the loaded end. Their final height is deliberately
    # trimmed only after the actual sensor + transfer pad deflection is measured.
    stop_h = G.load_cell.height_mm + G.overload_stop_gap_mm
    loaded_x = G.load_cell_pod_length_mm / 2 - 16.0
    for y in (-12.0, 12.0):
        tower = (
            cq.Workplane("XY")
            .center(loaded_x, y)
            .circle(G.overload_stop_diameter_mm / 2)
            .extrude(stop_h)
        )
        base = base.union(tower)
    return base


def zone_pad():
    """Heel/forefoot force-transfer pad with a small underside load button."""
    pad = (
        cq.Workplane("XY")
        .box(G.zone_pad_length_mm, G.zone_pad_width_mm, G.zone_pad_thickness_mm,
             centered=(True, True, False))
        .edges("|Z")
        .fillet(6)
    )
    button = (
        cq.Workplane("XY")
        .circle(G.force_button_diameter_mm / 2)
        .extrude(G.force_button_height_mm)
        .translate((0, 0, -G.force_button_height_mm))
    )
    return pad.union(button)


def electronics_box():
    """Simple low-voltage logger enclosure with cable-entry reliefs."""
    L, W, H, wall = (
        G.electronics_box_length_mm,
        G.electronics_box_width_mm,
        G.electronics_box_height_mm,
        G.electronics_wall_mm,
    )
    outer = cq.Workplane("XY").box(L, W, H, centered=(True, True, False)).edges("|Z").fillet(5)
    inner = (
        cq.Workplane("XY")
        .workplane(offset=wall)
        .box(L - 2 * wall, W - 2 * wall, H, centered=(True, True, False))
    )
    box = outer.cut(inner)
    # Four generous low-voltage cable windows. Exact glands are chosen later.
    for x in (-60.0, -20.0, 20.0, 60.0):
        cut = cq.Workplane("XZ").center(x, H / 2).rect(12, 10).extrude(W, both=True)
        box = box.cut(cut)
    return box


def alignment_jig():
    """Pocketed gauge for repeatable load-cell envelope placement during mock-up."""
    margin = 8.0
    L = G.load_cell.length_mm + 2 * margin
    W = G.load_cell.width_mm + 2 * margin
    jig = cq.Workplane("XY").box(L, W, 4.0, centered=(True, True, False))
    pocket = (
        cq.Workplane("XY")
        .box(G.load_cell.length_mm + 0.4, G.load_cell.width_mm + 0.4, 3.0,
             centered=(True, True, False))
        .translate((0, 0, 1.5))
    )
    return jig.cut(pocket)


def export(name: str, shape):
    cq.exporters.export(shape, str(OUT / f"{name}.step"))
    cq.exporters.export(shape, str(OUT / f"{name}.stl"), tolerance=0.12, angularTolerance=0.15)


def write_authority_report():
    (OUT / "fit_rig_authority.json").write_text(
        json.dumps(G.authority_report(), indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    errors = G.validate()
    if errors:
        raise SystemExit("Invalid fit-rig geometry: " + "; ".join(errors))

    export("fit_fixture_base_reference", fixture_base())
    export("fit_footplate_universal", footplate())
    export("fit_zone_pad", zone_pad())
    export("fit_load_cell_pod_reference", load_cell_pod())
    export("fit_load_cell_envelope_reference", load_cell_reference())
    export("fit_electronics_box_reference", electronics_box())
    export("fit_load_cell_alignment_jig", alignment_jig())
    for deg in (1, 2, 3, 4):
        export(f"fit_cant_wedge_{deg}deg", cant_wedge(float(deg)))
    write_authority_report()

    state = "FABRICATION READY" if G.sensor_mount_fabrication_ready else "MEASUREMENT GATED"
    print(f"Generated unpowered Fit Rig v0.3 reference parts in {OUT} [{state}]")
