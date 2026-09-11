#!/usr/bin/env python3
"""Qualify one physical X1 Fit Rig sensor pod from private bench evidence."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from fit.pilot_qualification import qualify_manifest


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("manifest",type=Path)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    report=qualify_manifest(args.manifest)
    text=json.dumps(report,indent=2,sort_keys=True)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(text,encoding="utf-8")
    print(text,end="")
    if not report["qualified_for_four_zone_duplication"]:
        raise SystemExit(2)


if __name__=="__main__":
    main()
