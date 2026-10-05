#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from configurator.engine import generate_candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate non-authoritative board design candidates.")
    parser.add_argument("profile", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    profile = json.loads(args.profile.read_text())
    result = generate_candidates(profile)
    text = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
