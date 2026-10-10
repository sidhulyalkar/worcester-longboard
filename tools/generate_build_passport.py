#!/usr/bin/env python3
"""Generate a deterministic planning Build Passport, never purchase instructions."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configurator.platform_engine import load_platform_bundle, generate_board_design_space
from configurator.build_passport import build_build_passport


def main():
    parser = argparse.ArgumentParser(description="Generate a non-authoritative Build Passport")
    parser.add_argument("profile", type=Path)
    parser.add_argument("candidate_id")
    args = parser.parse_args()
    bundle = load_platform_bundle()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    generated = generate_board_design_space(profile, bundle)
    selected = next((c for c in generated["candidates"] if c["id"] == args.candidate_id), None)
    if selected is None:
        parser.error("Unknown design candidate: " + args.candidate_id)
    print(json.dumps(build_build_passport(selected, bundle), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
