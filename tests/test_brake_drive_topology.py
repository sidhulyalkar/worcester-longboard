from tools.qualify_brake_drive_topology import qualify, TOPOLOGIES


def _sha(char="a"):
    return char * 64


def _valid_manifest(selected="same_rear_axle_v5_plus_drive"):
    candidates = {}
    for name, specific in TOPOLOGIES.items():
        candidates[name] = {
            "status": "PASS" if name == selected else "REJECTED",
            "reason": "selected by measured comparison" if name == selected else "rejected by measured comparison",
            specific: name == selected,
        }
    return {
        "scope": "unpowered_brake_drive_topology_measurement",
        "selected_topology": selected,
        "candidate_evaluations": candidates,
        "checks": {
            "manufacturer_constraints_recorded": True,
            "brake_static_and_rolling_evidence_linked": True,
            "motion_sweep_passed": True,
            "wheel_service_without_battery_disturbance_passed": True,
            "positive_wheel_and_drive_retention_defined": True,
            "cable_hose_sweep_clear": True,
            "replaceable_guard_strategy_defined": True,
            "rejected_topologies_documented": True,
            "mechanical_brake_independent_of_traction_power": True,
            "at_least_two_friction_braked_wheels": True,
        },
        "hardware_ids": {
            "front_truck": "TRUCK-F-A",
            "rear_truck": "TRUCK-R-A",
            "rear_axle": "AXLE-R-A",
            "rear_hub": "HUB-R-A",
            "rear_wheel": "WHEEL-R-A",
            "brake": "BRAKE-A",
            "drive_reference": "DRIVE-A",
        },
        "evidence_refs": {
            "brake_authority_fingerprint_sha256": _sha("a"),
            "rolling_chassis_authority_fingerprint_sha256": _sha("b"),
            "collision_sweep_sha256": _sha("c"),
            "service_record_sha256": _sha("d"),
        },
        "powered_operation_authorized": False,
    }


def test_all_supported_topologies_can_qualify_when_evidence_is_complete():
    for topology in TOPOLOGIES:
        report = qualify(_valid_manifest(topology))
        assert report["qualified"] is True
        assert report["selected_topology"] == topology
        assert report["powered_operation_authorized"] is False
        assert len(report["authority_fingerprint_sha256"]) == 64


def test_selected_topology_must_pass_specific_mechanical_check():
    manifest = _valid_manifest()
    specific = TOPOLOGIES[manifest["selected_topology"]]
    manifest["candidate_evaluations"][manifest["selected_topology"]][specific] = False
    report = qualify(manifest)
    assert report["qualified"] is False
    assert any(specific in error for error in report["errors"])


def test_nonselected_topologies_must_be_explicitly_rejected():
    manifest = _valid_manifest()
    other = "rear_v5_front_2wd"
    manifest["candidate_evaluations"][other]["status"] = "NOT_EVALUATED"
    report = qualify(manifest)
    assert report["qualified"] is False
    assert any(other in error for error in report["errors"])


def test_topology_authority_cannot_enable_powered_operation():
    manifest = _valid_manifest()
    manifest["powered_operation_authorized"] = True
    report = qualify(manifest)
    assert report["qualified"] is False
    assert report["powered_operation_authorized"] is False


def test_sha_evidence_refs_are_required():
    manifest = _valid_manifest()
    manifest["evidence_refs"]["collision_sweep_sha256"] = "not-a-digest"
    report = qualify(manifest)
    assert report["qualified"] is False
    assert any("collision_sweep_sha256" in error for error in report["errors"])
