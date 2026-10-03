#!/usr/bin/env python3
"""Qualify an Issue #63 off-axis one-zone platform-repeatability session."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fit.platform_repeatability import qualify


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--one-zone-authority", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    authority = json.loads(args.one_zone_authority.read_text(encoding="utf-8"))
    report = qualify(manifest, authority, args.manifest.resolve().parent)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["qualified"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
