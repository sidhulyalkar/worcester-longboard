#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

LB_TO_KG=0.45359237
IN_TO_MM=25.4


def main():
    ap=argparse.ArgumentParser(description="Create a local rider profile without committing personal data.")
    ap.add_argument("--height-in", type=float)
    ap.add_argument("--mass-lb", type=float)
    ap.add_argument("--left-shoe", type=str)
    ap.add_argument("--right-shoe", type=str)
    ap.add_argument("--board-mass-kg", type=float, default=20.0)
    ap.add_argument("--out", type=Path, default=Path("rider/private/profile.json"))
    args=ap.parse_args()

    profile={
        "schema_version": 2,
        "mass_kg": round(args.mass_lb*LB_TO_KG, 3) if args.mass_lb is not None else None,
        "height_mm": round(args.height_in*IN_TO_MM, 1) if args.height_in is not None else None,
        "board_mass_kg": args.board_mass_kg,
        "stance_width_mm": None,
        "fit_mode": "independent_left_right",
        "symmetric_trucks_default": True,
        "left_foot": {"length_mm": None,"width_mm": None,"shoe_size_label": args.left_shoe,"natural_yaw_deg": None,"natural_center_x_mm": None,"natural_center_y_mm": None,"cant_deg": 0.0},
        "right_foot": {"length_mm": None,"width_mm": None,"shoe_size_label": args.right_shoe,"natural_yaw_deg": None,"natural_center_x_mm": None,"natural_center_y_mm": None,"cant_deg": 0.0}
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(profile, indent=2)+"\n")
    print(args.out)

if __name__ == "__main__":
    main()
