"""Deterministic non-authoritative component Swap Lab.

A custom design is a study state layered on top of a generated candidate. It
cannot create procurement, fabrication, charging, or powered-operation authority.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from configurator.engine import READINESS_RANK, generate_candidates, load_bundle

ROOT = Path(__file__).resolve().parents[1]
SLOTS_PATH = ROOT / "configurator" / "swap_slots.v1.json"


def load_slots() -> dict[str, Any]:
    return json.loads(SLOTS_PATH.read_text(encoding="utf-8"))


def _worsen(current: str, candidate: str) -> str:
    return candidate if READINESS_RANK[candidate] > READINESS_RANK[current] else current


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _component_index(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in catalog["components"]}


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


def _bom_rows(ids: list[str], catalog: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = _component_index(catalog)
    rows: list[dict[str, Any]] = []
    low = 0.0
    high = 0.0
    unpriced: list[str] = []
    for component_id in _dedupe(ids):
        component = index[component_id]
        price = _price_range(component)
        if price is None:
            unpriced.append(component_id)
        else:
            low += price[0]
            high += price[1]
        rows.append(
            {
                "component_id": component_id,
                "category": component["category"],
                "label": component["label"],
                "manufacturer": component.get("manufacturer"),
                "sku": component.get("sku"),
                "evidence_state": component["evidence_state"],
                "procurement_state": component["procurement_state"],
                "price": copy.deepcopy(component.get("price")),
                "source_url": (component.get("source") or {}).get("url"),
                "source_as_of": (component.get("source") or {}).get("as_of"),
                "hold_reason": component.get("hold_reason"),
            }
        )
    return rows, {
        "known_min_usd": round(low, 2),
        "known_max_usd": round(high, 2),
        "unpriced_component_ids": unpriced,
        "shipping_tax_included": False,
    }


def _slot_options(slots: dict[str, Any]) -> dict[str, dict[Any, dict[str, Any]]]:
    return {
        slot["id"]: {option.get("value"): option for option in slot["options"]}
        for slot in slots["slots"]
    }


def seed_selection(candidate: dict[str, Any]) -> dict[str, Any]:
    bom_ids = {row["component_id"] for row in candidate["bom"]}
    wheel = None
    if candidate.get("capabilities", {}).get("wheel_class") == "8in_pneumatic":
        wheel = "TIRE-T1-8-REF"
    elif "TIRE-T2-9" in bom_ids:
        wheel = "TIRE-T2-9"

    battery = next(
        (item for item in ("BATTERY-TRAIL-CLASS", "BATTERY-RANGE-CLASS") if item in bom_ids),
        None,
    )

    return {
        "deck": candidate["deck_candidate_id"],
        "topology": candidate["topology_id"],
        "wheel": wheel,
        "brake": "BRAKE-V5" if "BRAKE-V5" in bom_ids else None,
        "drive": "DRIVE-G1-DUAL" if "DRIVE-G1-DUAL" in bom_ids else None,
        "battery": battery,
        "rider_interface": "SNOWDECK-V01-CUSTOM" if "SNOWDECK-V01-CUSTOM" in bom_ids else None,
        "armor": "TRAIL-ARMOR-STUDY" if "TRAIL-ARMOR-STUDY" in bom_ids else None,
        "dock": "PASSIVE-DOCK-STUDY" if "PASSIVE-DOCK-STUDY" in bom_ids else None,
    }


def validate_selection(selection: dict[str, Any], slots: dict[str, Any]) -> None:
    options = _slot_options(slots)
    expected = set(options)
    if set(selection) != expected:
        missing = sorted(expected - set(selection))
        extra = sorted(set(selection) - expected)
        raise ValueError(f"swap selection keys mismatch; missing={missing} extra={extra}")
    for slot_id, value in selection.items():
        if value not in options[slot_id]:
            raise ValueError(f"{slot_id}: unknown swap option {value!r}")


def _matches(rule: dict[str, Any], selection: dict[str, Any]) -> bool:
    return all(selection.get(key) == value for key, value in rule.get("when", {}).items())


def resolve_component_ids(
    selection: dict[str, Any],
    slots: dict[str, Any],
) -> list[str]:
    validate_selection(selection, slots)
    options = _slot_options(slots)

    packaged = next(
        (rule for rule in slots.get("packaged_foundation_rules", []) if _matches(rule, selection)),
        None,
    )

    component_ids: list[str] = []
    if packaged:
        component_ids.extend(packaged.get("use", []))
    else:
        for slot_id in ("deck", "topology", "wheel"):
            component_id = options[slot_id][selection[slot_id]].get("component_id")
            if component_id:
                component_ids.append(component_id)
        if selection["wheel"] in {"TIRE-T1-8-REF", "TIRE-T2-9"}:
            component_ids.append("HUB-RSII")
        component_ids.extend(
            slots.get("topology_support_components", {}).get(selection["topology"], [])
        )

    for slot_id in ("brake", "drive", "battery", "rider_interface", "armor", "dock"):
        value = selection[slot_id]
        if value:
            component_ids.append(options[slot_id][value]["component_id"])

    if selection["drive"]:
        component_ids.extend(
            slots.get("automatic_support_components", {}).get(selection["drive"], [])
        )

    return _dedupe(component_ids)


def _pair_findings(
    component_ids: set[str],
    compatibility: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for rule in compatibility.get("pair_rules", []):
        if rule["a"] in component_ids and rule["b"] in component_ids:
            findings.append(
                {
                    "id": rule["id"],
                    "state": rule["state"],
                    "a": rule["a"],
                    "b": rule["b"],
                    "reason": rule["reason"],
                }
            )
    return findings


def _battery_max_wh(selection: dict[str, Any], catalog: dict[str, Any]) -> float | None:
    battery_id = selection.get("battery")
    if not battery_id:
        return None
    component = _component_index(catalog)[battery_id]
    energy = (component.get("interfaces") or {}).get("energy_class_wh")
    if not energy:
        return None
    return float(max(energy))


def evaluate_swap(
    baseline_candidate: dict[str, Any],
    requirements: dict[str, Any],
    selection: dict[str, Any],
    *,
    bundle: dict[str, Any] | None = None,
    slots: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = bundle or load_bundle()
    slot_data = slots or load_slots()
    validate_selection(selection, slot_data)

    component_ids = resolve_component_ids(selection, slot_data)
    bom, cost = _bom_rows(component_ids, data["catalog"])
    selected_ids = set(component_ids)
    findings = _pair_findings(selected_ids, data["compatibility"])

    readiness = "REFERENCE_COMPATIBLE"
    blockers: list[str] = []
    unknowns: list[str] = []
    notes: list[str] = []

    for finding in findings:
        if finding["state"] == "INCOMPATIBLE":
            readiness = _worsen(readiness, "INCOMPATIBLE")
            blockers.append(finding["reason"])
        elif finding["state"] in {"MEASURE_FIRST", "UNKNOWN"}:
            readiness = _worsen(readiness, "MEASURE_FIRST")
            unknowns.append(finding["reason"])

    if selection["deck"] != "comp95":
        readiness = _worsen(readiness, "MEASURE_FIRST")
        unknowns.append(
            "Deck-to-truck structural interface is not normalized for this seed catalog; received geometry or a sourced mount pattern is required."
        )

    if requirements["independent_friction_brake_required"] and not selection["brake"]:
        readiness = _worsen(readiness, "BLOCKED")
        blockers.append(
            "The rider mission requires an independent friction brake, but the edited design removes it."
        )

    if requirements["electric_intent"] != "no":
        if not selection["drive"]:
            readiness = _worsen(readiness, "MEASURE_FIRST")
            unknowns.append(
                "The rider requested an electric-capable mission, but the edited design contains no drive."
            )
        elif not selection["battery"]:
            readiness = _worsen(readiness, "BLOCKED")
            blockers.append(
                "A drive is selected without a traction-energy class."
            )

    if selection["battery"] and not selection["drive"]:
        readiness = _worsen(readiness, "MEASURE_FIRST")
        unknowns.append(
            "A traction-energy class is selected without a drive; keep it only as a packaging study."
        )

    battery_max = _battery_max_wh(selection, data["catalog"])
    if battery_max is not None:
        required_wh = float(requirements["planning_installed_energy_wh"])
        if required_wh > battery_max:
            readiness = _worsen(readiness, "BLOCKED")
            blockers.append(
                f"Derived mission energy ({required_wh:.0f} Wh) exceeds the selected battery-class ceiling ({battery_max:.0f} Wh)."
            )

    if (
        requirements["wheel_strategy"] == "nine_inch_rollover_study"
        and selection["wheel"] == "TIRE-T1-8-REF"
    ):
        readiness = _worsen(readiness, "MEASURE_FIRST")
        unknowns.append(
            "The terrain model calls for a 9-inch rollover study, but the edited design retains the 8-inch reference."
        )

    if selection["wheel"] == "TIRE-T2-9":
        notes.append(
            "The 9-inch tire is a rollover study only; hub fit, clearance and gearing remain separate checks."
        )

    procurement_states = {row["procurement_state"] for row in bom}
    if "POWER_GATED" in procurement_states or blockers:
        checkout_state = "BLOCKED"
    elif procurement_states.intersection({"HOLD_MEASURE", "STUDY_ONLY"}):
        checkout_state = "HOLD_MEASURE"
    else:
        checkout_state = "SOURCE_LINKS"

    baseline_cost = baseline_candidate["cost"]
    delta_min = round(cost["known_min_usd"] - baseline_cost["known_min_usd"], 2)
    delta_max = round(cost["known_max_usd"] - baseline_cost["known_max_usd"], 2)

    baseline_selection = seed_selection(baseline_candidate)
    changes = [
        {
            "slot": slot_id,
            "from": baseline_selection[slot_id],
            "to": selection[slot_id],
        }
        for slot_id in baseline_selection
        if baseline_selection[slot_id] != selection[slot_id]
    ]

    layer_states = {
        "brake": bool(selection["brake"]),
        "drive": bool(selection["drive"]),
        "pack": bool(selection["battery"]),
        "snowdeck": bool(selection["rider_interface"]),
        "armor": bool(selection["armor"]),
        "dock": bool(selection["dock"]),
    }

    return {
        "schema_version": 1,
        "scope": "non_authoritative_component_swap_study",
        "baseline_candidate_id": baseline_candidate["id"],
        "selection": copy.deepcopy(selection),
        "changes": changes,
        "readiness": readiness,
        "checkout_state": checkout_state,
        "bom": bom,
        "cost": cost,
        "cost_delta_vs_baseline": {
            "known_min_usd": delta_min,
            "known_max_usd": delta_max,
        },
        "compatibility_findings": findings,
        "blockers": list(dict.fromkeys(blockers)),
        "unknowns": list(dict.fromkeys(unknowns)),
        "notes": list(dict.fromkeys(notes)),
        "twin_state": {
            "deck_candidate_id": selection["deck"],
            "topology_id": selection["topology"],
            "stance_mm": baseline_candidate.get("personalized_spec", {}).get("stance_center_mm"),
            "layers": layer_states,
        },
        "authority": {
            "procurement_authorized": False,
            "fabrication_authorized": False,
            "powered_operation_authorized": False,
            "generic_builder_may_promote_x1_authority": False,
        },
    }


def evaluate_profile_swap(
    profile: dict[str, Any],
    candidate_id: str,
    selection: dict[str, Any],
) -> dict[str, Any]:
    generated = generate_candidates(profile)
    try:
        candidate = next(row for row in generated["candidates"] if row["id"] == candidate_id)
    except StopIteration as exc:
        raise ValueError(f"unknown candidate {candidate_id!r}") from exc
    return evaluate_swap(
        candidate,
        generated["requirements"],
        selection,
    )
