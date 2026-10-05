#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configurator.engine import generate_candidates
from configurator.visual_state import visual_state_from_candidate


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic candidate visual states from a rider profile."
    )
    parser.add_argument("profile", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    profile = json.loads(args.profile.read_text())
    generated = generate_candidates(profile)
    payload = {
        "schema_version": 1,
        "winner_selected": False,
        "visualization_only": True,
        "states": [
            visual_state_from_candidate(candidate)
            for candidate in generated["candidates"]
        ],
    }
    text = json.dumps(payload, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
