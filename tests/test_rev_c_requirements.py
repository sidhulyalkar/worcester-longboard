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


def test_rev_c_mass_goals_are_explicitly_aspirational_against_current_pack_benchmarks():
    data = _requirements()
    ride = data["ride_targets"]
    assert ride["trail_configuration_mass_goal_lb"] == 35
    assert ride["range_configuration_mass_goal_lb"] == 45
    assert ride["mass_goals_status"] == "ASPIRATIONAL_UNTIL_COMPONENT_MASS_BUDGET_CLOSES"

    refs = {x["id"]: x for x in data["benchmark_only"]}
    mass = refs["MBS_AGENT_BATTERY_MASS_REFERENCE"]["known"]
    assert mass["battery_540_weight_lb"] == 15
    assert mass["battery_1080_weight_lb"] == 20
    assert mass["comp95_unpowered_weight_lb"] == 14.6


def test_pro_warren_iii_is_a_first_class_rev_c_chassis_candidate():
    data = _requirements()
    candidates = {x["id"]: x for x in data["candidate_architectures"]}
    warren = candidates["PRO_WARREN_III_REFERENCE"]
    known = warren["known"]
    assert known["deck_length_mm"] == 980
    assert known["deck_max_width_mm"] == 244
    assert known["axle_to_axle_mm_range"] == [910, 970]
    assert known["unpowered_mass_lb"] == 15.9
    assert known["deck_construction"] == "snowboard composite"
    assert known["v5_brake_listed_compatible"] is True
    assert known["availability_snapshot"] == "COMING_SOON_WAITLIST_2026-09-30"


def test_agent_deck_reference_uses_published_284mm_max_deck_width():
    data = _requirements()
    candidates = {x["id"]: x for x in data["candidate_architectures"]}
    assert candidates["AGENT_AIR_REFERENCE"]["known"]["deck_max_width_mm"] == 284


def test_issue_28_ride_compliance_is_unpowered_and_lightweight_first():
    data = _requirements()
    program = data["ride_compliance_program"]
    assert program["issue"] == 28
    assert program["phase"] == "POST_SELECTED_CHASSIS_UNPOWERED"
    assert program["powered_operation_authorized"] is False
    assert program["tuning_order"][:3] == [
        "pneumatic_tire_pressure",
        "truck_elastomer_position",
        "wheelbase_where_adjustable",
    ]
    assert program["tuning_order"][-1] == (
        "independent_suspension_only_after_measured_failure"
    )


def test_issue_28_does_not_turn_compliance_into_accessory_shopping():
    boundary = _requirements()["ride_compliance_program"]["procurement_boundary"]
    assert boundary["new_shock_blocks"] == (
        "DEFER_UNTIL_STOCK_POSITION_DEFICIENCY"
    )
    assert boundary["explorer_wheels"] == (
        "DEFER_UNTIL_200X50_COMPLIANCE_OR_TRACTION_DEFICIENCY"
    )
    assert boundary["nine_inch_wheels"] == (
        "DEFER_UNTIL_MEASURED_CLEARANCE_DEFICIENCY"
    )
    assert boundary["independent_suspension"] == (
        "REOPEN_ARCHITECTURE_ONLY_AFTER_LIGHTWEIGHT_STACK_FAILURE"
    )


def test_energy_architecture_selects_installed_energy_by_mission():
    energy = _requirements()["energy_architecture"]
    strategy = energy["mission_energy_strategy"]
    assert "smallest qualified pack class" in strategy["installed_energy_policy"]
    assert "permanently installed energy" in strategy["trip_energy_policy"]
    assert "powered-off" in strategy["cold_swap_role"]
    assert energy["planning_reserve_fraction"] >= 0.20


def test_issue_30_charge_dock_is_passive_and_cannot_authorize_live_charging():
    energy = _requirements()["energy_architecture"]
    dock = energy["charge_dock"]
    assert dock["issue"] == 30
    assert dock["architecture"] == "PASSIVE_MECHANICAL_ALIGNMENT_CRADLE"
    assert dock["live_battery_test_authorized"] is False
    assert dock["electrical_charge_authorized"] is False
    assert dock["powered_operation_authorized"] is False
    charging = energy["charging"]
    assert "explicitly approved" in charging["compatibility_rule"]
    assert charging["universal_daily_soc_assumption"] == (
        "NONE_FOLLOW_SELECTED_BATTERY_SYSTEM"
    )


def test_issue_33_shasta_program_is_research_only_and_dog_free_initially():
    program = _requirements()["control_architecture"]["shasta_companion_program"]
    assert program["issue"] == 33
    assert program["phase"] == "RESEARCH_ONLY_UNTIL_FUTURE_POWERED_AUTHORITY"
    assert program["powered_operation_authorized"] is False
    assert program["dog_accompanied_operation_authorized"] is False
    assert "board-mounted leash attachment prohibited" in program["hard_boundaries"]
    assert (
        "no dog in software, bench, or initial rider-only powered qualification"
        in program["hard_boundaries"]
    )
    assert "current slew is not physical jerk authority" in program["hard_boundaries"]


def test_issue_33_provisional_envelope_matches_control_research_target():
    env = _requirements()["control_architecture"]["shasta_companion_program"][
        "provisional_envelope"
    ]
    assert env == {
        "speed_cap_mps": 2.7,
        "accel_max_mps2": 0.45,
        "regen_decel_max_mps2": 0.8,
        "phase_current_max_a": 18.0,
        "drive_current_slew_max_a_per_s": 20.0,
        "brake_current_slew_max_a_per_s": 30.0,
        "fault_release_current_slew_a_per_s": 60.0,
    }


def test_issue_35_public_use_program_keeps_worcester_as_terrain_reference_only():
    program = _requirements()["public_use_program"]
    assert program["issue"] == 35
    assert program["status"] == "INFORMATIONAL_DESIGN_CONSTRAINT_ONLY"
    assert program["worcester_park_role"] == (
        "TERRAIN_REFERENCE_NOT_ASSUMED_TEST_VENUE"
    )
    assert program["powered_operation_authorized"] is False
    assert program["public_operation_authorized"] is False


def test_issue_35_does_not_treat_shasta_mode_as_vehicle_classification():
    program = _requirements()["public_use_program"]
    assert "do not assume Shasta" in program["classification_rule"]
    assert program["public_road_status"] == (
        "NOT_ESTABLISHED_FOR_HIGH_POWER_TRAIL_CONFIGURATION"
    )
    assert program["architecture_branches"] == [
        "TRAIL_PRIVATE_OR_EXPRESSLY_AUTHORIZED_USE",
        "PUBLIC_ROAD_ORIENTED_DERIVATIVE_STUDY",
    ]
