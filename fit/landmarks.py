from __future__ import annotations

from math import dist
from typing import Dict, Mapping, Sequence

REQUIRED=(
    "left_ankle","right_ankle",
    "left_knee","right_knee",
    "left_hip","right_hip",
    "left_shoulder","right_shoulder",
)


def _p(v: Sequence[float]) -> tuple[float,float,float]:
    if len(v) != 3:
        raise ValueError("landmark coordinates must be XYZ triples")
    return tuple(float(x) for x in v)


def midpoint(a: Sequence[float], b: Sequence[float]) -> tuple[float,float,float]:
    aa=_p(a); bb=_p(b)
    return tuple((x+y)/2 for x,y in zip(aa,bb))


def analyze(landmarks: Mapping[str, Sequence[float]]) -> Dict[str, object]:
    missing=[k for k in REQUIRED if k not in landmarks]
    if missing:
        raise ValueError("missing landmarks: "+", ".join(missing))
    p={k:_p(landmarks[k]) for k in REQUIRED}

    pelvis_mid=midpoint(p["left_hip"],p["right_hip"])
    shoulder_mid=midpoint(p["left_shoulder"],p["right_shoulder"])
    ankle_mid=midpoint(p["left_ankle"],p["right_ankle"])

    left_thigh=dist(p["left_hip"],p["left_knee"])
    right_thigh=dist(p["right_hip"],p["right_knee"])
    left_shank=dist(p["left_knee"],p["left_ankle"])
    right_shank=dist(p["right_knee"],p["right_ankle"])

    return {
        "schema_version": 1,
        "units": "mm",
        "pelvis_mid_xyz": pelvis_mid,
        "shoulder_mid_xyz": shoulder_mid,
        "ankle_mid_xyz": ankle_mid,
        "pelvis_width_mm": dist(p["left_hip"],p["right_hip"]),
        "shoulder_width_mm": dist(p["left_shoulder"],p["right_shoulder"]),
        "left_thigh_mm": left_thigh,
        "right_thigh_mm": right_thigh,
        "left_shank_mm": left_shank,
        "right_shank_mm": right_shank,
        "thigh_length_delta_mm": right_thigh-left_thigh,
        "shank_length_delta_mm": right_shank-left_shank,
        "hip_height_delta_mm": p["right_hip"][2]-p["left_hip"][2],
        "knee_height_delta_mm": p["right_knee"][2]-p["left_knee"][2],
        "ankle_height_delta_mm": p["right_ankle"][2]-p["left_ankle"][2],
        "shoulder_height_delta_mm": p["right_shoulder"][2]-p["left_shoulder"][2],
        "shoulder_vs_pelvis_lateral_offset_mm": shoulder_mid[0]-pelvis_mid[0],
        "pelvis_vs_ankle_lateral_offset_mm": pelvis_mid[0]-ankle_mid[0],
        "note": "Geometric descriptors only. Do not interpret as diagnosis or automatically convert them into steering bias."
    }
