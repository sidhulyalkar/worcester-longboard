#!/usr/bin/env python3
"""Initialize a private Issue #61 fit-pilot mass-reference record."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "hardware/x1_fit_pilot_mass_reference_template.json"


def initialize(
    output_path: Path,
    reference_set_id: str,
    measured_at_utc: str,
) -> dict:
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing record: {output_path}")
    if not reference_set_id.strip():
        raise ValueError("reference_set_id must be nonempty")
    if not measured_at_utc.strip():
        raise ValueError("measured_at_utc must be nonempty")

    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    data["reference_set_id"] = reference_set_id
    data["measured_at_utc"] = measured_at_utc
    data["masses"] = []

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--reference-set-id", required=True)
    parser.add_argument("--measured-at-utc", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            initialize(
                args.output,
                args.reference_set_id,
                args.measured_at_utc,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
