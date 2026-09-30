import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _requirements():
    return json.loads((ROOT / "hardware/rev_c_requirements.json").read_text())


def test_rev_c_keeps_independent_braking_and_professional_battery():
    data = _requirements()
    hard = data["hard_requirements"]
    assert hard["independent_mechanical_stopping"] is True
    assert hard["independent_friction_or_hydraulic_stopping"] is True
    assert hard["rear_v5_reference_preferred_if_compatible"] is True
    assert hard["professional_traction_battery_only"] is True
    assert hard["no_unqualified_safety_critical_spacers_or_brake_adapters"] is True


def test_rev_c_prioritizes_low_speed_and_modular_energy():
    data = _requirements()
    assert data["ride_targets"]["priority_speed_envelope_mph"] == [0, 15]
    energy = data["energy_architecture"]
    assert energy["trail_pack_nominal_wh_target"] == [500, 650]
    assert energy["range_pack_nominal_wh_target"] == [950, 1150]
    assert energy["planning_reserve_fraction"] >= 0.20


def test_shasta_mode_fails_conservative():
    data = _requirements()
    hard = data["hard_requirements"]
    assert hard["dog_mode_initial_speed_cap_mps"] <= 2.7
    assert hard["dog_mode_low_jerk_required"] is True
    carve = data["control_architecture"]["carve_assist"]
    assert carve["default"] == "OFF_UNTIL_LOW_SPEED_QUALIFIED"
    assert carve["must_disable_on_sensor_fault"] is True


def test_rev_c_does_not_authorize_expensive_hardware():
    gate = _requirements()["rev_c_purchase_gate"]
    assert gate["fit_pilot_parts"] == "ORDERABLE"
    assert gate["chassis_and_brake"] == "HOLD"
    assert gate["wheel_upgrades"] == "HOLD"
    assert gate["drive"] == "HOLD"
    assert gate["battery_and_esc"] == "HOLD"


def test_all_live_topology_branches_preserve_a_brake_question():
    branches = {x["id"]: x for x in _requirements()["topology_branches"]}
    assert branches["REAR_V5_FRONT_2WD"]["status"] == "LIVE"
    assert branches["REAR_V5_REAR_2WD_SHARED"]["status"] == "PHYSICAL_PROOF_REQUIRED"
    assert branches["REAR_2WD_FRONT_VENDOR_HYDRAULIC"]["status"] == "LIVE_REFERENCE_TO_STUDY"
    assert branches["ALTERNATE_REAR_DRIVE_PRESERVING_V5"]["status"] == "LIVE_FALLBACK"


def test_rev_c_vendor_front_brake_reference_is_not_a_custom_adapter():
    data = _requirements()
    refs = {x["id"]: x for x in data["benchmark_only"]}
    trampa = refs["TRAMPA_INFINITY_MAGURA_FRONT_BRAKE"]
    assert trampa["known"]["mounting_position"] == "front"
    assert trampa["known"]["complete_vendor_architecture"] is True
    assert any("not permission to adapt" in x for x in trampa["lessons"])
