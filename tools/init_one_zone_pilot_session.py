#!/usr/bin/env python3
"""Create a private one-zone pilot session from the public evidence contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_manifest(args) -> dict:
    return {
        "schema_version": 1,
        "hardware_ids": {
            "load_cell_id": args.load_cell_id,
            "hx711_id": args.hx711_id,
            "pod_id": args.pod_id,
            "zone_pad_id": args.zone_pad_id,
        },
        "channel": args.channel,
        "hx711_sps": args.sps,
        "acquisition": {"rate_jumper_verified": False},
        "observations": [
            {"kind": "zero_pre", "mass_kg": 0.0, "log": "raw/zero_pre.csv"},
            {"kind": "load_up", "mass_kg": 2.0, "log": "raw/up_2kg.csv"},
            {"kind": "load_up", "mass_kg": 5.0, "log": "raw/up_5kg.csv"},
            {"kind": "load_up", "mass_kg": 10.0, "log": "raw/up_10kg.csv"},
            {"kind": "load_down", "mass_kg": 5.0, "log": "raw/down_5kg.csv"},
            {"kind": "load_down", "mass_kg": 2.0, "log": "raw/down_2kg.csv"},
            {"kind": "zero_post", "mass_kg": 0.0, "log": "raw/zero_post.csv"},
        ],
        "validation": [
            {"mass_kg": 7.5, "log": "raw/validation_7p5kg.csv"}
        ],
        "mechanical": {
            "vendor_pattern_verified": False,
            "fixed_loaded_orientation_verified": False,
            "screw_stack_verified": False,
            "stop_gap_unloaded_mm": None,
            "stop_gap_min_loaded_mm": None,
        },
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("session_dir", type=Path)
    p.add_argument("--load-cell-id", required=True)
    p.add_argument("--hx711-id", required=True)
    p.add_argument("--pod-id", required=True)
    p.add_argument("--zone-pad-id", required=True)
    p.add_argument("--channel", choices=("left_heel", "left_forefoot", "right_heel", "right_forefoot"), default="left_heel")
    p.add_argument("--sps", type=int, choices=(10, 80), default=10)
    args = p.parse_args()

    root = args.session_dir.resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"Refusing to overwrite nonempty session directory: {root}")
    (root / "raw").mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(args)
    (root / "pilot_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (root / "NOTES.md").write_text(
        "# Private X1 one-zone pilot notes\n\n"
        "Record actual measured masses rather than trusting nominal plate labels.\n"
        "Keep transient load/unload periods out of plateau CSVs.\n"
        "Set rate_jumper_verified=true only after physically checking the HX711 RATE state.\n",
        encoding="utf-8",
    )
    print(root)


if __name__ == "__main__":
    main()
