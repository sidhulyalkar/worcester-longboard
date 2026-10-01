import json
from pathlib import Path

from tools.qualify_rev_c_trail_armor import qualify

ROOT = Path(__file__).resolve().parents[1]


def _manifest():
    data = json.loads(
        (ROOT / "hardware/rev_c_trail_armor_trial_template.json").read_text()
    )
    data.update(
        {
            "session_id": "armor-test",
            "protected_zone_id": "DRIVE-R-A",
            "armor_architecture": "replaceable-drive-skid",
            "wear_shoe_id": "WEAR-A",
            "carrier_or_vendor_guard_id": "CARRIER-A",
            "structural_mount_id": "MOUNT-A",
            "protected_inert_component_id": "INERT-DRIVE-A",
        }
    )
    for key in data["geometry_checks"]:
        data["geometry_checks"][key] = True
    data["load_path"] = {
        "type": "separate_sacrificial_skid",
        "description": "wear shoe to carrier to measured structural mount",
        "battery_shell_is_primary_impact_structure": False,
        "electrical_connector_is_structural_member": False,
        "adhesive_only_retention": False,
        "structural_mount_retention_inspectable": True,
        "witness_or_migration_check_present": True,
        "no_unqualified_safety_critical_adapter": True,
    }
    data["service_checks"] = {
        "wear_part_individually_replaceable": True,
        "replacement_does_not_open_traction_enclosure": True,
        "replacement_does_not_disturb_brake_critical_joint": True,
        "wheel_tube_service_preserved": True,
        "drivetrain_service_preserved": True,
        "replacement_method": "remove dedicated skid fasteners only",
        "replacement_time_minutes": 4.5,
    }
    for trial in data["low_energy_surrogate_trials"]:
        trial.update(
            {
                "surrogate_description": "fixed rounded root surrogate",
                "contact_direction": "forward",
                "measured_entry_speed_mps": 0.6,
                "intended_wear_surface_contacted_first": True,
                "armor_slid_or_deflected_over_surrogate_without_hooking": True,
                "protected_component_contacted": False,
                "wheel_brake_or_steering_interference": False,
                "armor_or_fastener_became_loose": False,
            }
        )
    data["post_trial_inspection"] = {
        "structural_mount_damage": False,
        "protected_component_damage": False,
        "new_crack_or_permanent_deformation": False,
        "retention_or_witness_movement": False,
        "loose_or_missing_hardware": False,
        "new_wheel_brake_steering_interference": False,
        "wear_part_condition_recorded": True,
    }
    return data


def test_inert_trail_armor_can_qualify_geometry_without_impact_authority():
    report = qualify(_manifest())
    assert report["qualified"] is True
    assert report["inert_geometry_service_qualified"] is True
    assert report["impact_energy_qualified"] is False
    assert report["live_battery_test_authorized"] is False
    assert report["procurement_authority"] is False
    assert report["powered_operation_authorized"] is False


def test_live_energy_or_power_always_fails_early_armor_qualification():
    data = _manifest()
    data["live_battery_present"] = True
    data["powered_vehicle"] = True
    report = qualify(data)
    assert report["qualified"] is False
    assert "live_battery_present must be false" in report["errors"]
    assert "powered_vehicle must be false" in report["errors"]


def test_protected_component_cannot_be_first_contact():
    data = _manifest()
    data["geometry_checks"]["wear_shoe_is_intended_first_hard_contact"] = False
    data["low_energy_surrogate_trials"][0]["protected_component_contacted"] = True
    report = qualify(data)
    assert report["qualified"] is False
    assert any("wear_shoe_is_intended_first_hard_contact" in x for x in report["errors"])
    assert any("protected_component_contacted" in x for x in report["errors"])


def test_skid_cannot_use_battery_shell_connector_or_adhesive_only_as_structure():
    data = _manifest()
    data["load_path"]["battery_shell_is_primary_impact_structure"] = True
    data["load_path"]["electrical_connector_is_structural_member"] = True
    data["load_path"]["adhesive_only_retention"] = True
    report = qualify(data)
    assert report["qualified"] is False
    assert any("battery_shell_is_primary_impact_structure" in x for x in report["errors"])
    assert any("electrical_connector_is_structural_member" in x for x in report["errors"])
    assert any("adhesive_only_retention" in x for x in report["errors"])


def test_wear_part_must_be_serviceable_without_disturbing_brake_or_enclosure():
    data = _manifest()
    data["service_checks"]["replacement_does_not_open_traction_enclosure"] = False
    data["service_checks"]["replacement_does_not_disturb_brake_critical_joint"] = False
    report = qualify(data)
    assert report["qualified"] is False
    assert any("replacement_does_not_open_traction_enclosure" in x for x in report["errors"])
    assert any("replacement_does_not_disturb_brake_critical_joint" in x for x in report["errors"])


def test_low_energy_root_surrogate_must_not_hook_or_loosen_armor():
    data = _manifest()
    trial = data["low_energy_surrogate_trials"][1]
    trial["armor_slid_or_deflected_over_surrogate_without_hooking"] = False
    trial["armor_or_fastener_became_loose"] = True
    report = qualify(data)
    assert report["qualified"] is False
    assert any("without_hooking" in x for x in report["errors"])
    assert any("armor_or_fastener_became_loose" in x for x in report["errors"])
