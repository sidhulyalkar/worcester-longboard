#!/usr/bin/env python3
"""Worcester X1 Alpha parametric CAD generator.

Custom parts are deliberately isolated from purchased load-path parts.
Dimensions are millimetres. Generated geometry is measurement-gated where the
vendor does not publish a trustworthy interface dimension.
"""
from pathlib import Path
import cadquery as cq
import ezdxf

OUT = Path(__file__).resolve().parent / "generated"
OUT.mkdir(parents=True, exist_ok=True)

DECK_LENGTH=912.0
DECK_WIDTH=228.0
DECK_REF_THICKNESS=13.0
WHEEL_DIAMETER=203.2
WHEEL_WIDTH=50.0
TRACK_WIDTH=419.1
WHEELBASE=945.0

CASE_L=330.0; CASE_W=188.0; CASE_H=58.0
CASE_WALL=4.0; CASE_FLOOR=4.0; CASE_CORNER_R=10.0
LID_PLATE=3.0; LID_LIP_H=3.0; LID_LIP_T=2.0
GASKET_GROOVE_W=2.6; GASKET_GROOVE_D=1.5

CELL_D=21.55; CELL_H=70.15; CELL_CLEAR=1.8
CELL_BLOCK_L=4*CELL_H+3*CELL_CLEAR
CELL_BLOCK_W=7*CELL_D+6*CELL_CLEAR
CELL_BLOCK_H=2*CELL_D+CELL_CLEAR

EAR_L=38.0; EAR_W=14.0; EAR_T=5.0
EAR_SLOT_L=18.0; EAR_SLOT_D=5.5; EAR_X=110.0
LID_HOLE_D=4.4; BOSS_OD=10.0
BOSS_X=[-(CASE_L/2-16),-55.0,55.0,CASE_L/2-16]
BOSS_Y=[-(CASE_W/2-10),CASE_W/2-10]
TRAY_L=235.0; TRAY_W=150.0; TRAY_T=3.0
TRAY_SLOT_L=28.0; TRAY_SLOT_W=4.5


def rounded_box_xy(length,width,height,radius):
    return cq.Workplane("XY").box(length,width,height,centered=(True,True,False)).edges("|Z").fillet(radius)


def make_base():
    outer=rounded_box_xy(CASE_L,CASE_W,CASE_H,CASE_CORNER_R)
    inner=(cq.Workplane("XY").workplane(offset=CASE_FLOOR)
           .box(CASE_L-2*CASE_WALL,CASE_W-2*CASE_WALL,CASE_H-CASE_FLOOR+1,centered=(True,True,False))
           .edges("|Z").fillet(max(1,CASE_CORNER_R-CASE_WALL)))
    base=outer.cut(inner)
    for x in BOSS_X:
        for y in BOSS_Y:
            base=base.union(cq.Workplane("XY").center(x,y).circle(BOSS_OD/2).extrude(CASE_H-4))
            base=base.cut(cq.Workplane("XY").center(x,y).circle(3.3/2).extrude(CASE_H+2))
    for x in (-EAR_X,EAR_X):
        for ysign in (-1,1):
            y=ysign*(CASE_W/2+EAR_W/2-1)
            base=base.union(cq.Workplane("XY").center(x,y).box(EAR_L,EAR_W,EAR_T,centered=(True,True,False)))
            slot=cq.Workplane("XY").center(x,y).rect(EAR_SLOT_L-EAR_SLOT_D,EAR_SLOT_D).extrude(EAR_T+2)
            slot=slot.union(cq.Workplane("XY").center(x-(EAR_SLOT_L-EAR_SLOT_D)/2,y).circle(EAR_SLOT_D/2).extrude(EAR_T+2))
            slot=slot.union(cq.Workplane("XY").center(x+(EAR_SLOT_L-EAR_SLOT_D)/2,y).circle(EAR_SLOT_D/2).extrude(EAR_T+2))
            base=base.cut(slot)
    return base


