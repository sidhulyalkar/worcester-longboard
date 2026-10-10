"""Feasibility receipts classify known hard stops separately from unknown evidence."""
from configurator.feasibility import build_feasibility_report


def make(name, **overrides):
    row = {
        "id": name, "label": name, "fit_score": .8,
        "readiness": "REFERENCE_COMPATIBLE", "blockers": [],
        "compatibility_findings": [],
        "cost": {"known_min_usd": 550, "unpriced_component_ids": ["battery-study"]},
        "evidence": {"summary": {
            "incompatible_interfaces": 0, "open_interfaces": 2,
            "source_refresh_or_integrity_issues": 1,
        }},
    }
    row.update(overrides)
    return row


shortlist = {
    "schema_version": 1,
    "scope": "non_authoritative_diverse_board_shortlist",
    "selected_ids": ["a"],
    "excluded": [
        {"id": "b", "reason": "KNOWN_COMPONENT_COST_EXCEEDS_HARD_BUDGET"},
        {"id": "c", "reason": "NOT_SELECTED_OR_INSUFFICIENT_MECHANICAL_DIVERSITY"},
    ],
}


def test_incomplete_cost_is_not_a_fully_qualified_budget():
    result = build_feasibility_report([make("a")], shortlist, 1500)
    row = result["records"][0]
    assert row["result"] == "UNRESOLVED_STUDY"
    assert row["shortlist_role"] == "DIVERSITY_SELECTED"
    assert row["cost"]["all_in_budget_status"] == "UNKNOWN_REQUIRES_QUOTES_AND_INTEGRATION_COST"
    assert not row["cost"]["known_minimum_already_over_budget"]
    assert "independent exact-revision" in " ".join(row["next_steps"])
    assert not any(result["authority"].values())


def test_over_limit_known_cost_is_hard_conflict():
    row = build_feasibility_report(
        [make("b", cost={"known_min_usd": 1800, "unpriced_component_ids": []})],
        shortlist, 1400,
    )["records"][0]
    assert row["result"] == "BLOCKED"
    assert row["cost"]["known_minimum_already_over_budget"]
    assert row["shortlist_exclusion_reason"] == "KNOWN_COMPONENT_COST_EXCEEDS_HARD_BUDGET"


def test_mechanical_conflict_independent_of_source_and_budget():
    row = build_feasibility_report([
        make("c", blockers=["Independent friction brake not qualified"],
             compatibility_findings=[{"state": "INCOMPATIBLE"}],
             readiness="BLOCKED")
    ], shortlist, 1500)["records"][0]
    assert row["result"] == "BLOCKED"
    assert row["mechanical"]["incompatible_interfaces"] == 1
    assert "SOURCE_EVIDENCE_REFRESH_REQUIRED" in row["issues"]
    assert row["physical_qualification_status"] == "NOT_QUALIFIED"


def test_no_uncertainty_does_not_create_physical_authority():
    row = build_feasibility_report([
        make("a", cost={"known_min_usd": 500, "unpriced_component_ids": []},
             evidence={"summary": {
                 "incompatible_interfaces": 0, "open_interfaces": 0,
                 "source_refresh_or_integrity_issues": 0,
             }})
    ], shortlist, 2000)["records"][0]
    assert row["result"] == "PLANNING_STUDY"
    assert row["physical_qualification_status"] == "NOT_QUALIFIED"
    assert not any(row["authority"].values())
    assert row["cost"]["all_in_budget_status"] == "UNKNOWN_REQUIRES_QUOTES_AND_INTEGRATION_COST"


def test_deterministic_no_input_mutation_and_rejected_invalid_scope():
    inputs = [make("b"), make("a")]
    output = build_feasibility_report(inputs, shortlist)
    assert [row["candidate_id"] for row in output["records"]] == ["a", "b"]
    assert inputs[0]["id"] == "b"
    import pytest
    with pytest.raises(ValueError):
        build_feasibility_report(inputs, {"scope": "checkout_ready"})
