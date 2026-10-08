import json
from pathlib import Path

from configurator.platform_engine import (
    generate_board_design_space,
    load_platform_bundle,
)
from configurator.swap_lab import evaluate_profile_swap, evaluate_swap

ROOT = Path(__file__).resolve().parents[1]


def profile(name: str):
    return json.loads(
        (ROOT / "configurator" / "examples" / name).read_text()
    )


def bom_signature(candidate):
    return tuple(
        sorted(row["component_id"] for row in candidate["bom"])
    )


def test_platform_engine_preserves_curated_candidates_and_adds_bounded_synthesis():
    bundle = load_platform_bundle()
    result = generate_board_design_space(
        profile("trail_rider_profile.json"),
        bundle=bundle,
    )

    summary = result["composition_summary"]
    assert summary["curated_count"] == len(
        bundle["architectures"]["architectures"]
    )
    assert 0 < summary["synthesized_count"] <= bundle["composer"][
        "max_synthesized_candidates"
    ]
    assert summary["total_count"] == len(result["candidates"])
    assert summary["composer_enabled"] is True

    curated = [row for row in result["candidates"] if row["origin"] == "CURATED"]
    synthesized = [
        row for row in result["candidates"]
        if row["origin"] == "SYNTHESIZED"
    ]
    assert len(curated) == summary["curated_count"]
    assert len(synthesized) == summary["synthesized_count"]

    assert {
        row["architecture_id"] for row in curated
    } == {
        row["id"] for row in bundle["architectures"]["architectures"]
    }


def test_synthesized_candidates_fail_closed_and_never_promote_authority():
    bundle = load_platform_bundle()
    result = generate_board_design_space(
        profile("trail_rider_profile.json"),
        bundle=bundle,
    )
    synthesized = [
        row for row in result["candidates"]
        if row["origin"] == "SYNTHESIZED"
    ]

    assert synthesized
    for candidate in synthesized:
        assert candidate["readiness"] in {
            "REFERENCE_COMPATIBLE",
            "MEASURE_FIRST",
        }
        assert candidate["blockers"] == []
        assert candidate["checkout_state"] in {
            "BLOCKED",
            "HOLD_MEASURE",
            "SOURCE_LINKS",
        }
        assert candidate["authority"] == {
            "procurement_authorized": False,
            "fabrication_authorized": False,
            "powered_operation_authorized": False,
        }
        assert candidate["composition"]["engine"] == "catalog_composer_v1"
        assert candidate["composition"]["unknown_count"] <= bundle["composer"][
            "max_unknown_findings"
        ]
        assert candidate["swap_defaults"]["drive"] is not None
        assert candidate["swap_defaults"]["battery"] is not None


def test_manual_composer_does_not_add_propulsion_or_battery():
    bundle = load_platform_bundle()
    result = generate_board_design_space(
        profile("manual_carver_profile.json"),
        bundle=bundle,
    )
    synthesized = [
        row for row in result["candidates"]
        if row["origin"] == "SYNTHESIZED"
    ]

    assert synthesized
    for candidate in synthesized:
        assert candidate["swap_defaults"]["drive"] is None
        assert candidate["swap_defaults"]["battery"] is None
        ids = {row["component_id"] for row in candidate["bom"]}
        assert not any(item.startswith("DRIVE-") for item in ids)
        assert not any(item.startswith("BATTERY-") for item in ids)


def test_synthesis_is_deterministic_and_deduplicated_against_curated_boms():
    bundle = load_platform_bundle()
    rider = profile("trail_rider_profile.json")
    left = generate_board_design_space(rider, bundle=bundle)
    right = generate_board_design_space(rider, bundle=bundle)

    assert [row["id"] for row in left["candidates"]] == [
        row["id"] for row in right["candidates"]
    ]

    curated_signatures = {
        bom_signature(row)
        for row in left["candidates"]
        if row["origin"] == "CURATED"
    }
    synthesized = [
        row for row in left["candidates"]
        if row["origin"] == "SYNTHESIZED"
    ]
    synth_signatures = [bom_signature(row) for row in synthesized]

    assert len(synth_signatures) == len(set(synth_signatures))
    assert not curated_signatures.intersection(synth_signatures)


def test_synthesized_candidate_round_trips_through_swap_lab_exactly():
    bundle = load_platform_bundle()
    result = generate_board_design_space(
        profile("trail_rider_profile.json"),
        bundle=bundle,
    )
    candidate = next(
        row for row in result["candidates"]
        if row["origin"] == "SYNTHESIZED"
    )

    evaluated = evaluate_swap(
        candidate,
        result["requirements"],
        candidate["swap_defaults"],
        bundle=bundle,
        slots=bundle["swapSlots"],
    )

    assert evaluated["changes"] == []
    assert evaluated["readiness"] in {
        "REFERENCE_COMPATIBLE",
        "MEASURE_FIRST",
    }
    assert evaluated["blockers"] == []
    assert tuple(
        sorted(row["component_id"] for row in evaluated["bom"])
    ) == bom_signature(candidate)


def test_platform_authority_stays_false_with_composer_enabled():
    result = generate_board_design_space(
        profile("trail_rider_profile.json")
    )
    assert result["authority"] == {
        "generic_builder_may_promote_x1_authority": False,
        "procurement_authorized": False,
        "fabrication_authorized": False,
        "powered_operation_authorized": False,
    }


