#!/usr/bin/env python3
"""Validate one physical Phidgets 3135 against X1's vendor CAD authority.

The vendor drawing is allowed to drive a one-zone pilot. This utility closes the
four-pod duplication gate only after a purchased sensor is physically checked.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cad.fit_rig_geometry import DEFAULT


def validate_file(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    cell = data.get("load_cell") or {}
    fixed = cell.get("fixed_hole_xy_mm")
    loaded = cell.get("loaded_hole_xy_mm")

    if fixed is None or loaded is None:
        report = DEFAULT.authority_report()
        report["input_file"] = str(path)
        report["input_complete"] = False
        return report

    try:
        geometry = DEFAULT.with_load_cell_verification(
            {"fixed_hole_xy_mm": fixed, "loaded_hole_xy_mm": loaded}
        )
        report = geometry.authority_report()
        report["verification_error"] = None
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        report = DEFAULT.authority_report()
        report["verification_error"] = str(exc)

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