def make_lid():
    lid=rounded_box_xy(CASE_L,CASE_W,LID_PLATE,CASE_CORNER_R)
    outer=rounded_box_xy(CASE_L-2*CASE_WALL-0.8,CASE_W-2*CASE_WALL-0.8,LID_LIP_H,max(1,CASE_CORNER_R-CASE_WALL))
    inner=rounded_box_xy(CASE_L-2*(CASE_WALL+LID_LIP_T)-0.8,CASE_W-2*(CASE_WALL+LID_LIP_T)-0.8,LID_LIP_H+0.5,max(1,CASE_CORNER_R-CASE_WALL-LID_LIP_T))
    lid=lid.union(outer.cut(inner).translate((0,0,-LID_LIP_H)))
    for x in BOSS_X:
        for y in BOSS_Y:
            lid=lid.cut(cq.Workplane("XY").center(x,y).circle(LID_HOLE_D/2).extrude(LID_PLATE+2))
    return lid


def make_tray():
    tray=cq.Workplane("XY").box(TRAY_L,TRAY_W,TRAY_T,centered=(True,True,False)).edges("|Z").fillet(5)
    slot_centers=[]
    for x0 in (-63,63):
        for dx in (-27,27):
            for y in (-47,47): slot_centers.append((x0+dx,y))
    for x in (-10,10):
        for y in (-45,0,45): slot_centers.append((x,y))
    for x,y in slot_centers:
        s=cq.Workplane("XY").center(x,y).rect(TRAY_SLOT_L-TRAY_SLOT_W,TRAY_SLOT_W).extrude(TRAY_T+1)
        s=s.union(cq.Workplane("XY").center(x-(TRAY_SLOT_L-TRAY_SLOT_W)/2,y).circle(TRAY_SLOT_W/2).extrude(TRAY_T+1))
        s=s.union(cq.Workplane("XY").center(x+(TRAY_SLOT_L-TRAY_SLOT_W)/2,y).circle(TRAY_SLOT_W/2).extrude(TRAY_T+1))
        tray=tray.cut(s)
    for x in (-TRAY_L/2+12,TRAY_L/2-12):
        for y in (-TRAY_W/2+12,TRAY_W/2-12):
            tray=tray.cut(cq.Workplane("XY").center(x,y).circle(5.5/2).extrude(TRAY_T+1))
    return tray


def make_encoder_bracket():
    base=cq.Workplane("XY").box(56,24,5,centered=(True,True,False)).edges("|Z").fillet(3)
    slot=cq.Workplane("XY").rect(24.5,5.5).extrude(7)
    slot=slot.union(cq.Workplane("XY").center(-12.25,0).circle(2.75).extrude(7))
    slot=slot.union(cq.Workplane("XY").center(12.25,0).circle(2.75).extrude(7))
    base=base.cut(slot)
    arm=cq.Workplane("XZ").box(5,34,44,centered=(True,True,False)).translate((0,9.5,5))
    return base.union(arm).cut(cq.Workplane("XZ").center(0,26).rect(5.0,24).extrude(20,both=True))


def make_bulkhead_plate():
    plate=cq.Workplane("XY").box(92,42,3,centered=(True,True,False)).edges("|Z").fillet(4)
    for x in (-39,39):
        for y in (-14,14): plate=plate.cut(cq.Workplane("XY").center(x,y).circle(2.2).extrude(5))
    for x,d in [(-24,8.0),(3,8.0),(29,6.0)]: plate=plate.cut(cq.Workplane("XY").center(x,0).circle(d/2).extrude(5))
    return plate


def export_part(name,shape):
    cq.exporters.export(shape,str(OUT/f"{name}.step"))
    cq.exporters.export(shape,str(OUT/f"{name}.stl"),tolerance=0.12,angularTolerance=0.15)


def export_bulkhead_dxf():
    doc=ezdxf.new("R2010"); msp=doc.modelspace(); x0,y0=-46,-21
    msp.add_lwpolyline([(x0,y0),(46,y0),(46,21),(x0,21),(x0,y0)])
    for x in (-39,39):
        for y in (-14,14): msp.add_circle((x,y),2.2)
    for x,d in [(-24,8.0),(3,8.0),(29,6.0)]: msp.add_circle((x,0),d/2)
    doc.saveas(OUT/"power_bulkhead_plate.dxf")


if __name__=="__main__":
    export_part("battery_enclosure_base",make_base())
    export_part("battery_enclosure_lid",make_lid())
    export_part("esc_ecu_tray",make_tray())
    export_part("front_encoder_universal_bracket",make_encoder_bracket())
    export_part("power_bulkhead_plate",make_bulkhead_plate())
    export_bulkhead_dxf()
    print("Generated Worcester X1 Alpha CAD in",OUT)
