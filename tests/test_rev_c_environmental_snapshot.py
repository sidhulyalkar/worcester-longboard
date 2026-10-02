import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _snapshot():
    return json.loads(
        (
            ROOT
            / "hardware/rev_c_environmental_durability_snapshot_2026-10-01.json"
        ).read_text()
    )


def test_environmental_snapshot_makes_no_ip_or_waterproof_claim():
    data = _snapshot()
    assert data["authority"] == "REFERENCE_ONLY"
    boundary = data["project_boundaries"]
    assert boundary["ip_rating_claimed"] is False
    assert boundary["waterproof_claimed"] is False
    assert boundary["corrosion_life_claimed"] is False


def test_initial_environmental_trials_remain_inert_and_unpowered():
    boundary = _snapshot()["project_boundaries"]
    assert boundary["live_traction_battery_in_initial_trials"] is False
    assert boundary["energized_high_voltage_in_initial_trials"] is False
    assert boundary["charger_connected_in_initial_trials"] is False
    assert boundary["powered_vehicle_in_initial_trials"] is False


def test_pressure_washing_and_immersion_are_not_assumed_safe():
    boundary = _snapshot()["project_boundaries"]
    assert boundary["pressure_washing_assumed_safe"] is False
    assert boundary["immersion_assumed_safe"] is False


def test_environmental_ladder_ends_with_future_energized_validation():
    layers = sorted(
        _snapshot()["environmental_layers"],
        key=lambda item: item["order"],
    )
    assert [item["order"] for item in layers] == list(range(1, 9))
    assert layers[0]["mechanism"] == "interface_inventory"
    assert layers[-1]["mechanism"] == "future_energized_validation"


def test_reference_methods_do_not_claim_standard_compliance():
    refs = {item["id"]: item for item in _snapshot()["standards_references"]}
    assert refs["ISO_20653_2023"]["compliance_claim"] is False
    assert refs["ASTM_B117_26"]["compliance_claim"] is False
    assert "do not reliably predict" in refs["ASTM_B117_26"]["caveat"]
