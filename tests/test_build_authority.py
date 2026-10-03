import copy
import hashlib
import json
from pathlib import Path

import pytest

from tools.evaluate_build_authority import evaluate, _validate_plan

ROOT = Path(__file__).resolve().parents[1]


def _plan():
    return json.loads((ROOT / "hardware/build_authority.json").read_text())


def _procurement():
    return json.loads((ROOT / "hardware/procurement_manifest.json").read_text())


def _stamp(doc):
    payload = json.dumps(doc, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    stamped = dict(doc)
    stamped["authority_fingerprint_sha256"] = hashlib.sha256(payload).hexdigest()
    return stamped


def _fit_pilot_evidence():
    return _stamp({
        "authority": "x1_one_zone_pilot",
        "scope": "unpowered_fit_rig_only",
        "qualified_for_four_zone_duplication": True,
        "powered_operation_authorized": False,
        "hardware_provenance": {
            "selection_authority_fingerprint_sha256": "1" * 64,
            "selection_record_sha256": "2" * 64,
        },
        "mass_reference_provenance": {
            "authority_fingerprint_sha256": "3" * 64,
            "record_sha256": "4" * 64,
        },
    })


def _platform_repeatability_evidence():
    return _stamp({
        "authority": "x1_fit_platform_repeatability",
        "scope": "unpowered_fit_platform_repeatability_only",
        "qualified": True,
        "position_repeatability_qualified": True,
        "one_zone_authority_fingerprint_sha256": "5" * 64,
        "powered_operation_authorized": False,
    })


def _all_physical_evidence():
    chassis = _stamp({
        "authority": "x1_rolling_chassis_physical",
        "qualified": True,
        "powered_operation_authorized": False,
    })
    return [
        _fit_pilot_evidence(),
        _platform_repeatability_evidence(),
        _stamp({
            "authority": "x1_rev_c_chassis_release",
            "schema_version": 1,
            "qualified": True,
            "deck_envelope_comparison_completed": True,
            "selected_deck_candidate_id": "comp95_class",
            "selected_chassis_family": "COMP95_BASELINE",
            "selected_wheel_family": "MBS_RSII_200X50",
            "selected_brake_architecture": "MBS_V5_REAR",
            "selected_topology_for_measurement": "REAR_V5_REAR_2WD_SHARED",
            "range_pack_inert_envelope_plausible": True,
            "no_unqualified_safety_critical_adapter": True,
            "powered_operation_authorized": False,
        }),
        _stamp({"authority": "x1_fit_session", "schema_version": 2, "rev_b_gate": {"ready_for_rev_b_fit_cad": True}}),
        _stamp({"authority": "x1_mechanical_brake_interface", "qualified": True, "brake_interface_verified": True, "powered_operation_authorized": False}),
        chassis,
        _stamp({"authority": "x1_brake_drive_topology", "schema_version": 1, "qualified": True, "selected_topology": "same_rear_axle_v5_plus_drive", "powered_operation_authorized": False}),
        _stamp({"authority": "x1_rev_b_template", "qualified": True}),
        _stamp({"authority": "x1_power_packaging_candidate", "schema_version": 1, "qualified": True, "powered_operation_authorized": False}),
        _stamp({"authority": "x1_dummy_pack_mount", "schema_version": 1, "qualified": True, "powered_operation_authorized": False}),
        _stamp({
            "authority": "x1_environmental_inert_candidate",
            "schema_version": 1,
            "qualified": True,
            "environmental_inert_candidate_qualified": True,
            "electrical_wet_operation_qualified": False,
            "powered_operation_authorized": False,
        }),
        _stamp({
            "authority": "x1_powertrain_envelope_candidate",
            "schema_version": 1,
            "qualified": True,
            "all_declared_scenarios_pass": True,
            "thermal_qualification": False,
            "procurement_authority": False,
            "controller_configuration_authority": False,
            "battery_configuration_authority": False,
            "powered_operation_authorized": False,
        }),
        _stamp({"authority": "x1_power_architecture", "qualified": True}),
        _stamp({
            "authority": "x1_lifecycle_health_state",
            "schema_version": 1,
            "valid": True,
            "health_state": "READY_FOR_ALLOWED_ACTIVITY",
            "ready_for_allowed_activity": True,
            "rolling_chassis_fingerprint_sha256": chassis[
                "authority_fingerprint_sha256"
            ],
            "powered_operation_authorized": False,
            "public_operation_authorized": False,
            "dog_accompanied_operation_authorized": False,
        }),
    ]


def _commissioning_evidence():
    venue = _stamp({
        "schema_version": 1,
        "authority": "x1_powered_test_venue_evidence",
        "qualified": True,
        "errors": [],
        "venue_id": "PRIVATE-A",
        "venue_name": "Synthetic private venue",
        "venue_permission_qualified": True,
        "vehicle_operation_legality_verified_recorded": False,
        "vehicle_powered_operation_authority": False,
        "public_operation_authority": False,
        "dog_accompanied_operation_authority": False,
        "interpretation_boundary": "synthetic",
    })
    stages = []
    for index, stage_id in enumerate((
        "BENCH_READINESS",
        "SECURED_UNLOADED_SPIN",
        "RESTRAINED_LOADED_BENCH",
        "RIDER_FREE_CONTROLLED_GROUND",
        "RIDER_ONLY_VERY_LOW_SPEED",
    )):
        stages.append(_stamp({
            "schema_version": 1,
            "authority": "x1_powered_commissioning_stage",
            "qualified": True,
            "stage_index": index,
            "stage_id": stage_id,
            "commissioning_stage_completed": True,
            "telemetry_replay_fingerprint_sha256": (
                None if index == 0 else hashlib.sha256(
                    f"replay-{index}".encode()
                ).hexdigest()
            ),
            "telemetry_session_fingerprint_sha256": (
                None if index == 0 else hashlib.sha256(
                    f"session-{index}".encode()
                ).hexdigest()
            ),
            "general_powered_operation_authorized": False,
            "public_operation_authorized": False,
            "dog_accompanied_operation_authorized": False,
        }))
    return [venue, *stages]


def test_energized_commissioning_gate_rejects_missing_telemetry_lineage():
    evidence = [*_all_physical_evidence(), *_commissioning_evidence()]
    for item in evidence:
        if (
            item.get("authority") == "x1_powered_commissioning_stage"
            and item.get("stage_index") == 2
        ):
            item.pop("telemetry_replay_fingerprint_sha256", None)
            item.pop("telemetry_session_fingerprint_sha256", None)
            item.pop("authority_fingerprint_sha256", None)
            item.update(_stamp(item))

    report = evaluate(_plan(), _procurement(), evidence)
    state = report["gates"]["commissioning_stage_2_qualified"]
    assert state["satisfied"] is False
    assert state["evidence_matched"] is False


def test_public_repo_defaults_are_conservative():
    report = evaluate(_plan(), _procurement(), [])
    assert report["capabilities"]["order_fit_pilot_parts"]["allowed"] is True
    assert report["capabilities"]["order_measurement_chassis_parts"]["allowed"] is False
    assert report["capabilities"]["duplicate_four_fit_zones"]["allowed"] is False
    assert report["capabilities"]["fabricate_unpowered_chassis"]["allowed"] is False
    assert report["capabilities"]["qualify_brake_drive_topology"]["allowed"] is False
    assert report["capabilities"]["define_power_packaging_candidate"]["allowed"] is False
    assert report["capabilities"]["build_inert_dummy_pack_fixture"]["allowed"] is False
    assert report["capabilities"]["qualify_dummy_pack_mount"]["allowed"] is False
    assert report["capabilities"]["order_power_hardware"]["allowed"] is False
    assert report["capabilities"]["powered_operation"]["allowed"] is False
    assert report["capabilities"]["dog_accompanied_operation"]["allowed"] is False
    assert report["capabilities"]["public_operation"]["allowed"] is False
    assert report["capabilities"]["qualify_inert_trail_armor"]["allowed"] is False
    assert report["capabilities"]["qualify_environmental_inert_candidate"]["allowed"] is False
    assert report["capabilities"]["establish_lifecycle_health_history"]["allowed"] is False
    assert report["capabilities"]["qualify_powertrain_envelope"]["allowed"] is False
    assert report["capabilities"]["prepare_powered_bench_readiness"]["allowed"] is False
    assert report["capabilities"]["conduct_secured_unloaded_spin"]["allowed"] is False
    assert report["capabilities"]["conduct_restrained_loaded_bench"]["allowed"] is False
    assert report["capabilities"]["conduct_rider_free_controlled_ground"]["allowed"] is False
    assert report["capabilities"]["conduct_rider_only_very_low_speed_commissioning"]["allowed"] is False
    assert report["gates"]["lifecycle_health_ready"]["satisfied"] is False


def test_fit_pilot_gate_requires_issue_59_hardware_provenance():
    legacy = _stamp({
        "authority": "x1_one_zone_pilot",
        "scope": "unpowered_fit_rig_only",
        "qualified_for_four_zone_duplication": True,
    })
    report = evaluate(_plan(), _procurement(), [legacy])
    assert report["gates"]["fit_pilot_qualified"]["satisfied"] is False

    report = evaluate(_plan(), _procurement(), [_fit_pilot_evidence()])
    assert report["gates"]["fit_pilot_qualified"]["satisfied"] is True
    assert report["gates"]["fit_platform_repeatability_qualified"]["satisfied"] is False
    assert report["capabilities"]["qualify_fit_platform_repeatability"]["allowed"] is True
    assert report["capabilities"]["duplicate_four_fit_zones"]["allowed"] is False


def test_issue63_platform_repeatability_unlocks_four_zone_duplication():
    fit = _fit_pilot_evidence()
    platform = _platform_repeatability_evidence()

    report = evaluate(_plan(), _procurement(), [fit])
    assert report["gates"]["fit_pilot_qualified"]["satisfied"] is True
    assert report["gates"]["fit_platform_repeatability_qualified"]["satisfied"] is False
    assert report["capabilities"]["duplicate_four_fit_zones"]["allowed"] is False

    report = evaluate(_plan(), _procurement(), [fit, platform])
    assert report["gates"]["fit_platform_repeatability_qualified"]["satisfied"] is True
    assert report["capabilities"]["duplicate_four_fit_zones"]["allowed"] is True


def test_issue63_does_not_block_rev_c_chassis_release():
    fit = _fit_pilot_evidence()
    release = _stamp({
        "authority": "x1_rev_c_chassis_release",
        "schema_version": 1,
        "qualified": True,
        "deck_envelope_comparison_completed": True,
        "selected_deck_candidate_id": "comp95_class",
        "selected_chassis_family": "COMP95_BASELINE",
        "selected_wheel_family": "MBS_RSII_200X50",
        "selected_brake_architecture": "MBS_V5_REAR",
        "selected_topology_for_measurement": "REAR_V5_REAR_2WD_SHARED",
        "range_pack_inert_envelope_plausible": True,
        "no_unqualified_safety_critical_adapter": True,
        "powered_operation_authorized": False,
    })

    report = evaluate(_plan(), _procurement(), [fit, release])
    assert report["gates"]["fit_platform_repeatability_qualified"]["satisfied"] is False
    assert report["gates"]["rev_c_chassis_release_qualified"]["satisfied"] is True
    assert report["capabilities"]["order_measurement_chassis_parts"]["allowed"] is True


def test_fit_pilot_gate_requires_issue_61_mass_reference_provenance():
    hardware_only = _stamp({
        "authority": "x1_one_zone_pilot",
        "scope": "unpowered_fit_rig_only",
        "qualified_for_four_zone_duplication": True,
        "powered_operation_authorized": False,
        "hardware_provenance": {
            "selection_authority_fingerprint_sha256": "1" * 64,
            "selection_record_sha256": "2" * 64,
        },
    })
    report = evaluate(_plan(), _procurement(), [hardware_only])
    assert report["gates"]["fit_pilot_qualified"]["satisfied"] is False

    report = evaluate(_plan(), _procurement(), [_fit_pilot_evidence()])
    assert report["gates"]["fit_pilot_qualified"]["satisfied"] is True


def test_rev_c_blocks_measurement_chassis_procurement_until_release_conditions_close():
    report = evaluate(_plan(), _procurement(), [])
    items = report["procurement_items"]
    assert report["procurement_stage_authorized"]["MEASURE_FIRST"] is False
    assert items["DONOR-COMP95"]["orderable"] is False
    assert items["BRAKE-V5"]["orderable"] is False
    assert any("rev_c_chassis_release_qualified" in x for x in items["DONOR-COMP95"]["blockers"])
    assert items["TRUCK-M3-400"]["orderable"] is False
    assert items["HUB-RSII"]["orderable"] is False
    assert items["TIRE-T2-9"]["orderable"] is False
    assert items["TUBE-9"]["orderable"] is False
    assert items["AXLE-M3-70"]["orderable"] is False
    assert any("deferred until" in blocker for blocker in items["AXLE-M3-70"]["blockers"])


def test_rev_c_release_requires_fit_pilot_and_then_opens_preferred_measurement_items():
    fit = _fit_pilot_evidence()
    release = _stamp({
        "authority": "x1_rev_c_chassis_release",
        "schema_version": 1,
        "qualified": True,
        "deck_envelope_comparison_completed": True,
        "selected_deck_candidate_id": "comp95_class",
        "selected_chassis_family": "COMP95_BASELINE",
        "selected_wheel_family": "MBS_RSII_200X50",
        "selected_brake_architecture": "MBS_V5_REAR",
        "selected_topology_for_measurement": "REAR_V5_REAR_2WD_SHARED",
        "range_pack_inert_envelope_plausible": True,
        "no_unqualified_safety_critical_adapter": True,
        "powered_operation_authorized": False,
    })

    report = evaluate(_plan(), _procurement(), [release])
    assert report["gates"]["rev_c_chassis_release_qualified"]["satisfied"] is False
    assert report["procurement_items"]["DONOR-COMP95"]["orderable"] is False

    report = evaluate(_plan(), _procurement(), [fit, release])
    assert report["gates"]["rev_c_chassis_release_qualified"]["satisfied"] is True
    assert report["procurement_items"]["DONOR-COMP95"]["orderable"] is True
    assert report["procurement_items"]["BRAKE-V5"]["orderable"] is True
    assert report["procurement_items"]["TRUCK-M3-400"]["orderable"] is False
    assert report["procurement_items"]["HUB-RSII"]["orderable"] is False
    assert report["capabilities"]["order_measurement_chassis_parts"]["allowed"] is True
    assert report["capabilities"]["order_power_hardware"]["allowed"] is False
    assert report["capabilities"]["powered_operation"]["allowed"] is False


def test_release_for_warren_does_not_unlock_comp95_or_v5_items():
    fit = _fit_pilot_evidence()
    release = _stamp({
        "authority": "x1_rev_c_chassis_release",
        "schema_version": 1,
        "qualified": True,
        "deck_envelope_comparison_completed": True,
        "selected_deck_candidate_id": "pro_warren_iii_class",
        "selected_chassis_family": "PRO_WARREN_III_REFERENCE",
        "selected_wheel_family": "MBS_RSII_200X50",
        "selected_brake_architecture": "MBS_V5_REAR",
        "selected_topology_for_measurement": "REAR_V5_REAR_2WD_SHARED",
        "range_pack_inert_envelope_plausible": True,
        "no_unqualified_safety_critical_adapter": True,
        "powered_operation_authorized": False,
    })
    report = evaluate(_plan(), _procurement(), [fit, release])
    assert report["gates"]["rev_c_chassis_release_qualified"]["satisfied"] is True
    assert report["procurement_items"]["DONOR-COMP95"]["orderable"] is False
    assert report["procurement_items"]["BRAKE-V5"]["orderable"] is False
    assert any(
        "selected_chassis_family='PRO_WARREN_III_REFERENCE'" in blocker
        for blocker in report["procurement_items"]["DONOR-COMP95"]["blockers"]
    )
    assert report["capabilities"]["order_measurement_chassis_parts"]["allowed"] is False


def test_front_hydraulic_release_does_not_unlock_v5_brake():
    fit = _fit_pilot_evidence()
    release = _stamp({
        "authority": "x1_rev_c_chassis_release",
        "schema_version": 1,
        "qualified": True,
        "deck_envelope_comparison_completed": True,
        "selected_deck_candidate_id": "comp95_class",
        "selected_chassis_family": "COMP95_BASELINE",
        "selected_wheel_family": "MBS_RSII_200X50",
        "selected_brake_architecture": "VENDOR_FRONT_HYDRAULIC",
        "selected_topology_for_measurement": "REAR_2WD_FRONT_VENDOR_HYDRAULIC",
        "range_pack_inert_envelope_plausible": True,
        "no_unqualified_safety_critical_adapter": True,
        "powered_operation_authorized": False,
    })
    report = evaluate(_plan(), _procurement(), [fit, release])
    assert report["gates"]["rev_c_chassis_release_qualified"]["satisfied"] is True
    assert report["procurement_items"]["DONOR-COMP95"]["orderable"] is True
    assert report["procurement_items"]["BRAKE-V5"]["orderable"] is False
    assert any(
        "selected_brake_architecture='VENDOR_FRONT_HYDRAULIC'" in blocker
        for blocker in report["procurement_items"]["BRAKE-V5"]["blockers"]
    )
    assert report["capabilities"]["order_power_hardware"]["allowed"] is False
    assert report["capabilities"]["powered_operation"]["allowed"] is False


def test_fallback_requires_strategy_change_after_rev_c_release():
    procurement = copy.deepcopy(_procurement())
    procurement["rules"]["instantiated_chassis_item_id"] = None
    fit, release = _all_physical_evidence()[:2]
    report = evaluate(_plan(), procurement, [fit, release])
    assert report["procurement_items"]["TRUCK-M3-400"]["orderable"] is True
    assert report["procurement_items"]["HUB-RSII"]["orderable"] is True


def test_downstream_evidence_cannot_skip_upstream_gate():
    evidence = [_stamp({"authority": "x1_rolling_chassis_physical", "qualified": True, "powered_operation_authorized": False})]
    report = evaluate(_plan(), _procurement(), evidence)
    state = report["gates"]["rolling_chassis_physical_qualified"]
    assert state["evidence_matched"] is True
    assert state["satisfied"] is False
    assert any("brake_interface_qualified" in x for x in state["blockers"])


def test_topology_evidence_cannot_skip_brake_or_chassis():
    topology = _stamp({
        "authority": "x1_brake_drive_topology",
        "schema_version": 1,
        "qualified": True,
        "selected_topology": "same_rear_axle_v5_plus_drive",
        "powered_operation_authorized": False,
    })
    report = evaluate(_plan(), _procurement(), [topology])
    state = report["gates"]["brake_drive_topology_qualified"]
    assert state["evidence_matched"] is True
    assert state["satisfied"] is False
    assert any("brake_interface_qualified" in x for x in state["blockers"])
    assert any("rolling_chassis_physical_qualified" in x for x in state["blockers"])


def test_lifecycle_health_tracking_begins_only_after_rolling_chassis_qualification():
    evidence = _all_physical_evidence()
    report = evaluate(_plan(), _procurement(), evidence)
    health = report["capabilities"]["establish_lifecycle_health_history"]
    assert health["allowed"] is True

    without_chassis = [
        doc for doc in evidence
        if doc.get("authority") != "x1_rolling_chassis_physical"
    ]
    report = evaluate(_plan(), _procurement(), without_chassis)
    health = report["capabilities"]["establish_lifecycle_health_history"]
    assert health["allowed"] is False
    assert any(
        "rolling_chassis_physical_qualified" in blocker
        for blocker in health["blockers"]
    )


def test_inert_trail_armor_requires_topology_and_packaging_geometry():
    evidence = _all_physical_evidence()
    report = evaluate(_plan(), _procurement(), evidence)
    assert report["capabilities"]["qualify_inert_trail_armor"]["allowed"] is True

    without_packaging = [
        doc for doc in evidence
        if doc.get("authority") != "x1_power_packaging_candidate"
    ]
    report = evaluate(_plan(), _procurement(), without_packaging)
    armor = report["capabilities"]["qualify_inert_trail_armor"]
    assert armor["allowed"] is False
    assert any(
        "power_packaging_candidate_defined" in blocker
        for blocker in armor["blockers"]
    )

    without_topology = [
        doc for doc in evidence
        if doc.get("authority") != "x1_brake_drive_topology"
    ]
    report = evaluate(_plan(), _procurement(), without_topology)
    armor = report["capabilities"]["qualify_inert_trail_armor"]
    assert armor["allowed"] is False
    assert any(
        "brake_drive_topology_qualified" in blocker
        for blocker in armor["blockers"]
    )


def test_packaging_candidate_cannot_skip_topology_or_revb():
    candidate = _stamp({
        "authority": "x1_power_packaging_candidate",
        "schema_version": 1,
        "qualified": True,
        "powered_operation_authorized": False,
    })
    report = evaluate(_plan(), _procurement(), [candidate])
    state = report["gates"]["power_packaging_candidate_defined"]
    assert state["evidence_matched"] is True
    assert state["satisfied"] is False
    assert any("brake_drive_topology_qualified" in x for x in state["blockers"])
    assert any("rev_b_template_qualified" in x for x in state["blockers"])


def test_dummy_pack_evidence_cannot_skip_candidate():
    evidence = [x for x in _all_physical_evidence() if x.get("authority") not in {"x1_power_packaging_candidate", "x1_power_architecture"}]
    report = evaluate(_plan(), _procurement(), evidence)
    state = report["gates"]["dummy_pack_mount_qualified"]
    assert state["evidence_matched"] is True
    assert state["satisfied"] is False
    assert any("power_packaging_candidate_defined" in x for x in state["blockers"])


def test_environmental_candidate_requires_dummy_pack_mount():
    evidence = [
        x for x in _all_physical_evidence()
        if x.get("authority") not in {
            "x1_dummy_pack_mount",
            "x1_power_architecture",
        }
    ]
    report = evaluate(_plan(), _procurement(), evidence)
    state = report["gates"]["environmental_inert_candidate_qualified"]
    assert state["evidence_matched"] is True
    assert state["satisfied"] is False
    assert any(
        "dummy_pack_mount_qualified" in blocker
        for blocker in state["blockers"]
    )
    assert (
        report["capabilities"]["qualify_environmental_inert_candidate"]["allowed"]
        is False
    )


def test_powertrain_envelope_requires_topology_chassis_and_dummy_pack():
    evidence = _all_physical_evidence()
    report = evaluate(_plan(), _procurement(), evidence)
    assert report["capabilities"]["qualify_powertrain_envelope"]["allowed"] is True
    assert report["gates"]["powertrain_envelope_qualified"]["satisfied"] is True

    for missing_authority, blocker in (
        ("x1_brake_drive_topology", "brake_drive_topology_qualified"),
        ("x1_rolling_chassis_physical", "rolling_chassis_physical_qualified"),
        ("x1_dummy_pack_mount", "dummy_pack_mount_qualified"),
    ):
        reduced = [
            doc for doc in evidence
            if doc.get("authority") != missing_authority
        ]
        report = evaluate(_plan(), _procurement(), reduced)
        state = report["gates"]["powertrain_envelope_qualified"]
        assert state["satisfied"] is False
        assert any(blocker in item for item in state["blockers"])


def test_power_architecture_cannot_freeze_without_powertrain_envelope():
    evidence = [
        doc for doc in _all_physical_evidence()
        if doc.get("authority") != "x1_powertrain_envelope_candidate"
    ]
    report = evaluate(_plan(), _procurement(), evidence)
    assert report["gates"]["dummy_pack_mount_qualified"]["satisfied"] is True
    assert report["gates"]["environmental_inert_candidate_qualified"]["satisfied"] is True
    assert report["gates"]["powertrain_envelope_qualified"]["satisfied"] is False
    assert report["gates"]["power_architecture_frozen"]["satisfied"] is False
    assert any(
        "powertrain_envelope_qualified" in blocker
        for blocker in report["gates"]["power_architecture_frozen"]["blockers"]
    )


def test_power_architecture_cannot_freeze_without_environmental_candidate():
    evidence = [
        x for x in _all_physical_evidence()
        if x.get("authority") != "x1_environmental_inert_candidate"
    ]
    report = evaluate(_plan(), _procurement(), evidence)
    assert report["gates"]["dummy_pack_mount_qualified"]["satisfied"] is True
    assert (
        report["gates"]["environmental_inert_candidate_qualified"]["satisfied"]
        is False
    )
    assert report["gates"]["power_architecture_frozen"]["satisfied"] is False
    assert any(
        "environmental_inert_candidate_qualified" in blocker
        for blocker in report["gates"]["power_architecture_frozen"]["blockers"]
    )


def test_power_architecture_cannot_freeze_without_dummy_pack_mount():
    evidence = [x for x in _all_physical_evidence() if x.get("authority") != "x1_dummy_pack_mount"]
    report = evaluate(_plan(), _procurement(), evidence)
    assert report["gates"]["power_architecture_frozen"]["satisfied"] is False
    assert any("dummy_pack_mount_qualified" in x for x in report["gates"]["power_architecture_frozen"]["blockers"])


def test_power_ordering_stays_blocked_by_procurement_policy():
    report = evaluate(_plan(), _procurement(), _all_physical_evidence())
    assert report["gates"]["brake_drive_topology_qualified"]["satisfied"] is True
    assert report["gates"]["power_packaging_candidate_defined"]["satisfied"] is True
    assert report["gates"]["dummy_pack_mount_qualified"]["satisfied"] is True
    assert report["gates"]["environmental_inert_candidate_qualified"]["satisfied"] is True
    assert report["gates"]["powertrain_envelope_qualified"]["satisfied"] is True
    assert report["gates"]["power_architecture_frozen"]["satisfied"] is True
    assert report["gates"]["lifecycle_health_ready"]["satisfied"] is True
    assert report["capabilities"]["order_power_hardware"]["allowed"] is False
    assert "procurement stage blocked: POWER_GATED" in report["capabilities"]["order_power_hardware"]["blockers"]
    assert report["capabilities"]["powered_operation"]["allowed"] is False


def test_lifecycle_health_ready_requires_chassis_and_ready_health_evidence():
    health = _stamp({
        "authority": "x1_lifecycle_health_state",
        "schema_version": 1,
        "valid": True,
        "health_state": "READY_FOR_ALLOWED_ACTIVITY",
        "ready_for_allowed_activity": True,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
    })

    report = evaluate(_plan(), _procurement(), [health])
    gate = report["gates"]["lifecycle_health_ready"]
    assert gate["evidence_matched"] is True
    assert gate["satisfied"] is False
    assert any(
        "rolling_chassis_physical_qualified" in blocker
        for blocker in gate["blockers"]
    )

    report = evaluate(_plan(), _procurement(), _all_physical_evidence())
    assert report["gates"]["lifecycle_health_ready"]["satisfied"] is True


def test_lifecycle_health_from_different_chassis_cannot_satisfy_gate():
    evidence = _all_physical_evidence()
    health_index = next(
        i for i, doc in enumerate(evidence)
        if doc.get("authority") == "x1_lifecycle_health_state"
    )
    wrong = {
        key: value
        for key, value in evidence[health_index].items()
        if key != "authority_fingerprint_sha256"
    }
    wrong["rolling_chassis_fingerprint_sha256"] = "0" * 64
    evidence[health_index] = _stamp(wrong)

    report = evaluate(_plan(), _procurement(), evidence)
    gate = report["gates"]["lifecycle_health_ready"]
    assert gate["evidence_matched"] is True
    assert gate["satisfied"] is False
    assert any("evidence link mismatch" in blocker for blocker in gate["blockers"])


def test_missing_lifecycle_health_blocks_every_commissioning_action():
    evidence = [
        doc for doc in _all_physical_evidence()
        if doc.get("authority") != "x1_lifecycle_health_state"
    ]
    report = evaluate(_plan(), _procurement(), evidence)

    assert report["gates"]["power_architecture_frozen"]["satisfied"] is True
    assert report["gates"]["lifecycle_health_ready"]["satisfied"] is False

    for capability in (
        "prepare_powered_bench_readiness",
        "conduct_secured_unloaded_spin",
        "conduct_restrained_loaded_bench",
        "conduct_rider_free_controlled_ground",
        "conduct_rider_only_very_low_speed_commissioning",
    ):
        assert report["capabilities"][capability]["allowed"] is False
        assert any(
            "lifecycle_health_ready" in blocker
            for blocker in report["capabilities"][capability]["blockers"]
        )


def test_nonready_lifecycle_health_blocks_commissioning_and_operation_paths():
    evidence = _all_physical_evidence()
    index = next(
        i for i, doc in enumerate(evidence)
        if doc.get("authority") == "x1_lifecycle_health_state"
    )
    evidence[index] = _stamp({
        "authority": "x1_lifecycle_health_state",
        "schema_version": 1,
        "valid": True,
        "health_state": "SERVICE_REQUIRED",
        "ready_for_allowed_activity": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
    })
    evidence += _commissioning_evidence()

    report = evaluate(_plan(), _procurement(), evidence)
    assert report["gates"]["lifecycle_health_ready"]["satisfied"] is False

    for capability in (
        "prepare_powered_bench_readiness",
        "conduct_secured_unloaded_spin",
        "conduct_restrained_loaded_bench",
        "conduct_rider_free_controlled_ground",
        "conduct_rider_only_very_low_speed_commissioning",
        "powered_operation",
        "public_operation",
        "dog_accompanied_operation",
    ):
        assert report["capabilities"][capability]["allowed"] is False
        assert any(
            "lifecycle_health_ready" in blocker
            for blocker in report["capabilities"][capability]["blockers"]
        )


def test_commissioning_capabilities_open_only_stage_by_stage():
    base = _all_physical_evidence()
    commissioning = _commissioning_evidence()
    venue, stage0, stage1, stage2, stage3, stage4 = commissioning

    report = evaluate(_plan(), _procurement(), base)
    assert report["gates"]["power_architecture_frozen"]["satisfied"] is True
    assert report["capabilities"]["prepare_powered_bench_readiness"]["allowed"] is True
    assert report["capabilities"]["conduct_secured_unloaded_spin"]["allowed"] is False

    report = evaluate(_plan(), _procurement(), base + [stage0])
    assert report["gates"]["commissioning_stage_0_qualified"]["satisfied"] is True
    assert report["capabilities"]["conduct_secured_unloaded_spin"]["allowed"] is True
    assert report["capabilities"]["conduct_restrained_loaded_bench"]["allowed"] is False

    report = evaluate(_plan(), _procurement(), base + [stage0, stage1])
    assert report["gates"]["commissioning_stage_1_qualified"]["satisfied"] is True
    assert report["capabilities"]["conduct_restrained_loaded_bench"]["allowed"] is True
    assert report["capabilities"]["conduct_rider_free_controlled_ground"]["allowed"] is False

    report = evaluate(_plan(), _procurement(), base + [stage0, stage1, stage2])
    assert report["gates"]["commissioning_stage_2_qualified"]["satisfied"] is True
    assert report["capabilities"]["conduct_rider_free_controlled_ground"]["allowed"] is False
    assert any(
        "powered_test_venue_qualified" in blocker
        for blocker in report["capabilities"]["conduct_rider_free_controlled_ground"]["blockers"]
    )

    report = evaluate(
        _plan(),
        _procurement(),
        base + [venue, stage0, stage1, stage2],
    )
    assert report["gates"]["powered_test_venue_qualified"]["satisfied"] is True
    assert report["capabilities"]["conduct_rider_free_controlled_ground"]["allowed"] is True

    report = evaluate(
        _plan(),
        _procurement(),
        base + [venue, stage0, stage1, stage2, stage3],
    )
    assert report["gates"]["commissioning_stage_3_qualified"]["satisfied"] is True
    assert (
        report["capabilities"]["conduct_rider_only_very_low_speed_commissioning"]["allowed"]
        is True
    )


def test_even_complete_stage_four_commissioning_does_not_unlock_normal_riding():
    evidence = _all_physical_evidence() + _commissioning_evidence()
    report = evaluate(_plan(), _procurement(), evidence)

    for index in range(5):
        assert report["gates"][f"commissioning_stage_{index}_qualified"]["satisfied"] is True
    assert report["gates"]["powered_test_venue_qualified"]["satisfied"] is True

    powered = report["capabilities"]["powered_operation"]
    assert powered["allowed"] is False
    assert any(
        "Stage 4 is commissioning evidence only" in blocker
        for blocker in powered["blockers"]
    )
    assert report["capabilities"]["public_operation"]["allowed"] is False
    assert report["capabilities"]["dog_accompanied_operation"]["allowed"] is False


def test_ground_commissioning_evidence_cannot_skip_venue_or_prior_stage():
    base = _all_physical_evidence()
    venue, stage0, stage1, stage2, stage3, _ = _commissioning_evidence()

    report = evaluate(
        _plan(),
        _procurement(),
        base + [stage0, stage1, stage2, stage3],
    )
    state = report["gates"]["commissioning_stage_3_qualified"]
    assert state["evidence_matched"] is True
    assert state["satisfied"] is False
    assert any("powered_test_venue_qualified" in x for x in state["blockers"])

    report = evaluate(
        _plan(),
        _procurement(),
        base + [venue, stage0, stage2, stage3],
    )
    state = report["gates"]["commissioning_stage_3_qualified"]
    assert state["satisfied"] is False
    assert any("commissioning_stage_2_qualified" in x for x in state["blockers"])


def test_even_complete_existing_evidence_cannot_authorize_public_operation():
    report = evaluate(_plan(), _procurement(), _all_physical_evidence())
    assert report["gates"]["power_architecture_frozen"]["satisfied"] is True
    public = report["capabilities"]["public_operation"]
    assert public["allowed"] is False
    assert any(
        "Issue #35 has not established a public-use vehicle classification" in blocker
        for blocker in public["blockers"]
    )


def test_even_complete_existing_evidence_cannot_authorize_dog_accompanied_operation():
    report = evaluate(_plan(), _procurement(), _all_physical_evidence())
    assert report["gates"]["power_architecture_frozen"]["satisfied"] is True
    companion = report["capabilities"]["dog_accompanied_operation"]
    assert companion["allowed"] is False
    assert any(
        "Issue #33 has no current physical companion authority contract" in blocker
        for blocker in companion["blockers"]
    )


def test_future_power_ordering_requires_explicit_manifest_promotion():
    procurement = copy.deepcopy(_procurement())
    procurement["rules"]["power_gated_authorized"] = True
    report = evaluate(_plan(), procurement, _all_physical_evidence())
    assert report["capabilities"]["order_power_hardware"]["allowed"] is True
    assert report["capabilities"]["powered_operation"]["allowed"] is False


def test_tampered_evidence_fingerprint_is_rejected():
    evidence = _all_physical_evidence()
    evidence[3]["brake_interface_verified"] = False
    report = evaluate(_plan(), _procurement(), evidence)
    assert report["gates"]["brake_interface_qualified"]["satisfied"] is False


def test_gate_cycles_are_rejected():
    plan = _plan()
    plan["gates"]["fit_pilot_qualified"]["requires"] = ["power_architecture_frozen"]
    with pytest.raises(ValueError, match="cycle"):
        _validate_plan(plan)
