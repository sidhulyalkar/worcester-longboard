import hashlib
import json

from tools.qualify_rev_c_powertrain_candidate import qualify


def _stamp(doc):
    payload = json.dumps(
        doc,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    out = dict(doc)
    out["authority_fingerprint_sha256"] = hashlib.sha256(payload).hexdigest()
    return out


def _authorities(selected_topology="same_rear_axle_v5_plus_drive"):
    chassis = _stamp(
        {
            "schema_version": 1,
            "authority": "x1_rolling_chassis_physical",
            "qualified": True,
            "powered_operation_authorized": False,
        }
    )
    topology = _stamp(
        {
            "schema_version": 1,
            "authority": "x1_brake_drive_topology",
            "qualified": True,
            "selected_topology": selected_topology,
            "powered_operation_authorized": False,
        }
    )
    dummy = _stamp(
        {
            "schema_version": 1,
            "authority": "x1_dummy_pack_mount",
            "qualified": True,
            "powered_operation_authorized": False,
        }
    )
    return chassis, topology, dummy


def _manifest(selected_topology="same_rear_axle_v5_plus_drive"):
    chassis, topology, dummy = _authorities(selected_topology)
    topology_class = (
        "front" if selected_topology == "rear_v5_front_2wd" else "rear"
    )
    manifest = {
        "schema_version": 1,
        "scope": "rev_c_powertrain_candidate_qualification",
        "issue": 43,
        "candidate_id": "SYNTHETIC-POWERTRAIN-A",
        "selected_drive_family": "synthetic-test-family",
        "linked_authorities": {
            "rolling_chassis_fingerprint_sha256": chassis[
                "authority_fingerprint_sha256"
            ],
            "brake_drive_topology_fingerprint_sha256": topology[
                "authority_fingerprint_sha256"
            ],
            "dummy_pack_fingerprint_sha256": dummy[
                "authority_fingerprint_sha256"
            ],
        },
        "source_refs": {
            "motor_kv_rpm_per_v": "synthetic manufacturer motor sheet",
            "motor_pole_pairs": "synthetic manufacturer motor sheet",
            "phase_current_limit_a_per_motor": "synthetic controller/motor study",
            "battery_current_limit_a_total": "synthetic battery-builder limit",
            "erpm_limit": "synthetic controller hardware limit",
            "nominal_voltage_v": "synthetic battery-builder specification",
            "full_voltage_v": "synthetic battery-builder specification",
            "motor_mount_and_shaft": "synthetic motor mechanical drawing",
            "wheel_gear_teeth": "synthetic drive drawing",
            "motor_gear_teeth": "synthetic drive drawing",
            "drivetrain_efficiency_basis": "study-assumption: 0.90",
            "electrical_efficiency_basis": "study-assumption: 0.92",
            "rolling_resistance_basis": "study-assumption: 0.03",
            "traction_mu_basis": "study-assumption: scenario-specific conservative values",
        },
        "envelope_config": {
            "schema_version": 1,
            "scope": "rev_c_powertrain_envelope",
            "vehicle": {
                "total_mass_kg": 80.0,
                "wheelbase_m": 0.94,
                "cg_from_rear_m": 0.47,
                "cg_height_m": 0.35,
                "wheel_diameter_m": 0.20,
                "rolling_resistance_coeff": 0.03,
                "aero_drag_area_m2": 0.0,
                "air_density_kg_m3": 1.225,
            },
            "candidate": {
                "id": "SYNTHETIC-POWERTRAIN-A",
                "topology": topology_class,
                "motor_count": 2,
                "motor_kv_rpm_per_v": 120.0,
                "motor_pole_pairs": 7,
                "wheel_gear_teeth": 64,
                "motor_gear_teeth": 15,
                "nominal_voltage_v": 50.4,
                "full_voltage_v": 58.8,
                "speed_voltage_basis": "nominal",
                "phase_current_limit_a_per_motor": 80.0,
                "battery_current_limit_a_total": 60.0,
                "electrical_power_limit_w_total": 3000.0,
                "erpm_limit": 100000.0,
                "drivetrain_efficiency": 0.90,
                "electrical_efficiency": 0.92,
            },
            "scenarios": [
                {
                    "name": "flat_cruise",
                    "scenario_class": "flat_cruise",
                    "grade": 0.0,
                    "target_speed_mps": 5.0,
                    "acceleration_mps2": 0.0,
                    "assumed_mu": 0.7,
                },
                {
                    "name": "grade_climb",
                    "scenario_class": "grade_climb",
                    "grade": 0.20,
                    "target_speed_mps": 4.0,
                    "acceleration_mps2": 0.2,
                    "assumed_mu": 0.8,
                },
                {
                    "name": "low_speed_accel",
                    "scenario_class": "low_speed_accel",
                    "grade": 0.05,
                    "target_speed_mps": 2.0,
                    "acceleration_mps2": 0.5,
                    "assumed_mu": 0.8,
                },
            ],
            "physical_authority": False,
            "procurement_authority": False,
            "controller_configuration_authority": False,
            "battery_configuration_authority": False,
            "powered_operation_authorized": False,
        },
        "thermal_qualification": False,
        "procurement_authority": False,
        "controller_configuration_authority": False,
        "battery_configuration_authority": False,
        "powered_operation_authorized": False,
    }
    return manifest, chassis, topology, dummy


def test_sourced_candidate_can_qualify_architecture_envelope_only():
    manifest, chassis, topology, dummy = _manifest()
    report = qualify(manifest, chassis, topology, dummy)

    assert report["qualified"] is True
    assert report["all_declared_scenarios_pass"] is True
    assert report["selected_topology"] == "same_rear_axle_v5_plus_drive"
    assert report["propulsion_topology_class"] == "rear"
    assert report["ratio_wheel_over_motor"] == 64 / 15
    assert len(report["envelope_config_sha256"]) == 64
    assert len(report["analysis_sha256"]) == 64
    assert len(report["authority_fingerprint_sha256"]) == 64
    assert report["thermal_qualification"] is False
    assert report["physical_authority"] is False
    assert report["procurement_authority"] is False
    assert report["controller_configuration_authority"] is False
    assert report["battery_configuration_authority"] is False
    assert report["powered_operation_authorized"] is False


def test_unsourced_candidate_input_is_rejected():
    manifest, chassis, topology, dummy = _manifest()
    manifest["source_refs"]["motor_kv_rpm_per_v"] = ""

    report = qualify(manifest, chassis, topology, dummy)
    assert report["qualified"] is False
    assert "source_refs.motor_kv_rpm_per_v must be nonempty" in report["errors"]


def test_candidate_topology_must_match_issue_19_selection():
    manifest, chassis, topology, dummy = _manifest(
        selected_topology="rear_v5_front_2wd"
    )
    manifest["envelope_config"]["candidate"]["topology"] = "rear"

    report = qualify(manifest, chassis, topology, dummy)
    assert report["qualified"] is False
    assert any("does not match Issue #19" in error for error in report["errors"])


def test_required_mission_scenario_classes_cannot_be_skipped():
    manifest, chassis, topology, dummy = _manifest()
    manifest["envelope_config"]["scenarios"] = [
        s
        for s in manifest["envelope_config"]["scenarios"]
        if s["scenario_class"] != "grade_climb"
    ]

    report = qualify(manifest, chassis, topology, dummy)
    assert report["qualified"] is False
    assert any(
        "missing required scenario classes: grade_climb" in error
        for error in report["errors"]
    )


def test_candidate_failing_declared_current_limit_is_rejected():
    manifest, chassis, topology, dummy = _manifest()
    manifest["envelope_config"]["candidate"][
        "phase_current_limit_a_per_motor"
    ] = 5.0

    report = qualify(manifest, chassis, topology, dummy)
    assert report["qualified"] is False
    assert any(
        "fails one or more first-order scenarios" in error
        for error in report["errors"]
    )


def test_manifest_cannot_link_different_dummy_pack():
    manifest, chassis, topology, dummy = _manifest()
    manifest["linked_authorities"]["dummy_pack_fingerprint_sha256"] = "0" * 64

    report = qualify(manifest, chassis, topology, dummy)
    assert report["qualified"] is False
    assert any(
        "does not link the supplied x1_dummy_pack_mount" in error
        for error in report["errors"]
    )


def test_tampered_upstream_authority_is_rejected():
    manifest, chassis, topology, dummy = _manifest()
    topology["selected_topology"] = "rear_v5_front_2wd"

    report = qualify(manifest, chassis, topology, dummy)
    assert report["qualified"] is False
    assert any(
        "x1_brake_drive_topology must be qualified and fingerprint-valid" in error
        for error in report["errors"]
    )
