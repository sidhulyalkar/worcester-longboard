import copy
import json
from pathlib import Path

from tools.analyze_rev_c_chassis_trade import analyze, validate

ROOT = Path(__file__).resolve().parents[1]


def _snapshot():
    return json.loads(
        (ROOT / "hardware/rev_c_chassis_trade_snapshot_2026-09-30.json").read_text()
    )


def test_snapshot_validates_and_analysis_is_non_authoritative():
    report = analyze(_snapshot())
    assert report["valid"] is True
    assert report["physical_authority"] is False
    assert report["procurement_authority"] is False


def test_warren_is_narrower_than_comp95_but_slightly_heavier():
    report = analyze(_snapshot())
    rows = {x["id"]: x for x in report["candidate_rows"]}
    warren = rows["PRO_WARREN_III_REFERENCE"]
    assert warren["deck_width_delta_mm_vs_comp95"] == -7.0
    assert warren["complete_mass_delta_lb_vs_comp95"] == 1.3
    assert warren["wheelbase_adjustment_span_mm"] == 60.0
    assert warren["deck_construction"] == "Snowboard composite"


def test_agent_unknowns_stay_unknown_instead_of_being_inferred():
    report = analyze(_snapshot())
    rows = {x["id"]: x for x in report["candidate_rows"]}
    agent = rows["AGENT_AIR_REFERENCE"]
    assert agent["complete_unpowered_mass_lb"] is None
    assert agent["wheelbase_range_mm"] is None
    assert agent["brake_compatible_published"] is None
    assert "chassis.complete_unpowered_weight_lb" in agent["unknown_fields"]
    assert "chassis.brake_compatible" in agent["unknown_fields"]


def test_explorer_trade_exposes_tire_only_mass_penalty_without_inventing_hub_delta():
    report = analyze(_snapshot())
    wheel = report["wheel_trade"]
    assert wheel["same_published_diameter_mm"] == 194
    assert wheel["explorer_width_gain_mm_vs_t1"] == 29.0
    assert wheel["explorer_tire_only_added_mass_four_wheels_vs_t1_g"] == 1232.0
    assert wheel["explorer_tire_only_added_mass_four_wheels_vs_t1_lb"] == 2.72
    assert wheel["full_wheel_mass_delta_computable"] is False


def test_missing_candidate_fails_closed():
    snapshot = copy.deepcopy(_snapshot())
    snapshot["candidates"] = [
        x for x in snapshot["candidates"] if x["id"] != "PRO_WARREN_III_REFERENCE"
    ]
    errors = validate(snapshot)
    assert any("PRO_WARREN_III_REFERENCE" in e for e in errors)
