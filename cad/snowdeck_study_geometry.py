"""Pure geometry contract for the X1 SnowDeck v0.1 bench study.

This module defines visualization/bench-study bounds only. It does not define a
ride-ready rider interface, structural deck attachment, or retention system.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Tuple

try:
    from cad.fit_rig_geometry import DEFAULT as FIT_RIG
except ModuleNotFoundError:
    from fit_rig_geometry import DEFAULT as FIT_RIG


@dataclass(frozen=True)
class SnowDeckStudyGeometry:
    plate_length_mm: float = FIT_RIG.footplate_length_mm
    plate_width_mm: float = FIT_RIG.footplate_width_mm
    plate_thickness_mm: float = FIT_RIG.footplate_thickness_mm

    insert_envelope_length_mm: float = FIT_RIG.footplate_length_mm - 10.0
    insert_envelope_width_mm: float = FIT_RIG.footplate_width_mm - 10.0
    insert_study_max_thickness_mm: float = 8.0

    cant_study_angles_deg: Tuple[float, ...] = (0.0, 2.0, 4.0)
    viewer_stance_min_mm: float = 260.0
    viewer_stance_max_mm: float = 520.0
    viewer_yaw_abs_max_deg: float = 30.0
    viewer_cant_max_deg: float = 5.0

    structural_deck_interface_verified: bool = False
    rider_retention_verified: bool = False
    ride_load_path_verified: bool = False

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.plate_length_mm <= 0 or self.plate_width_mm <= 0:
            errors.append("plate envelope must be positive")
        if self.plate_thickness_mm <= 0:
            errors.append("plate thickness must be positive")
        if self.insert_envelope_length_mm >= self.plate_length_mm:
            errors.append("insert envelope must remain inside plate length")
        if self.insert_envelope_width_mm >= self.plate_width_mm:
            errors.append("insert envelope must remain inside plate width")
        if not 0 < self.insert_study_max_thickness_mm <= 12:
            errors.append("insert study thickness outside visualization bounds")
        if not self.cant_study_angles_deg:
            errors.append("cant study requires at least one control angle")
        if any(angle < 0 or angle > self.viewer_cant_max_deg for angle in self.cant_study_angles_deg):
            errors.append("cant study angle outside viewer study bounds")
        if self.viewer_stance_min_mm >= self.viewer_stance_max_mm:
            errors.append("stance study range is inverted")
        return errors

    @property
    def fabrication_ready(self) -> bool:
        return False

    @property
    def ride_ready(self) -> bool:
        return False

    def authority_report(self) -> dict:
        return {
            "schema_version": 1,
            "scope": "x1_snowdeck_reversible_bench_study_only",
            "geometry": asdict(self),
            "validation_errors": self.validate(),
            "fabrication_authority": False,
            "ride_authority": False,
            "powered_operation_authorized": False,
            "structural_deck_interface_verified": self.structural_deck_interface_verified,
            "rider_retention_verified": self.rider_retention_verified,
            "ride_load_path_verified": self.ride_load_path_verified,
            "measurement_gates": [
                "complete qualified four-zone rider-fit evidence before rider-specific geometry",
                "template final left/right geometry before permanent drilling",
                "measure any compliant insert stiffness, hysteresis, settling and compression set",
                "verify fastener retention and deck load path separately before any ride use",
                "verify emergency disengagement behavior for any future retention concept",
            ],
            "note": (
                "Study bounds are visualization/bench variables, not recommended ride settings. "
                "The plate envelope reuses the existing Fit Rig universal plate geometry so the "
                "study can begin without inventing a second rider-fit coordinate system."
            ),
        }


DEFAULT = SnowDeckStudyGeometry()
