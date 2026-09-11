from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional


@dataclass
class FootProfile:
    length_mm: Optional[float] = None
    width_mm: Optional[float] = None
    shoe_size_label: Optional[str] = None
    natural_yaw_deg: Optional[float] = None
    natural_center_x_mm: Optional[float] = None
    natural_center_y_mm: Optional[float] = None
    cant_deg: float = 0.0


@dataclass
class RiderProfile:
    schema_version: int = 2
    mass_kg: Optional[float] = None
    height_mm: Optional[float] = None
    board_mass_kg: Optional[float] = None
    stance_width_mm: Optional[float] = None
    left_foot: FootProfile = field(default_factory=FootProfile)
    right_foot: FootProfile = field(default_factory=FootProfile)
    fit_mode: str = "independent_left_right"
    symmetric_trucks_default: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiderProfile":
        left = FootProfile(**data.get("left_foot", {}))
        right = FootProfile(**data.get("right_foot", {}))
        fields = {
            "schema_version": data.get("schema_version", 2),
            "mass_kg": data.get("mass_kg"),
            "height_mm": data.get("height_mm"),
            "board_mass_kg": data.get("board_mass_kg"),
            "stance_width_mm": data.get("stance_width_mm"),
            "left_foot": left,
            "right_foot": right,
            "fit_mode": data.get("fit_mode", "independent_left_right"),
            "symmetric_trucks_default": data.get("symmetric_trucks_default", True),
        }
        return cls(**fields)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def system_mass_kg(self) -> Optional[float]:
        if self.mass_kg is None or self.board_mass_kg is None:
            return None
        return self.mass_kg + self.board_mass_kg

    def validate(self) -> List[str]:
        errors: List[str] = []
        if self.height_mm is not None and not (1200 <= self.height_mm <= 2300):
            errors.append("height_mm outside expected human-fit range")
        if self.mass_kg is not None and not (25 <= self.mass_kg <= 250):
            errors.append("mass_kg outside expected rider range")
        if self.board_mass_kg is not None and not (5 <= self.board_mass_kg <= 60):
            errors.append("board_mass_kg outside expected prototype range")
        if self.fit_mode != "independent_left_right":
            errors.append("unsupported fit_mode")
        for side, foot in (("left", self.left_foot), ("right", self.right_foot)):
            if foot.length_mm is not None and not (150 <= foot.length_mm <= 360):
                errors.append(f"{side}_foot.length_mm outside expected range")
            if foot.width_mm is not None and not (55 <= foot.width_mm <= 150):
                errors.append(f"{side}_foot.width_mm outside expected range")
            if not (-8 <= foot.cant_deg <= 8):
                errors.append(f"{side}_foot.cant_deg outside adjustable rig range")
        return errors

    def measurement_gaps(self) -> List[str]:
        gaps: List[str] = []
        if self.height_mm is None:
            gaps.append("height_mm")
        if self.mass_kg is None:
            gaps.append("mass_kg")
        if self.left_foot.length_mm is None:
            gaps.append("left_foot.length_mm")
        if self.left_foot.width_mm is None:
            gaps.append("left_foot.width_mm")
        if self.right_foot.length_mm is None:
            gaps.append("right_foot.length_mm")
        if self.right_foot.width_mm is None:
            gaps.append("right_foot.width_mm")
        if self.left_foot.natural_yaw_deg is None:
            gaps.append("left_foot.natural_yaw_deg")
        if self.right_foot.natural_yaw_deg is None:
            gaps.append("right_foot.natural_yaw_deg")
        if self.stance_width_mm is None:
            gaps.append("stance_width_mm")
        return gaps
