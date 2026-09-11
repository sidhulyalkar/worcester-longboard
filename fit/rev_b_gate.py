#!/usr/bin/env python3
"""Measurement, repeatability, and raw-data gate before Rev-B rider-interface CAD.

These are engineering workflow gates, not medical criteria and not a claim that
one stance is anatomically 'correct'. Stable left/right load asymmetry is not a
failure condition. A fit result cannot qualify if its underlying sensor logs are
missing or unhealthy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from fit.profile_schema import RiderProfile


@dataclass(frozen=True)
class RevBGatePolicy:
    min_trials: int = 3
    min_trial_duration_s: float = 20.0
    min_complete_force_fraction: float = 0.98
    min_imu_valid_fraction: float = 0.95
    max_left_load_repeatability_sd: float = 0.03
    max_deck_roll_bias_deg: float = 0.75
    max_deck_roll_rms_deg: float = 1.00
    max_stance_width_sd_mm: float = 5.0
    max_yaw_sd_deg: float = 2.0


def _check_raw_quality(
    raw_quality: Iterable[Mapping[str, object]] | None,
    policy: RevBGatePolicy,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    reports = list(raw_quality or [])

    if len(reports) < policy.min_trials:
        blockers.append(f"need raw quality reports for >= {policy.min_trials} remount trials")
        return blockers, warnings

    for i, report in enumerate(reports, start=1):
        trial = str(report.get("trial_id") or f"trial-{i}")
        if not bool(report.get("monotonic_time", False)):
            blockers.append(f"{trial}: raw timestamps are not strictly monotonic")
        if float(report.get("duration_s", 0.0)) < policy.min_trial_duration_s:
            blockers.append(
                f"{trial}: raw duration is below {policy.min_trial_duration_s:g} s"
            )
        if float(report.get("complete_force_fraction", 0.0)) < policy.min_complete_force_fraction:
            blockers.append(
                f"{trial}: complete four-channel force coverage is below "
                f"{policy.min_complete_force_fraction:.0%}"
            )
        if float(report.get("imu_valid_fraction", 0.0)) < policy.min_imu_valid_fraction:
            blockers.append(
                f"{trial}: fixture IMU coverage is below {policy.min_imu_valid_fraction:.0%}"
            )

        channel_fraction = report.get("channel_valid_fraction") or {}
        if isinstance(channel_fraction, Mapping):
            for channel, fraction in channel_fraction.items():
                if float(fraction) < policy.min_complete_force_fraction:
                    blockers.append(
                        f"{trial}: {channel} coverage is below "
                        f"{policy.min_complete_force_fraction:.0%}"
                    )

        upstream_warnings = report.get("warnings") or []
        for warning in upstream_warnings if isinstance(upstream_warnings, list) else []:
            warnings.append(f"{trial}: raw-log warning: {warning}")

    return blockers, warnings


def evaluate(
    profile: RiderProfile,
    score: Mapping[str, float],
    raw_quality: Iterable[Mapping[str, object]] | None = None,
    policy: RevBGatePolicy = RevBGatePolicy(),
) -> dict:
    blockers: list[str] = []
    warnings: list[str] = []

    profile_errors = profile.validate()
    if profile_errors:
        blockers.extend(f"profile: {e}" for e in profile_errors)
    gaps = profile.measurement_gaps()
    if gaps:
        blockers.extend(f"missing measurement: {g}" for g in gaps)

    checks = (
        (int(score.get("trials", 0)) >= policy.min_trials,
         f"need >= {policy.min_trials} remount trials"),
        (float(score.get("left_load_repeatability_sd", 999.0)) <= policy.max_left_load_repeatability_sd,
         "left/right load distribution is not repeatable enough"),
        (float(score.get("deck_roll_bias_deg", 999.0)) <= policy.max_deck_roll_bias_deg,
         "neutral deck-roll bias exceeds provisional fit gate"),
        (float(score.get("deck_roll_rms_deg", 999.0)) <= policy.max_deck_roll_rms_deg,
         "neutral deck-roll RMS exceeds provisional fit gate"),
        (float(score.get("stance_width_sd_mm", 999.0)) <= policy.max_stance_width_sd_mm,
         "stance width is not repeatable enough"),
        (float(score.get("left_yaw_sd_deg", 999.0)) <= policy.max_yaw_sd_deg,
         "left foot yaw is not repeatable enough"),
        (float(score.get("right_yaw_sd_deg", 999.0)) <= policy.max_yaw_sd_deg,
         "right foot yaw is not repeatable enough"),
    )
    blockers.extend(message for passed, message in checks if not passed)

    raw_blockers, raw_warnings = _check_raw_quality(raw_quality, policy)
    blockers.extend(raw_blockers)
    warnings.extend(raw_warnings)

    load_mean = score.get("left_load_mean")
    if load_mean is not None and not (0.15 <= float(load_mean) <= 0.85):
        warnings.append(
            "very concentrated left/right loading observed; review fixture and comfort before freezing geometry"
        )

    if not profile.symmetric_trucks_default:
        blockers.append("Rev-B fit phase requires symmetric truck geometry by default")

    return {
        "ready_for_rev_b_fit_cad": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "policy": {
            "min_trials": policy.min_trials,
            "min_trial_duration_s": policy.min_trial_duration_s,
            "min_complete_force_fraction": policy.min_complete_force_fraction,
            "min_imu_valid_fraction": policy.min_imu_valid_fraction,
            "max_left_load_repeatability_sd": policy.max_left_load_repeatability_sd,
            "max_deck_roll_bias_deg": policy.max_deck_roll_bias_deg,
            "max_deck_roll_rms_deg": policy.max_deck_roll_rms_deg,
            "max_stance_width_sd_mm": policy.max_stance_width_sd_mm,
            "max_yaw_sd_deg": policy.max_yaw_sd_deg,
        },
        "note": (
            "Engineering fit/data-quality gate only; thresholds are provisional and do not "
            "define medical or anatomical correctness."
        ),
    }
