#!/usr/bin/env python3
"""Create a private one-zone pilot session from actual measured calibration masses."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

HARD_MAX_PILOT_MASS_KG = 20.0


def _mass_slug(value: float) -> str:
    return f"{value:.10g}".replace(".", "p")


def _validated_masses(args) -> tuple[list[float], float]:
    masses = sorted(float(x) for x in args.calibration_mass_kg)
    validation = float(args.validation_mass_kg)
    if len(masses) < 3:
        raise ValueError("need at least three measured calibration masses")
    if len(set(masses)) != len(masses):
        raise ValueError("calibration masses must be unique")
    for mass in [*masses, validation]:
        if not math.isfinite(mass) or mass <= 0:
            raise ValueError("all calibration/validation masses must be finite and positive")
        if mass > HARD_MAX_PILOT_MASS_KG:
            raise ValueError(f"pilot mass exceeds hard {HARD_MAX_PILOT_MASS_KG:g} kg limit")
    if any(math.isclose(validation, mass, rel_tol=0.0, abs_tol=1e-9) for mass in masses):
        raise ValueError("validation mass must be independent of calibration masses")
    return masses, validation


def build_manifest(args) -> dict:
    masses, validation = _validated_masses(args)
    observations = [{"kind": "zero_pre", "mass_kg": 0.0, "log": "raw/zero_pre.csv"}]
    observations.extend(
        {
            "kind": "load_up",
            "mass_kg": mass,
            "log": f"raw/up_{_mass_slug(mass)}kg.csv",
        }
        for mass in masses
    )
    observations.extend(
        {
            "kind": "load_down",
            "mass_kg": mass,
            "log": f"raw/down_{_mass_slug(mass)}kg.csv",
        }
        for mass in reversed(masses[:-1])
    )
    observations.append({"kind": "zero_post", "mass_kg": 0.0, "log": "raw/zero_post.csv"})

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
        "observations": observations,
        "validation": [
            {
                "mass_kg": validation,
                "log": f"raw/validation_{_mass_slug(validation)}kg.csv",
            }
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
    p.add_argument(
        "--calibration-mass-kg",
        type=float,
        action="append",
        required=True,
        help="actual measured mass in kg; repeat at least three times",
    )
    p.add_argument(
        "--validation-mass-kg",
        type=float,
        required=True,
        help="independent actual measured mass in kg, not one of the calibration masses",
    )
    args = p.parse_args()

    try:
        manifest = build_manifest(args)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    root = args.session_dir.resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"Refusing to overwrite nonempty session directory: {root}")
    (root / "raw").mkdir(parents=True, exist_ok=True)
    (root / "pilot_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    sequence = [
        f"{row['kind']}:{row['mass_kg']:g}kg" for row in manifest["observations"]
    ] + [f"validation:{manifest['validation'][0]['mass_kg']:g}kg"]
    (root / "NOTES.md").write_text(
        "# Private X1 one-zone pilot notes\n\n"
        "The manifest was generated from the actual masses supplied on the command line.\n"
        "Do not replace them with nominal plate labels after capture.\n"
        "Keep transient load/unload periods out of plateau CSVs.\n"
        "Set rate_jumper_verified=true only after physically checking the HX711 RATE state.\n\n"
        "## Capture order\n\n- " + "\n- ".join(sequence) + "\n",
        encoding="utf-8",
    )
    print(root)


if __name__ == "__main__":
    main()
