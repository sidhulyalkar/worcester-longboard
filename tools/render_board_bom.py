#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from configurator.engine import generate_candidates, render_bom_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a source-aware BOM for one generated candidate.")
    parser.add_argument("profile", type=Path)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    profile = json.loads(args.profile.read_text())
    result = generate_candidates(profile)
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
