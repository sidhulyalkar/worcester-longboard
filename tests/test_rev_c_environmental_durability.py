import hashlib
import json
from pathlib import Path

from tools.qualify_rev_c_environmental_durability import qualify

ROOT = Path(__file__).resolve().parents[1]


def _stamp(doc):
    payload = json.dumps(
        doc,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    result = dict(doc)
    result["authority_fingerprint_sha256"] = hashlib.sha256(payload).hexdigest()
    return result


def _authorities():
    chassis = _stamp(
        {
            "schema_version": 1,
            "authority": "x1_rolling_chassis_physical",
            "qualified": True,
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
    return chassis, dummy


def _manifest():
    chassis, dummy = _authorities()
    data = json.loads(
        (ROOT / "hardware/rev_c_environmental_trial_template.json").read_text()
    )
    data.update(
        {
            "session_id": "environmental-test",
            "chassis_authority_fingerprint_sha256": chassis[
                "authority_fingerprint_sha256"
            ],
            "dummy_pack_authority_fingerprint_sha256": dummy[
                "authority_fingerprint_sha256"
            ],
            "candidate_enclosure_id": "INERT-ENC-A",
            "harness_revision_id": "HARNESS-SURROGATE-A",
        }
    )

    data["interface_inventory"] = [
        {
            "id": "ENC-SEAM-A",
            "function": "primary enclosure perimeter seam",
            "exposure_location": "under-deck",
            "protection_method": "compressed gasket surrogate",
            "drainage_or_shedding_method": "external drip edge and downhill drain path",
            "inspection_method": "external seam and witness strip inspection",
            "service_method": "inspect externally; open only by normal service procedure",
            "external_protection_inspectable_without_breaking_primary_seal": True,
            "strain_relief_or_not_applicable": True,
            "direct_spray_orientation_or_shielding_checked": True,
        },
        {
            "id": "HARNESS-ENTRY-A",
            "function": "low-voltage harness entry surrogate",
            "exposure_location": "rear enclosure face",
            "protection_method": "gland surrogate plus drip loop",
            "drainage_or_shedding_method": "entry faces down and cable has drip loop",
            "inspection_method": "external gland and cable inspection",
            "service_method": "disconnect only after dry external cleaning",
            "external_protection_inspectable_without_breaking_primary_seal": True,
            "strain_relief_or_not_applicable": True,
            "direct_spray_orientation_or_shielding_checked": True,
        },
    ]

    media = {
        "dry_grit": ("clean inert dry grit surrogate", 50.0, "g"),
        "splash": ("clean water splash surrogate", 1.5, "L"),
        "mud_surrogate": ("non-energized inert mud surrogate", 0.5, "kg"),
    }
    for cycle in data["exposure_cycles"]:
        desc, qty, unit = media[cycle["exposure_type"]]
        cycle.update(
            {
                "media_description": desc,
                "method_description": "repeatable fixture exposure with recorded orientation",
                "exposure_quantity": qty,
                "exposure_quantity_unit": unit,
                "duration_s": 60.0,
                "protected_zone_ingress_observed": False,
                "drainage_or_shedding_path_functional": True,
                "steering_brake_wheel_motion_free": True,
                "service_access_preserved": True,
                "seal_or_gasket_displaced": False,
                "harness_or_hose_chafe_created": False,
                "contamination_trapped_against_protected_component": False,
            }
        )

    data["connector_service_trials"] = [
        {
            "id": "CONN-01",
            "connector_id": "INERT-CONNECTOR-A",
            "connector_role": "disconnected low-voltage harness surrogate",
            "energized": False,
            "traction_voltage_connector": False,
            "contamination_description": "external dry grit and splash residue",
            "cleaning_method": "dry external clean per selected connector service guidance",
            "manufacturer_service_guidance_source": "synthetic-fixture-guidance",
            "contamination_beyond_intended_seal_observed": False,
            "pin_or_contact_damage_observed": False,
            "seal_damage_or_displacement_observed": False,
            "cable_used_as_disconnect_handle": False,
            "fully_reseated_after_service": True,
            "positive_latch_or_retention_verified": True,
        }
    ]

    data["wheel_brake_steering_recovery"] = {
        "wheel_free_spin_after_cleaning": True,
        "bearing_play_increase_observed": False,
        "tire_valve_access_preserved": True,
        "brake_releases_without_drag": True,
        "brake_actuation_normal": True,
        "brake_friction_surface_contaminated": False,
        "steering_returns_freely": True,
        "service_completed_without_opening_traction_enclosure": True,
    }

    data["drying_and_post_inspection"] = {
        "drying_method": "gravity drain plus ambient dry inspection",
        "declared_dry_time_minutes": 60.0,
        "drainage_paths_clear": True,
        "visible_retained_moisture": False,
        "hidden_zone_witness_dry": True,
        "corrosion_observed": False,
        "fretting_or_contact_discoloration_observed": False,
        "harness_chafe_observed": False,
        "fastener_or_witness_migration_observed": False,
        "enclosure_crack_or_seal_damage_observed": False,
        "contamination_guard_reusable_or_replaced": True,
    }
    return data, chassis, dummy


def test_inert_environmental_candidate_can_qualify_without_wet_power_authority():
    data, chassis, dummy = _manifest()
    report = qualify(data, chassis, dummy)

    assert report["qualified"] is True
    assert report["environmental_inert_candidate_qualified"] is True
    assert report["ip_rating_claimed"] is False
    assert report["waterproof_claimed"] is False
    assert report["corrosion_life_claimed"] is False
    assert report["electrical_wet_operation_qualified"] is False
    assert report["live_battery_test_authorized"] is False
    assert report["procurement_authority"] is False
    assert report["powered_operation_authorized"] is False
    assert len(report["authority_fingerprint_sha256"]) == 64


def test_live_energy_pressure_washing_or_immersion_fail():
    data, chassis, dummy = _manifest()
    data["live_battery_present"] = True
    data["traction_voltage_present"] = True
    data["pressure_washer_used"] = True
    data["immersion_used"] = True

    report = qualify(data, chassis, dummy)
    assert report["qualified"] is False
    for key in (
        "live_battery_present",
        "traction_voltage_present",
        "pressure_washer_used",
        "immersion_used",
    ):
        assert f"{key} must be false" in report["errors"]


def test_all_three_contamination_modes_are_required():
    data, chassis, dummy = _manifest()
    data["exposure_cycles"] = [
        cycle
        for cycle in data["exposure_cycles"]
        if cycle["exposure_type"] != "mud_surrogate"
    ]

    report = qualify(data, chassis, dummy)
    assert report["qualified"] is False
    assert any("mud_surrogate" in error for error in report["errors"])


def test_protected_ingress_or_blocked_drain_fails():
    data, chassis, dummy = _manifest()
    data["exposure_cycles"][1]["protected_zone_ingress_observed"] = True
    data["exposure_cycles"][1]["drainage_or_shedding_path_functional"] = False

    report = qualify(data, chassis, dummy)
    assert report["qualified"] is False
    assert any("protected_zone_ingress_observed" in error for error in report["errors"])
    assert any("drainage_or_shedding_path_functional" in error for error in report["errors"])


def test_connector_damage_or_contamination_beyond_seal_fails():
    data, chassis, dummy = _manifest()
    trial = data["connector_service_trials"][0]
    trial["contamination_beyond_intended_seal_observed"] = True
    trial["pin_or_contact_damage_observed"] = True

    report = qualify(data, chassis, dummy)
    assert report["qualified"] is False
    assert any(
        "contamination_beyond_intended_seal_observed" in error
        for error in report["errors"]
    )
    assert any("pin_or_contact_damage_observed" in error for error in report["errors"])


def test_brake_or_bearing_recovery_failure_blocks_candidate():
    data, chassis, dummy = _manifest()
    recovery = data["wheel_brake_steering_recovery"]
    recovery["bearing_play_increase_observed"] = True
    recovery["brake_releases_without_drag"] = False

    report = qualify(data, chassis, dummy)
    assert report["qualified"] is False
    assert any("bearing_play_increase_observed" in error for error in report["errors"])
    assert any("brake_releases_without_drag" in error for error in report["errors"])


def test_retained_moisture_or_post_exposure_damage_fails():
    data, chassis, dummy = _manifest()
    post = data["drying_and_post_inspection"]
    post["visible_retained_moisture"] = True
    post["hidden_zone_witness_dry"] = False
    post["enclosure_crack_or_seal_damage_observed"] = True

    report = qualify(data, chassis, dummy)
    assert report["qualified"] is False
    assert any("visible_retained_moisture" in error for error in report["errors"])
    assert any("hidden_zone_witness_dry" in error for error in report["errors"])
    assert any(
        "enclosure_crack_or_seal_damage_observed" in error
        for error in report["errors"]
    )


def test_manifest_must_link_supplied_physical_authorities():
    data, chassis, dummy = _manifest()
    data["dummy_pack_authority_fingerprint_sha256"] = "0" * 64

    report = qualify(data, chassis, dummy)
    assert report["qualified"] is False
    assert any("dummy-pack authority" in error for error in report["errors"])


def test_tampered_upstream_authority_is_rejected():
    data, chassis, dummy = _manifest()
    dummy["qualified"] = False

    report = qualify(data, chassis, dummy)
    assert report["qualified"] is False
    assert any("x1_dummy_pack_mount is not qualified" in error for error in report["errors"])
    assert any("fingerprint is invalid" in error for error in report["errors"])
