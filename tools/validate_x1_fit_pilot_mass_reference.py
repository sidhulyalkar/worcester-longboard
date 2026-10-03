#!/usr/bin/env python3
"""Validate Issue #61 fit-pilot calibration-mass reference evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fit.mass_reference import validate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    record = json.loads(args.record.read_text(encoding="utf-8"))
    report = validate(record)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
