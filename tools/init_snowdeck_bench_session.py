#!/usr/bin/env python3
"""Initialize a private SnowDeck bench-observation session from the public template."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "hardware" / "snowdeck_bench_trial_template.json"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("out", type=Path)
    p.add_argument("--session-id", required=True)
    p.add_argument("--condition-id", default="S0")
    args = p.parse_args()

    if args.out.exists():
        raise SystemExit(f"Refusing to overwrite existing session: {args.out}")

    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    data["session_id"] = args.session_id
    data["condition_id"] = args.condition_id

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Initialized private SnowDeck bench session: {args.out}")
    print("fabrication_authority=false ride_authority=false powered_operation_authorized=false")


if __name__ == "__main__":
    main()
