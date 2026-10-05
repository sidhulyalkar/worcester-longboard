import json
from pathlib import Path

from configurator.engine import generate_candidates
from configurator.swap_lab import evaluate_swap, load_slots, seed_selection
from tools.validate_board_builder import validate

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text())


def candidate(result, candidate_id):
    return next(row for row in result["candidates"] if row["id"] == candidate_id)


def test_multivendor_catalog_has_dated_sources_and_no_silent_fx_conversion():
    catalog = load("catalog/board_components.v1.json")
    snapshots = load("catalog/source_snapshots_2026-10-04.json")
    components = {row["id"]: row for row in catalog["components"]}
    source_ids = {row["id"] for row in snapshots["sources"]}

    expected = {
        "DECK-TRAMPA-SHORT-969",
        "DECK-TRAMPA-HS11-969",
        "TRUCK-TRAMPA-VERTIGO-12",
        "TRUCK-TRAMPA-INFINITY-HS11",
        "WHEEL-TRAMPA-ALPHA8",
        "WHEEL-TRAMPA-MEGASTAR9",
        "BRAKE-TRAMPA-HS11",
        "DRIVE-TRAMPA-OBD-DUAL",
        "TRUCK-APEX-AIR",
        "DRIVE-BOARDNAMICS-M1-AT",
    }
    assert expected.issubset(components)

    for component_id in expected:
        row = components[component_id]
        source = row["source"]
        assert source["as_of"] == "2026-10-04"
        assert source["url"].startswith("https://")
        assert source["snapshot_id"] in source_ids
        if source.get("native_price_snapshot"):
            assert row["price"] is None

    assert components["DRIVE-TRAMPA-OBD-DUAL"]["procurement_state"] == "POWER_GATED"
    assert components["DRIVE-BOARDNAMICS-M1-AT"]["procurement_state"] == "POWER_GATED"


def test_multivendor_geometry_registry_preserves_sourced_dimensions():
    geometry = load("catalog/board_geometry.v1.json")
    decks = {row["id"]: row for row in geometry["decks"]}
    topologies = {row["id"]: row for row in geometry["topologies"]}

    assert decks["trampa_short_969"]["length_mm"] == 895
    assert decks["trampa_short_969"]["width_mm"] == 228
    assert decks["trampa_short_969"]["wheelbase_mm"] == 888
    assert decks["trampa_hs11_969"]["length_mm"] == 912
    assert decks["trampa_hs11_969"]["wheelbase_mm"] == 945

    assert topologies["trampa_vertigo_406"]["truck_total_width_mm"] == 406.4
    assert topologies["trampa_vertigo_406"]["axle_diameter_mm"] == 12
    assert topologies["trampa_infinity_hs11_406"]["truck_total_width_mm"] == 406.4
    assert topologies["apex_air_434"]["truck_total_width_mm"] == 434
    assert topologies["apex_air_434"]["steering_family"] == "parallel_kingpin"
    assert topologies["apex_air_434"]["visual_geometry_state"] == "ASSUMED"


def test_validator_accepts_generic_geometry_and_fail_closed_pair_defaults():
    report = validate()
    assert report["valid"] is True, report["errors"]
    assert report["catalog_components"] >= 33
    assert report["catalog_sources"] >= 10
    assert report["geometry_decks"] >= 5
    assert report["geometry_topologies"] >= 6
    assert report["architectures"] >= 9


def test_manual_profile_exposes_reference_compatible_trampa_chassis_families():
    manual = load("configurator/examples/manual_carver_profile.json")
    result = generate_candidates(manual)

    carve = candidate(result, "trampa_short_carve_core")
    hydraulic = candidate(result, "trampa_hydraulic_freeride")

    assert carve["vendor_family"] == "TRAMPA"
    assert carve["readiness"] == "REFERENCE_COMPATIBLE"
    assert carve["checkout_state"] == "SOURCE_LINKS"
    assert hydraulic["readiness"] == "REFERENCE_COMPATIBLE"
    assert hydraulic["checkout_state"] == "SOURCE_LINKS"
    assert any(
        finding["id"] == "trampa_infinity_hs11_brake"
        and finding["state"] == "REFERENCE_COMPATIBLE"
        for finding in hydraulic["compatibility_findings"]
    )


def test_boardnamics_trampa_candidate_keeps_unknown_truck_drive_coexistence():
    trail = load("configurator/examples/trail_rider_profile.json")
    result = generate_candidates(trail)
    mixed = candidate(result, "trampa_boardnamics_coexistence")

    assert mixed["vendor_family"] == "TRAMPA + Boardnamics"
    assert mixed["readiness"] == "MEASURE_FIRST"
    assert mixed["checkout_state"] == "BLOCKED"
    assert any(
        finding["id"].startswith("default:truck:drive:")
        and finding["state"] == "UNKNOWN"
        for finding in mixed["compatibility_findings"]
    )
    assert any(
        finding["id"] == "trampa_alpha8_boardnamics"
        and finding["state"] == "REFERENCE_COMPATIBLE"
        for finding in mixed["compatibility_findings"]
    )


def test_apex_m1at_candidate_preserves_published_drive_fit_but_blocks_system():
    trail = load("configurator/examples/trail_rider_profile.json")
    result = generate_candidates(trail)
    apex = candidate(result, "apex_m1at_rough_study")

    assert apex["readiness"] == "BLOCKED"
    assert apex["checkout_state"] == "BLOCKED"
    assert any(
        finding["id"] == "apex_air_boardnamics"
        and finding["state"] == "REFERENCE_COMPATIBLE"
        for finding in apex["compatibility_findings"]
    )
    assert any(
        finding["source"] == "category_default"
        and finding["state"] == "UNKNOWN"
        for finding in apex["compatibility_findings"]
    )
    assert any("friction-brake" in text for text in apex["blockers"])