def test_profile_swap_api_can_reopen_synthesized_candidate():
    rider = profile("trail_rider_profile.json")
    generated = generate_board_design_space(rider)
    candidate = next(
        row for row in generated["candidates"]
        if row["origin"] == "SYNTHESIZED"
    )

    result = evaluate_profile_swap(
        rider,
        candidate["id"],
        candidate["swap_defaults"],
    )

    assert result["changes"] == []
    assert result["blockers"] == []
    assert result["readiness"] in {
        "REFERENCE_COMPATIBLE",
        "MEASURE_FIRST",
    }


# Shared adversarial fixtures exercise exact mechanical identities, not only counts.
def test_composer_critical_interface_fixtures():
    fixtures = json.loads((ROOT / "configurator/examples/composer_compatibility_cases.v1.json").read_text())["cases"]
    bundle = load_platform_bundle()
    profiles = {
        name: generate_board_design_space(profile(name), bundle=bundle)
        for name in sorted({row["profile"] for row in fixtures})
    }
    for case in fixtures:
        selection = {key: case.get(key) for key in (
            "deck", "topology", "wheel", "brake", "drive", "battery"
        )}
        selection.update({"rider_interface": None, "armor": None, "dock": None})
        source = profiles[case["profile"]]
        result = evaluate_swap(
            source["candidates"][0], source["requirements"], selection,
            bundle=bundle, slots=bundle["swapSlots"],
        )
        assert result["readiness"] in case["expected_readiness"], case["id"]
        assert result["friction_brake_path_state"] == case["expected_brake_path"], case["id"]
        assert case["expected_rule"] in {f["id"] for f in result["compatibility_findings"]}, case["id"]
        assert all(value is False for value in result["authority"].values()), case["id"]
        assert result["compatibility_interface_ids"], case["id"]
        if case["drive"]:
            assert result["checkout_state"] == "BLOCKED", case["id"]
            assert all(row["procurement_state"] == "POWER_GATED" for row in result["bom"]
                if row["category"] in {"drive", "motor", "esc", "battery", "charger"}), case["id"]
        if case["id"] == "mbs_donor_400_g1":
            assert "DONOR-COMP95" in {r["component_id"] for r in result["bom"]}
            assert "TRUCK-M3-400" not in {r["component_id"] for r in result["bom"]}
            assert "TRUCK-M3-400" in result["compatibility_interface_ids"]
        if case["id"] == "missing_friction_brake":
            assert any("independent friction brake" in reason for reason in result["blockers"])


def test_missing_brake_evidence_degrades_readiness_without_rule_fallback():
    import copy
    bundle = load_platform_bundle()
    result = generate_board_design_space(profile("manual_carver_profile.json"), bundle=bundle)
    selection = {
        "deck": "trampa_hs11_969", "topology": "trampa_infinity_hs11_406",
        "wheel": "WHEEL-TRAMPA-ALPHA8", "brake": "BRAKE-TRAMPA-HS11",
        "drive": None, "battery": None, "rider_interface": None, "armor": None, "dock": None,
    }
    degraded = copy.deepcopy(bundle)
    degraded["compatibility"]["pair_rules"] = [r for r in degraded["compatibility"]["pair_rules"]
        if r["id"] != "trampa_infinity_hs11_brake"]
    degraded["compatibility"]["category_pair_defaults"] = [r for r in degraded["compatibility"]["category_pair_defaults"]
        if set(r["categories"]) != {"truck", "brake"}]
    evaluated = evaluate_swap(result["candidates"][0], result["requirements"], selection,
        bundle=degraded, slots=degraded["swapSlots"])
    assert evaluated["friction_brake_path_state"] == "MEASURE_FIRST"
    assert evaluated["readiness"] == "MEASURE_FIRST"
    assert any("Unresolved truck/brake" in reason for reason in evaluated["unknowns"])
    assert all(value is False for value in evaluated["authority"].values())


def test_constrained_composer_produces_distinct_vendor_studies_without_authority():
    import copy
    from configurator.composer import compose_candidates
    bundle = load_platform_bundle()
    selected = (
        ("manual_carver_profile.json", "comp95", "brake_first_400mm", "TIRE-T1-8-REF", "BRAKE-V5", "DRIVE-G1-DUAL"),
        ("manual_carver_profile.json", "trampa_hs11_969", "trampa_infinity_hs11_406", "WHEEL-TRAMPA-ALPHA8", "BRAKE-TRAMPA-HS11", "DRIVE-TRAMPA-OBD-DUAL"),
        ("trail_rider_profile.json", "trampa_hs11_969", "trampa_infinity_hs11_406", "WHEEL-TRAMPA-MEGASTAR9", "BRAKE-TRAMPA-HS11", "DRIVE-BOARDNAMICS-M1-AT"),
    )
    families = []
    for name, deck, topology, wheel, brake, drive in selected:
        reduced = copy.deepcopy(bundle)
        reduced["composer"]["slots"] = {
            "deck": [deck], "topology": [topology], "wheel": [wheel],
            "brake": [brake], "drive": [drive],
        }
        generated = generate_board_design_space(profile(name), bundle=bundle)
        candidates = compose_candidates(generated["profile"], generated["requirements"], reduced)
        assert candidates, (name, deck, topology, wheel)
        candidate = candidates[0]
        assert candidate["origin"] == "SYNTHESIZED"
        assert candidate["composition"]["physical_interface_ids"]
        assert candidate["compatibility_findings"]
        assert candidate["blockers"] == []
        assert all(value is False for value in candidate["authority"].values())
        families.append(candidate["vendor_family"])
    assert any("Cross-vendor" in family for family in families)
    assert len(set(families)) >= 2
