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
    assert visual["deck"]["id"] == "comp95"
    assert visual["deck"]["length_mm"] == 950.0
    assert visual["deck"]["width_mm"] == 251.0
    assert visual["deck"]["shape_family"] == "mbs_powerlam"
    assert visual["deck"]["evidence_state"] == "REFERENCE"
    assert visual["topology"]["id"] == "brake_hanger_70mm_topology_study"
    assert visual["topology"]["truck_total_width_mm"] == 440.0
    assert visual["topology"]["wheel_center_lateral_mm"] == 185.0
    assert visual["topology"]["steering_family"] == "channel_spring"
    assert visual["topology"]["evidence_state"] == "ASSUMED"
    assert visual["wheel"]["study_id"] == "TIRE-T1-8-REF"
    assert visual["wheel"]["diameter_mm"] == 194.0
    assert visual["wheel"]["width_mm"] == 51.0
    assert visual["wheel"]["visible"] is True
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
    assert visual["wheel"]["study_id"] == "TIRE-T2-9"
    assert visual["wheel"]["diameter_mm"] == 219.0
    assert visual["wheel"]["width_mm"] == 67.0
    assert visual["wheel"]["visible"] is True
    assert visual["layers"]["brake"] is True
    assert visual["layers"]["drive"] is True
    assert visual["layers"]["pack"] is True
    assert visual["authority"]["powered_operation_authorized"] is False


def test_trampa_visuals_use_normalized_vendor_geometry_and_styles():
    generated = generate_candidates(profile("manual_carver_profile.json"))
    carve = candidate(generated, "trampa_short_carve_core")
    hydraulic = candidate(generated, "trampa_hydraulic_freeride")

    carve_visual = visual_state_from_candidate(carve)
    hydraulic_visual = visual_state_from_candidate(hydraulic)

    assert carve_visual["vendor_family"] == "TRAMPA"
    assert carve_visual["deck"]["id"] == "trampa_short_969"
    assert carve_visual["deck"]["length_mm"] == 895.0
    assert carve_visual["deck"]["shape_family"] == "trampa_composite"
    assert carve_visual["topology"]["steering_family"] == "channel_spring"
    assert carve_visual["wheel"]["study_id"] == "WHEEL-TRAMPA-ALPHA8"
    assert carve_visual["wheel"]["diameter_mm"] == 203.2

    assert hydraulic_visual["visual_style"]["brake_family"] == "trampa_magura_hs11"
    assert hydraulic_visual["layers"]["brake"] is True


def test_apex_and_obd_visuals_expose_different_mechanical_families():
    generated = generate_candidates(profile("trail_rider_profile.json"))
    apex = visual_state_from_candidate(candidate(generated, "apex_m1at_rough_study"))
    obd = visual_state_from_candidate(
        candidate(generated, "trampa_obd_9in_power_study")
    )

    assert apex["visual_style"]["steering_family"] == "parallel_kingpin"
    assert apex["visual_style"]["drive_type"] == "gear"
    assert obd["visual_style"]["drive_type"] == "open_belt"
    assert obd["wheel"]["study_id"] == "WHEEL-TRAMPA-MEGASTAR9"
    assert obd["wheel"]["diameter_mm"] == 230.0
