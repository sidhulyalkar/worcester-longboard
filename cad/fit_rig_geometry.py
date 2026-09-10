"""Pure-Python geometry authority for the unpowered X1 Fit Rig v0.3.

This module intentionally contains no rider-specific values.  It separates known
vendor envelopes from dimensions that must be measured on physical parts before
fabrication.  CadQuery generators consume this authority; tests can validate the
same invariants without importing CadQuery.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass(frozen=True)
class LoadCellEnvelope:
    length_mm: float = 55.25
    width_mm: float = 12.70
    height_mm: float = 12.70
    thread: str = "M5"
    fixed_hole_spacing_mm: Optional[float] = None
    load_hole_spacing_mm: Optional[float] = None

    @property
    def fabrication_ready(self) -> bool:
        return (
            self.fixed_hole_spacing_mm is not None
            and self.load_hole_spacing_mm is not None
            and self.fixed_hole_spacing_mm > 0
            and self.load_hole_spacing_mm > 0
        )


@dataclass(frozen=True)
class FitRigGeometry:
    base_length_mm: float = 700.0
    base_width_mm: float = 300.0
    base_thickness_mm: float = 12.0

    footplate_length_mm: float = 260.0
    footplate_width_mm: float = 132.0
    footplate_thickness_mm: float = 6.0

    zone_pad_length_mm: float = 105.0
    zone_pad_width_mm: float = 78.0
    zone_pad_thickness_mm: float = 6.0
    force_button_diameter_mm: float = 12.0
    force_button_height_mm: float = 2.0

    load_cell_pod_length_mm: float = 92.0
    load_cell_pod_width_mm: float = 38.0
    load_cell_pod_thickness_mm: float = 6.0
    overload_stop_gap_mm: float = 0.8
    overload_stop_diameter_mm: float = 10.0

    electronics_box_length_mm: float = 185.0
    electronics_box_width_mm: float = 125.0
    electronics_box_height_mm: float = 42.0
    electronics_wall_mm: float = 3.0

    rail_slot_length_mm: float = 105.0
    rail_slot_width_mm: float = 6.5
    rail_offset_y_mm: float = 42.0

    load_cell: LoadCellEnvelope = LoadCellEnvelope()

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.base_length_mm < 2 * self.footplate_length_mm + 80:
            errors.append("base is too short for two independently adjustable footplates")
        if self.base_width_mm < self.footplate_width_mm + 80:
            errors.append("base is too narrow for footplate adjustment and hardware clearance")
        if self.zone_pad_width_mm >= self.footplate_width_mm:
            errors.append("zone pad must fit inside the footplate width")
        if self.load_cell_pod_width_mm <= self.load_cell.width_mm + 8:
            errors.append("load-cell pod lacks lateral clearance")
        if not 0.3 <= self.overload_stop_gap_mm <= 2.0:
            errors.append("overload stop gap outside conservative fixture range")
        if self.force_button_diameter_mm > self.zone_pad_width_mm / 2:
            errors.append("force-transfer button is too large for the zone pad")
        if self.electronics_wall_mm < 2.0:
            errors.append("electronics enclosure wall is too thin for prototype handling")
        return errors

    @property
    def sensor_mount_fabrication_ready(self) -> bool:
        return self.load_cell.fabrication_ready

    def authority_report(self) -> dict:
        return {
            "schema_version": 1,
            "fixture_type": "unpowered_fit_rig_only",
            "geometry": asdict(self),
            "validation_errors": self.validate(),
            "sensor_mount_fabrication_ready": self.sensor_mount_fabrication_ready,
            "measurement_gates": [] if self.sensor_mount_fabrication_ready else [
                "load_cell.fixed_hole_spacing_mm",
                "load_cell.load_hole_spacing_mm",
            ],
            "note": (
                "Reference geometry may be generated before the measurement gates close, "
                "but load-cell mounting features are not fabrication-authoritative until "
                "physical sensors are measured."
            ),
        }


DEFAULT = FitRigGeometry()
