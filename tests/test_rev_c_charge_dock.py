import json
from pathlib import Path

from tools.qualify_rev_c_charge_dock import qualify

ROOT = Path(__file__).resolve().parents[1]


def _manifest():
    data = json.loads(
        (ROOT / "hardware/rev_c_charge_dock_mechanical_template.json").read_text()
    )
    data.update(
        {
            "session_id": "dock-test",
            "selected_pack_reference_id": "PACK-REF-A",
            "selected_charger_reference_id": "CHARGER-REF-A",
            "charger_compatibility_source": "manufacturer-system-document",
            "inert_pack_fixture_id": "INERT-PACK-A",
            "inert_connector_fixture_id": "INERT-CONNECTOR-A",
        }
    )
    for key in data["dock_design"]:
        data["dock_design"][key] = True
    data["alignment_limits"] = {
        "connector_manufacturer_source": "manufacturer-system-document",
        "lateral_misalignment_limit_checked": True,
        "angular_misalignment_limit_checked": True,
        "mating_force_or_method_limit_checked": True,
        "dock_guides_prevent_exceeding_known_connector_limits": True,
    }
    data["stability_check"] = {
        "method": "repeatable low-energy disturbance check",
        "board_remained_stable": True,
        "connector_not_used_as_retention": True,
    }
    data["cable_check"] = {
        "manufacturer_or_system_source": "manufacturer-system-document",
        "bend_radius_and_strain_requirements_checked": True,
        "no_sharp_edge_contact": True,
        "no_wheel_or_steering_sweep_contact": True,
    }
    for trial in data["alignment_trials"]:
        for key in tuple(trial):
            if key != "id":
                trial[key] = True
    data["post_trial_inspection"] = {
        "dock_shifted_or_loosened": False,
        "connector_fixture_damage": False,
        "cable_or_strain_relief_damage": False,
        "board_or_chassis_damage": False,
    }
    return data


def test_inert_dock_can_qualify_mechanics_without_electrical_authority():
    report = qualify(_manifest())
    assert report["qualified"] is True
    assert report["alignment_trial_count"] == 5
    assert report["connector_alignment_limits_verified"] is True
    assert report["inert_mechanical_alignment_qualified"] is True
    assert report["live_battery_test_authorized"] is False
    assert report["electrical_charge_authorized"] is False
    assert report["procurement_authority"] is False
    assert report["powered_operation_authorized"] is False


def test_live_energy_presence_always_fails_this_qualifier():
    data = _manifest()
    data["electrical_energy_present"] = True
    report = qualify(data)
    assert report["qualified"] is False
    assert "electrical_energy_present must be false" in report["errors"]


def test_connector_cannot_be_structural_retention():
    data = _manifest()
    data["stability_check"]["connector_not_used_as_retention"] = False
    report = qualify(data)
    assert report["qualified"] is False
    assert any("connector_not_used_as_retention" in x for x in report["errors"])


def test_connector_alignment_limits_must_be_sourced_and_checked():
    data = _manifest()
    data["alignment_limits"]["connector_manufacturer_source"] = ""
    data["alignment_limits"]["dock_guides_prevent_exceeding_known_connector_limits"] = False
    report = qualify(data)
    assert report["qualified"] is False
    assert any(
        "alignment_limits.connector_manufacturer_source" in x
        for x in report["errors"]
    )
    assert any(
        "dock_guides_prevent_exceeding_known_connector_limits" in x
        for x in report["errors"]
    )


def test_connector_cannot_be_used_as_board_retention_or_forced_alignment():
    data = _manifest()
    data["dock_design"]["board_retention_independent_of_connector"] = False
    data["dock_design"]["connector_mating_axis_free_to_self_align"] = False
    report = qualify(data)
    assert report["qualified"] is False
    assert any("board_retention_independent_of_connector" in x for x in report["errors"])
    assert any("connector_mating_axis_free_to_self_align" in x for x in report["errors"])


def test_five_repeatable_alignment_trials_are_required():
    data = _manifest()
    data["alignment_trials"] = data["alignment_trials"][:4]
    report = qualify(data)
    assert report["qualified"] is False
    assert "at least five alignment trials are required" in report["errors"]


def test_cable_source_and_protection_are_required():
    data = _manifest()
    data["cable_check"]["manufacturer_or_system_source"] = ""
    data["cable_check"]["no_sharp_edge_contact"] = False
    report = qualify(data)
    assert report["qualified"] is False
    assert any("manufacturer_or_system_source" in x for x in report["errors"])
    assert any("no_sharp_edge_contact" in x for x in report["errors"])


def test_failed_post_trial_inspection_blocks_qualification():
    data = _manifest()
    data["post_trial_inspection"]["connector_fixture_damage"] = True
    report = qualify(data)
    assert report["qualified"] is False
    assert any("connector_fixture_damage" in x for x in report["errors"])
