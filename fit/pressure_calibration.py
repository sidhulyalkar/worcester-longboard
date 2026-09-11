#!/usr/bin/env python3
"""Four-zone fit-rig load-cell calibration utilities.

This module converts raw ADC counts into force. It intentionally does not infer
posture quality or steering corrections from left/right load differences.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

G = 9.80665
CHANNELS = ("left_heel", "left_forefoot", "right_heel", "right_forefoot")

@dataclass(frozen=True)
class ChannelCalibration:
    zero_raw: float
    span_raw: float
    span_newtons: float

    def __post_init__(self):
        if abs(self.span_raw - self.zero_raw) < 1e-9:
            raise ValueError("zero_raw and span_raw must differ")
        if self.span_newtons <= 0:
            raise ValueError("span_newtons must be positive")

    @property
    def newtons_per_count(self) -> float:
        return self.span_newtons / (self.span_raw - self.zero_raw)

    def force_newtons(self, raw: float) -> float:
        return max(0.0, (float(raw) - self.zero_raw) * self.newtons_per_count)


def from_known_mass(zero_raw: float, loaded_raw: float, known_mass_kg: float) -> ChannelCalibration:
    if known_mass_kg <= 0:
        raise ValueError("known_mass_kg must be positive")
    return ChannelCalibration(float(zero_raw), float(loaded_raw), float(known_mass_kg) * G)


def calibrate_sample(raw: Mapping[str, float], calibration: Mapping[str, ChannelCalibration]) -> dict[str, float]:
    missing = [name for name in CHANNELS if name not in raw or name not in calibration]
    if missing:
        raise KeyError(f"missing channels: {', '.join(missing)}")
    return {name: calibration[name].force_newtons(float(raw[name])) for name in CHANNELS}


def total_force_newtons(sample: Mapping[str, float]) -> float:
    return sum(float(sample[name]) for name in CHANNELS)
