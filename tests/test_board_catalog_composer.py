import json
from pathlib import Path

from configurator.platform_engine import (
    generate_board_design_space,
    load_platform_bundle,
)
from configurator.swap_lab import evaluate_swap

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
