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
    geometry = load("catalog/board_geometry.v1.json")
    source_snapshots = load("catalog/source_snapshots_2026-10-04.json")
    catalog_health = load("catalog/catalog_health.v1.json")
    architectures = load("configurator/architectures.v1.json")
    compatibility = load("configurator/compatibility_rules.v1.json")
    swap_slots = load("configurator/swap_slots.v1.json")
    composer = load("configurator/composer.v1.json")
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
        if source.get("kind") in {"vendor", "retailer", "vendor_reference"}:
            if not source.get("url") or not source.get("as_of"):
                errors.append(f"{cid}: sourced component requires url + as_of")
        if source.get("native_price_snapshot") and row.get("price") is not None:
            errors.append(
                f"{cid}: native-currency source snapshot may not be silently stored as USD price"
            )
        if row.get("category") in {"drive", "motor", "esc", "battery", "charger"}:
            if row.get("procurement_state") != "POWER_GATED":
                errors.append(f"{cid}: live-power category must remain POWER_GATED in seed catalog")
        if row.get("procurement_state") == "BUY_CANDIDATE":
            warnings.append(f"{cid}: BUY_CANDIDATE exists; verify generic purchase policy intentionally allows it")

    source_rows = source_snapshots.get("sources", [])
    source_ids = [row.get("id") for row in source_rows]
    if len(source_ids) != len(set(source_ids)):
        errors.append("source snapshot ids must be unique")
    source_index = {row["id"]: row for row in source_rows if row.get("id")}

    for row in components:
        source = row.get("source") or {}
        snapshot_id = source.get("snapshot_id")
        if snapshot_id and snapshot_id not in source_index:
            errors.append(f"{row['id']}: unknown source snapshot {snapshot_id!r}")
        if snapshot_id:
            snapshot = source_index[snapshot_id]
            if source.get("url") != snapshot.get("url"):
                errors.append(
                    f"{row['id']}: component source URL differs from dated snapshot"
                )

    health_rows = catalog_health.get("component_health", [])
    health_ids = [row.get("component_id") for row in health_rows]
    if len(health_ids) != len(set(health_ids)):
        errors.append("catalog health component ids must be unique")
    if set(health_ids) != set(component_index):
        errors.append("catalog health must contain exactly one row for every catalog component")
    health_summary = catalog_health.get("summary") or {}
    if catalog_health.get("valid") is not True:
        errors.append("canonical catalog health report must be integrity-valid")
    if catalog_health.get("integrity_errors"):
        errors.append("canonical catalog health report may not carry integrity errors")
    if health_summary.get("catalog_components") != len(component_index):
        errors.append("catalog health component count does not match catalog")
    if health_summary.get("source_linked_components") != sum(
        1 for row in components if (row.get("source") or {}).get("url")
    ):
        errors.append("catalog health sourced-component count does not match catalog")
    if health_summary.get("missing_provenance") != 0:
        errors.append("canonical catalog health may not contain missing provenance")
    health_authority = catalog_health.get("authority") or {}
    if (
        health_authority.get("stock_currently_verified") is not False
        or health_authority.get("procurement_authorized") is not False
        or health_authority.get("fabrication_authorized") is not False
        or health_authority.get("powered_operation_authorized") is not False
        or health_authority.get("source_health_may_promote_x1_authority") is not False
    ):
        errors.append("catalog health must remain non-authoritative")

    deck_rows = geometry.get("decks", [])
    topology_rows = geometry.get("topologies", [])
    deck_ids_list = [row.get("id") for row in deck_rows]
    topology_ids_list = [row.get("id") for row in topology_rows]
    if len(deck_ids_list) != len(set(deck_ids_list)):
        errors.append("geometry deck ids must be unique")
    if len(topology_ids_list) != len(set(topology_ids_list)):
        errors.append("geometry topology ids must be unique")

    deck_ids = set(deck_ids_list)
    topology_ids = set(topology_ids_list)
    for deck in deck_rows:
        for key in ("length_mm", "width_mm", "shape_family", "evidence_state"):
            if deck.get(key) is None:
                errors.append(f"{deck.get('id')}: missing deck geometry {key}")
    for topology in topology_rows:
        for key in (
            "truck_total_width_mm",
            "wheel_center_lateral_mm",
            "steering_family",
            "evidence_state",
        ):
            if topology.get(key) is None:
                errors.append(f"{topology.get('id')}: missing topology geometry {key}")

    twin_deck_ids = {
        row["id"]
        for row in twin.get("design_studies", {}).get("deck_candidates", [])
    }
    twin_topology_ids = {
        row["id"]
        for row in twin.get("design_studies", {}).get("topology_branches", [])
    }
    if not twin_deck_ids.issubset(deck_ids):
        errors.append("generic geometry registry must contain every X1 twin deck")
    if not twin_topology_ids.issubset(topology_ids):
        errors.append("generic geometry registry must contain every X1 twin topology")

    architecture_ids: set[str] = set()
    required_traits = {"range", "carve", "stability", "durability", "portability", "cost", "low_maintenance", "rough_terrain"}
    twin_presets = {
        row["id"]
        for row in twin.get("design_studies", {}).get("configuration_lab", {}).get("presets", [])
    }
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
        if not architecture.get("vendor_family"):
            errors.append(f"{aid}: vendor_family is required")
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

    valid_compat_states = {
        "COMPATIBLE",
        "REFERENCE_COMPATIBLE",
        "MEASURE_FIRST",
        "UNKNOWN",
        "INCOMPATIBLE",
    }
    for rule in compatibility.get("pair_rules", []):
        for side in ("a", "b"):
            if rule.get(side) not in component_index:
                errors.append(f"{rule.get('id')}: compatibility rule references unknown {side}")
        if rule.get("state") not in valid_compat_states:
            errors.append(f"{rule.get('id')}: invalid compatibility state")

    default_pairs: set[tuple[str, str]] = set()
    conservative_defaults = {"MEASURE_FIRST", "UNKNOWN", "INCOMPATIBLE"}
    known_categories = {row["category"] for row in components}
    for fallback in compatibility.get("category_pair_defaults", []):
        categories = fallback.get("categories") or []
        if len(categories) != 2 or categories[0] == categories[1]:
            errors.append("category_pair_defaults require two distinct categories")
            continue
        pair = tuple(sorted(categories))
        if pair in default_pairs:
            errors.append(f"duplicate category-pair default {pair}")
        default_pairs.add(pair)
        if any(category not in known_categories for category in categories):
            errors.append(f"unknown category in pair default {categories}")
        if fallback.get("state") not in conservative_defaults:
            errors.append(
                f"category-pair default {categories} must fail closed, not {fallback.get('state')!r}"
            )

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

    wheel_options = slot_options.get("wheel", set())
    for wheel_id, support_ids in swap_slots.get(
        "wheel_support_components", {}
    ).items():
        if wheel_id not in wheel_options:
            errors.append(f"swap wheel support unknown: {wheel_id!r}")
        for support_id in support_ids:
            if support_id not in component_index:
                errors.append(f"swap wheel support component unknown: {support_id!r}")

    for topology_id, support_ids in swap_slots.get(
        "topology_support_components", {}
    ).items():
        if topology_id not in topology_ids:
            errors.append(f"swap topology support unknown: {topology_id!r}")
        for support_id in support_ids:
            if support_id not in component_index:
                errors.append(f"swap topology component unknown: {support_id!r}")

    if composer.get("scope") != "non_authoritative_catalog_synthesis":
        errors.append("composer scope must remain non-authoritative catalog synthesis")
    if not isinstance(composer.get("enabled"), bool):
        errors.append("composer enabled must be boolean")

    max_raw = composer.get("max_raw_combinations")
    if not isinstance(max_raw, int) or not 1 <= max_raw <= 100000:
        errors.append("composer max_raw_combinations must be integer 1..100000")
    max_unknown = composer.get("max_unknown_findings")
    if not isinstance(max_unknown, int) or max_unknown < 0:
        errors.append("composer max_unknown_findings must be integer >= 0")
    max_candidates = composer.get("max_synthesized_candidates")
    if not isinstance(max_candidates, int) or not 1 <= max_candidates <= 50:
        errors.append("composer max_synthesized_candidates must be integer 1..50")
    max_per_family = composer.get("max_per_vendor_family")
    if not isinstance(max_per_family, int) or not 1 <= max_per_family <= 20:
        errors.append("composer max_per_vendor_family must be integer 1..20")

    allowed_readiness = set(composer.get("allowed_readiness", []))
    safe_synth_readiness = {"REFERENCE_COMPATIBLE", "MEASURE_FIRST"}
    if not allowed_readiness or not allowed_readiness.issubset(safe_synth_readiness):
        errors.append(
            "composer allowed_readiness may contain only REFERENCE_COMPATIBLE or MEASURE_FIRST"
        )

    composer_slots = composer.get("slots") or {}
    expected_composer_slots = {"deck", "topology", "wheel", "brake", "drive"}
    if set(composer_slots) != expected_composer_slots:
        errors.append("composer slots must exactly match the supported synthesis core")
    for slot_id, values in composer_slots.items():
        known = slot_options.get(slot_id, set())
        if not isinstance(values, list) or not values:
            errors.append(f"composer {slot_id} must contain at least one option")
            continue
        if len(values) != len(set(values)):
            errors.append(f"composer {slot_id} contains duplicate options")
        for value in values:
            if value not in known:
                errors.append(
                    f"composer {slot_id} references unknown swap option {value!r}"
                )

    manual_policy = composer.get("manual_policy") or {}
    for slot_id in ("drive", "battery"):
        value = manual_policy.get(slot_id)
        if value not in slot_options.get(slot_id, set()):
            errors.append(
                f"composer manual_policy {slot_id} references unknown option {value!r}"
            )

    electric_policy = composer.get("electric_policy") or {}
    if electric_policy.get("require_drive") is not True:
        errors.append("composer electric policy must require a drive")
    battery_options = slot_options.get("battery", set())
    battery_classes = electric_policy.get("battery_classes") or []
    if not battery_classes:
        errors.append("composer electric policy requires at least one battery class")
    for value in battery_classes:
        if value not in battery_options:
            errors.append(
                f"composer electric battery class references unknown option {value!r}"
            )

    fixed_selection = composer.get("fixed_selection") or {}
    expected_fixed = {"rider_interface", "armor", "dock"}
    if set(fixed_selection) != expected_fixed:
        errors.append("composer fixed_selection must exactly cover rider_interface/armor/dock")
    for slot_id, value in fixed_selection.items():
        if value not in slot_options.get(slot_id, set()):
            errors.append(
                f"composer fixed selection {slot_id} references unknown option {value!r}"
            )

    trait_model = composer.get("trait_model") or {}
    if trait_model.get("model_class") != "PLANNING_HEURISTIC":
        errors.append("composer trait model must remain PLANNING_HEURISTIC")
    for key in (
        "deck_length_bounds_mm",
        "truck_width_bounds_mm",
        "wheel_diameter_bounds_mm",
    ):
        bounds = trait_model.get(key)
        if (
            not isinstance(bounds, list)
            or len(bounds) != 2
            or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in bounds)
            or bounds[1] <= bounds[0]
        ):
            errors.append(f"composer trait model {key} must be ascending numeric [min,max]")
    if not isinstance(trait_model.get("known_cost_reference_usd"), (int, float)):
        errors.append("composer known_cost_reference_usd must be numeric")

    composer_authority = composer.get("authority") or {}
    required_false = {
        "procurement_authorized",
        "fabrication_authorized",
        "powered_operation_authorized",
        "generic_builder_may_promote_x1_authority",
    }
    if set(composer_authority) != required_false or any(
        composer_authority.get(key) is not False for key in required_false
    ):
        errors.append("composer authority contract must contain exactly four false flags")

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
        "catalog_sources": len(source_index),
        "catalog_health_as_of": catalog_health.get("as_of"),
        "catalog_source_fresh": health_summary.get("source_fresh"),
        "catalog_refresh_due": health_summary.get("refresh_due"),
        "catalog_stale": health_summary.get("stale"),
        "geometry_decks": len(deck_ids),
        "geometry_topologies": len(topology_ids),
        "architectures": len(architecture_ids),
        "swap_slots": len(swap_slot_ids),
        "composer_enabled": composer.get("enabled") is True,
        "composer_max_candidates": composer.get("max_synthesized_candidates"),
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
