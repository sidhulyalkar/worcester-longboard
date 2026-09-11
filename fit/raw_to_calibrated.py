"""Convert X1 Fit Rig raw samples into calibrated four-zone force rows."""
from __future__ import annotations

from typing import Mapping, Sequence

from fit.pressure_calibration import CHANNELS, ChannelCalibration, calibrate_sample
from fit.raw_log import RawSample


def convert_samples(
    samples: Sequence[RawSample],
    calibration: Mapping[str, ChannelCalibration],
    *,
    require_complete_force: bool = True,
    require_imu: bool = True,
) -> list[dict[str, float]]:
    """Return calibrated rows using one relative timebase.

    Qualification defaults are deliberately strict. Partial force rows and missing
    fixture roll remain visible in the raw log but do not enter a qualified neutral
    trial unless a caller explicitly opts out for diagnostics.
    """
    missing_cal = [name for name in CHANNELS if name not in calibration]
    if missing_cal:
        raise KeyError(f"missing calibration: {', '.join(missing_cal)}")

    accepted: list[RawSample] = []
    for sample in samples:
        if require_complete_force and not sample.complete_force_sample:
            continue
        if require_imu and (not sample.imu_ok or sample.roll_deg is None):
            continue
        accepted.append(sample)

    if not accepted:
        return []

    t0 = accepted[0].t_us
    rows: list[dict[str, float]] = []
    for sample in accepted:
        raw_map = {
            name: float(sample.raw[i])
            for i, name in enumerate(CHANNELS)
            if sample.raw[i] is not None
        }
        if len(raw_map) != len(CHANNELS):
            if require_complete_force:
                continue
            # The downstream calibrated schema has no representation for missing
            # force zones, so diagnostic partial samples are not emitted here.
            continue
        force = calibrate_sample(raw_map, calibration)
        rows.append({
            "t_s": (sample.t_us - t0) / 1_000_000.0,
            "left_heel_N": force["left_heel"],
            "left_forefoot_N": force["left_forefoot"],
            "right_heel_N": force["right_heel"],
            "right_forefoot_N": force["right_forefoot"],
            "roll_deg": float(sample.roll_deg) if sample.roll_deg is not None else 0.0,
        })
    return rows
