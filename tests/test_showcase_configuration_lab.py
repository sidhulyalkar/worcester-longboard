import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "showcase" / "x1_rev_c.json"


def load_seed():
    return json.loads(SEED.read_text())


def test_configuration_lab_presets_reference_known_design_choices():
    seed = load_seed()
    studies = seed["design_studies"]
    lab = studies["configuration_lab"]

    deck_ids = {row["id"] for row in studies["deck_candidates"]}
    topology_ids = {row["id"] for row in studies["topology_branches"]}
    layer_ids = {row["id"] for row in lab["layers"]}

    assert lab["scope"] == "non_authoritative_visual_trade_study"
    assert lab["winner_selected"] is False
    assert len(layer_ids) == len(lab["layers"])

    preset_ids = set()
    for preset in lab["presets"]:
        assert preset["id"] not in preset_ids
        preset_ids.add(preset["id"])
        assert preset["deck_candidate_id"] in deck_ids
        assert preset["topology_id"] in topology_ids
        assert set(preset["layers"]) == layer_ids
        assert all(isinstance(value, bool) for value in preset["layers"].values())
        assert "winner" not in preset
        assert "qualified" not in preset
        assert "authority" not in preset


def test_configuration_lab_layers_map_to_known_component_kinds():
    seed = load_seed()
    lab = seed["design_studies"]["configuration_lab"]
    component_kinds = {
        component["render"]["kind"]
        for component in seed["components"]
        if component.get("render", {}).get("kind")
    }

    for layer in lab["layers"]:
        assert layer["component_kind"] in component_kinds


def test_configuration_lab_snowdeck_presets_stay_inside_visual_study_bounds():
    seed = load_seed()
    presets = seed["design_studies"]["configuration_lab"]["presets"]

    for preset in presets:
        snow = preset["snowdeck"]
        assert 260 <= snow["stance_mm"] <= 520
        assert -30 <= snow["front_yaw_deg"] <= 30
        assert -30 <= snow["rear_yaw_deg"] <= 30
        assert 0 <= snow["front_cant_deg"] <= 5
        assert 0 <= snow["rear_cant_deg"] <= 5
        assert 0 <= snow["insert_proxy_mm"] <= 8


def test_coexistence_preset_is_explicitly_a_question_not_a_claim():
    seed = load_seed()
    lab = seed["design_studies"]["configuration_lab"]
    preset = next(row for row in lab["presets"] if row["id"] == "coexistence_question")

    assert preset["layers"]["brake"] is True
    assert preset["layers"]["drive"] is True
    assert "unresolved coexistence problem" in preset["description"]
    assert "not a compatibility claim" in preset["description"]
