import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _snapshot():
    return json.loads(
        (
            ROOT / "hardware/rev_c_energy_charge_snapshot_2026-10-01.json"
        ).read_text()
    )


def test_energy_snapshot_keeps_battery_and_charger_system_native():
    data = _snapshot()
    boundary = data["project_boundary"]
    assert boundary["traction_pack"] == (
        "professionally built or qualified integrated system only"
    )
    assert boundary["charger"] == "battery/system-approved charger only"
    assert boundary["hot_swap"].startswith("not allowed")
    assert boundary["powered_operation_authorized"] is False


def test_dock_is_mechanical_alignment_not_a_new_charger():
    dock = _snapshot()["dock_architecture"]
    assert dock["name"] == "passive alignment charge cradle"
    assert "preserve" in dock["electrical_principle"]
    prohibited = set(dock["prohibited"])
    assert "exposed traction-voltage contacts" in prohibited
    assert "charger/BMS bypass" in prohibited
    assert "automatic hot-swap" in prohibited
    assert "parallel connection of unequal packs" in prohibited


def test_energy_classes_preserve_light_and_range_configurations():
    classes = _snapshot()["energy_classes"]
    assert classes["trail"]["target_wh"] == [500, 650]
    assert classes["range"]["target_wh"] == [950, 1150]


def test_commercial_reference_pack_masses_are_explicit():
    refs = {
        item["id"]: item
        for item in _snapshot()["commercial_references"]
    }
    assert refs["MBS_AGENT_540"]["nominal_energy_wh"] == 540
    assert refs["MBS_AGENT_540"]["weight_lb"] == 15
    assert refs["MBS_AGENT_1080"]["nominal_energy_wh"] == 1089
    assert refs["MBS_AGENT_1080"]["weight_lb"] == 20


def test_charge_time_arithmetic_is_never_a_product_claim():
    invariants = _snapshot()["experimental_invariants"]
    assert any("ideal charge-time lower bound" in x for x in invariants)
    assert any("Range claims remain planning envelopes" in x for x in invariants)
