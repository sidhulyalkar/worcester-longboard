import json
from pathlib import Path

from tools.analyze_rev_c_energy_trade import analyze

ROOT = Path(__file__).resolve().parents[1]


def _snapshot():
    return json.loads(
        (ROOT / "hardware/rev_c_energy_charge_snapshot_2026-10-01.json").read_text()
    )


def test_energy_trade_reports_specific_energy_without_selecting_pack():
    report = analyze(_snapshot())
    assert report["valid"] is True
    assert report["physical_authority"] is False
    assert report["procurement_authority"] is False
    assert report["charger_compatibility_authority"] is False
    assert report["powered_operation_authorized"] is False

    rows = {row["id"]: row for row in report["reference_rows"]}
    assert rows["MBS_AGENT_540"]["specific_energy_wh_per_lb"] == 36.0
    assert rows["MBS_AGENT_1080"]["specific_energy_wh_per_lb"] == 54.45


def test_cold_swap_separates_installed_mass_from_total_inventory_mass():
    comparison = analyze(_snapshot())["architecture_comparison"]
    dual = comparison["two_540_inventory_reference"]
    large = comparison["one_1080_reference"]

    assert dual["nominal_trip_energy_wh"] == 1080
    assert dual["total_battery_inventory_mass_lb"] == 30
    assert dual["installed_battery_mass_lb_during_cold_swap_operation"] == 15
    assert dual["simultaneous_on_board_installation_assumed"] is False
    assert dual["safe_spare_location_required"] is True
    assert dual["rider_body_carry_default"] is False

    assert large["nominal_trip_energy_wh"] == 1089
    assert large["installed_battery_mass_lb"] == 20
    assert comparison["energy_delta_wh_two_540_minus_1080"] == -9
    assert comparison["inventory_mass_delta_lb_two_540_minus_1080"] == 10
    assert comparison["installed_mass_delta_lb_one_540_minus_1080"] == -5


def test_energy_trade_uses_conservative_planning_ranges():
    rows = {row["id"]: row for row in analyze(_snapshot())["reference_rows"]}
    assert rows["MBS_AGENT_540"]["trail_range_miles_20pct_reserve"] == [9.6, 13.5]
    assert rows["MBS_AGENT_1080"]["trail_range_miles_20pct_reserve"] == [19.4, 27.2]
    assert rows["MBS_AGENT_1080"]["mixed_range_miles_20pct_reserve"] == [29.0, 39.6]


def test_invalid_snapshot_fails_closed():
    data = _snapshot()
    data["facts_only"] = False
    report = analyze(data)
    assert report["valid"] is False
    assert "snapshot must remain facts_only" in report["errors"]
