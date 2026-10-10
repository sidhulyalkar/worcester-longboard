"""Physical diversity and blocker gates for the non-authoritative shortlist."""
from __future__ import annotations

from configurator.diversity import build_diverse_shortlist, mechanical_signature


def make_candidate(name, deck, truck, wheel, brake, drive, score=.8, **changes):
    candidate = {
        "id": name, "label": name, "deck_candidate_id": deck,
        "topology_id": truck, "fit_score": score,
        "bom": [{"category": "wheel", "component_id": wheel}]
        + ([{"category": "brake", "component_id": brake}] if brake else [])
        + ([{"category": "drive", "component_id": drive}] if drive else []),
        "cost": {
            "known_min_usd": 400,
            "unpriced_component_ids": ["UNKNOWN-ELECTRICAL"],
        },
        "blockers": [], "compatibility_findings": [],
        "evidence": {"summary": {"open_interfaces": 2, "incompatible_interfaces": 0}},
    }
    candidate.update(changes)
    return candidate


a = make_candidate("a", "deck-a", "truck-x", "wheel-8", "brake-mech", None, .95)
b = make_candidate("b", "deck-b", "truck-y", "wheel-9", "brake-hydro", "belt", .80)
c = make_candidate("c", "deck-c", "truck-z", "wheel-8", "brake-hydro", "gear", .70)
same = make_candidate("same-topology", "deck-a", "truck-x", "wheel-8", "brake-mech", None, .92)


def test_diversity_no_visual_clones():
    report = build_diverse_shortlist([a, same, b, c], 1800)
    assert report["selected_ids"] == ["a", "b", "c"]
    assert {"deck", "truck"}.issubset(report["studies"][1]["differing_axes_from_first"])
    assert report["studies"][0]["unpriced_component_count"] == 1
    assert not any(report["authority"].values())


def test_blockers_and_hard_budget_never_disguised_as_viability():
    blocked = make_candidate("blocked", "deck-z", "truck-z", "wheel-9", "b", "d", .99,
                             blockers=["missing friction brake"])
    incompatible = make_candidate(
        "incompatible", "deck-x", "truck-x", "wheel-9", "b", "d", .98,
        compatibility_findings=[{"state": "INCOMPATIBLE"}]
    )
    over = make_candidate(
        "over", "deck-w", "truck-w", "wheel-9", "b", "d", .97,
        cost={"known_min_usd": 2300, "unpriced_component_ids": []}
    )
    report = build_diverse_shortlist([blocked, incompatible, over, a, b, c], 1200)
    assert report["selected_ids"] == ["a", "b", "c"]
    assert [row["reason"] for row in report["excluded"][:3]] == [
        "HARD_MECHANICAL_OR_MISSION_BLOCKER",
        "INCOMPATIBLE_INTERFACE",
        "KNOWN_COMPONENT_COST_EXCEEDS_HARD_BUDGET",
    ]


def test_insufficient_diversity_is_explicit():
    report = build_diverse_shortlist([a, same], 1200)
    assert report["selected_ids"] == ["a"]
    assert report["shortage_reason"].startswith("Only 1 mechanically distinct")
    assert report["eligible_count"] == 2


def test_catalog_slot_identity_and_no_qualification():
    composed = {
        **a, "composition": {"selection": {
            "deck": "d", "truck": "t", "wheel": "catalog-wheel",
            "brake": None, "drive": "catalog-drive",
        }}
    }
    signature = mechanical_signature(composed)
    assert signature["wheel"] == "catalog-wheel"
    assert signature["drive"] == "catalog-drive"
    assert signature["deck"] == "deck-a"
    assert not any(build_diverse_shortlist([composed])["authority"].values())
