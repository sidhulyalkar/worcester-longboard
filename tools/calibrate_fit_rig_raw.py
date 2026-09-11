#!/usr/bin/env python3
"""Convert an X1 Fit Rig raw logger file into calibrated neutral-trial CSV.

The default path refuses to export a qualification CSV when raw sensor quality is
below the current fit-rig gate. Use the raw file for diagnostics rather than
silently interpolating or dropping a large amount of bad data.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from fit.pressure_calibration import CHANNELS, from_known_mass
from fit.raw_log import parse_text, quality_report
from fit.raw_to_calibrated import convert_samples


def load_calibration(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    channels = data.get("channels") or {}
    out = {}
    for name in CHANNELS:
        row = channels.get(name) or {}
        required = ("zero_raw", "loaded_raw", "known_mass_kg")
        if any(row.get(k) is None for k in required):
            raise ValueError(f"{name}: incomplete calibration")
        out[name] = from_known_mass(
            float(row["zero_raw"]),
            float(row["loaded_raw"]),
            float(row["known_mass_kg"]),
        )
    return out


def quality_is_qualified(report: dict) -> bool:
    return (
        report.get("samples", 0) > 0
        and bool(report.get("monotonic_time"))
        and float(report.get("complete_force_fraction", 0.0)) >= 0.98
        and float(report.get("imu_valid_fraction", 0.0)) >= 0.95
        and not report.get("warnings")
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("raw_log", type=Path)
    p.add_argument("calibration", type=Path)
    p.add_argument("out_csv", type=Path)
    p.add_argument(
        "--diagnostic-override",
        action="store_true",
        help="allow conversion of an unqualified raw log for diagnostics only",
    )
    args = p.parse_args()

    samples = parse_text(args.raw_log.read_text(encoding="utf-8"))
    quality = quality_report(samples)
    if not quality_is_qualified(quality) and not args.diagnostic_override:
        print(json.dumps({"raw_quality": quality, "exported": False}, indent=2))
        raise SystemExit(2)

    calibration = load_calibration(args.calibration)
    rows = convert_samples(samples, calibration)
    if not rows:
        raise SystemExit("No complete force + IMU rows available for calibrated export")

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "t_s",
        "left_heel_N",
        "left_forefoot_N",
        "right_heel_N",
        "right_forefoot_N",
        "roll_deg",
    ]
    with args.out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({
        "raw_quality": quality,
        "calibrated_rows": len(rows),
        "out_csv": str(args.out_csv),
        "diagnostic_override": args.diagnostic_override,
    }, indent=2))


if __name__ == "__main__":
    main()
