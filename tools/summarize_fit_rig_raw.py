#!/usr/bin/env python3
"""Summarize X1 Fit Rig raw-log timing and sensor coverage before calibration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fit.raw_log import parse_text, quality_report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("raw_log", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()

    report = quality_report(parse_text(args.raw_log.read_text(encoding="utf-8")))
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")

    # Non-zero means the log should be inspected before it enters a qualified
    # calibration/fit session. We deliberately do not auto-delete bad samples.
    if report["samples"] == 0 or report["warnings"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
