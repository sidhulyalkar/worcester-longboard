"""Parse and quality-check Worcester X1 Fit Rig v0.3 raw logger output."""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from io import StringIO
from statistics import median
from typing import Iterable

CHANNELS = ("left_heel", "left_forefoot", "right_heel", "right_forefoot")


@dataclass(frozen=True)
class RawSample:
    t_us: int
    raw: tuple[int | None, int | None, int | None, int | None]
    load_valid_mask: int
    roll_deg: float | None
    imu_ok: bool

    @property
    def complete_force_sample(self) -> bool:
        return self.load_valid_mask == 0x0F and all(v is not None for v in self.raw)


def _maybe_int(value: str) -> int | None:
    value = value.strip().lower()
    if value in ("", "nan", "none"):
        return None
    return int(value)


def _maybe_float(value: str) -> float | None:
    value = value.strip().lower()
    if value in ("", "nan", "none"):
        return None
    out = float(value)
    return out if math.isfinite(out) else None


def parse_text(text: str) -> list[RawSample]:
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not lines:
        return []
    reader = csv.DictReader(StringIO("\n".join(lines)))
    out: list[RawSample] = []
    for row in reader:
        mask = int(row["load_valid_mask"])
        if not 0 <= mask <= 15:
            raise ValueError(f"invalid load_valid_mask={mask}")
        raw = (
            _maybe_int(row["left_heel_raw"]),
            _maybe_int(row["left_forefoot_raw"]),
            _maybe_int(row["right_heel_raw"]),
            _maybe_int(row["right_forefoot_raw"]),
        )
        # Mask and payload must agree. A set bit with nan is corrupt rather than a
        # merely missing sample because downstream calibration would be ambiguous.
        for i, value in enumerate(raw):
            if (mask & (1 << i)) and value is None:
                raise ValueError(f"mask marks channel {CHANNELS[i]} valid but payload is missing")
        out.append(
            RawSample(
                t_us=int(row["t_us"]),
                raw=raw,
                load_valid_mask=mask,
                roll_deg=_maybe_float(row["roll_deg"]),
                imu_ok=row["imu_ok"].strip() in ("1", "true", "True"),
            )
        )
    return out


def quality_report(samples: Iterable[RawSample]) -> dict:
    rows = list(samples)
    if not rows:
        return {
            "samples": 0,
            "duration_s": 0.0,
            "monotonic_time": False,
            "complete_force_fraction": 0.0,
            "imu_valid_fraction": 0.0,
            "warnings": ["empty raw log"],
        }

    monotonic = all(b.t_us > a.t_us for a, b in zip(rows, rows[1:]))
    duration_s = max(0.0, (rows[-1].t_us - rows[0].t_us) / 1_000_000.0)
    complete = sum(r.complete_force_sample for r in rows) / len(rows)
    imu_fraction = sum(r.imu_ok and r.roll_deg is not None for r in rows) / len(rows)
    channel_fraction = {
        name: sum(bool(r.load_valid_mask & (1 << i)) for r in rows) / len(rows)
        for i, name in enumerate(CHANNELS)
    }
    dts_ms = [
        (b.t_us - a.t_us) / 1000.0
        for a, b in zip(rows, rows[1:])
        if b.t_us > a.t_us
    ]

    warnings: list[str] = []
    if not monotonic:
        warnings.append("timestamps are not strictly monotonic")
    if complete < 0.98:
        warnings.append("fewer than 98% of samples contain all four force channels")
    if min(channel_fraction.values()) < 0.98:
        warnings.append("one or more force channels has >=2% dropout")
    if imu_fraction < 0.95:
        warnings.append("fixture IMU coverage is below 95%")

    return {
        "samples": len(rows),
        "duration_s": duration_s,
        "monotonic_time": monotonic,
        "median_dt_ms": median(dts_ms) if dts_ms else None,
        "complete_force_fraction": complete,
        "channel_valid_fraction": channel_fraction,
        "imu_valid_fraction": imu_fraction,
        "warnings": warnings,
    }
