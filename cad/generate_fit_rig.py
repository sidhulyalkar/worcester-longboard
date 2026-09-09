#!/usr/bin/env python3
"""Generate non-riding adjustable X1 fit-rig parts.

These parts are for stance calibration only. They are not qualified as structural
riding components.
"""
from pathlib import Path
import cadquery as cq

OUT=Path(__file__).resolve().parent/"generated_fit"
OUT.mkdir(parents=True, exist_ok=True)

PLATE_L=260.0
PLATE_W=132.0
PLATE_T=6.0
TRACK_SLOT_L=105.0
TRACK_SLOT_W=6.5
TRACK_Y=42.0
BINDING_SLOT_L=34.0
BINDING_SLOT_W=6.5


def capsule_slot(length: float, width: float, depth: float):
    straight=length-width
    shape=cq.Workplane("XY").rect(straight,width).extrude(depth)
    shape=shape.union(cq.Workplane("XY").center(-straight/2,0).circle(width/2).extrude(depth))
    shape=shape.union(cq.Workplane("XY").center(straight/2,0).circle(width/2).extrude(depth))
    return shape


def footplate():
    p=cq.Workplane("XY").box(PLATE_L,PLATE_W,PLATE_T,centered=(True,True,False)).edges("|Z").fillet(8)
    for y in (-TRACK_Y, TRACK_Y):
        p=p.cut(capsule_slot(TRACK_SLOT_L,TRACK_SLOT_W,PLATE_T+2).translate((0,y,0)))
    for x in (-78,78):
        for y in (-26,26):
            p=p.cut(capsule_slot(BINDING_SLOT_L,BINDING_SLOT_W,PLATE_T+2).translate((x,y,0)))
    p=p.cut(cq.Workplane("XY").circle(1.25).extrude(PLATE_T+2))
    return p


def cant_wedge(angle_deg: float):
    import math
    rise=PLATE_W*math.tan(math.radians(angle_deg))
    pts=[(-PLATE_W/2,0),(PLATE_W/2,0),(PLATE_W/2,rise),(-PLATE_W/2,0)]
    return cq.Workplane("YZ").polyline(pts).close().extrude(PLATE_L/2,both=True)


def export(name,shape):
    cq.exporters.export(shape,str(OUT/f"{name}.step"))
    cq.exporters.export(shape,str(OUT/f"{name}.stl"),tolerance=0.12,angularTolerance=0.15)


if __name__ == "__main__":
    export("fit_footplate_universal", footplate())
    for deg in (1,2,3,4):
        export(f"fit_cant_wedge_{deg}deg", cant_wedge(float(deg)))
    print("Generated unpowered fit-rig parts in", OUT)
