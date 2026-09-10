#!/usr/bin/env python3
"""Normalize RuView pose payloads into X1's generic keypoint format.

RuView pose is auxiliary dynamic-comparison data. It is never treated as
millimetre-accurate manufacturing geometry or as a sole safety/control source.
"""
from __future__ import annotations
from typing import Any

COCO17 = (
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip", "left_knee",
    "right_knee", "left_ankle", "right_ankle",
)


def _xyz_conf(value: Any) -> tuple[float, float, float, float | None]:
    if isinstance(value, dict):
        return (
            float(value.get("x", 0.0)),
            float(value.get("y", 0.0)),
            float(value.get("z", 0.0)),
            float(value["confidence"]) if value.get("confidence") is not None else None,
        )
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        x, y = float(value[0]), float(value[1])
        z = float(value[2]) if len(value) >= 3 else 0.0
        conf = float(value[3]) if len(value) >= 4 else None
        return x, y, z, conf
    raise ValueError("Unsupported keypoint representation")


def normalize_pose(payload: dict[str, Any]) -> dict[str, Any]:
    persons = payload.get("persons") or payload.get("people") or payload.get("poses")
    if persons is None:
        persons = [payload]
    if isinstance(persons, dict):
        persons = [persons]
    if not persons:
        raise ValueError("No pose person found")

    person = persons[0]
    raw = person.get("keypoints") or person.get("joints") or person.get("pose")
    if raw is None:
        raise ValueError("Pose payload has no keypoints")

    out: dict[str, dict[str, float | None]] = {}
    if isinstance(raw, dict):
        items = raw.items()
    elif raw and isinstance(raw[0], dict) and raw[0].get("name") is not None:
        items = ((str(value["name"]), value) for value in raw)
    else:
        if len(raw) < 17:
            raise ValueError("Unnamed pose arrays must contain all 17 COCO keypoints")
        items = zip(COCO17, raw[:17])

    for name, value in items:
        if name not in COCO17:
            continue
        x, y, z, conf = _xyz_conf(value)
        out[name] = {"x": x, "y": y, "z": z, "confidence": conf}

    missing = [name for name in COCO17 if name not in out]
    return {
        "schema_version": 1,
        "source": "ruview_pose",
        "source_frame_id": payload.get("frame_id"),
        "source_timestamp_ms": payload.get("timestamp_ms"),
        "keypoints": out,
        "missing_keypoints": missing,
        "metric_geometry_authoritative": False,
        "control_authoritative": False,
        "intended_use": "dynamic_stance_comparison",
    }
