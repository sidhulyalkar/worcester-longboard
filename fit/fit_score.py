#!/usr/bin/env python3
"""Session-level scoring for unpowered Worcester X1 stance candidates.

The score rewards repeatability and neutral board response. It intentionally does
not reward a 50/50 left-right load split, because stable asymmetry may be normal
for a given rider.
"""
from __future__ import annotations
from dataclasses import dataclass, fields
from statistics import pstdev
from typing import Iterable, Mapping

@dataclass(frozen=True)
class TrialSummary:
    left_load_fraction: float
    deck_roll_mean_deg: float
    deck_roll_rms_deg: float
    stance_width_mm: float
    left_yaw_deg: float
    right_yaw_deg: float


def _coerce_trial(row: Mapping[str, float]) -> TrialSummary:
    required = tuple(f.name for f in fields(TrialSummary))
    missing = [name for name in required if name not in row]
    if missing:
        raise KeyError(f"trial summary missing fields: {', '.join(missing)}")
    return TrialSummary(**{name: float(row[name]) for name in required})


def score_trials(trials: Iterable[Mapping[str, float]]) -> dict[str, float | int]:
    rows = [_coerce_trial(row) for row in trials]
    if len(rows) < 2:
        raise ValueError("At least two remount trials are required")

    load_repeat = pstdev(r.left_load_fraction for r in rows)
    roll_bias = sum(abs(r.deck_roll_mean_deg) for r in rows) / len(rows)
    roll_rms = sum(r.deck_roll_rms_deg for r in rows) / len(rows)
    width_repeat = pstdev(r.stance_width_mm for r in rows)
    left_yaw_repeat = pstdev(r.left_yaw_deg for r in rows)
    right_yaw_repeat = pstdev(r.right_yaw_deg for r in rows)

    score = (
        100.0 * load_repeat
        + 2.0 * roll_bias
        + 1.0 * roll_rms
        + 0.02 * width_repeat
        + 0.10 * (left_yaw_repeat + right_yaw_repeat)
    )
    return {
        "trials": len(rows),
        "score_lower_is_better": score,
        "left_load_mean": sum(r.left_load_fraction for r in rows) / len(rows),
        "left_load_repeatability_sd": load_repeat,
        "deck_roll_bias_deg": roll_bias,
        "deck_roll_rms_deg": roll_rms,
        "stance_width_sd_mm": width_repeat,
        "left_yaw_sd_deg": left_yaw_repeat,
        "right_yaw_sd_deg": right_yaw_repeat,
    }
