#!/usr/bin/env python3
"""Validate private load-cell measurements before they are used by CAD.

This utility prints a machine-readable authority report. It never invents missing
coordinates and does not write measurements into the public repository.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cad.fit_rig_geometry import DEFAULT


def validate_file(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    cell = data.get("load_cell") or {}
    fixed = cell.get("fixed_holes_xy_mm")
    loaded = cell.get("loaded_holes_xy_mm")

    if not fixed or not loaded:
        report = DEFAULT.authority_report()
        report["input_file"] = str(path)
        report["input_complete"] = False
        return report

    geometry = DEFAULT.with_load_cell_measurements(
        {"fixed_holes_xy_mm": fixed, "loaded_holes_xy_mm": loaded}
    )
    report = geometry.authority_report()
    report["input_file"] = str(path)
    report["input_complete"] = True
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("measurements", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()

    report = validate_file(args.measurements)
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")

    if not report["sensor_mount_fabrication_ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
