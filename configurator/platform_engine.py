"""Unified Board Builder design-space engine.

Curated architectures remain stable regression anchors. Catalog Composer v1 adds
bounded synthesized candidates without changing procurement or physical authority.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from configurator.composer import compose_candidates
from configurator.engine import READINESS_RANK, generate_candidates, load_bundle

ROOT = Path(__file__).resolve().parents[1]
COMPOSER_PATH = ROOT / "configurator" / "composer.v1.json"
SWAP_SLOTS_PATH = ROOT / "configurator" / "swap_slots.v1.json"
GEOMETRY_PATH = ROOT / "catalog" / "board_geometry.v1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_platform_bundle() -> dict[str, Any]:
    bundle = load_bundle()
    bundle.update(
        {
            "composer": _load(COMPOSER_PATH),
            "swapSlots": _load(SWAP_SLOTS_PATH),
            "geometry": _load(GEOMETRY_PATH),
        }
    )
    return bundle


def _bom_signature(candidate: dict[str, Any]) -> str:
    return "|".join(
        sorted(row["component_id"] for row in candidate.get("bom", []))
    )


def _non_dominated(candidates: list[dict[str, Any]]) -> set[str]:
    metrics = (
        "range",
        "carve",
        "stability",
        "durability",
        "portability",
        "cost",
        "low_maintenance",
    )
    frontier: set[str] = set()
    for candidate in candidates:
        dominated = False
        for other in candidates:
            if other is candidate:
                continue
            no_worse = all(
                float(other.get("traits", {}).get(metric, 0))
                >= float(candidate.get("traits", {}).get(metric, 0))
                for metric in metrics
            )
            better = any(
                float(other.get("traits", {}).get(metric, 0))
                > float(candidate.get("traits", {}).get(metric, 0))
                for metric in metrics
            )
            if no_worse and better:
                dominated = True
                break
        if not dominated:
            frontier.add(candidate["id"])
    return frontier


def generate_board_design_space(
    profile: dict[str, Any],
    bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = copy.deepcopy(bundle or load_platform_bundle())
    curated = generate_candidates(profile, bundle=data)

    for candidate in curated["candidates"]:
        candidate["origin"] = "CURATED"

    curated_signatures = {
        _bom_signature(candidate)
        for candidate in curated["candidates"]
    }
    # Exclude curated BOMs before synthesized ranking/capping to avoid wasting slots.
    unique_synthesized = compose_candidates(
        curated["profile"], curated["requirements"], data,
        excluded_commercial_boms=curated_signatures,
    )

    candidates = [
        *curated["candidates"],
        *unique_synthesized,
    ]
    candidates.sort(
        key=lambda candidate: (
            -candidate["fit_score"],
            READINESS_RANK[candidate["readiness"]],
            candidate["label"],
        )
    )

    frontier = _non_dominated(candidates)
    for candidate in candidates:
        candidate["trade_space_frontier"] = candidate["id"] in frontier

    return {
        **curated,
        "candidates": candidates,
        "composition_summary": {
            "schema_version": 1,
            "curated_count": len(curated["candidates"]),
            "synthesized_count": len(unique_synthesized),
            "total_count": len(candidates),
            "composer_enabled": bool(data.get("composer", {}).get("enabled")),
            "synthesized_candidate_cap": int(
                data.get("composer", {}).get("max_synthesized_candidates", 0)
            ),
        },
        "authority": {
            **curated["authority"],
            "generic_builder_may_promote_x1_authority": False,
            "procurement_authorized": False,
            "fabrication_authorized": False,
            "powered_operation_authorized": False,
        },
    }
