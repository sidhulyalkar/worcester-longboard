"""Deterministic multi-vendor visual-state derivation.

Visual states are comparison projections of normalized catalog geometry.
They never create procurement, fabrication, charging, or ride authority.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GEOMETRY_PATH = ROOT / "catalog" / "board_geometry.v1.json"
CATALOG_PATH = ROOT / "catalog" / "board_components.v1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_visual_sources() -> tuple[dict[str, Any], dict[str, Any]]:
    return _load(GEOMETRY_PATH), _load(CATALOG_PATH)


def _indices(
    geometry: dict[str, Any],
    catalog: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    decks = {row["id"]: row for row in geometry.get("decks", [])}
    topologies = {row["id"]: row for row in geometry.get("topologies", [])}
    components = {row["id"]: row for row in catalog["components"]}
    return decks, topologies, components


def _first_interface(
    interfaces: dict[str, Any],
    keys: tuple[str, ...],
    fallback: Any = None,
) -> Any:
    for key in keys:
        value = interfaces.get(key)
        if value is not None:
            return value
    return fallback


def _wheel_state(
    wheel_id: str | None,
    components: dict[str, Any],
) -> dict[str, Any]:
    if not wheel_id:
        return {
            "study_id": "none",
            "manufacturer": None,
            "wheel_class": "none",
            "hub_family": None,
            "diameter_mm": 0.0,
            "width_mm": 0.0,
            "visible": False,
        }

    component = components.get(wheel_id)
    if component is None:
        raise ValueError(f"unknown visual wheel component {wheel_id!r}")
    interface = component.get("interfaces") or {}
    diameter = float(
        _first_interface(
            interface,
            ("measured_reference_diameter_mm", "published_diameter_mm"),
            0,
        )
    )
    width = float(
        _first_interface(
            interface,
            ("measured_reference_width_mm", "published_width_mm"),
            0,
        )
    )
    if diameter <= 0 or width <= 0:
        raise ValueError(
            f"visual wheel component lacks normalized diameter/width {wheel_id!r}"
        )

    hub_family = interface.get("hub_family")
    if hub_family is None and wheel_id == "TIRE-T1-8-REF":
        hub_family = "rockstar_ii"
    if hub_family is None and wheel_id == "TIRE-T2-9":
        hub_family = "multi_hub_measure_first"

    return {
        "study_id": wheel_id,
        "manufacturer": component.get("manufacturer"),
        "wheel_class": interface.get("wheel_class", "pneumatic"),
        "hub_family": hub_family,
        "diameter_mm": diameter,
        "width_mm": width,
        "visible": True,
    }


def _candidate_wheel_id(candidate: dict[str, Any]) -> str | None:
    wheel_row = next(
        (row for row in candidate.get("bom", []) if row.get("category") == "wheel"),
        None,
    )
    if wheel_row:
        return wheel_row["component_id"]
    wheel_class = candidate.get("capabilities", {}).get("wheel_class")
    if wheel_class == "8in_pneumatic":
        return "TIRE-T1-8-REF"
    if wheel_class == "9in_pneumatic":
        return "TIRE-T2-9"
    return None


def _layers_from_bom(rows: list[dict[str, Any]]) -> dict[str, bool]:
    categories = {row.get("category") for row in rows}
    return {
        "brake": "brake" in categories,
        "drive": "drive" in categories,
        "pack": "battery" in categories,
        "snowdeck": "rider_interface" in categories,
        "armor": "armor" in categories,
        "dock": "dock" in categories,
    }


def _selected_component(
    rows: list[dict[str, Any]],
    category: str,
    components: dict[str, Any],
) -> dict[str, Any] | None:
    row = next((item for item in rows if item.get("category") == category), None)
    return components.get(row["component_id"]) if row else None


def _visual_style(
    deck: dict[str, Any],
    topology: dict[str, Any],
    wheel: dict[str, Any],
    brake: dict[str, Any] | None,
    drive: dict[str, Any] | None,
) -> dict[str, str]:
    brake_family = "none"
    if brake:
        brake_family = (
            (brake.get("interfaces") or {}).get("brake_family")
            or ("mbs_v5_mechanical" if brake["id"] == "BRAKE-V5" else "friction_brake")
        )

    drive_type = "none"
    if drive:
        drive_type = (
            (drive.get("interfaces") or {}).get("drive_type")
            or ("gear" if drive["id"] == "DRIVE-G1-DUAL" else "drive")
        )

    return {
        "deck_shape": deck.get("shape_family", "generic_mountainboard"),
        "steering_family": topology.get("steering_family", "generic"),
        "wheel_family": wheel.get("hub_family") or wheel.get("wheel_class") or "none",
        "brake_family": brake_family,
        "drive_type": drive_type,
    }


def _base_visual_state(
    *,
    scope: str,
    subject_id: str,
    label: str,
    vendor_family: str,
    deck_id: str,
    topology_id: str,
    wheel_id: str | None,
    stance_mm: float | int | None,
    layers: dict[str, bool],
    brake_component: dict[str, Any] | str | None,
    drive_component: dict[str, Any] | str | None,
    readiness: str,
    checkout_state: str,
    fit_score: float | None,
    cost: dict[str, Any],
    geometry: dict[str, Any],
    catalog: dict[str, Any],
) -> dict[str, Any]:
    decks, topologies, components = _indices(geometry, catalog)
    if deck_id not in decks:
        raise ValueError(f"unknown visual deck candidate {deck_id!r}")
    if topology_id not in topologies:
        raise ValueError(f"unknown visual topology {topology_id!r}")

    deck = decks[deck_id]
    topology = topologies[topology_id]
    stance = None if stance_mm is None else float(stance_mm)
    if stance is not None and not 260 <= stance <= 520:
        raise ValueError(f"visual stance {stance} outside 260..520 mm study bounds")

    wheel = _wheel_state(wheel_id, components)

    def resolve_component(
        value: dict[str, Any] | str | None,
    ) -> dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, dict):
            component_id = value.get("component_id") or value.get("id")
        else:
            component_id = value
        return components.get(component_id)

    brake = resolve_component(brake_component)
    drive = resolve_component(drive_component)

    return {
        "schema_version": 1,
        "scope": scope,
        "subject_id": subject_id,
        "vendor_family": vendor_family or "Custom mix",
        "label": label,
        "deck": {
            "id": deck_id,
            "manufacturer": deck.get("manufacturer"),
            "length_mm": float(deck["length_mm"]),
            "width_mm": float(deck["width_mm"]),
            "wheelbase_mm": (
                None if deck.get("wheelbase_mm") is None else float(deck["wheelbase_mm"])
            ),
            "tip_angle_deg": (
                None if deck.get("tip_angle_deg") is None else float(deck["tip_angle_deg"])
            ),
            "shape_family": deck.get("shape_family", "generic_mountainboard"),
            "evidence_state": deck["evidence_state"],
        },
        "topology": {
            "id": topology_id,
            "manufacturer": topology.get("manufacturer"),
            "truck_total_width_mm": float(topology["truck_total_width_mm"]),
            "wheel_center_lateral_mm": float(topology["wheel_center_lateral_mm"]),
            "steering_family": topology.get("steering_family", "generic"),
            "axle_diameter_mm": (
                None
                if topology.get("axle_diameter_mm") is None
                else float(topology["axle_diameter_mm"])
            ),
            "evidence_state": topology["evidence_state"],
            "visual_geometry_state": topology.get("visual_geometry_state"),
        },
        "wheel": wheel,
        "stance_mm": stance,
        "layers": {
            key: bool(layers.get(key, False))
            for key in ("brake", "drive", "pack", "snowdeck", "armor", "dock")
        },
        "visual_style": _visual_style(deck, topology, wheel, brake, drive),
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
    geometry: dict[str, Any] | None = None,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if geometry is None or catalog is None:
        loaded_geometry, loaded_catalog = load_visual_sources()
        geometry = geometry or loaded_geometry
        catalog = catalog or loaded_catalog

    _, _, components = _indices(geometry, catalog)
    brake = _selected_component(candidate.get("bom", []), "brake", components)
    drive = _selected_component(candidate.get("bom", []), "drive", components)

    return _base_visual_state(
        scope="candidate_preview",
        subject_id=candidate["id"],
        label=candidate["label"],
        vendor_family=candidate.get("vendor_family", "Unspecified"),
        deck_id=candidate["deck_candidate_id"],
        topology_id=candidate["topology_id"],
        wheel_id=_candidate_wheel_id(candidate),
        stance_mm=candidate.get("personalized_spec", {}).get("stance_center_mm"),
        layers=_layers_from_bom(candidate.get("bom", [])),
        brake_component=brake,
        drive_component=drive,
        readiness=candidate["readiness"],
        checkout_state=candidate["checkout_state"],
        fit_score=candidate.get("fit_score"),
        cost=candidate["cost"],
        geometry=geometry,
        catalog=catalog,
    )


def visual_state_from_swap(
    baseline_candidate: dict[str, Any],
    swap_result: dict[str, Any],
    *,
    geometry: dict[str, Any] | None = None,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if geometry is None or catalog is None:
        loaded_geometry, loaded_catalog = load_visual_sources()
        geometry = geometry or loaded_geometry
        catalog = catalog or loaded_catalog

    twin_state = swap_result["twin_state"]
    selection = swap_result["selection"]

    return _base_visual_state(
        scope="custom_swap_preview",
        subject_id=f"custom:{baseline_candidate['id']}",
        label=f"{baseline_candidate['label']} · Custom",
        vendor_family="Custom mix",
        deck_id=twin_state["deck_candidate_id"],
        topology_id=twin_state["topology_id"],
        wheel_id=selection.get("wheel"),
        stance_mm=twin_state.get("stance_mm"),
        layers=twin_state["layers"],
        brake_component=selection.get("brake"),
        drive_component=selection.get("drive"),
        readiness=swap_result["readiness"],
        checkout_state=swap_result["checkout_state"],
        fit_score=None,
        cost=swap_result["cost"],
        geometry=geometry,
        catalog=catalog,
    )
