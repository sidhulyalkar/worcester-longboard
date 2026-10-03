#!/usr/bin/env python3
"""Compare two SnowDeck bench signatures without selecting a winner."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_signature(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("scope") != "x1_snowdeck_bench_signature":
        raise ValueError(f"{path}: wrong SnowDeck signature scope")
    if data.get("physical_authority") is not False:
        raise ValueError(f"{path}: signature must remain non-authoritative")
    if data.get("powered_operation_authorized") is not False:
        raise ValueError(f"{path}: powered authority is forbidden")
    return data


def delta(variant: dict, baseline: dict, path: tuple[str, ...]) -> float:
    v: Any = variant
    b: Any = baseline
    for key in path:
        v = v[key]
        b = b[key]
    return float(v) - float(b)


def compare(baseline: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    metrics = {
        "neutral_left_load_mean": ("neutral", "left_load_fraction", "mean"),
        "neutral_left_load_sd": ("neutral", "left_load_fraction", "sd"),
        "neutral_left_forefoot_mean": ("neutral", "left_forefoot_fraction", "mean"),
        "neutral_right_forefoot_mean": ("neutral", "right_forefoot_fraction", "mean"),
        "neutral_total_load_sd": ("neutral", "total_load", "sd"),
        "left_heel_to_toe_transfer_mean": (
            "heel_to_toe_forefoot_transfer", "left", "mean"
        ),
        "right_heel_to_toe_transfer_mean": (
            "heel_to_toe_forefoot_transfer", "right", "mean"
        ),
        "deep_knee_left_load_delta_mean": (
            "deep_knee_delta_from_neutral", "left_load_fraction", "mean"
        ),
        "deep_knee_left_forefoot_delta_mean": (
            "deep_knee_delta_from_neutral", "left_forefoot_fraction", "mean"
        ),
        "deep_knee_right_forefoot_delta_mean": (
            "deep_knee_delta_from_neutral", "right_forefoot_fraction", "mean"
        ),
    }
    return {
        "schema_version": 1,
        "scope": "x1_snowdeck_bench_signature_comparison",
        "baseline": {
            "session_id": baseline.get("session_id"),
            "condition_id": baseline.get("condition_id"),
            "mechanical_rejects": baseline.get("mechanical_rejects", []),
        },
        "variant": {
            "session_id": variant.get("session_id"),
            "condition_id": variant.get("condition_id"),
            "mechanical_rejects": variant.get("mechanical_rejects", []),
        },
        "signed_variant_minus_baseline": {
            name: delta(variant, baseline, path)
            for name, path in metrics.items()
        },
        "variant_eligible_for_further_bench_comparison": bool(
            variant.get("eligible_for_further_bench_comparison")
        ),
        "winner_selected": False,
        "interpretation": (
            "Signed deltas only. No direction is automatically preferred; inspect the "
            "mechanical reject state and the individual tradeoffs."
        ),
        "physical_authority": False,
        "fabrication_authority": False,
        "ride_authority": False,
        "powered_operation_authorized": False,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("baseline", type=Path)
    p.add_argument("variant", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()

    report = compare(load_signature(args.baseline), load_signature(args.variant))
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
