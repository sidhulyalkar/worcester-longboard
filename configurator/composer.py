"""Bounded catalog synthesis for the Worcester Board Builder.

The composer creates non-authoritative architecture hypotheses from normalized
catalog slots. Every combination is evaluated through the same Swap Lab
compatibility contract before the standard rider-fit scorer sees it.
"""
from __future__ import annotations

import copy
from typing import Any

from configurator.engine import READINESS_RANK, score_architecture
from configurator.swap_lab import evaluate_swap


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _slot_options(slots: dict[str, Any]) -> dict[str, dict[Any, dict[str, Any]]]:
    return {
        slot["id"]: {option.get("value"): option for option in slot.get("options", [])}
        for slot in slots.get("slots", [])
    }


def _component_index(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in catalog.get("components", [])}


def _normalized(value: float, bounds: list[float]) -> float:
    lo, hi = map(float, bounds)
    if hi <= lo:
        return 0.5
    return _clamp((float(value) - lo) / (hi - lo))


def _chosen_battery(
    requirements: dict[str, Any],
    composer: dict[str, Any],
) -> str | None:
    if requirements["electric_intent"] == "no":
        return None
    classes = composer.get("electric_policy", {}).get("battery_classes", [])
    energy = float(requirements["planning_installed_energy_wh"])
    if energy <= 650 and "BATTERY-TRAIL-CLASS" in classes:
        return "BATTERY-TRAIL-CLASS"
    if "BATTERY-RANGE-CLASS" in classes:
        return "BATTERY-RANGE-CLASS"
    return classes[0] if classes else None


def _geometry_index(geometry: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        {row["id"]: row for row in geometry.get("decks", [])},
        {row["id"]: row for row in geometry.get("topologies", [])},
    )


def _wheel_geometry(component: dict[str, Any] | None) -> dict[str, Any]:
    interfaces = (component or {}).get("interfaces") or {}
    return {
        "diameter_mm": float(
            interfaces.get(
                "measured_reference_diameter_mm",
                interfaces.get("published_diameter_mm", 0),
            )
        ),
        "width_mm": float(
            interfaces.get(
                "measured_reference_width_mm",
                interfaces.get("published_width_mm", 0),
            )
        ),
        "wheel_class": interfaces.get("wheel_class", "unknown"),
    }


def _path_state(
    selected_id: str | None,
    category: str,
    evaluation: dict[str, Any],
) -> str:
    if not selected_id:
        return "NOT_PRESENT"
    if not any(
        row["category"] == category and row["component_id"] == selected_id
        for row in evaluation["bom"]
    ):
        return "NOT_PRESENT"

    relevant = [
        finding
        for finding in evaluation["compatibility_findings"]
        if finding["a"] == selected_id or finding["b"] == selected_id
    ]
    if any(finding["state"] == "INCOMPATIBLE" for finding in relevant):
        return "INCOMPATIBLE"
    if any(
        finding["state"] in {"UNKNOWN", "MEASURE_FIRST"}
        for finding in relevant
    ):
        return "MEASURE_FIRST"
    return "REFERENCE_COMPATIBLE"


def _vendor_family(evaluation: dict[str, Any]) -> str:
    makers = sorted(
        {
            str(row["manufacturer"])
            for row in evaluation["bom"]
            if row.get("manufacturer")
        }
    )
    if not makers:
        return "Catalog mix"
    if len(makers) == 1:
        return makers[0]
    return "Cross-vendor"


