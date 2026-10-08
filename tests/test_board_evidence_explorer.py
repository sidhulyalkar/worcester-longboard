"""Regression tests for read-only Catalog Composer v1.1 evidence contracts."""
import copy
import json
from pathlib import Path

from configurator.evidence_explorer import build_evidence_explorer
from configurator.platform_engine import generate_board_design_space, load_platform_bundle
from configurator.swap_lab import evaluate_swap

ROOT = Path(__file__).resolve().parents[1]


def rider(name):
    return json.loads((ROOT / "configurator" / "examples" / name).read_text())


def test_every_curated_and_composed_candidate_has_non_authoritative_evidence():
    bundle = load_platform_bundle()
    for profile in ("trail_rider_profile.json", "manual_carver_profile.json"):
        result = generate_board_design_space(rider(profile), bundle=bundle)
        assert any(c["origin"] == "SYNTHESIZED" for c in result["candidates"])
        for c in result["candidates"]:
            e = c["evidence"]
            assert e["candidate_id"] == c["id"]
            assert e["scope"] == "non_authoritative_catalog_evidence_explorer"
            assert not any(e["authority"].values())
            assert e["readiness"] == c["readiness"]
            assert e["checkout_state"] == c["checkout_state"]
            assert e["price_basis"] == "KNOWN_USD_SUBTOTAL_ONLY"
            assert e["score_basis"] == "PLANNING_PREFERENCE_NOT_SAFETY"
            assert e["summary"]["open_interfaces"] == len(e["measurement_worklist"])
            assert e["summary"]["incompatible_interfaces"] == sum(
                f["state"] == "INCOMPATIBLE" for f in e["interfaces"]
            )
            assert e["summary"]["unpriced_items"] == len(e["unpriced_component_ids"])
            assert e["summary"]["price_complete"] == (not e["unpriced_component_ids"])
            assert all(f["sources"] for f in e["interfaces"])
            assert all(
                f["evidence_kind"] in {
                    "CONSERVATIVE_CATEGORY_FALLBACK", "EXPLICIT_CATALOG_RULE"
                } for f in e["interfaces"]
            )
            if c["origin"] == "SYNTHESIZED":
                assert e["summary"]["physical_basis"] == "EXPANDED_COMPONENT_GRAPH"
            else:
                assert e["summary"]["physical_basis"] == "REFERENCE_BOM_ONLY"


def test_trampa_boardnamics_unknown_gets_measurement_worklist_not_qualification():
    data = generate_board_design_space(rider("trail_rider_profile.json"))
    c = next(c for c in data["candidates"] if c["id"] == "trampa_boardnamics_coexistence")
    e = c["evidence"]
    finding = next(f for f in e["interfaces"] if f["category_pair"] == "drive:truck"
                   and f["state"] == "UNKNOWN")
    assert finding["evidence_kind"] == "CONSERVATIVE_CATEGORY_FALLBACK"
    task = next(t for t in e["measurement_worklist"] if t["id"] == finding["id"])
    assert "drive-mount geometry" in task["question"]
    assert "exact-revision" in task["evidence_required"]
    assert not any(e["authority"].values())
    assert e["checkout_state"] == "BLOCKED"


def test_mbs_packaged_donor_records_incompatible_internal_truck_drive():
    bundle = load_platform_bundle()
    result = generate_board_design_space(rider("trail_rider_profile.json"), bundle=bundle)
    baseline = result["candidates"][0]
    selection = {
        "deck": "comp95", "topology": "brake_first_400mm", "wheel": "TIRE-T1-8-REF",
        "brake": "BRAKE-V5", "drive": "DRIVE-G1-DUAL",
        "battery": "BATTERY-RANGE-CLASS", "rider_interface": None,
        "armor": None, "dock": None,
    }
    swap = evaluate_swap(
        baseline, result["requirements"], selection, bundle=bundle, slots=bundle["swapSlots"]
    )
    e = build_evidence_explorer({
        **swap, "id": "mbs:study",
        "composition": {"physical_interface_ids": swap["compatibility_interface_ids"]},
    }, bundle["catalog"], bundle["catalogHealth"])
    assert "TRUCK-M3-400" in {s["component_id"] for s in e["source_evidence"]}
    assert "TRUCK-M3-400" not in {r["component_id"] for r in swap["bom"]}
    assert any(f["id"] == "matrix400_g1_as_shipped" and f["state"] == "INCOMPATIBLE"
               for f in e["interfaces"])
    assert e["summary"]["incompatible_interfaces"] >= 1
    assert e["readiness"] == "INCOMPATIBLE"
    assert not any(e["authority"].values())


def test_source_health_cannot_promote_compatibility_or_authority():
    bundle = load_platform_bundle()
    c = next(c for c in generate_board_design_space(
        rider("trail_rider_profile.json"), bundle=bundle
    )["candidates"] if c["id"] == "trampa_boardnamics_coexistence")
    fresh = copy.deepcopy(bundle["catalogHealth"])
    for row in fresh["component_health"]:
        row["status"] = "SOURCE_FRESH"
    baseline = c["evidence"]
    changed = build_evidence_explorer(c, bundle["catalog"], fresh)
    assert baseline["measurement_worklist"] == changed["measurement_worklist"]
    assert baseline["readiness"] == changed["readiness"]
    assert baseline["checkout_state"] == changed["checkout_state"]
    assert not any(changed["authority"].values())
    # Without a loaded source-health registry, never call anything 'fresh'.
    missing = build_evidence_explorer(c, bundle["catalog"], None)
    assert all(row["health_status"] == "HEALTH_UNAVAILABLE"
               for row in missing["source_evidence"])
    assert missing["summary"]["source_refresh_or_integrity_issues"] == len(
        missing["source_evidence"]
    )
    assert not any(missing["authority"].values())


def test_evidence_stable_when_catalog_and_findings_are_reordered():
    bundle = load_platform_bundle()
    c = next(c for c in generate_board_design_space(
        rider("trail_rider_profile.json"), bundle=bundle
    )["candidates"] if c["id"] == "trampa_boardnamics_coexistence")
    reversed_catalog = copy.deepcopy(bundle["catalog"])
    reversed_catalog["components"].reverse()
    reversed_health = copy.deepcopy(bundle["catalogHealth"])
    reversed_health["component_health"].reverse()
    changed_candidate = copy.deepcopy(c)
    changed_candidate["compatibility_findings"].reverse()
    actual = build_evidence_explorer(
        changed_candidate, reversed_catalog, reversed_health
    )
    assert c["evidence"] == actual
