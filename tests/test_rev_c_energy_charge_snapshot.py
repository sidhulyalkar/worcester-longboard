import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _snapshot():
    return json.loads(
        (ROOT / "hardware/rev_c_energy_charge_snapshot_2026-10-01.json").read_text()
    )


def test_energy_snapshot_keeps_battery_and_charger_system_boundary():
    data = _snapshot()
    assert data["schema_version"] == 1
    assert data["facts_only"] is True
    boundary = data["project_boundary"]
    assert "professional" in boundary["traction_pack"]
    assert "approved charger" in boundary["charger"]
    assert "mechanical alignment" in boundary["dock"]
    assert boundary["powered_operation_authorized"] is False


def test_mbs_reference_pack_facts_are_dated_not_procurement_authority():
    refs = {x["id"]: x for x in _snapshot()["commercial_references"]}
    small = refs["MBS_AGENT_540"]
    large = refs["MBS_AGENT_1080"]

    assert small["nominal_energy_wh"] == 540
    assert small["weight_lb"] == 15
    assert small["quick_swap"] is True
    assert small["discharge_ports"] == 1

    assert large["nominal_energy_wh"] == 1089
    assert large["weight_lb"] == 20
    assert large["quick_swap"] is True
    assert large["discharge_ports"] == 2
    assert large["usb_c_pd_w"] == 60


def test_charger_reference_does_not_infer_cross_pack_compatibility():
    refs = {x["id"]: x for x in _snapshot()["charger_references"]}
    normal = refs["MBS_AGENT_CHARGER_530W"]
    fast = refs["EXWAY_SMART_SUPER_CHARGER_1050W"]
    assert normal["published_power_w"] == 530
    assert "exact pack compatibility" in normal["compatibility_rule"]
    assert fast["published_power_w"] == 1050
    assert "do not infer 540 compatibility" in fast["compatibility_rule"]


def test_passive_dock_prohibits_custom_high_voltage_shortcuts():
    dock = _snapshot()["dock_architecture"]
    prohibited = "\n".join(dock["prohibited"])
    assert "exposed traction-voltage contacts" in prohibited
    assert "pogo-pin" in prohibited
    assert "charger/BMS bypass" in prohibited
    assert "parallel connection of unequal packs" in prohibited


def test_daily_and_storage_soc_are_deferred_to_selected_battery_system():
    modes = _snapshot()["operating_modes"]
    assert "if the selected BMS/charger explicitly supports it" in (
        modes["everyday"]["target_soc_policy"]
    )
    assert "manufacturer/builder" in modes["storage"]["target_soc_policy"]
