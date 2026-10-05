#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


KEYS = (
    "schema_version",
    "scope",
    "baseline_candidate_id",
    "selection",
    "changes",
    "readiness",
    "checkout_state",
    "cost",
    "cost_delta_vs_baseline",
    "compatibility_findings",
    "blockers",
    "unknowns",
    "notes",
    "twin_state",
    "authority",
)


def load(path: Path):
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Python and browser Swap Lab output.")
    parser.add_argument("python_output", type=Path)
    parser.add_argument("browser_output", type=Path)
    args = parser.parse_args()

    left = load(args.python_output)
    right = load(args.browser_output)
    errors = []
    for key in KEYS:
        if left.get(key) != right.get(key):
            errors.append(f"{key} differs: {left.get(key)!r} != {right.get(key)!r}")

    left_bom = [row["component_id"] for row in left.get("bom", [])]
    right_bom = [row["component_id"] for row in right.get("bom", [])]
    if left_bom != right_bom:
        errors.append(f"bom component order differs: {left_bom!r} != {right_bom!r}")

    report = {"valid": not errors, "errors": errors}
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
