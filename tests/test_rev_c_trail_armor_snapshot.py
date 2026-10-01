import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _snapshot():
    return json.loads(
        (
            ROOT / "hardware/rev_c_trail_armor_snapshot_2026-10-01.json"
        ).read_text()
    )


def test_trail_armor_snapshot_is_facts_only_and_non_authoritative():
    data = _snapshot()
    assert data["facts_only"] is True
    boundary = data["authority_boundary"]
    assert boundary["physical_authority"] is False
    assert boundary["procurement_authority"] is False
    assert boundary["powered_operation_authorized"] is False


def test_armor_layer_order_keeps_replaceable_wear_part_first():
    layers = sorted(_snapshot()["armor_layers"], key=lambda x: x["order"])
    assert [layer["name"] for layer in layers] == [
        "wear_shoe",
        "carrier_or_vendor_guard_structure",
        "structural_mount",
        "protected_component",
    ]
    assert layers[-1]["design_state"] == "MUST_NOT_BE_FIRST_CONTACT"


def test_material_and_thickness_are_intentionally_unfrozen():
    policy = _snapshot()["material_policy"]
    assert policy["selected_material"] is None
    assert policy["selected_thickness_mm"] is None
    assert "Do not freeze material or thickness" in policy["rule"]


def test_live_battery_and_battery_shell_shortcuts_are_prohibited():
    shortcuts = _snapshot()["prohibited_shortcuts"]
    assert "live battery used as first armor impact surrogate" in shortcuts
    assert any("battery shell" in item for item in shortcuts)
    assert any("brake retention" in item for item in shortcuts)


def test_mbs_reference_is_used_for_replaceable_service_philosophy():
    refs = {
        item["id"]: item
        for item in _snapshot()["commercial_references"]
    }
    g1 = refs["MBS_G1_GEAR_DRIVE"]
    assert "replaceable aluminum skid plates protect the vulnerable underside" in g1["facts"]
    assert "replacement skid plates are sold as service parts" in g1["facts"]