def _traits_for(
    selection: dict[str, Any],
    evaluation: dict[str, Any],
    bundle: dict[str, Any],
) -> dict[str, float]:
    model = bundle["composer"]["trait_model"]
    decks, topologies = _geometry_index(bundle["geometry"])
    components = _component_index(bundle["catalog"])

    deck = decks.get(selection["deck"], {})
    topology = topologies.get(selection["topology"], {})
    wheel = _wheel_geometry(components.get(selection["wheel"]))
    drive = components.get(selection["drive"]) if selection["drive"] else None
    brake = components.get(selection["brake"]) if selection["brake"] else None

    deck_n = _normalized(
        float(deck.get("length_mm", 950)),
        model["deck_length_bounds_mm"],
    )
    truck_n = _normalized(
        float(topology.get("truck_total_width_mm", 400)),
        model["truck_width_bounds_mm"],
    )
    wheel_n = _normalized(
        float(wheel["diameter_mm"] or 200),
        model["wheel_diameter_bounds_mm"],
    )

    steering = str(topology.get("steering_family", ""))
    steering_carve = 0.04
    if "channel" in steering:
        steering_carve = 0.08
    elif "parallel" in steering:
        steering_carve = 0.05
    elif "precision" in steering:
        steering_carve = 0.10

    drive_type = str(((drive or {}).get("interfaces") or {}).get("drive_type", "none"))
    powered = bool(selection["drive"])
    battery_range = selection["battery"] == "BATTERY-RANGE-CLASS"
    unknown_penalty = min(0.12, len(evaluation["unknowns"]) * 0.03)
    known_cost = float(evaluation["cost"]["known_min_usd"] or 0)
    unpriced_penalty = min(
        0.20,
        len(evaluation["cost"]["unpriced_component_ids"]) * 0.04,
    )

    low_maintenance = 0.92
    if drive_type == "gear":
        low_maintenance = 0.72
    elif "belt" in drive_type:
        low_maintenance = 0.56
    elif powered:
        low_maintenance = 0.62
    brake_family = str(((brake or {}).get("interfaces") or {}).get("brake_family", ""))
    if "hs11" in brake_family:
        low_maintenance -= 0.04

    return {
        "range": round(_clamp(0.95 if battery_range else 0.76 if powered else 0.18), 6),
        "carve": round(
            _clamp(0.70 + (1 - deck_n) * 0.15 + steering_carve - truck_n * 0.03),
            6,
        ),
        "stability": round(
            _clamp(0.58 + truck_n * 0.17 + deck_n * 0.10 + wheel_n * 0.06),
            6,
        ),
        "durability": round(
            _clamp(0.84 - (0.07 if powered else 0) - unknown_penalty),
            6,
        ),
        "portability": round(
            _clamp(0.93 - deck_n * 0.18 - wheel_n * 0.12 - (0.16 if powered else 0)),
            6,
        ),
        "cost": round(
            _clamp(
                1
                - known_cost / float(model.get("known_cost_reference_usd", 2500))
                - unpriced_penalty
            ),
            6,
        ),
        "low_maintenance": round(
            _clamp(low_maintenance - unknown_penalty * 0.4),
            6,
        ),
        "rough_terrain": round(
            _clamp(0.58 + wheel_n * 0.30 + truck_n * 0.08),
            6,
        ),
    }


def _visual_preset(selection: dict[str, Any]) -> str:
    if selection["drive"]:
        return "drive_packaging"
    if selection["brake"]:
        return "brake_first_trail"
    return "snowdeck_fit"


def _short_option_label(
    options: dict[str, dict[Any, dict[str, Any]]],
    slot: str,
    value: Any,
) -> str:
    label = options.get(slot, {}).get(value, {}).get("label", str(value or "none"))
    return label.split("·")[0].strip()


def _composition_label(
    selection: dict[str, Any],
    options: dict[str, dict[Any, dict[str, Any]]],
) -> str:
    deck = _short_option_label(options, "deck", selection["deck"])
    truck = _short_option_label(options, "topology", selection["topology"])
    wheel = _short_option_label(options, "wheel", selection["wheel"])
    return f"Compose · {deck} / {truck} / {wheel}"


def _slug(value: Any) -> str:
    raw = str(value or "none").lower()
    out = []
    previous_dash = False
    for char in raw:
        if char.isalnum():
            out.append(char)
            previous_dash = False
        elif not previous_dash:
            out.append("-")
            previous_dash = True
    return "".join(out).strip("-")


