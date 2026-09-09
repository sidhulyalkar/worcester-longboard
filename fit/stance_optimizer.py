from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

from .profile_schema import RiderProfile


@dataclass
class FitRigEnvelope:
    stance_width_min_mm: float = 320.0
    stance_width_max_mm: float = 560.0
    longitudinal_adjust_mm: float = 70.0
    lateral_adjust_mm: float = 22.0
    yaw_min_deg: float = -25.0
    yaw_max_deg: float = 25.0
    cant_options_deg: tuple = (0.0, 1.0, 2.0, 3.0, 4.0)


@dataclass
class StanceRecommendation:
    status: str
    left: Dict[str, Optional[float]]
    right: Dict[str, Optional[float]]
    stance_width_mm: Optional[float]
    notes: list[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def recommend(profile: RiderProfile, envelope: FitRigEnvelope | None = None) -> StanceRecommendation:
    """Create an initial fit-rig recommendation from measured neutral stance.

    This intentionally does not infer geometry from shoe size labels or anatomy.
    It mirrors measured natural foot centers/yaw when available and otherwise
    leaves those dimensions unresolved for physical calibration.
    """
    env = envelope or FitRigEnvelope()
    notes: list[str] = [
        "Use this only on the unpowered fit rig before transferring dimensions to the rideable board.",
        "Keep truck geometry symmetric during initial fit work.",
    ]

    stance = profile.stance_width_mm
    if stance is not None:
        stance = _clamp(stance, env.stance_width_min_mm, env.stance_width_max_mm)
    else:
        notes.append("Stance width is unresolved; measure natural foot-center spacing on the fit rig.")

    def side(foot):
        yaw = foot.natural_yaw_deg
        if yaw is not None:
            yaw = _clamp(yaw, env.yaw_min_deg, env.yaw_max_deg)
        return {
            "center_x_mm": foot.natural_center_x_mm,
            "center_y_mm": foot.natural_center_y_mm,
            "yaw_deg": yaw,
            "cant_deg": foot.cant_deg,
            "foot_length_mm": foot.length_mm,
            "foot_width_mm": foot.width_mm,
        }

    unresolved = profile.measurement_gaps()
    if unresolved:
        notes.append("Missing measurements: " + ", ".join(unresolved))

    return StanceRecommendation(
        status="measurement_gated" if unresolved else "ready_for_unpowered_fit_validation",
        left=side(profile.left_foot),
        right=side(profile.right_foot),
        stance_width_mm=stance,
        notes=notes,
    )
