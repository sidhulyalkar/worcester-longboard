#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configurator.platform_engine import generate_board_design_space
from configurator.swap_lab import evaluate_swap


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a non-authoritative custom Board Builder swap study.")
    parser.add_argument("profile", type=Path)
    parser.add_argument("selection", type=Path)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    profile = json.loads(args.profile.read_text())
    selection = json.loads(args.selection.read_text())
    generated = generate_board_design_space(profile)
    try:
        candidate = next(row for row in generated["candidates"] if row["id"] == args.candidate)
    except StopIteration as exc:
        raise SystemExit(f"unknown candidate {args.candidate!r}") from exc

    result = evaluate_swap(candidate, generated["requirements"], selection)
    text = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