def _selection_id(selection: dict[str, Any]) -> str:
    return "__".join(
        [
            "synth",
            _slug(selection["deck"]),
            _slug(selection["topology"]),
            _slug(selection["wheel"]),
            _slug(selection["brake"]),
            _slug(selection["drive"]),
            _slug(selection["battery"]),
        ]
    )


def _synthetic_baseline(
    requirements: dict[str, Any],
    selection: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": "catalog_composer_seed",
        "architecture_id": "catalog_composer_seed",
        "label": "Catalog composer seed",
        "deck_candidate_id": selection["deck"],
        "topology_id": selection["topology"],
        "bom": [],
        "cost": {
            "known_min_usd": 0,
            "known_max_usd": 0,
            "unpriced_component_ids": [],
            "shipping_tax_included": False,
        },
        "capabilities": {"wheel_class": "unknown"},
        "personalized_spec": {
            "stance_center_mm": requirements["stance_study"]["center_mm"],
        },
        "swap_defaults": copy.deepcopy(selection),
    }


def _architecture_from_selection(
    profile: dict[str, Any],
    requirements: dict[str, Any],
    selection: dict[str, Any],
    evaluation: dict[str, Any],
    bundle: dict[str, Any],
) -> dict[str, Any]:
    options = _slot_options(bundle["swapSlots"])
    components = _component_index(bundle["catalog"])
    wheel_component = components.get(selection["wheel"], {})
    wheel_class = (wheel_component.get("interfaces") or {}).get(
        "wheel_class", "unknown"
    )
    brake_path = _path_state(selection["brake"], "brake", evaluation)
    drive_path = _path_state(selection["drive"], "drive", evaluation)
    family = _vendor_family(evaluation)
    candidate_id = _selection_id(selection)

    architecture = {
        "id": candidate_id,
        "label": _composition_label(selection, options),
        "short_label": (
            "Composed mix"
            if family == "Cross-vendor"
            else f"Composed {family}"
        ),
        "vendor_family": family,
        "description": (
            "Catalog-composed planning study generated from normalized parts. "
            "Every critical interface is evaluated through the same fail-closed "
            "compatibility rules as Swap Lab."
        ),
        "visual_preset": _visual_preset(selection),
        "deck_candidate_id": selection["deck"],
        "topology_id": selection["topology"],
        "traits": _traits_for(selection, evaluation, bundle),
        "capabilities": {
            "friction_brake_path": brake_path,
            "drive_path": drive_path,
            "electric_complete": False,
            "wheel_class": wheel_class,
            "snowdeck": False,
        },
        "bom": [row["component_id"] for row in evaluation["bom"]],
        "known_unknowns": list(evaluation["unknowns"]),
        "hard_blockers": list(evaluation["blockers"]),
    }

    scored = score_architecture(
        profile,
        requirements,
        architecture,
        bundle["catalog"],
        bundle["compatibility"],
    )
    scored["origin"] = "SYNTHESIZED"
    scored["swap_defaults"] = copy.deepcopy(selection)
    states = (
        "REFERENCE_COMPATIBLE",
        "MEASURE_FIRST",
        "UNKNOWN",
        "INCOMPATIBLE",
    )
    scored["composition"] = {
        "schema_version": 1,
        "engine": "catalog_composer_v1",
        "selection": copy.deepcopy(selection),
        "manufacturers": sorted(
            {
                str(row["manufacturer"])
                for row in evaluation["bom"]
                if row.get("manufacturer")
            }
        ),
        "compatibility_states": {
            state: sum(
                finding["state"] == state
                for finding in evaluation["compatibility_findings"]
            )
            for state in states
        },
        "unknown_count": len(evaluation["unknowns"]),
        "rationale": (
            "Generated from catalog slots, pruned by Swap Lab compatibility, "
            "then scored by the standard rider-fit engine."
        ),
    }
    return scored


def _bom_signature(candidate: dict[str, Any]) -> str:
    return "|".join(
        sorted(row["component_id"] for row in candidate.get("bom", []))
    )


