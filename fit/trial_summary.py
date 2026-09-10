#!/usr/bin/env python3
"""Reduce a calibrated neutral fit-rig trial to stance-scoring features."""
from __future__ import annotations
import math
from typing import Iterable, Mapping

FORCE_FIELDS = ("left_heel_N", "left_forefoot_N", "right_heel_N", "right_forefoot_N")


def summarize_neutral_trial(
    rows: Iterable[Mapping[str, float]],
    *,
    stance_width_mm: float,
    left_yaw_deg: float,
    right_yaw_deg: float,
) -> dict[str, float | int]:
    valid = []
    for row in rows:
        try:
            forces = [max(0.0, float(row[name])) for name in FORCE_FIELDS]
            roll = float(row["roll_deg"])
        except (KeyError, TypeError, ValueError):
            continue
        total = sum(forces)
        if total <= 1e-6 or not math.isfinite(roll):
            continue
        valid.append((forces, roll))

    if len(valid) < 2:
        raise ValueError("Need at least two valid calibrated samples")

    left_fractions = []
    rolls = []
    total_forces = []
    for forces, roll in valid:
        total = sum(forces)
        left_fractions.append((forces[0] + forces[1]) / total)
        total_forces.append(total)
        rolls.append(roll)

    mean_roll = sum(rolls) / len(rolls)
    rms_roll = math.sqrt(sum(r * r for r in rolls) / len(rolls))
    mean_total = sum(total_forces) / len(total_forces)

    return {
        "samples": len(valid),
        "left_load_fraction": sum(left_fractions) / len(left_fractions),
        "mean_total_force_N": mean_total,
        "deck_roll_mean_deg": mean_roll,
        "deck_roll_rms_deg": rms_roll,
        "stance_width_mm": float(stance_width_mm),
        "left_yaw_deg": float(left_yaw_deg),
        "right_yaw_deg": float(right_yaw_deg),
    }
