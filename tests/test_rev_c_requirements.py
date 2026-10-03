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


def test_issue_37_trail_armor_is_inert_first_and_non_authoritative():
    program = _requirements()["trail_armor_program"]
    assert program["issue"] == 37
    assert program["phase"] == "POST_TOPOLOGY_AND_PACKAGING_GEOMETRY_INERT_FIRST"
    assert program["impact_path"] == [
        "terrain",
        "replaceable_wear_shoe_or_vendor_skid",
        "carrier_or_vendor_guard_structure",
        "qualified_structural_mount",
        "protected_component",
    ]
    assert program["procurement_authority"] is False
    assert program["powered_operation_authorized"] is False


def test_issue_37_keeps_battery_shell_connectors_and_material_choice_out_of_shortcuts():
    boundaries = _requirements()["trail_armor_program"]["hard_boundaries"]
    assert "live battery excluded from initial armor qualification" in boundaries
    assert "battery shell is not primary trail armor structure" in boundaries
    assert "electrical connectors are not structural armor members" in boundaries
    assert (
        "material and thickness remain unfrozen until topology/contact/load path are known"
        in boundaries
    )
    assert "inert geometry qualification is not impact-energy authority" in boundaries


def test_issue_39_environmental_program_is_inert_and_pre_power_freeze():
    program = _requirements()["environmental_durability_program"]
    assert program["issue"] == 39
    assert program["phase"] == "POST_DUMMY_PACK_PRE_FINAL_POWER_FREEZE"
    assert program["initial_scope"] == (
        "INERT_PACKAGING_DRAINAGE_AND_SERVICE_RECOVERY_ONLY"
    )
    assert program["required_exposure_types"] == [
        "dry_grit",
        "splash",
        "mud_surrogate",
    ]
    assert program["must_close_before"] == "power_architecture_frozen"
    assert program["powered_operation_authorized"] is False


def test_issue_39_forbids_ip_shortcuts_and_live_ingress_discovery():
    boundaries = _requirements()["environmental_durability_program"][
        "hard_boundaries"
    ]
    assert "no live traction battery in initial environmental trials" in boundaries
    assert "no energized traction voltage in initial environmental trials" in boundaries
    assert "no pressure washer or immersion as leak-discovery methods" in boundaries
    assert (
        "no IP rating waterproof claim or corrosion-life claim from project surrogate tests"
        in boundaries
    )
    assert (
        "passing inert environmental evidence does not authorize energized wet operation"
        in boundaries
    )


def test_issue_41_lifecycle_health_starts_after_rolling_chassis_and_persists():
    program = _requirements()["lifecycle_health_program"]
    assert program["issue"] == 41
    assert program["phase"] == (
        "START_AFTER_ROLLING_CHASSIS_AND_CONTINUE_FOR_VEHICLE_LIFE"
    )
    assert program["upstream_anchor"] == (
        "fingerprinted x1_rolling_chassis_physical authority"
    )
    assert program["health_states"] == [
        "READY_FOR_ALLOWED_ACTIVITY",
        "INSPECTION_REQUIRED",
        "SERVICE_REQUIRED",
        "STOP_USE",
    ]
    assert program["powered_operation_authorized"] is False
    assert program["public_operation_authorized"] is False
    assert program["dog_accompanied_operation_authorized"] is False


def test_issue_41_ready_state_never_becomes_operation_authority():
    program = _requirements()["lifecycle_health_program"]
    boundaries = program["hard_boundaries"]
    assert "health state never authorizes powered operation" in boundaries
    assert "health state never authorizes public operation" in boundaries
    assert "health state never authorizes dog-accompanied operation" in boundaries
    assert "health state never overrides blocked build authority" in boundaries
    assert (
        "future powered commissioning must require a fresh READY_FOR_ALLOWED_ACTIVITY state on the current configuration in addition to all other authorities"
        in program["policies"]
    )


def test_issue_41_does_not_invent_service_intervals_or_erase_history():
    policies = _requirements()["lifecycle_health_program"]["policies"]
    assert "append-only event history rather than rewriting prior inspections" in policies
    assert "component replacement creates explicit configuration lineage" in policies
    assert (
        "no fixed mileage hour or calendar service interval without an accepted source"
        in policies
    )
    assert (
        "open STOP findings require explicit inspection/service closure and a fresh preflight"
        in policies
    )


def test_issue_43_powertrain_envelope_is_sourced_and_pre_power_freeze():
    program = _requirements()["powertrain_envelope_program"]
    assert program["issue"] == 43
    assert program["phase"] == (
        "POST_TOPOLOGY_AND_DUMMY_PACK_PRE_FINAL_POWER_FREEZE"
    )
    assert program["required_scenario_classes"] == [
        "flat_cruise",
        "grade_climb",
        "low_speed_accel",
    ]
    assert program["must_close_before"] == "power_architecture_frozen"
    assert program["physical_authority"] is False
    assert program["procurement_authority"] is False
    assert program["controller_configuration_authority"] is False
    assert program["battery_configuration_authority"] is False
    assert program["thermal_qualification"] is False
    assert program["powered_operation_authorized"] is False


def test_issue_43_keeps_phase_battery_current_and_thermal_boundaries_explicit():
    boundaries = _requirements()["powertrain_envelope_program"]["hard_boundaries"]
    assert "motor phase current and battery current remain distinct quantities" in boundaries
    assert "no-load geometric speed is not a ride-speed claim" in boundaries
    assert "first-order current and power analysis is not thermal qualification" in boundaries
    assert (
        "all candidate electrical and motor limits require explicit source references"
        in boundaries
    )
    assert (
        "Issue #19 selected topology must match the candidate propulsion topology"
        in boundaries
    )


