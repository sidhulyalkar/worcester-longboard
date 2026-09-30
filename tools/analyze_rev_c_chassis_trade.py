#!/usr/bin/env python3
"""Analyze the dated Worcester X1 Rev-C chassis trade snapshot.

The analysis is intentionally non-authoritative. It derives transparent deltas
from published candidate facts and highlights missing evidence. It does not
choose the chassis and cannot open procurement.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

LB_PER_KG = 2.2046226218
G_PER_LB = 453.59237

REQUIRED_CANDIDATES = {
    "COMP95_BASELINE",
    "PRO_WARREN_III_REFERENCE",
    "AGENT_AIR_REFERENCE",
}
REQUIRED_WHEELS = {"T1_200X50", "T3_200X50", "EXPLORER_200X70"}


def _candidate_map(snapshot: dict) -> dict[str, dict]:
    return {x["id"]: x for x in snapshot.get("candidates", []) if isinstance(x, dict) and x.get("id")}


def _wheel_map(snapshot: dict) -> dict[str, dict]:
    return {x["id"]: x for x in snapshot.get("wheel_references", []) if isinstance(x, dict) and x.get("id")}


def validate(snapshot: dict) -> list[str]:
    errors: list[str] = []
    if snapshot.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if snapshot.get("scope") != "rev_c_chassis_candidate_trade_snapshot":
        errors.append("wrong snapshot scope")
    if snapshot.get("facts_only") is not True:
        errors.append("snapshot must be explicitly facts_only")

    candidates = _candidate_map(snapshot)
    missing = sorted(REQUIRED_CANDIDATES - set(candidates))
    if missing:
        errors.append("missing chassis candidates: " + ", ".join(missing))

    wheels = _wheel_map(snapshot)
    missing_wheels = sorted(REQUIRED_WHEELS - set(wheels))
    if missing_wheels:
        errors.append("missing wheel references: " + ", ".join(missing_wheels))

    for cid, candidate in candidates.items():
        deck = candidate.get("deck", {})
        for key in ("length_mm", "max_width_mm", "weight_lb"):
            value = deck.get(key)
            if not isinstance(value, (int, float)) or value <= 0:
                errors.append(f"{cid}: invalid deck {key}")
        chassis = candidate.get("chassis", {})
        mass = chassis.get("complete_unpowered_weight_lb")
        if mass is not None and (not isinstance(mass, (int, float)) or mass <= 0):
            errors.append(f"{cid}: invalid complete mass")
        if not candidate.get("sources"):
            errors.append(f"{cid}: missing source list")

    for wid, wheel in wheels.items():
        for key in ("diameter_mm", "width_mm", "tire_mass_g_each"):
            value = wheel.get(key)
            if not isinstance(value, (int, float)) or value <= 0:
                errors.append(f"{wid}: invalid {key}")
        if not str(wheel.get("source", "")).startswith("https://"):
            errors.append(f"{wid}: missing https source")

    return errors


def _unknown_fields(candidate: dict) -> list[str]:
    unknowns: list[str] = []
    deck = candidate.get("deck", {})
    chassis = candidate.get("chassis", {})
    for path, value in (
        ("deck.stiffness", deck.get("stiffness")),
        ("chassis.complete_unpowered_weight_lb", chassis.get("complete_unpowered_weight_lb")),
        ("chassis.wheelbase_mm_min", chassis.get("wheelbase_mm_min")),
        ("chassis.wheelbase_mm_max", chassis.get("wheelbase_mm_max")),
        ("chassis.brake_compatible", chassis.get("brake_compatible")),
    ):
        if value is None or (isinstance(value, str) and value.startswith("NOT_PUBLISHED")):
            unknowns.append(path)
    return unknowns


def analyze(snapshot: dict) -> dict:
    errors = validate(snapshot)
    if errors:
        return {
            "schema_version": 1,
            "scope": "rev_c_chassis_candidate_trade_analysis",
            "valid": False,
            "errors": errors,
            "physical_authority": False,
            "procurement_authority": False,
        }

    candidates = _candidate_map(snapshot)
    wheels = _wheel_map(snapshot)
    comp = candidates["COMP95_BASELINE"]

    comp_width = float(comp["deck"]["max_width_mm"])
    comp_length = float(comp["deck"]["length_mm"])
    comp_deck_mass = float(comp["deck"]["weight_lb"])
    comp_complete_mass = float(comp["chassis"]["complete_unpowered_weight_lb"])

    candidate_rows = []
    for cid in (
        "COMP95_BASELINE",
        "PRO_WARREN_III_REFERENCE",
        "AGENT_AIR_REFERENCE",
    ):
        c = candidates[cid]
        deck = c["deck"]
        chassis = c["chassis"]
        complete_mass = chassis.get("complete_unpowered_weight_lb")
        wheelbase_min = chassis.get("wheelbase_mm_min")
        wheelbase_max = chassis.get("wheelbase_mm_max")
        candidate_rows.append(
            {
                "id": cid,
                "deck_candidate_id": c["deck_candidate_id"],
                "deck_width_mm": deck["max_width_mm"],
                "deck_width_delta_mm_vs_comp95": round(float(deck["max_width_mm"]) - comp_width, 1),
                "deck_length_mm": deck["length_mm"],
                "deck_length_delta_mm_vs_comp95": round(float(deck["length_mm"]) - comp_length, 1),
                "deck_area_proxy_mm2": round(float(deck["length_mm"]) * float(deck["max_width_mm"]), 1),
                "deck_area_proxy_delta_pct_vs_comp95": round(
                    (
                        float(deck["length_mm"]) * float(deck["max_width_mm"])
                        / (comp_length * comp_width)
                        - 1.0
                    )
                    * 100.0,
                    2,
                ),
                "deck_mass_lb": deck["weight_lb"],
                "deck_mass_delta_lb_vs_comp95": round(float(deck["weight_lb"]) - comp_deck_mass, 2),
                "complete_unpowered_mass_lb": complete_mass,
                "complete_mass_delta_lb_vs_comp95": (
                    None if complete_mass is None else round(float(complete_mass) - comp_complete_mass, 2)
                ),
                "wheelbase_range_mm": (
                    None
                    if wheelbase_min is None or wheelbase_max is None
                    else [wheelbase_min, wheelbase_max]
                ),
                "wheelbase_adjustment_span_mm": (
                    None
                    if wheelbase_min is None or wheelbase_max is None
                    else round(float(wheelbase_max) - float(wheelbase_min), 1)
                ),
                "deck_construction": deck["construction"],
                "deck_stiffness": deck["stiffness"],
                "brake_compatible_published": chassis.get("brake_compatible"),
                "electric_native": c["electric_native"],
                "availability_snapshot": c["availability_snapshot"],
                "unknown_fields": _unknown_fields(c),
                "unresolved_count": len(c.get("unresolved", [])),
            }
        )

    t1 = wheels["T1_200X50"]
    t3 = wheels["T3_200X50"]
    explorer = wheels["EXPLORER_200X70"]

    explorer_vs_t1_g = (float(explorer["tire_mass_g_each"]) - float(t1["tire_mass_g_each"])) * 4
    explorer_vs_t3_g = (float(explorer["tire_mass_g_each"]) - float(t3["tire_mass_g_each"])) * 4

    warren = candidates["PRO_WARREN_III_REFERENCE"]
    warren_min = float(warren["chassis"]["wheelbase_mm_min"])
    warren_max = float(warren["chassis"]["wheelbase_mm_max"])
    comp_wheelbase = float(comp["chassis"]["wheelbase_mm_min"])
    wheelbase_experiment = {
        "comp95_reference_mm": comp_wheelbase,
        "warren_min_mm": warren_min,
        "warren_max_mm": warren_max,
        "warren_midpoint_mm": round((warren_min + warren_max) / 2.0, 1),
        "comp95_matches_warren_midpoint": abs(
            comp_wheelbase - (warren_min + warren_max) / 2.0
        )
        < 1e-9,
        "warren_short_delta_vs_comp95_mm": round(warren_min - comp_wheelbase, 1),
        "warren_long_delta_vs_comp95_mm": round(warren_max - comp_wheelbase, 1),
        "same_steer_curvature_ratio_short_vs_long_bicycle_proxy": round(
            warren_max / warren_min, 3
        ),
        "interpretation": (
            "At the same effective steer angle, a first-order bicycle model makes "
            "turning curvature inverse to wheelbase. The Warren range therefore "
            "supports a controlled wheelbase experiment around the Comp 95 reference; "
            "this is a sensitivity proxy, not mountainboard steering qualification."
        ),
    }

    wheel_trade = {
        "same_published_diameter_mm": (
            t1["diameter_mm"]
            if t1["diameter_mm"] == t3["diameter_mm"] == explorer["diameter_mm"]
            else None
        ),
        "explorer_width_ratio_vs_200x50": round(
            float(explorer["width_mm"]) / float(t1["width_mm"]), 3
        ),
        "explorer_width_gain_mm_vs_t1": round(
            float(explorer["width_mm"]) - float(t1["width_mm"]), 1
        ),
        "explorer_tire_only_added_mass_four_wheels_vs_t1_g": round(explorer_vs_t1_g, 1),
        "explorer_tire_only_added_mass_four_wheels_vs_t1_lb": round(
            explorer_vs_t1_g / G_PER_LB, 2
        ),
        "explorer_tire_only_added_mass_four_wheels_vs_t3_g": round(explorer_vs_t3_g, 1),
        "explorer_tire_only_added_mass_four_wheels_vs_t3_lb": round(
            explorer_vs_t3_g / G_PER_LB, 2
        ),
        "explorer_hub_requirement": explorer.get("compatible_only_with_hub_family"),
        "explorer_hub_mass_g_each": explorer.get("hub_mass_g_each"),
        "rockstar_ii_hub_mass_known": False,
        "full_wheel_mass_delta_computable": False,
        "interpretation": (
            "The Explorer option increases published tire width without increasing "
            "published tire diameter, but adds about 2.7 lb across four tires before "
            "the unknown Rockstar II-to-Pro-II-XL hub mass delta."
        ),
    }

    return {
        "schema_version": 1,
        "scope": "rev_c_chassis_candidate_trade_analysis",
        "valid": True,
        "errors": [],
        "physical_authority": False,
        "procurement_authority": False,
        "snapshot_as_of": snapshot["as_of"],
        "candidate_rows": candidate_rows,
        "wheelbase_experiment": wheelbase_experiment,
        "wheel_trade": wheel_trade,
        "decision_boundaries": [
            "cardboard/foam envelopes can qualify stance geometry, not real deck flex",
            "published brake compatibility does not prove simultaneous brake plus drivetrain coexistence",
            "unknown Agent complete mass and exact unpowered truck width prevent a closed mass/brake comparison",
            "current Warren waitlist prevents treating it as immediately purchasable",
            "a candidate selected by Issue #25 must match an explicitly released procurement item before checkout",
        ],
        "physical_questions_remaining": [
            "Which of the three deck envelopes gives the best repeatable leverage and emergency step-off?",
            "Does the Warren stiff/high-pop composite feel too reactive once a real chassis is available?",
            "Does 200x50 compliance suffice before paying the roughly 2.7 lb tire-only penalty of Explorer wheels?",
            "Which independent brake and rear-drive topology survives real wheel-end measurements?",
            "Where can trail and range inert pack envelopes sit without harming stance, flex or clearance?",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "snapshot",
        nargs="?",
        type=Path,
        default=Path("hardware/rev_c_chassis_trade_snapshot_2026-09-30.json"),
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = analyze(json.loads(args.snapshot.read_text(encoding="utf-8")))
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
