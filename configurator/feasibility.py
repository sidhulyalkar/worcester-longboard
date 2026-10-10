"""Explanatory feasibility receipts; never an X1 physical-authority input."""
from __future__ import annotations

import math
from typing import Any

AUTHORITY = {
    "procurement_authorized": False,
    "fabrication_authorized": False,
    "charging_authorized": False,
    "powered_operation_authorized": False,
    "generic_builder_may_promote_x1_authority": False,
}
COST_INSTRUCTION = (
    "Confirm exact supplier variants and quotations; known parts exclude shipping, "
    "tax, tools, specialist labor and validation."
)
PHYSICAL_INSTRUCTION = (
    "Obtain independent exact-revision fit, braking, structural and electrical "
    "qualification before any physical release."
)
REASON_LABELS = {
    "HARD_MECHANICAL_OR_MISSION_BLOCKER": "Blocked by a recorded mechanical or mission requirement",
    "INCOMPATIBLE_INTERFACE": "Recorded component interface incompatibility",
    "KNOWN_COMPONENT_COST_EXCEEDS_HARD_BUDGET": "Known parts already exceed the stated maximum",
    "NOT_SELECTED_OR_INSUFFICIENT_MECHANICAL_DIVERSITY": "Not included in a mechanically distinct three-way sample",
    "DUPLICATE_ID": "Duplicate candidate identity",
    "INVALID_PLANNING_CANDIDATE": "Invalid candidate source record",
}


def _numeric(value: Any) -> int | float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return value
    return None


def build_feasibility_report(
    candidates: list[dict[str, Any]], shortlist: dict[str, Any],
    hard_budget_usd: int | float | None = None,
) -> dict[str, Any]:
    if not isinstance(candidates, list) or shortlist.get("scope") != "non_authoritative_diverse_board_shortlist":
        raise ValueError("Feasibility requires candidates and a valid diverse shortlist")
    hard_budget = _numeric(hard_budget_usd)
    selected = set(shortlist.get("selected_ids") or [])
    omitted = {row["id"]: row["reason"] for row in shortlist.get("excluded", [])}
    records = []
    for candidate in sorted(candidates, key=lambda row: str(row["id"])):
        blockers = sorted(set(map(str, candidate.get("blockers") or [])))
        incompatible_pairs = sum(
            row.get("state") == "INCOMPATIBLE"
            for row in candidate.get("compatibility_findings") or []
        )
        summary = (candidate.get("evidence") or {}).get("summary") or {}
        incompatible = max(incompatible_pairs, _numeric(summary.get("incompatible_interfaces")) or 0)
        unresolved = _numeric(summary.get("open_interfaces")) or 0
        sources = _numeric(summary.get("source_refresh_or_integrity_issues")) or 0
        unpriced = len((candidate.get("cost") or {}).get("unpriced_component_ids") or [])
        known_min = _numeric((candidate.get("cost") or {}).get("known_min_usd"))
        above_budget = hard_budget is not None and known_min is not None and known_min > hard_budget
        blocked = bool(blockers) or incompatible > 0 or candidate.get("readiness") == "BLOCKED" or above_budget
        issues = []
        if blockers: issues.append("RECORDED_HARD_BLOCKER")
        if incompatible > 0: issues.append("INCOMPATIBLE_COMPONENT_INTERFACES")
        if candidate.get("readiness") == "BLOCKED": issues.append("CATALOG_READINESS_BLOCKED")
        if above_budget: issues.append("KNOWN_MINIMUM_PARTS_ABOVE_BUDGET")
        if unresolved > 0: issues.append("UNRESOLVED_INTERFACE_EVIDENCE")
        if sources > 0: issues.append("SOURCE_EVIDENCE_REFRESH_REQUIRED")
        if unpriced > 0: issues.append("UNPRICED_COMPONENTS")
        next_steps = []
        if blockers or candidate.get("readiness") == "BLOCKED":
            next_steps.append("Resolve the documented mission or mechanical blocker; do not fabricate or purchase from this proposal.")
        if incompatible > 0:
            next_steps.append("Select a documented compatible interface and re-evaluate; an improvised adapter is not a qualification.")
        if above_budget:
            next_steps.append("Revise the parts budget or compare other sourced families; current known minimum already exceeds the limit.")
        if unresolved > 0:
            next_steps.append("Measure exact-revision hub, axle, brake, drive and mount interfaces where flagged in the worklist.")
        if sources > 0:
            next_steps.append("Refresh dated manufacturer evidence for affected component variants.")
        next_steps.extend((COST_INSTRUCTION, PHYSICAL_INSTRUCTION))
        reason = omitted.get(candidate["id"])
        records.append({
            "candidate_id": candidate["id"],
            "result": "BLOCKED" if blocked else "UNRESOLVED_STUDY" if issues else "PLANNING_STUDY",
            "shortlist_role": "DIVERSITY_SELECTED" if candidate["id"] in selected else "NOT_IN_SHORTLIST",
            "shortlist_exclusion_reason": reason,
            "shortlist_exclusion_explanation": REASON_LABELS.get(reason, "Not selected by the shortlist policy") if reason else None,
            "mechanical": {
                "explicit_blockers": blockers,
                "incompatible_interfaces": incompatible,
                "unresolved_interfaces": unresolved,
                "source_followups": sources,
            },
            "cost": {
                "stated_hard_budget_usd": hard_budget,
                "known_minimum_parts_usd": known_min,
                "unpriced_component_count": unpriced,
                "known_minimum_already_over_budget": above_budget,
                "all_in_budget_status": "UNKNOWN_REQUIRES_QUOTES_AND_INTEGRATION_COST",
            },
            "issues": sorted(set(issues)),
            "next_steps": sorted(set(next_steps)),
            "physical_qualification_status": "NOT_QUALIFIED",
            "authority": dict(AUTHORITY),
        })
    return {
        "schema_version": 1,
        "scope": "non_authoritative_board_feasibility_receipts",
        "candidate_count": len(records),
        "blocked_count": sum(row["result"] == "BLOCKED" for row in records),
        "unresolved_study_count": sum(row["result"] == "UNRESOLVED_STUDY" for row in records),
        "records": records,
        "note": "A feasibility receipt explains planning constraints; it is not proof of structural fit, brake performance, sourcing completeness or safe operation.",
        "authority": dict(AUTHORITY),
    }
