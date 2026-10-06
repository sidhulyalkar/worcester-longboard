#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configurator.platform_engine import generate_board_design_space, render_bom_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a source-aware BOM for one generated candidate.")
    parser.add_argument("profile", type=Path)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    profile = json.loads(args.profile.read_text())
    result = generate_board_design_space(profile)
    try:
        candidate = next(row for row in result["candidates"] if row["id"] == args.candidate)
    except StopIteration as exc:
        choices = ", ".join(row["id"] for row in result["candidates"])
        raise SystemExit(f"unknown candidate {args.candidate!r}; choices: {choices}") from exc

    text = render_bom_markdown(candidate)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
