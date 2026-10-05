#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare Python and browser candidate visual states."
    )
    parser.add_argument("python_output", type=Path)
    parser.add_argument("browser_output", type=Path)
    args = parser.parse_args()

    left = json.loads(args.python_output.read_text())
    right = json.loads(args.browser_output.read_text())

    errors: list[str] = []
    if left != right:
        left_by_id = {row["subject_id"]: row for row in left.get("states", [])}
        right_by_id = {row["subject_id"]: row for row in right.get("states", [])}
        if set(left_by_id) != set(right_by_id):
            errors.append(
                f"state ids differ: {sorted(left_by_id)} != {sorted(right_by_id)}"
            )
        for subject_id in sorted(set(left_by_id) & set(right_by_id)):
            if left_by_id[subject_id] != right_by_id[subject_id]:
                errors.append(f"visual state differs for {subject_id}")

        for key in ("schema_version", "winner_selected", "visualization_only"):
            if left.get(key) != right.get(key):
                errors.append(
                    f"{key} differs: {left.get(key)!r} != {right.get(key)!r}"
                )

    report = {"valid": not errors, "errors": errors}
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
