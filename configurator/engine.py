"""Deterministic planning engine for the Worcester Board Builder.

This module compares design hypotheses. It does not create procurement,
fabrication, charging, ride, or powered-operation authority.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUESTIONNAIRE_PATH = ROOT / "configurator" / "questionnaire.v1.json"
RULES_PATH = ROOT / "configurator" / "rules.v1.json"
CATALOG_PATH = ROOT / "catalog" / "board_components.v1.json"
ARCHITECTURES_PATH = ROOT / "configurator" / "architectures.v1.json"
COMPATIBILITY_PATH = ROOT / "configurator" / "compatibility_rules.v1.json"

READINESS_RANK = {
    "REFERENCE_COMPATIBLE": 0,
    "MEASURE_FIRST": 1,
    "BLOCKED": 2,
    "INCOMPATIBLE": 3,
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_bundle() -> dict[str, Any]:
    return {
        "questionnaire": load_json(QUESTIONNAIRE_PATH),
        "rules": load_json(RULES_PATH),
        "catalog": load_json(CATALOG_PATH),
        "architectures": load_json(ARCHITECTURES_PATH),
        "compatibility": load_json(COMPATIBILITY_PATH),
    }


def questionnaire_defaults(questionnaire: dict[str, Any]) -> dict[str, Any]:
    defaults: dict[str, Any] = {}
    for section in questionnaire.get("sections", []):
        for field in section.get("fields", []):
            defaults[field["id"]] = copy.deepcopy(field.get("default"))
    return defaults


def normalize_profile(
    profile: dict[str, Any],
    questionnaire: dict[str, Any] | None = None,
) -> dict[str, Any]:
    questionnaire = questionnaire or load_json(QUESTIONNAIRE_PATH)
    merged = questionnaire_defaults(questionnaire)
    for key, value in profile.items():
        if value != "":
            merged[key] = value
    return merged


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _terrain(profile: dict[str, Any]) -> tuple[dict[str, float], list[str]]:
    keys = {
        "pavement": "terrain_pavement",
        "packed_dirt": "terrain_packed_dirt",
        "loose_gravel": "terrain_loose_gravel",
        "roots_rocks": "terrain_roots_rocks",
        "grass_brush": "terrain_grass_brush",
    }
    raw = {name: max(0.0, float(profile.get(key) or 0.0)) for name, key in keys.items()}
    total = sum(raw.values())
    warnings: list[str] = []
    if total <= 0:
        raw = {
            "pavement": 20.0,
            "packed_dirt": 35.0,
            "loose_gravel": 25.0,
            "roots_rocks": 15.0,
            "grass_brush": 5.0,
        }
        total = 100.0
        warnings.append("Terrain mix was empty; builder defaults were used.")
    elif abs(total - 100.0) > 1e-6:
        warnings.append(
            f"Terrain sliders totaled {total:.0f}%; they were normalized to 100% for planning."
        )
    return {name: value / total for name, value in raw.items()}, warnings


def _normalized_priorities(profile: dict[str, Any]) -> dict[str, float]:
    mapping = {
        "range": "priority_range",
        "carve": "priority_carve",
        "stability": "priority_stability",
        "durability": "priority_durability",
        "portability": "priority_portability",
        "cost": "priority_cost",
        "low_maintenance": "priority_low_maintenance",
    }
    raw = {name: max(0.0, float(profile.get(key) or 0.0)) for name, key in mapping.items()}
    total = sum(raw.values())
    if total <= 0:
        return {name: 1.0 / len(raw) for name in raw}
    return {name: value / total for name, value in raw.items()}


def derive_requirements(
    profile: dict[str, Any],
    rules: dict[str, Any] | None = None,
    questionnaire: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bundle_rules = rules or load_json(RULES_PATH)
    normalized = normalize_profile(profile, questionnaire)
    terrain, warnings = _terrain(normalized)

    loaded_lb = float(normalized["weight_lb"]) + float(normalized.get("cargo_lb") or 0)
    loaded_kg = loaded_lb * bundle_rules["unit_conversions"]["lb_to_kg"]

    energy = bundle_rules["energy"]
    mass_factor = (loaded_lb / energy["reference_loaded_mass_lb"]) ** energy["mass_exponent"]
    terrain_factor = sum(
        terrain[name] * energy["terrain_multipliers"][name]
        for name in terrain
    )
    hill_factor = energy["hill_multipliers"][normalized["hill_profile"]]
    stop_factor = energy["stop_start_multiplier"] if normalized.get("stop_start") else 1.0
    wh_per_mile = (
        energy["base_wh_per_mile"]
        * mass_factor
        * terrain_factor
        * hill_factor
        * stop_factor
    )

    typical = float(normalized["typical_miles"])
    longest = float(normalized["longest_miles"])
    target_range = max(longest, typical * energy["target_range_typical_multiplier"])
    if longest < typical:
        warnings.append("Longest desired ride was shorter than typical ride; typical-ride reserve controls.")

    rough_fraction = (
        terrain["loose_gravel"]
        + terrain["roots_rocks"]
        + terrain["grass_brush"]
        + 0.35 * terrain["packed_dirt"]
    )
    reserve = energy["reserve_fraction_base"]
    if rough_fraction >= bundle_rules["wheel_strategy"]["rollover_rough_fraction_threshold"]:
        reserve += energy["reserve_fraction_rough_bonus"]
    if normalized["wet_exposure"] == "frequent":
        reserve += energy["reserve_fraction_wet_bonus"]
    if normalized["hill_profile"] in {"steep", "long_descents"}:
        reserve += energy["reserve_fraction_steep_bonus"]
    reserve = min(reserve, energy["reserve_fraction_max"])
    installed_wh = target_range * wh_per_mile / max(0.5, 1.0 - reserve)

    wheel_rules = bundle_rules["wheel_strategy"]
    if (
        rough_fraction >= wheel_rules["rollover_rough_fraction_threshold"]
        and terrain["roots_rocks"] >= wheel_rules["rollover_roots_fraction_threshold"]
    ):
        wheel_strategy = "nine_inch_rollover_study"
    elif (
        terrain["pavement"] >= wheel_rules["pavement_efficiency_fraction_threshold"]
        and rough_fraction < 0.15
    ):
        wheel_strategy = "pavement_efficiency_study"
    else:
        wheel_strategy = "eight_inch_pneumatic_reference"

    electric_intent = normalized["electric_propulsion"]
    brake_required = False
    if normalized["hill_profile"] == "long_descents":
        brake_required = True
    if electric_intent != "no":
        if (
            float(normalized["speed_ceiling_mph"])
            >= bundle_rules["brake"]["powered_speed_threshold_mph"]
            or normalized["hill_profile"] != "flat"
        ):
            brake_required = True

    stance_rules = bundle_rules["stance"]
    user_stance = normalized.get("stance_width_mm")
    if user_stance is not None:
        stance_center = float(user_stance)
        stance_source = "user"
    else:
        height_mm = float(normalized["height_in"]) * bundle_rules["unit_conversions"]["in_to_mm"]
        stance_center = _clamp(
            height_mm * stance_rules["height_ratio"],
            stance_rules["min_center_mm"],
            stance_rules["max_center_mm"],
        )
        stance_source = "height_seed"
    half_span = stance_rules["default_half_span_mm"]
    stance_min = _clamp(stance_center - half_span, 260, 520)
    stance_max = _clamp(stance_center + half_span, 260, 520)

    height_in = float(normalized["height_in"])
    if (
        height_in <= bundle_rules["deck"]["compact_height_in_max"]
        and normalized["portability_need"] == "high"
    ):
        deck_pref = "compact"
    elif (
        height_in >= bundle_rules["deck"]["long_height_in_min"]
        or float(normalized["stability_preference"])
        >= bundle_rules["deck"]["long_stability_threshold"]
    ):
        deck_pref = "long_stable"
    else:
        deck_pref = "balanced"

    ingress = {
        "never": "low",
        "occasional": "medium",
        "frequent": "high",
    }[normalized["wet_exposure"]]

    if float(normalized["hard_budget_usd"]) < float(normalized["budget_usd"]):
        warnings.append("Absolute maximum budget is below target budget; hard maximum controls.")

    assumptions = [
        "Energy and range are comparative planning estimates, not validated X1 telemetry.",
        "Height-derived stance is an adjustable study seed, not a rider-fit prescription.",
        "Catalog price/stock is snapshot data and must be refreshed before checkout.",
        "Questionnaire answers cannot qualify structural, brake, electrical, battery, charging, or powered-operation safety.",
    ]
    if wheel_strategy == "nine_inch_rollover_study":
        assumptions.append(
            "Nine-inch wheels are a rollover study only; current standard Rockstar II compatibility is not assumed."
        )

    return {
        "schema_version": 1,
        "model_class": "PLANNING_ESTIMATE",
        "loaded_rider_mass_kg": round(loaded_kg, 2),
        "target_range_mi": round(target_range, 1),
        "energy_reserve_fraction": round(reserve, 3),
        "planning_energy_wh_per_mi": round(wh_per_mile, 1),
        "planning_installed_energy_wh": round(installed_wh),
        "terrain_normalized": {k: round(v, 4) for k, v in terrain.items()},
        "rough_terrain_fraction": round(rough_fraction, 4),
        "wheel_strategy": wheel_strategy,
        "independent_friction_brake_required": brake_required,
        "stance_study": {
            "center_mm": round(stance_center),
            "min_mm": round(stance_min),
            "max_mm": round(stance_max),
            "source": stance_source,
        },
        "deck_envelope_preference": deck_pref,
        "ingress_priority": ingress,
        "electric_intent": electric_intent,
        "budget": {
            "target_usd": float(normalized["budget_usd"]),
            "hard_max_usd": float(normalized["hard_budget_usd"]),
        },
        "priorities": _normalized_priorities(normalized),
        "assumptions": assumptions,
        "warnings": warnings,
    }


def _price_range(component: dict[str, Any]) -> tuple[float, float] | None:
    price = component.get("price")
    if not price:
        return None
    qty = float(price.get("qty", 1))
    if price["kind"] in {"unit", "ceiling"}:
        value = float(price["unit_price_usd"]) * qty
        return value, value
    if price["kind"] == "range":
        return float(price["min_usd"]) * qty, float(price["max_usd"]) * qty
    raise ValueError(f"unknown price kind {price['kind']!r} for {component['id']}")


def _bom(
    architecture: dict[str, Any],
    catalog: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = {row["id"]: row for row in catalog["components"]}
    rows: list[dict[str, Any]] = []
    priced_min = 0.0
    priced_max = 0.0
    unpriced: list[str] = []

    for component_id in architecture["bom"]:
        component = index[component_id]
        price_range = _price_range(component)
        if price_range is None:
            unpriced.append(component_id)
        else:
            priced_min += price_range[0]
            priced_max += price_range[1]
        source = component.get("source") or {}
        rows.append(
            {
                "component_id": component_id,
                "category": component["category"],
                "label": component["label"],
                "manufacturer": component.get("manufacturer"),
                "sku": component.get("sku"),
                "evidence_state": component["evidence_state"],
                "procurement_state": component["procurement_state"],
                "price": component.get("price"),
                "source_url": source.get("url"),
                "source_as_of": source.get("as_of"),
                "hold_reason": component.get("hold_reason"),
            }
        )

    return rows, {
        "known_min_usd": round(priced_min, 2),
        "known_max_usd": round(priced_max, 2),
        "unpriced_component_ids": unpriced,
        "shipping_tax_included": False,
    }


def _compatibility_findings(
    selected_ids: set[str],
    catalog: dict[str, Any],
    compatibility: dict[str, Any],
) -> list[dict[str, Any]]:
    index = {row["id"]: row for row in catalog["components"]}
    findings: list[dict[str, Any]] = []
    covered: set[tuple[str, str]] = set()

    def pair_key(a: str, b: str) -> tuple[str, str]:
        return tuple(sorted((a, b)))

    for rule in compatibility.get("pair_rules", []):
        if rule["a"] not in selected_ids or rule["b"] not in selected_ids:
            continue
        covered.add(pair_key(rule["a"], rule["b"]))
        findings.append(
            {
                "id": rule["id"],
                "state": rule["state"],
                "reason": rule["reason"],
                "a": rule["a"],
                "b": rule["b"],
                "source": "explicit_rule",
            }
        )

    rows = [index[item] for item in selected_ids if item in index]
    for fallback in compatibility.get("category_pair_defaults", []):
        category_a, category_b = fallback["categories"]
        rows_a = [row for row in rows if row["category"] == category_a]
        rows_b = [row for row in rows if row["category"] == category_b]
        for a in rows_a:
            for b in rows_b:
                if a["id"] == b["id"]:
                    continue
                key = pair_key(a["id"], b["id"])
                if key in covered:
                    continue
                covered.add(key)
                findings.append(
                    {
                        "id": f"default:{category_a}:{category_b}:{a['id']}:{b['id']}",
                        "state": fallback["state"],
                        "reason": fallback["reason"],
                        "a": a["id"],
                        "b": b["id"],
                        "source": "category_default",
                    }
                )
    return findings


def _worsen(readiness: str, candidate: str) -> str:
    return candidate if READINESS_RANK[candidate] > READINESS_RANK[readiness] else readiness


def _deck_fit_adjustment(requirements: dict[str, Any], deck_candidate_id: str) -> tuple[float, str]:
    mapping = {
        "compact": {"comp95", "trampa_short_969"},
        "balanced": {"comp95", "pro_warren_iii", "trampa_short_969", "trampa_hs11_969"},
        "long_stable": {"pro_warren_iii", "agent", "trampa_hs11_969"},
    }
    if deck_candidate_id in mapping[requirements["deck_envelope_preference"]]:
        return 0.05, f"Deck envelope matches the {requirements['deck_envelope_preference']} planning preference."
    return -0.02, f"Deck envelope differs from the {requirements['deck_envelope_preference']} planning preference."


def score_architecture(
    profile: dict[str, Any],
    requirements: dict[str, Any],
    architecture: dict[str, Any],
    catalog: dict[str, Any],
    compatibility: dict[str, Any],
) -> dict[str, Any]:
    priorities = requirements["priorities"]
    traits = architecture["traits"]
    preference_fit = {
        "range": float(traits["range"]),
        "carve": 1.0
        - abs(
            float(traits["carve"])
            - float(profile.get("snowboard_feel", 100.0)) / 100.0
        ),
        "stability": 1.0
        - abs(
            float(traits["stability"])
            - float(profile.get("stability_preference", 100.0)) / 100.0
        ),
        "durability": float(traits["durability"]),
        "portability": float(traits["portability"]),
        "cost": float(traits["cost"]),
        "low_maintenance": float(traits["low_maintenance"]),
    }
    weighted = sum(
        priorities[key] * _clamp(preference_fit[key], 0.0, 1.0)
        for key in priorities
    )
    score = weighted
    explanations: list[str] = []
    blockers = list(architecture.get("hard_blockers", []))
    unknowns = list(architecture.get("known_unknowns", []))
    readiness = "BLOCKED" if blockers else "REFERENCE_COMPATIBLE"

    deck_adjustment, deck_explanation = _deck_fit_adjustment(
        requirements, architecture["deck_candidate_id"]
    )
    score += deck_adjustment
    explanations.append(deck_explanation)

    electric_intent = requirements["electric_intent"]
    drive_path = architecture["capabilities"]["drive_path"]
    if electric_intent == "no":
        if drive_path == "NOT_PRESENT":
            score += 0.06
            explanations.append("Unpowered intent avoids unnecessary propulsion complexity.")
        else:
            score -= 0.06
            explanations.append("This architecture carries drive complexity despite an unpowered mission.")
    else:
        if drive_path == "REFERENCE_COMPATIBLE":
            score += 0.06
            explanations.append("Drive reference aligns with the electric mission intent.")
        elif drive_path == "MEASURE_FIRST":
            score += 0.01
            readiness = _worsen(readiness, "MEASURE_FIRST")
            unknowns.append(
                "Drive path is catalog-plausible but still depends on an unresolved physical interface."
            )
            explanations.append(
                "Drive path is promising for the electric mission, but coexistence still needs measurement."
            )
        elif drive_path == "NOT_PRESENT":
            score -= 0.14
            readiness = _worsen(readiness, "MEASURE_FIRST")
            unknowns.append("Electric propulsion is intentionally deferred in this mechanical core.")
            explanations.append("Strong mechanical baseline, but it does not yet satisfy the electric mission.")

    friction = architecture["capabilities"]["friction_brake_path"]
    if requirements["independent_friction_brake_required"]:
        if friction == "REFERENCE_COMPATIBLE":
            score += 0.06
            explanations.append("Independent friction-brake reference matches the mission requirement.")
        elif friction == "MEASURE_FIRST":
            readiness = _worsen(readiness, "MEASURE_FIRST")
            unknowns.append("Independent friction braking depends on unresolved physical coexistence.")
            explanations.append("Brake path is promising but not yet established after the axle/topology change.")
        else:
            readiness = _worsen(readiness, "BLOCKED")
            blockers.append("Mission requires independent friction braking, but this architecture has no documented path.")
            score -= 0.22

    wheel_strategy = requirements["wheel_strategy"]
    wheel_class = architecture["capabilities"]["wheel_class"]
    if wheel_strategy == "nine_inch_rollover_study":
        if wheel_class == "9in_pneumatic":
            score += 0.04
            explanations.append(
                "Nine-inch pneumatic study directly matches the rough-terrain rollover target."
            )
        elif wheel_class == "8in_pneumatic":
            unknowns.append(
                "Rough-terrain profile justifies a separate 9-inch rollover study."
            )
            explanations.append(
                "Eight-inch pneumatics remain a lower-rollover baseline for this terrain model."
            )
            score -= 0.03
    elif wheel_strategy == "eight_inch_pneumatic_reference" and wheel_class == "8in_pneumatic":
        score += 0.03
        explanations.append("Eight-inch pneumatic reference matches the current terrain model.")

    resolved_architecture = copy.deepcopy(architecture)
    resolved_bom = list(resolved_architecture["bom"])
    energy_wh = float(requirements["planning_installed_energy_wh"])
    selected_energy_class = None

    if "BATTERY-TRAIL-CLASS" in resolved_bom:
        if energy_wh <= 650:
            selected_energy_class = "BATTERY-TRAIL-CLASS"
            explanations.append(
                "The 500–650 Wh trail planning class covers the derived mission-energy envelope."
            )
        elif energy_wh <= 1150:
            resolved_bom = [
                "BATTERY-RANGE-CLASS" if item == "BATTERY-TRAIL-CLASS" else item
                for item in resolved_bom
            ]
            selected_energy_class = "BATTERY-RANGE-CLASS"
            explanations.append(
                "Mission energy exceeds the trail-pack class, so this study moves to the 950–1150 Wh range class."
            )
        else:
            resolved_bom = [
                "BATTERY-RANGE-CLASS" if item == "BATTERY-TRAIL-CLASS" else item
                for item in resolved_bom
            ]
            selected_energy_class = "BATTERY-RANGE-CLASS"
            blockers.append(
                "Derived mission energy exceeds the largest seeded 1150 Wh planning class."
            )
            readiness = _worsen(readiness, "BLOCKED")
    elif "BATTERY-RANGE-CLASS" in resolved_bom:
        selected_energy_class = "BATTERY-RANGE-CLASS"
        if energy_wh > 1150:
            blockers.append(
                "Derived mission energy exceeds the largest seeded 1150 Wh planning class."
            )
            readiness = _worsen(readiness, "BLOCKED")

    resolved_architecture["bom"] = resolved_bom
    bom, cost = _bom(resolved_architecture, catalog)
    selected_ids = {row["component_id"] for row in bom}
    pair_rules = _selected_pair_rules(selected_ids, compatibility)
    pair_findings: list[dict[str, Any]] = []
    for rule in pair_rules:
        pair_findings.append(
            {
                "id": rule["id"],
                "state": rule["state"],
                "reason": rule["reason"],
                "a": rule["a"],
                "b": rule["b"],
            }
        )
        if rule["state"] == "INCOMPATIBLE":
            readiness = _worsen(readiness, "INCOMPATIBLE")
            blockers.append(rule["reason"])
        elif rule["state"] in {"MEASURE_FIRST", "UNKNOWN"}:
            readiness = _worsen(readiness, "MEASURE_FIRST")
            unknowns.append(rule["reason"])

    hard_budget = requirements["budget"]["hard_max_usd"]
    if cost["known_min_usd"] > hard_budget:
        blockers.append(
            f"Known-price portion alone (USD {cost['known_min_usd']:.0f}) exceeds the hard budget (USD {hard_budget:.0f})."
        )
        readiness = _worsen(readiness, "BLOCKED")
        score -= 0.18
    elif cost["known_max_usd"] > requirements["budget"]["target_usd"]:
        explanations.append("Known-price portion is above the target budget but remains below the hard maximum.")
        score -= 0.04
    else:
        score += 0.03

    procurement_states = {row["procurement_state"] for row in bom}
    if "POWER_GATED" in procurement_states or blockers:
        checkout_state = "BLOCKED"
    elif procurement_states.intersection({"HOLD_MEASURE", "STUDY_ONLY"}):
        checkout_state = "HOLD_MEASURE"
    else:
        checkout_state = "SOURCE_LINKS"

    if cost["unpriced_component_ids"]:
        unknowns.append("Some study/reference components are unpriced; displayed BOM total is partial.")

    score = _clamp(score, 0.0, 1.0)
    explanations.insert(
        0,
        f"Priority-weighted preference match is {weighted * 100:.0f}% before mission compatibility adjustments."
    )

    return {
        "id": architecture["id"],
        "architecture_id": architecture["id"],
        "label": architecture["label"],
        "short_label": architecture["short_label"],
        "description": architecture["description"],
        "fit_score": round(score, 4),
        "readiness": readiness,
        "checkout_state": checkout_state,
        "visual_preset": architecture["visual_preset"],
        "deck_candidate_id": architecture["deck_candidate_id"],
        "topology_id": architecture["topology_id"],
        "traits": copy.deepcopy(traits),
        "preference_fit": {
            key: round(_clamp(value, 0.0, 1.0), 4)
            for key, value in preference_fit.items()
        },
        "capabilities": copy.deepcopy(architecture["capabilities"]),
        "personalized_spec": {
            "target_range_mi": requirements["target_range_mi"],
            "planning_installed_energy_wh": requirements[
                "planning_installed_energy_wh"
            ],
            "selected_energy_class": selected_energy_class,
            "wheel_strategy": requirements["wheel_strategy"],
            "stance_center_mm": requirements["stance_study"]["center_mm"],
            "stance_range_mm": [
                requirements["stance_study"]["min_mm"],
                requirements["stance_study"]["max_mm"],
            ],
            "independent_friction_brake_required": requirements[
                "independent_friction_brake_required"
            ],
        },
        "bom": bom,
        "cost": cost,
        "compatibility_findings": pair_findings,
        "explanations": list(dict.fromkeys(explanations)),
        "blockers": list(dict.fromkeys(blockers)),
        "unknowns": list(dict.fromkeys(unknowns)),
        "authority": {
            "procurement_authorized": False,
            "fabrication_authorized": False,
            "powered_operation_authorized": False,
        },
    }


def _non_dominated(candidates: list[dict[str, Any]]) -> set[str]:
    """Return candidates not strictly dominated on declared soft traits."""
    ids: set[str] = set()
    metrics = (
        "range",
        "carve",
        "stability",
        "durability",
        "portability",
        "cost",
        "low_maintenance",
    )
    for candidate in candidates:
        dominated = False
        for other in candidates:
            if candidate is other:
                continue
            no_worse = all(
                float(other["traits"][metric]) >= float(candidate["traits"][metric])
                for metric in metrics
            )
            strictly_better = any(
                float(other["traits"][metric]) > float(candidate["traits"][metric])
                for metric in metrics
            )
            if no_worse and strictly_better:
                dominated = True
                break
        if not dominated:
            ids.add(candidate["id"])
    return ids


def generate_candidates(
    profile: dict[str, Any],
    *,
    bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = bundle or load_bundle()
    normalized = normalize_profile(profile, data["questionnaire"])
    requirements = derive_requirements(normalized, data["rules"], data["questionnaire"])
    candidates = [
        score_architecture(
            normalized,
            requirements,
            architecture,
            data["catalog"],
            data["compatibility"],
        )
        for architecture in data["architectures"]["architectures"]
    ]
    frontier = _non_dominated(candidates)
    for candidate in candidates:
        candidate["trade_space_frontier"] = candidate["id"] in frontier
    candidates.sort(
        key=lambda row: (
            -row["fit_score"],
            READINESS_RANK[row["readiness"]],
            row["label"],
        )
    )
    return {
        "schema_version": 1,
        "profile": normalized,
        "requirements": requirements,
        "candidates": candidates,
        "winner_selected": False,
        "authority": {
            "generic_builder_may_promote_x1_authority": False,
            "procurement_authorized": False,
            "fabrication_authorized": False,
            "powered_operation_authorized": False,
        },
    }


def render_bom_markdown(candidate: dict[str, Any]) -> str:
    lines = [
        f"# {candidate['label']} BOM",
        "",
        f"**Compatibility readiness:** {candidate['readiness']}",
        f"**Checkout state:** {candidate['checkout_state']}",
        "",
        "| Category | Component | State | Price | Source |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in candidate["bom"]:
        price = row.get("price")
        if not price:
            price_text = "unpriced"
        elif price["kind"] in {"unit", "ceiling"}:
            price_text = f"USD {price['unit_price_usd'] * price.get('qty', 1):.2f}"
        else:
            price_text = (
                f"USD {price['min_usd'] * price.get('qty', 1):.2f}"
                f"–{price['max_usd'] * price.get('qty', 1):.2f}"
            )
        source = row.get("source_url") or "reference / TBD"
        lines.append(
            f"| {row['category']} | {row['label']} | {row['procurement_state']} | "
            f"{price_text} | {source} |"
        )

    cost = candidate["cost"]
    lines += [
        "",
        f"Known-price subtotal: **USD {cost['known_min_usd']:.2f}–{cost['known_max_usd']:.2f}** before shipping/tax.",
    ]
    if cost["unpriced_component_ids"]:
        lines.append(
            "Unpriced study/reference items: " + ", ".join(cost["unpriced_component_ids"])
        )
    lines += [
        "",
        "> Source links are not checkout authorization. Refresh live stock/price and resolve every HOLD/POWER_GATED item before purchase.",
        "> This configurator cannot create fabrication or powered-operation authority.",
        "",
    ]
    return "\\n".join(lines)