def test_nine_inch_trampa_study_matches_rough_terrain_but_hard_blocker_wins():
    trail = load("configurator/examples/trail_rider_profile.json")
    result = generate_candidates(trail)
    obd = candidate(result, "trampa_obd_9in_power_study")

    assert result["requirements"]["wheel_strategy"] == "nine_inch_rollover_study"
    assert obd["readiness"] == "BLOCKED"
    assert any(
        "Nine-inch pneumatic study directly matches" in text
        for text in obd["explanations"]
    )
    assert any("friction-brake" in text for text in obd["blockers"])


def test_trampa_swap_seed_reconstructs_real_vendor_family():
    manual = load("configurator/examples/manual_carver_profile.json")
    generated = generate_candidates(manual)
    baseline = candidate(generated, "trampa_hydraulic_freeride")
    selection = seed_selection(baseline)
    result = evaluate_swap(
        baseline,
        generated["requirements"],
        selection,
        slots=load_slots(),
    )

    assert selection == {
        "deck": "trampa_hs11_969",
        "topology": "trampa_infinity_hs11_406",
        "wheel": "WHEEL-TRAMPA-ALPHA8",
        "brake": "BRAKE-TRAMPA-HS11",
        "drive": None,
        "battery": None,
        "rider_interface": None,
        "armor": None,
        "dock": None,
    }
    assert result["readiness"] == "REFERENCE_COMPATIBLE"
    assert result["checkout_state"] == "SOURCE_LINKS"


def test_cross_vendor_swap_defaults_to_unknown_instead_of_assuming_fit():
    manual = load("configurator/examples/manual_carver_profile.json")
    generated = generate_candidates(manual)
    baseline = candidate(generated, "trampa_hydraulic_freeride")
    selection = seed_selection(baseline)
    selection["topology"] = "apex_air_434"

    result = evaluate_swap(
        baseline,
        generated["requirements"],
        selection,
        slots=load_slots(),
    )

    assert result["readiness"] == "MEASURE_FIRST"
    assert any(
        finding["id"] == "apex_air_hs11_unknown"
        and finding["state"] == "UNKNOWN"
        for finding in result["compatibility_findings"]
    )
    assert any(
        finding["id"].startswith("default:deck:truck:")
        and finding["state"] == "UNKNOWN"
        for finding in result["compatibility_findings"]
    )


def test_lacroix_family_is_normalized_without_promoting_complete_board_facts():
    catalog = load("catalog/board_components.v1.json")
    geometry = load("catalog/board_geometry.v1.json")
    components = {row["id"]: row for row in catalog["components"]}
    decks = {row["id"]: row for row in geometry["decks"]}
    topologies = {row["id"]: row for row in geometry["topologies"]}

    deck = components["DECK-LACROIX-BARREL-REF"]
    truck = components["TRUCK-LACROIX-HYPERLITE"]
    wheel = components["WHEEL-LACROIX-KENDA8-RSII"]
    drive = components["DRIVE-LACROIX-BARREL-BELT"]

    assert deck["procurement_state"] == "STUDY_ONLY"
    assert deck["interfaces"]["standalone_part_source"] is False
    assert truck["interfaces"]["published_hanger_width_mm"] == 381
    assert truck["interfaces"]["steering_family"] == "precision_bushing_spring"
    assert wheel["interfaces"]["published_diameter_mm"] == 203.2
    assert wheel["interfaces"]["visual_geometry_state"] == "ASSUMED"
    assert drive["interfaces"]["drive_type"] == "belt"
    assert drive["procurement_state"] == "POWER_GATED"

    assert decks["lacroix_barrel_876"]["length_mm"] == 876.3
    assert decks["lacroix_barrel_876"]["wheelbase_mm"] == 838.2
    assert topologies["lacroix_hyperlite_381"]["truck_total_width_mm"] == 381
    assert topologies["lacroix_hyperlite_381"]["visual_geometry_state"] == "ASSUMED"


def test_lacroix_native_pairs_are_reference_compatible_but_power_study_stays_blocked():
    manual = load("configurator/examples/manual_carver_profile.json")
    trail = load("configurator/examples/trail_rider_profile.json")

    manual_result = generate_candidates(manual)
    trail_result = generate_candidates(trail)

    carve = candidate(manual_result, "lacroix_barrel_carve_reference")
    power = candidate(trail_result, "lacroix_barrel_belt_study")

    assert carve["vendor_family"] == "Lacroix Boards"
    assert carve["readiness"] == "REFERENCE_COMPATIBLE"
    assert carve["checkout_state"] == "HOLD_MEASURE"
    assert any(
        finding["id"] == "lacroix_barrel_hyperlite"
        and finding["state"] == "REFERENCE_COMPATIBLE"
        for finding in carve["compatibility_findings"]
    )

    assert power["readiness"] == "BLOCKED"
    assert power["checkout_state"] == "BLOCKED"
    assert any(
        finding["id"] == "lacroix_hyperlite_belt"
        and finding["state"] == "REFERENCE_COMPATIBLE"
        for finding in power["compatibility_findings"]
    )
    assert any("friction-brake" in text for text in power["blockers"])
