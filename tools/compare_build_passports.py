#!/usr/bin/env python3
"""Exact cross-runtime Build Passport parity with useful JSON path on mismatch."""
import argparse
import json
from pathlib import Path


def diffs(left, right, pointer="$"):
    if type(left) is not type(right):
        return [f"{pointer}: types {type(left).__name__} != {type(right).__name__}"]
    if isinstance(left, dict):
        out = []
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                out.append(f"{pointer}.{key}: missing in one output")
            else:
                out.extend(diffs(left[key], right[key], pointer + "." + key))
            if len(out) >= 20:
                return out[:20]
        return out
    if isinstance(left, list):
        out = []
        if len(left) != len(right):
            out.append(f"{pointer}: list lengths {len(left)} != {len(right)}")
        for index, (a, b) in enumerate(zip(left, right)):
            out.extend(diffs(a, b, f"{pointer}[{index}]"))
            if len(out) >= 20:
                return out[:20]
        return out
    return [f"{pointer}: {left!r} != {right!r}"] if left != right else []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("python_report", type=Path)
    parser.add_argument("browser_report", type=Path)
    args = parser.parse_args()
    a = json.loads(args.python_report.read_text(encoding="utf-8"))
    b = json.loads(args.browser_report.read_text(encoding="utf-8"))
    differences = diffs(a, b)
    assert not differences, "Build Passport parity failure:\n" + "\n".join(differences)
    assert a["scope"] == "NON_AUTHORITATIVE_BUILD_PASSPORT"
    assert not any(a["authority"].values())
    assert a["sourcing"]["all_in_total_usd"] is None
    assert not a["sourcing"]["live_stock_verified"]
    print(f"Build Passport parity PASS: {a['candidate_id']}, {len(a['parts'])} source rows")


if __name__ == "__main__":
    main()
