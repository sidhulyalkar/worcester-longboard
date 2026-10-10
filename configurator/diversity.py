"""Deterministic, non-authoritative diverse planning shortlist (JS parity)."""
from __future__ import annotations

from typing import Any

AXES = ("deck", "truck", "wheel", "brake", "drive")
AUTHORITY = {
    "procurement_authorized": False,
    "fabrication_authorized": False,
    "charging_authorized": False,
    "powered_operation_authorized": False,
    "generic_builder_may_promote_x1_authority": False,
}


def _as_id(value: Any) -> str:
    return "UNKNOWN" if value is None or value == "" else str(value)


def _category_part(candidate: dict[str, Any], category: str) -> str | None:
    ids = sorted(
        row["component_id"] for row in candidate.get("bom", [])
        if row.get("category") == category and row.get("component_id")
    )
    return "+".join(ids) if ids else None


def mechanical_signature(candidate: dict[str, Any]) -> dict[str, str]:
    selected = candidate.get("composition", {}).get("selection") or candidate.get(
        "swap_defaults"
    ) or {}
    capabilities = candidate.get("capabilities") or {}
    return {
        "deck": _as_id(candidate.get("deck_candidate_id") or selected.get("deck")),
        "truck": _as_id(candidate.get("topology_id") or selected.get("truck")),
        "wheel": _as_id(
            selected.get("wheel") or _category_part(candidate, "wheel")
            or capabilities.get("wheel_class")
        ),
        "brake": _as_id(
            selected.get("brake") or _category_part(candidate, "brake")
            or "NOT_SPECIFIED"
        ),
        "drive": _as_id(
            selected.get("drive") or _category_part(candidate, "drive")
            or "NOT_SPECIFIED"
        ),
    }


def _difference(a: dict[str, str], b: dict[str, str]) -> list[str]:
    return [axis for axis in AXES if a[axis] != b[axis]]


def _materially_distinct(a: dict[str, str], b: dict[str, str]) -> bool:
    differences = _difference(a, b)
    return len(differences) >= 2 and ("deck" in differences or "truck" in differences)


def _exclusion(candidate: dict[str, Any], hard_budget: float | None) -> str | None:
    if not isinstance(candidate, dict) or not candidate.get("id") or not isinstance(
        candidate.get("fit_score"), (int, float)
    ):
        return "INVALID_PLANNING_CANDIDATE"
    if candidate.get("blockers"):
        return "HARD_MECHANICAL_OR_MISSION_BLOCKER"
    if any(
        row.get("state") == "INCOMPATIBLE"
        for row in candidate.get("compatibility_findings", [])
    ) or (candidate.get("evidence", {}).get("summary", {}).get(
        "incompatible_interfaces", 0
    ) or 0) > 0:
        return "INCOMPATIBLE_INTERFACE"
    known_min = (candidate.get("cost") or {}).get("known_min_usd")
    if hard_budget is not None and isinstance(known_min, (int, float)) and (
        known_min > hard_budget
    ):
        return "KNOWN_COMPONENT_COST_EXCEEDS_HARD_BUDGET"
    return None


def build_diverse_shortlist(
    candidates: list[dict[str, Any]], hard_budget_usd: float | None = None,
    limit: int = 3,
) -> dict[str, Any]:
    if not isinstance(candidates, list):
        raise ValueError("Candidates must be a list")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 5:
        raise ValueError("Invalid shortlist size")
    budget = float(hard_budget_usd) if isinstance(hard_budget_usd, (int, float)) else None
    viable: list[tuple[dict[str, Any], dict[str, str]]] = []
    excluded: list[dict[str, str]] = []
    seen: set[str] = set()
    # Do not inherit presentation/locale label ordering from the JS/Python
    # candidate engines. Compare by the same numeric fit and stable ID.
    def sorting_key(candidate: dict[str, Any]) -> tuple[float, str]:
        score = candidate.get("fit_score") if isinstance(candidate, dict) else None
        numeric = score if isinstance(score, (int, float)) and not isinstance(score, bool) else -1
        return (-numeric, str(candidate.get("id") or "") if isinstance(candidate, dict) else "")

    ordered = sorted(candidates, key=sorting_key)
    for candidate in ordered:
        candidate_id = candidate.get("id") if isinstance(candidate, dict) else None
        if candidate_id and candidate_id in seen:
            excluded.append({"id": candidate_id, "reason": "DUPLICATE_ID"})
            continue
        if candidate_id:
            seen.add(candidate_id)
        why = _exclusion(candidate, budget)
        if why:
            excluded.append({"id": candidate_id or "UNKNOWN", "reason": why})
        else:
            viable.append((candidate, mechanical_signature(candidate)))

    chosen = viable[:1]
    while len(chosen) < limit:
        eligible = [
            row for row in viable if all(
                row[0]["id"] != previous[0]["id"]
                and _materially_distinct(row[1], previous[1])
                for previous in chosen
            )
        ]
        if not eligible:
            break

        def novelty(row: tuple[dict[str, Any], dict[str, str]]) -> int:
            return sum(
                (2 if key in ("deck", "truck") else 1)
                for key in AXES
                if not any(previous[1][key] == row[1][key] for previous in chosen)
            )

        chosen.append(max(eligible, key=novelty))

    selected_ids = {row[0]["id"] for row in chosen}
    studies = [
        {
            "id": candidate["id"],
            "mechanical_signature": signature,
            "differing_axes_from_first": (
                _difference(chosen[0][1], signature) if index else []
            ),
            "open_interfaces": int(
                (candidate.get("evidence") or {}).get("summary", {}).get(
                    "open_interfaces", 0
                ) or 0
            ),
            "unpriced_component_count": len(
                (candidate.get("cost") or {}).get("unpriced_component_ids") or []
            ),
            "known_parts_cost_min_usd": (candidate.get("cost") or {}).get(
                "known_min_usd"
            ),
            "evidence_state": "PLANNING_STUDY_NOT_PHYSICALLY_QUALIFIED",
        }
        for index, (candidate, signature) in enumerate(chosen)
    ]
    excluded.extend(
        {"id": candidate["id"], "reason": "NOT_SELECTED_OR_INSUFFICIENT_MECHANICAL_DIVERSITY"}
        for candidate, _ in viable if candidate["id"] not in selected_ids
    )
    return {
        "schema_version": 1,
        "scope": "non_authoritative_diverse_board_shortlist",
        "target_count": limit,
        "considered_count": len(candidates),
        "eligible_count": len(viable),
        "selected_ids": [candidate["id"] for candidate, _ in chosen],
        "studies": studies,
        "excluded": excluded,
        "shortage_reason": (
            "Only " + str(len(chosen)) +
            " mechanically distinct, non-hard-blocked planning studies satisfy the shortlist rules. Check exclusions and unresolved interfaces."
            if len(chosen) < limit else None
        ),
        "interpretation": (
            "Different mechanical concepts for comparison, not verified assemblies, "
            "compatible kits, complete quotes or safe ride recommendations."
        ),
        "authority": dict(AUTHORITY),
    }
