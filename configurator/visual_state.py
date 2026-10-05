"""Candidate visual-state derivation for Worcester Board Builder.

Visual states are deterministic projections of existing candidate/swap data into
the geometry contract used by the X1 digital twin. They are visualization only.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TWIN_SEED_PATH = ROOT / "showcase" / "x1_rev_c.json"
CATALOG_PATH = ROOT / "catalog" / "board_components.v1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_visual_sources() -> tuple[dict[str, Any], dict[str, Any]]:
    return _load(TWIN_SEED_PATH), _load(CATALOG_PATH)


def _indices(
    twin_seed: dict[str, Any],
    catalog: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    studies = twin_seed["design_studies"]
    decks = {row["id"]: row for row in studies["deck_candidates"]}
    topologies = {row["id"]: row for row in studies["topology_branches"]}
    components = {row["id"]: row for row in catalog["components"]}
    return decks, topologies, components


def _wheel_state(
    wheel_id: str | None,
    components: dict[str, Any],
) -> dict[str, Any]:
    if not wheel_id:
        return {
            "study_id": "none",
            "diameter_mm": 0,
            "width_mm": 0,
            "visible": False,
        }

    if wheel_id == "TIRE-T1-8-REF":
        component = components[wheel_id]
        interface = component["interfaces"]
        return {
            "study_id": wheel_id,
            "diameter_mm": float(interface["measured_reference_diameter_mm"]),
            "width_mm": float(interface["measured_reference_width_mm"]),
            "visible": True,
        }

    if wheel_id == "TIRE-T2-9":
        component = components[wheel_id]
        interface = component["interfaces"]
        return {
            "study_id": wheel_id,
            "diameter_mm": float(interface["published_diameter_mm"]),
            "width_mm": float(interface["published_width_mm"]),
            "visible": True,
        }

    raise ValueError(f"unsupported visual wheel study {wheel_id!r}")


def _candidate_wheel_id(candidate: dict[str, Any]) -> str | None:
    bom_ids = {row["component_id"] for row in candidate.get("bom", [])}
    if "TIRE-T2-9" in bom_ids:
        return "TIRE-T2-9"
    if candidate.get("capabilities", {}).get("wheel_class") == "8in_pneumatic":
        return "TIRE-T1-8-REF"
    return None


def _layers_from_component_ids(component_ids: set[str]) -> dict[str, bool]:
    return {
        "brake": "BRAKE-V5" in component_ids,
        "drive": "DRIVE-G1-DUAL" in component_ids,
        "pack": bool(
            {"BATTERY-TRAIL-CLASS", "BATTERY-RANGE-CLASS"} & component_ids
        ),
        "snowdeck": "SNOWDECK-V01-CUSTOM" in component_ids,
        "armor": "TRAIL-ARMOR-STUDY" in component_ids,
        "dock": "PASSIVE-DOCK-STUDY" in component_ids,
    }


def _base_visual_state(
    *,
    scope: str,
    subject_id: str,
    label: str,
    deck_id: str,
    topology_id: str,
    wheel_id: str | None,
    stance_mm: float | int | None,
    layers: dict[str, bool],
    readiness: str,
    checkout_state: str,
    fit_score: float | None,
    cost: dict[str, Any],
    twin_seed: dict[str, Any],
    catalog: dict[str, Any],
) -> dict[str, Any]:
    decks, topologies, components = _indices(twin_seed, catalog)

    if deck_id not in decks:
        raise ValueError(f"unknown visual deck candidate {deck_id!r}")
    if topology_id not in topologies:
        raise ValueError(f"unknown visual topology {topology_id!r}")

    deck = decks[deck_id]
    topology = topologies[topology_id]

    stance = None if stance_mm is None else float(stance_mm)
    if stance is not None and not 260 <= stance <= 520:
        raise ValueError(f"visual stance {stance} outside 260..520 mm study bounds")

    return {
        "schema_version": 1,
        "scope": scope,
        "subject_id": subject_id,
        "label": label,
        "deck": {
            "id": deck_id,
            "length_mm": float(deck["length_mm"]),
            "width_mm": float(deck["width_mm"]),
            "evidence_state": deck["evidence_state"],
        },
        "topology": {
            "id": topology_id,
            "truck_total_width_mm": float(topology["truck_total_width_mm"]),
            "wheel_center_lateral_mm": float(topology["wheel_center_lateral_mm"]),
            "evidence_state": topology["evidence_state"],
        },
        "wheel": _wheel_state(wheel_id, components),
        "stance_mm": stance,
        "layers": {
            key: bool(layers.get(key, False))
            for key in ("brake", "drive", "pack", "snowdeck", "armor", "dock")
        },
        "readiness": readiness,
        "checkout_state": checkout_state,
        "fit_score": None if fit_score is None else float(fit_score),
        "cost": copy.deepcopy(cost),
        "views": ["hero", "top", "side"],
        "authority": {
            "visualization_only": True,
            "procurement_authorized": False,
            "fabrication_authorized": False,
            "powered_operation_authorized": False,
        },
    }


def visual_state_from_candidate(
    candidate: dict[str, Any],
    *,
    twin_seed: dict[str, Any] | None = None,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if twin_seed is None or catalog is None:
        loaded_twin, loaded_catalog = load_visual_sources()
        twin_seed = twin_seed or loaded_twin
        catalog = catalog or loaded_catalog

    component_ids = {row["component_id"] for row in candidate.get("bom", [])}
    stance = candidate.get("personalized_spec", {}).get("stance_center_mm")

    return _base_visual_state(
        scope="candidate_preview",
        subject_id=candidate["id"],
        label=candidate["label"],
        deck_id=candidate["deck_candidate_id"],
        topology_id=candidate["topology_id"],
        wheel_id=_candidate_wheel_id(candidate),
        stance_mm=stance,
        layers=_layers_from_component_ids(component_ids),
        readiness=candidate["readiness"],
        checkout_state=candidate["checkout_state"],
        fit_score=candidate.get("fit_score"),
        cost=candidate["cost"],
        twin_seed=twin_seed,
        catalog=catalog,
    )


def visual_state_from_swap(
    baseline_candidate: dict[str, Any],
    swap_result: dict[str, Any],
    *,
    twin_seed: dict[str, Any] | None = None,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if twin_seed is None or catalog is None:
        loaded_twin, loaded_catalog = load_visual_sources()
        twin_seed = twin_seed or loaded_twin
        catalog = catalog or loaded_catalog

    twin_state = swap_result["twin_state"]
    selection = swap_result["selection"]

    return _base_visual_state(
        scope="custom_swap_preview",
        subject_id=f"custom:{baseline_candidate['id']}",
        label=f"{baseline_candidate['label']} · Custom",
        deck_id=twin_state["deck_candidate_id"],
        topology_id=twin_state["topology_id"],
        wheel_id=selection.get("wheel"),
        stance_mm=twin_state.get("stance_mm"),
        layers=twin_state["layers"],
        readiness=swap_result["readiness"],
        checkout_state=swap_result["checkout_state"],
        fit_score=None,
        cost=swap_result["cost"],
        twin_seed=twin_seed,
        catalog=catalog,
    )
