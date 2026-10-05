#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text())


def validate() -> dict[str, Any]:
    q = load("configurator/questionnaire.v1.json")
    rules = load("configurator/rules.v1.json")
    catalog = load("catalog/board_components.v1.json")
    architectures = load("configurator/architectures.v1.json")
    compatibility = load("configurator/compatibility_rules.v1.json")
    swap_slots = load("configurator/swap_slots.v1.json")
    refs = load("configurator/reference_builds.v1.json")
    visual_schema = load("configurator/schemas/candidate_visual_state.schema.json")
    twin = load("showcase/x1_rev_c.json")

    errors: list[str] = []
    warnings: list[str] = []

    field_ids: set[str] = set()
    for section in q.get("sections", []):
        for field in section.get("fields", []):
            fid = field.get("id")
            if not fid or fid in field_ids:
                errors.append(f"duplicate/missing questionnaire field id: {fid!r}")
                continue
            field_ids.add(fid)
            if field.get("type") in {"number", "range"} and field.get("default") is not None:
                default = field["default"]
                if "min" in field and default < field["min"]:
                    errors.append(f"{fid}: default below min")
                if "max" in field and default > field["max"]:
                    errors.append(f"{fid}: default above max")

    components = catalog.get("components", [])
    component_ids = [row.get("id") for row in components]
    if len(component_ids) != len(set(component_ids)):
        errors.append("component ids must be unique")
    component_index = {row["id"]: row for row in components}

    valid_procurement = {"SOURCE_ONLY", "HOLD_MEASURE", "POWER_GATED", "STUDY_ONLY", "BUY_CANDIDATE"}
    valid_evidence = {"QUALIFIED", "REFERENCE", "ASSUMED", "BLOCKED", "NOT_PRESENT"}
    for row in components:
        cid = row["id"]
        if row.get("procurement_state") not in valid_procurement:
            errors.append(f"{cid}: invalid procurement_state")
        if row.get("evidence_state") not in valid_evidence:
            errors.append(f"{cid}: invalid evidence_state")
        source = row.get("source") or {}
        if source.get("kind") == "vendor":
            if not source.get("url") or not source.get("as_of"):
                errors.append(f"{cid}: vendor source requires url + as_of")
        if row.get("category") in {"drive", "motor", "esc", "battery", "charger"}:
            if row.get("procurement_state") != "POWER_GATED":
                errors.append(f"{cid}: live-power category must remain POWER_GATED in seed catalog")
        if row.get("procurement_state") == "BUY_CANDIDATE":
            warnings.append(f"{cid}: BUY_CANDIDATE exists; verify generic purchase policy intentionally allows it")

    architecture_ids: set[str] = set()
    required_traits = {"range", "carve", "stability", "durability", "portability", "cost", "low_maintenance", "rough_terrain"}
    twin_presets = {
        row["id"]
        for row in twin.get("design_studies", {}).get("configuration_lab", {}).get("presets", [])
    }
    deck_ids = {row["id"] for row in twin.get("design_studies", {}).get("deck_candidates", [])}
    topology_ids = {row["id"] for row in twin.get("design_studies", {}).get("topology_branches", [])}

    for architecture in architectures.get("architectures", []):
        aid = architecture.get("id")
        if not aid or aid in architecture_ids:
            errors.append(f"duplicate/missing architecture id: {aid!r}")
            continue
        architecture_ids.add(aid)
        missing = [cid for cid in architecture.get("bom", []) if cid not in component_index]
        if missing:
            errors.append(f"{aid}: unknown BOM ids {missing}")
        if architecture.get("visual_preset") not in twin_presets:
            errors.append(f"{aid}: visual_preset does not resolve in showcase")
        if architecture.get("deck_candidate_id") not in deck_ids:
            errors.append(f"{aid}: unknown deck candidate")
        if architecture.get("topology_id") not in topology_ids:
            errors.append(f"{aid}: unknown topology")
        traits = architecture.get("traits") or {}
        if set(traits) != required_traits:
            errors.append(f"{aid}: trait vector must exactly match required traits")
        for key, value in traits.items():
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
                errors.append(f"{aid}: trait {key} must be numeric 0..1")
        if "winner" in architecture or "qualified" in architecture or "authority" in architecture:
            errors.append(f"{aid}: architecture template may not carry winner/authority claims")

    for rule in compatibility.get("pair_rules", []):
        for side in ("a", "b"):
            if rule.get(side) not in component_index:
                errors.append(f"{rule.get('id')}: compatibility rule references unknown {side}")

    if swap_slots.get("scope") != "non_authoritative_component_swap_study":
        errors.append("swap_slots scope must remain non-authoritative")

    swap_slot_ids: set[str] = set()
    slot_options: dict[str, set[Any]] = {}
    for slot in swap_slots.get("slots", []):
        slot_id = slot.get("id")
        if not slot_id or slot_id in swap_slot_ids:
            errors.append(f"duplicate/missing swap slot id: {slot_id!r}")
            continue
        swap_slot_ids.add(slot_id)
        values: set[Any] = set()
        for option in slot.get("options", []):
            value = option.get("value")
            if value in values:
                errors.append(f"{slot_id}: duplicate swap option {value!r}")
            values.add(value)
            component_id = option.get("component_id")
            if component_id is not None and component_id not in component_index:
                errors.append(
                    f"{slot_id}: swap option references unknown component {component_id!r}"
                )
            twin_deck_id = option.get("twin_deck_id")
            if twin_deck_id is not None and twin_deck_id not in deck_ids:
                errors.append(
                    f"{slot_id}: unknown twin deck id {twin_deck_id!r}"
                )
            twin_topology_id = option.get("twin_topology_id")
            if twin_topology_id is not None and twin_topology_id not in topology_ids:
                errors.append(
                    f"{slot_id}: unknown twin topology id {twin_topology_id!r}"
                )
        slot_options[slot_id] = values

    required_swap_slots = {
        "deck",
        "topology",
        "wheel",
        "brake",
        "drive",
        "battery",
        "rider_interface",
        "armor",
        "dock",
    }
    if swap_slot_ids != required_swap_slots:
        errors.append(
            "swap slot ids must exactly match the supported editing contract"
        )

    for source_id, support_ids in swap_slots.get(
        "automatic_support_components", {}
    ).items():
        if source_id not in component_index:
            errors.append(f"swap support source component unknown: {source_id!r}")
        for support_id in support_ids:
            if support_id not in component_index:
                errors.append(f"swap support component unknown: {support_id!r}")

    for topology_id, support_ids in swap_slots.get(
        "topology_support_components", {}
    ).items():
        if topology_id not in topology_ids:
            errors.append(f"swap topology support unknown: {topology_id!r}")
        for support_id in support_ids:
            if support_id not in component_index:
                errors.append(f"swap topology component unknown: {support_id!r}")

    for packaged in swap_slots.get("packaged_foundation_rules", []):
        when = packaged.get("when") or {}
        for slot_id, value in when.items():
            if slot_id not in slot_options:
                errors.append(f"packaged swap rule references unknown slot {slot_id!r}")
            elif value not in slot_options[slot_id]:
                errors.append(
                    f"packaged swap rule has unknown {slot_id} option {value!r}"
                )
        for component_id in packaged.get("use", []):
            if component_id not in component_index:
                errors.append(
                    f"packaged swap rule references unknown component {component_id!r}"
                )

    for ref in refs.get("builds", []):
        if ref.get("architecture_id") not in architecture_ids:
            errors.append(f"{ref.get('id')}: unknown architecture")
        if ref.get("generic_builder_may_promote_authority") is not False:
            errors.append(f"{ref.get('id')}: generic builder authority promotion must be false")

    if rules.get("model_class") != "PLANNING_ESTIMATE":
        errors.append("rules model_class must remain PLANNING_ESTIMATE")

    visual_props = visual_schema.get("properties") or {}
    authority_props = (
        visual_props.get("authority", {}).get("properties", {})
    )
    if (
        authority_props.get("visualization_only", {}).get("const") is not True
        or authority_props.get("procurement_authorized", {}).get("const") is not False
        or authority_props.get("fabrication_authorized", {}).get("const") is not False
        or authority_props.get("powered_operation_authorized", {}).get("const") is not False
    ):
        errors.append(
            "candidate visual-state schema must remain visualization-only and authority-false"
        )
    visual_views = visual_props.get("views", {}).get("prefixItems", [])
    if [row.get("const") for row in visual_views] != ["hero", "top", "side"]:
        errors.append("candidate visual-state views must remain hero/top/side")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "questionnaire_fields": len(field_ids),
        "catalog_components": len(component_index),
        "architectures": len(architecture_ids),
        "swap_slots": len(swap_slot_ids),
        "candidate_visual_views": 3,
        "power_categories_checkout_enabled": False,
        "generic_builder_may_promote_x1_authority": False,
    }


def main() -> None:
    report = validate()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
