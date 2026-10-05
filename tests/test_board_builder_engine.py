import json
from pathlib import Path

from configurator.engine import (
    derive_requirements,
    generate_candidates,
    load_bundle,
    render_bom_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
TRAIL = json.loads((ROOT / "configurator" / "examples" / "trail_rider_profile.json").read_text())
MANUAL = json.loads((ROOT / "configurator" / "examples" / "manual_carver_profile.json").read_text())


def candidate(result, candidate_id):
    return next(row for row in result["candidates"] if row["id"] == candidate_id)


def test_trail_profile_derives_planning_requirements_without_authority():
    bundle = load_bundle()
    req = derive_requirements(TRAIL, bundle["rules"], bundle["questionnaire"])

    assert req["model_class"] == "PLANNING_ESTIMATE"
    assert req["electric_intent"] == "yes"
    assert req["independent_friction_brake_required"] is True
    assert req["target_range_mi"] >= TRAIL["longest_miles"]
    assert 0.20 <= req["energy_reserve_fraction"] <= 0.35
    assert req["planning_installed_energy_wh"] > 0
    assert req["stance_study"]["min_mm"] < req["stance_study"]["center_mm"] < req["stance_study"]["max_mm"]
    assert req["wheel_strategy"] in {
        "eight_inch_pneumatic_reference",
        "nine_inch_rollover_study",
        "pavement_efficiency_study",
    }


def test_manual_profile_prefers_unpowered_architectures_over_power_complexity():
    result = generate_candidates(MANUAL)

    assert result["winner_selected"] is False
    assert result["authority"] == {
        "generic_builder_may_promote_x1_authority": False,
        "procurement_authorized": False,
        "fabrication_authorized": False,
        "powered_operation_authorized": False,
    }
    fit_bench = candidate(result, "snowdeck_fit_bench")
    electric = candidate(result, "x1_compact_electric_study")
    assert fit_bench["fit_score"] > electric["fit_score"]


def test_electric_coexistence_study_propagates_measure_first_and_power_hold():
    result = generate_candidates(TRAIL)
    electric = candidate(result, "x1_compact_electric_study")

    assert electric["readiness"] == "MEASURE_FIRST"
    assert electric["checkout_state"] == "BLOCKED"
    assert any(
        finding["state"] == "MEASURE_FIRST"
        and finding["id"] == "axle70_v5"
        for finding in electric["compatibility_findings"]
    )
    assert any(row["component_id"] == "DRIVE-G1-DUAL" for row in electric["bom"])
    assert all(value is False for value in electric["authority"].values())


def test_drive_clearance_range_study_fails_closed_without_friction_brake():
    result = generate_candidates(TRAIL)
    range_study = candidate(result, "drive_clearance_range_study")

    assert range_study["readiness"] == "BLOCKED"
    assert range_study["checkout_state"] == "BLOCKED"
    assert any("friction-brake" in blocker for blocker in range_study["blockers"])


def test_brake_first_core_retains_source_links_but_is_not_auto_checkout():
    result = generate_candidates(TRAIL)
    core = candidate(result, "brake_first_trail_core")
    rows = {row["component_id"]: row for row in core["bom"]}

    assert rows["DONOR-COMP95"]["source_url"].startswith("https://www.mbs.com/")
    assert rows["BRAKE-V5"]["source_url"].startswith("https://www.mbs.com/")
    assert rows["DONOR-COMP95"]["procurement_state"] == "HOLD_MEASURE"
    assert core["checkout_state"] == "HOLD_MEASURE"


def test_all_power_components_remain_gated_and_placeholders_lack_fake_links():
    bundle = load_bundle()
    power_categories = {"drive", "motor", "esc", "battery", "charger"}

    for component in bundle["catalog"]["components"]:
        if component["category"] not in power_categories:
            continue
        assert component["procurement_state"] == "POWER_GATED"
        if component["source"]["kind"] == "planning_placeholder":
            assert component["source"]["url"] is None


def test_bom_markdown_carries_hold_language_and_no_authority():
    result = generate_candidates(TRAIL)
    electric = candidate(result, "x1_compact_electric_study")
    text = render_bom_markdown(electric)

    assert "Source links are not checkout authorization" in text
    assert "POWER_GATED" in text
    assert "cannot create fabrication or powered-operation authority" in text


def test_candidate_set_exposes_trade_space_instead_of_winner():
    result = generate_candidates(TRAIL)

    assert len(result["candidates"]) >= 3
    assert result["winner_selected"] is False
    assert any(row["trade_space_frontier"] for row in result["candidates"])
    assert all("fit_score" in row and "readiness" in row for row in result["candidates"])