def compose_candidates(
    profile: dict[str, Any],
    requirements: dict[str, Any],
    bundle: dict[str, Any],
) -> list[dict[str, Any]]:
    composer = bundle.get("composer") or {}
    if not composer.get("enabled"):
        return []

    options = _slot_options(bundle["swapSlots"])
    allowed = set(
        composer.get(
            "allowed_readiness",
            ["REFERENCE_COMPATIBLE", "MEASURE_FIRST"],
        )
    )
    battery = _chosen_battery(requirements, composer)
    if requirements["electric_intent"] == "no":
        drives = [composer.get("manual_policy", {}).get("drive")]
        batteries = [composer.get("manual_policy", {}).get("battery")]
    else:
        drives = list(composer.get("slots", {}).get("drive", []))
        batteries = [battery]

    brakes = list(composer.get("slots", {}).get("brake", []))
    if not requirements["independent_friction_brake_required"]:
        brakes = [None, *brakes]

    selections: list[dict[str, Any]] = []
    raw_count = 0
    stop = False
    for deck in composer.get("slots", {}).get("deck", []):
        if stop:
            break
        for topology in composer.get("slots", {}).get("topology", []):
            if stop:
                break
            for wheel in composer.get("slots", {}).get("wheel", []):
                if stop:
                    break
                for brake in brakes:
                    if stop:
                        break
                    for drive in drives:
                        if stop:
                            break
                        for selected_battery in batteries:
                            raw_count += 1
                            if raw_count > int(
                                composer.get("max_raw_combinations", 5000)
                            ):
                                stop = True
                                break
                            if drive and not selected_battery:
                                continue
                            if not drive and selected_battery:
                                continue
                            selections.append(
                                {
                                    "deck": deck,
                                    "topology": topology,
                                    "wheel": wheel,
                                    "brake": brake,
                                    "drive": drive,
                                    "battery": selected_battery,
                                    "rider_interface": composer.get(
                                        "fixed_selection", {}
                                    ).get("rider_interface"),
                                    "armor": composer.get(
                                        "fixed_selection", {}
                                    ).get("armor"),
                                    "dock": composer.get(
                                        "fixed_selection", {}
                                    ).get("dock"),
                                }
                            )

    candidates: list[dict[str, Any]] = []
    seen_bom: set[str] = set()

    for selection in selections:
        valid = all(
            value in options.get(slot, {})
            for slot, value in selection.items()
        )
        if not valid:
            continue

        evaluation = evaluate_swap(
            _synthetic_baseline(requirements, selection),
            requirements,
            selection,
            bundle=bundle,
            slots=bundle["swapSlots"],
        )

        if evaluation["readiness"] not in allowed:
            continue
        if evaluation["blockers"]:
            continue
        if len(evaluation["unknowns"]) > int(
            composer.get("max_unknown_findings", 3)
        ):
            continue

        candidate = _architecture_from_selection(
            profile,
            requirements,
            selection,
            evaluation,
            bundle,
        )
        if candidate["readiness"] not in allowed:
            continue
        if candidate["blockers"]:
            continue

        signature = _bom_signature(candidate)
        if signature in seen_bom:
            continue
        seen_bom.add(signature)
        candidates.append(candidate)

    candidates.sort(
        key=lambda candidate: (
            -candidate["fit_score"],
            READINESS_RANK[candidate["readiness"]],
            candidate["id"],
        )
    )

    selected: list[dict[str, Any]] = []
    family_counts: dict[str, int] = {}
    max_per_family = int(composer.get("max_per_vendor_family", 3))
    max_candidates = int(composer.get("max_synthesized_candidates", 8))
    for candidate in candidates:
        family = candidate["vendor_family"]
        count = family_counts.get(family, 0)
        if count >= max_per_family:
            continue
        selected.append(candidate)
        family_counts[family] = count + 1
        if len(selected) >= max_candidates:
            break

    return selected
