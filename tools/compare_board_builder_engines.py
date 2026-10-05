#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIREMENT_KEYS = (
    "loaded_rider_mass_kg",
    "target_range_mi",
    "energy_reserve_fraction",
    "planning_energy_wh_per_mi",
    "planning_installed_energy_wh",
    "rough_terrain_fraction",
    "wheel_strategy",
    "independent_friction_brake_required",
    "stance_study",
    "deck_envelope_preference",
    "ingress_priority",
    "electric_intent",
    "budget",
    "priorities",
)

CANDIDATE_KEYS = (
    "fit_score",
    "readiness",
    "checkout_state",
    "visual_preset",
    "deck_candidate_id",
    "topology_id",
    "cost",
    "trade_space_frontier",
    "preference_fit",
    "personalized_spec",
    "blockers",
    "unknowns",
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compare(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if left.get("winner_selected") != right.get("winner_selected"):
        errors.append("winner_selected differs")
    if left.get("authority") != right.get("authority"):
        errors.append("authority differs")

    lreq = left.get("requirements") or {}
    rreq = right.get("requirements") or {}
    for key in REQUIREMENT_KEYS:
        if lreq.get(key) != rreq.get(key):
            errors.append(
                f"requirements.{key} differs: {lreq.get(key)!r} != {rreq.get(key)!r}"
            )

    lc = {row["id"]: row for row in left.get("candidates", [])}
    rc = {row["id"]: row for row in right.get("candidates", [])}
    if set(lc) != set(rc):
        errors.append(
            f"candidate ids differ: {sorted(lc)} != {sorted(rc)}"
        )
        return errors

    for candidate_id in sorted(lc):
        for key in CANDIDATE_KEYS:
            if lc[candidate_id].get(key) != rc[candidate_id].get(key):
                errors.append(
                    f"{candidate_id}.{key} differs: "
                    f"{lc[candidate_id].get(key)!r} != "
                    f"{rc[candidate_id].get(key)!r}"
                )
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare Python and browser Board Builder outputs."
    )
    parser.add_argument("python_output", type=Path)
    parser.add_argument("browser_output", type=Path)
    args = parser.parse_args()

    errors = compare(load(args.python_output), load(args.browser_output))
    report = {
        "valid": not errors,
        "errors": errors,
        "authority_comparison_included": True,
        "winner_selection_comparison_included": True,
    }
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
