import json
from pathlib import Path

from configurator.engine import generate_candidates
from configurator.swap_lab import evaluate_swap
from configurator.visual_state import (
    visual_state_from_candidate,
    visual_state_from_swap,
)

ROOT = Path(__file__).resolve().parents[1]


def profile(name):
    return json.loads((ROOT / "configurator" / "examples" / name).read_text())


def candidate(result, candidate_id):
    return next(row for row in result["candidates"] if row["id"] == candidate_id)


def test_compact_electric_visual_state_uses_twin_geometry_and_actual_layers():
    generated = generate_candidates(profile("trail_rider_profile.json"))
    row = candidate(generated, "x1_compact_electric_study")
    visual = visual_state_from_candidate(row)

    assert visual["scope"] == "candidate_preview"
    assert visual["deck"] == {
        "id": "comp95",
        "length_mm": 950.0,
        "width_mm": 251.0,
        "evidence_state": "REFERENCE",
    }
    assert visual["topology"] == {
        "id": "brake_hanger_70mm_topology_study",
        "truck_total_width_mm": 440.0,
        "wheel_center_lateral_mm": 185.0,
        "evidence_state": "ASSUMED",
    }
    assert visual["wheel"] == {
        "study_id": "TIRE-T1-8-REF",
        "diameter_mm": 194.0,
        "width_mm": 51.0,
        "visible": True,
    }
    assert visual["layers"] == {
        "brake": True,
        "drive": True,
        "pack": True,
        "snowdeck": True,
        "armor": True,
        "dock": False,
    }
    assert 260 <= visual["stance_mm"] <= 520
    assert visual["views"] == ["hero", "top", "side"]
    assert visual["authority"] == {
        "visualization_only": True,
        "procurement_authorized": False,
        "fabrication_authorized": False,
        "powered_operation_authorized": False,
    }


def test_candidate_preview_uses_bom_not_visual_preset_defaults():
    generated = generate_candidates(profile("trail_rider_profile.json"))
    row = candidate(generated, "brake_first_trail_core")
    visual = visual_state_from_candidate(row)

    # The historical showcase preset exposes an inert pack study, but this
    # generated candidate has no battery-class component in its BOM.
    assert visual["layers"]["pack"] is False
    assert visual["layers"]["brake"] is True
    assert visual["layers"]["drive"] is False
    assert visual["layers"]["armor"] is True


def test_range_explorer_visual_state_is_long_deck_drive_configuration():
    generated = generate_candidates(profile("trail_rider_profile.json"))
    row = candidate(generated, "drive_clearance_range_study")
    visual = visual_state_from_candidate(row)

    assert visual["deck"]["id"] == "agent"
    assert visual["deck"]["length_mm"] == 1020.0
    assert visual["deck"]["width_mm"] == 284.0
    assert visual["topology"]["id"] == "drive_clearance_420mm"
    assert visual["topology"]["truck_total_width_mm"] == 420.0
    assert visual["layers"]["drive"] is True
    assert visual["layers"]["brake"] is False
    assert visual["layers"]["pack"] is True
    assert visual["layers"]["dock"] is True


def test_fit_bench_visual_has_no_wheel_or_power_claim():
    generated = generate_candidates(profile("manual_carver_profile.json"))
    row = candidate(generated, "snowdeck_fit_bench")
    visual = visual_state_from_candidate(row)

    assert visual["wheel"]["study_id"] == "none"
    assert visual["wheel"]["visible"] is False
    assert visual["layers"]["drive"] is False
    assert visual["layers"]["pack"] is False
    assert visual["layers"]["snowdeck"] is True


def test_swap_visual_state_reflects_9in_incompatible_study():
    generated = generate_candidates(profile("trail_rider_profile.json"))
    baseline = candidate(generated, "x1_compact_electric_study")
    selection = json.loads(
        (ROOT / "configurator" / "examples" / "swap_incompatible_study.json").read_text()
    )
    swap = evaluate_swap(baseline, generated["requirements"], selection)
    visual = visual_state_from_swap(baseline, swap)

    assert visual["scope"] == "custom_swap_preview"
    assert visual["readiness"] == "INCOMPATIBLE"
    assert visual["topology"]["id"] == "drive_clearance_420mm"
    assert visual["wheel"] == {
        "study_id": "TIRE-T2-9",
        "diameter_mm": 219.0,
        "width_mm": 67.0,
        "visible": True,
    }
    assert visual["layers"]["brake"] is True
    assert visual["layers"]["drive"] is True
    assert visual["layers"]["pack"] is True
    assert visual["authority"]["powered_operation_authorized"] is False