def test_issue_43_g1_ratio_reference_does_not_select_a_ratio_for_x1():
    reference = _requirements()["powertrain_envelope_program"][
        "official_g1_reference_ratio_study"
    ]
    assert reference["wheel_gear_teeth"] == 64
    assert reference["official_agent_motor_gear_references_teeth"] == [13, 15, 17]
    assert reference["stock_agent_motor_gear_teeth"] == 15
    assert reference["selection_for_x1"] == "NONE"


def test_issue_45_powered_commissioning_is_staged_and_post_freeze():
    program = _requirements()["powered_commissioning_program"]
    assert program["issue"] == 45
    assert program["phase"] == "POST_FINAL_POWER_ARCHITECTURE_STAGED_COMMISSIONING"
    assert [stage["id"] for stage in program["stages"]] == [
        "BENCH_READINESS",
        "SECURED_UNLOADED_SPIN",
        "RESTRAINED_LOADED_BENCH",
        "RIDER_FREE_CONTROLLED_GROUND",
        "RIDER_ONLY_VERY_LOW_SPEED",
    ]
    assert [stage["index"] for stage in program["stages"]] == [0, 1, 2, 3, 4]


def test_issue_45_ground_and_rider_stages_are_distinct():
    stages = {
        stage["id"]: stage
        for stage in _requirements()["powered_commissioning_program"]["stages"]
    }
    assert stages["SECURED_UNLOADED_SPIN"]["ground_travel"] is False
    assert stages["RESTRAINED_LOADED_BENCH"]["ground_travel"] is False
    assert stages["RIDER_FREE_CONTROLLED_GROUND"] == {
        "index": 3,
        "id": "RIDER_FREE_CONTROLLED_GROUND",
        "ground_travel": True,
        "rider": False,
        "venue_required": True,
    }
    assert stages["RIDER_ONLY_VERY_LOW_SPEED"] == {
        "index": 4,
        "id": "RIDER_ONLY_VERY_LOW_SPEED",
        "ground_travel": True,
        "rider": True,
        "venue_required": True,
    }


def test_issue_45_never_turns_commissioning_into_normal_operation_authority():
    program = _requirements()["powered_commissioning_program"]
    boundaries = program["hard_boundaries"]
    assert "Stage 4 completion does not authorize general powered operation" in boundaries
    assert "Stage 4 completion does not authorize public operation" in boundaries
    assert "Stage 4 completion does not authorize dog-accompanied operation" in boundaries
    assert program["general_powered_operation_authorized"] is False
    assert program["public_operation_authorized"] is False
    assert program["dog_accompanied_operation_authorized"] is False


def test_issue_45_requires_health_and_venue_lineage():
    boundaries = _requirements()["powered_commissioning_program"]["hard_boundaries"]
    assert (
        "every stage starts from a READY lifecycle-health state for the same board/configuration"
        in boundaries
    )
    assert (
        "every energized stage closes with a new READY post-stage lifecycle-health state"
        in boundaries
    )
    assert (
        "ground stages require fingerprinted qualified powered-test venue evidence"
        in boundaries
    )


def test_issues_47_49_telemetry_program_is_evidence_only():
    program = _requirements()["telemetry_evidence_program"]
    assert program["issues"] == [47, 49]
    assert program["phase"] == "REQUIRED_FOR_COMMISSIONING_STAGE_1_THROUGH_4"
    assert program["raw_storage"] == "rider/private/"
    assert program["powered_operation_authorized"] is False
    assert program["public_operation_authorized"] is False
    assert program["dog_accompanied_operation_authorized"] is False


def test_telemetry_program_seals_raw_files_and_never_controls_propulsion():
    policies = _requirements()["telemetry_evidence_program"]["policies"]
    assert "logging is never a real-time control dependency" in policies
    assert "raw files are sealed by SHA-256 before validation" in policies
    assert (
        "Stage 1 through Stage 4 commissioning measurements must reference fingerprinted telemetry replay evidence"
        in policies
    )


def test_issue_59_binds_issue4_to_fingerprinted_sensor_selection():
    program = _requirements()["fit_pilot_hardware_provenance_program"]
    assert program["issue"] == 59
    assert program["phase"] == (
        "POST_CART_A_CHECKOUT_RECEIVING_PRE_ISSUE4_SESSION"
    )
    assert program["allowed_required_sensor_sources"] == [
        "RECEIVED_ORDER",
        "OWNED_EXACT_UNUSED",
    ]
    assert program["required_roles"]["load_cell"] == [
        "PILOT_ACTIVE_CANDIDATE",
        "SPARE_UNTOUCHED",
    ]
    assert program["required_roles"]["hx711"] == [
        "PILOT_ACTIVE_CANDIDATE",
        "SPARE_UNTOUCHED",
    ]
    assert program["physical_qualification_authority"] is False
    assert program["four_zone_duplication_authorized"] is False
    assert program["powered_operation_authorized"] is False


def test_issue_59_requires_new_session_when_active_evidence_hardware_changes():
    boundaries = _requirements()["fit_pilot_hardware_provenance_program"][
        "hard_boundaries"
    ]
    assert (
        "one untouched spare load cell and HX711 must remain preserved"
        in boundaries
    )
    assert (
        "sensor substitutes or equivalents cannot satisfy Issue #4 evidence hardware"
        in boundaries
    )
    assert (
        "changing active sensor hardware requires a new selection authority and new Issue #4 session"
        in boundaries
    )
    assert (
        "Issue #4 qualification must preserve the exact Issue #59 selection fingerprint"
        in boundaries
    )
