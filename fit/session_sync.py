#!/usr/bin/env python3
"""Nearest-timestamp synchronization for private fit-rig data streams."""
from __future__ import annotations
from bisect import bisect_left
from typing import Iterable


def _nearest(rows, t):
    times = [float(r["t_s"]) for r in rows]
    i = bisect_left(times, t)
    candidates = []
    if i < len(rows):
        candidates.append(rows[i])
    if i:
        candidates.append(rows[i - 1])
    return min(candidates, key=lambda r: abs(float(r["t_s"]) - t)) if candidates else None


def synchronize(reference: Iterable[dict], streams: dict[str, Iterable[dict]], tolerance_s: float = 0.05) -> list[dict]:
    if tolerance_s <= 0:
        raise ValueError("tolerance_s must be positive")
    ref = sorted((dict(r) for r in reference), key=lambda r: float(r["t_s"]))
    prepared = {
        name: sorted((dict(r) for r in rows), key=lambda r: float(r["t_s"]))
        for name, rows in streams.items()
    }
    out = []
    for r in ref:
        t = float(r["t_s"])
        joined = {"reference": r}
        valid = True
        for name, rows in prepared.items():
            match = _nearest(rows, t)
            if match is None or abs(float(match["t_s"]) - t) > tolerance_s:
                valid = False
                break
            joined[name] = match
        if valid:
            out.append(joined)
    return out
