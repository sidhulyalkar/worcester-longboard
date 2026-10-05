import json
from pathlib import Path

from configurator.engine import generate_candidates
from configurator.swap_lab import (
    evaluate_swap,
    load_slots,
    seed_selection,
)

ROOT = Path(__file__).resolve().parents[1]


def load_profile(name):
    return json.loads((ROOT / "configurator" / "examples" / name).read_text())


def candidate(result, candidate_id):
    return next(row for row in result["candidates"] if row["id"] == candidate_id)


def test_swap_seed_reconstructs_compact_electric_baseline():
    generated = generate_candidates(load_profile("trail_rider_profile.json"))
    baseline = candidate(generated, "x1_compact_electric_study")
    selection = seed_selection(baseline)
    result = evaluate_swap(
        baseline,
        generated["requirements"],
        selection,
        slots=load_slots(),
    )

    assert selection["deck"] == "comp95"
    assert selection["topology"] == "brake_hanger_70mm_topology_study"
    assert selection["wheel"] == "TIRE-T1-8-REF"
    assert selection["brake"] == "BRAKE-V5"
    assert selection["drive"] == "DRIVE-G1-DUAL"
    assert result["readiness"] == "MEASURE_FIRST"
    assert result["checkout_state"] == "BLOCKED"
    assert result["changes"] == []
    assert result["cost_delta_vs_baseline"] == {
        "known_min_usd": 0.0,
        "known_max_usd": 0.0,
    }


def test_swap_420_drive_reference_with_v5_fails_closed():
    generated = generate_candidates(load_profile("trail_rider_profile.json"))
    baseline = candidate(generated, "x1_compact_electric_study")
    selection = json.loads(
        (ROOT / "configurator" / "examples" / "swap_incompatible_study.json").read_text()
    )
    result = evaluate_swap(baseline, generated["requirements"], selection)

    assert result["readiness"] == "INCOMPATIBLE"
    assert result["checkout_state"] == "BLOCKED"
    assert any(
        finding["id"] == "matrix420_v5"
        and finding["state"] == "INCOMPATIBLE"
        for finding in result["compatibility_findings"]
    )
    assert any(
        finding["id"] == "matrix420_g1"
        and finding["state"] == "REFERENCE_COMPATIBLE"
        for finding in result["compatibility_findings"]
    )
    assert any(
        finding["id"] == "rockstarII_t2_9"
        and finding["state"] == "MEASURE_FIRST"
        for finding in result["compatibility_findings"]
    )


def test_removing_required_friction_brake_blocks_custom_design():
    generated = generate_candidates(load_profile("trail_rider_profile.json"))
    baseline = candidate(generated, "x1_compact_electric_study")
    selection = seed_selection(baseline)
    selection["brake"] = None

    result = evaluate_swap(baseline, generated["requirements"], selection)

    assert result["readiness"] == "BLOCKED"
    assert any("requires an independent friction brake" in text for text in result["blockers"])


def test_selected_battery_class_must_cover_derived_mission_energy():
    profile = load_profile("trail_rider_profile.json")
    profile["longest_miles"] = 35
    generated = generate_candidates(profile)
    baseline = candidate(generated, "x1_compact_electric_study")
    selection = seed_selection(baseline)
    selection["battery"] = "BATTERY-TRAIL-CLASS"

    result = evaluate_swap(baseline, generated["requirements"], selection)

    assert generated["requirements"]["planning_installed_energy_wh"] > 650
    assert result["readiness"] == "BLOCKED"
    assert any("selected battery-class ceiling" in text for text in result["blockers"])


def test_swap_lab_never_promotes_authority():
    generated = generate_candidates(load_profile("manual_carver_profile.json"))
    baseline = candidate(generated, "snowdeck_fit_bench")
    selection = seed_selection(baseline)
    result = evaluate_swap(baseline, generated["requirements"], selection)

    assert result["scope"] == "non_authoritative_component_swap_study"
    assert result["authority"] == {
        "procurement_authorized": False,
        "fabrication_authorized": False,
        "powered_operation_authorized": False,
        "generic_builder_may_promote_x1_authority": False,
    }
