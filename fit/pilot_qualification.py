"""One-zone load-cell qualification for the unpowered X1 Fit Rig.

This module qualifies only the low-voltage calibration fixture sensor stack for
four-zone duplication. It does not qualify rideable structure or powered use.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import fmean, pstdev

from fit.raw_log import CHANNELS, parse_text

G = 9.80665
HARD_MAX_PILOT_MASS_KG = 20.0
LIMITS = {
    "min_duration_s": 5.0,
    "min_coverage": 0.98,
    "min_r2": 0.999,
    "max_residual_fs": 0.01,
    "max_hysteresis_fs": 0.015,
    "max_zero_return_fs": 0.005,
    "max_validation_error": 0.02,
    "max_noise_fs": 0.005,
    "min_loaded_gap_mm": 0.15,
    "min_unloaded_gap_mm": 0.30,
    "max_unloaded_gap_mm": 2.00,
}
MIN_LIMITS = {"min_duration_s", "min_coverage", "min_r2", "min_loaded_gap_mm", "min_unloaded_gap_mm"}
MAX_LIMITS = {
    "max_residual_fs", "max_hysteresis_fs", "max_zero_return_fs",
    "max_validation_error", "max_noise_fs", "max_unloaded_gap_mm",
}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _digest(obj: dict) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def _tool_sha256() -> str:
    return _sha(Path(__file__).resolve())


def _resolve_log(base: Path, relative: str) -> Path:
    candidate = (base / relative).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"pilot log escapes manifest directory: {relative}") from exc
    return candidate


def _logger_sps(text: str) -> int | None:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# hx711_sps="):
            try:
                return int(line.split("=", 1)[1].strip())
            except ValueError as exc:
                raise ValueError(f"invalid HX711 rate header: {line}") from exc
    return None


def _plateau(path: Path, channel: str, kind: str, mass: float) -> dict:
    text = path.read_text(encoding="utf-8")
    rows = parse_text(text)
    if not rows:
        raise ValueError(f"{path}: empty log")
    try:
        idx = CHANNELS.index(channel)
    except ValueError as exc:
        raise ValueError(f"unknown channel {channel!r}") from exc
    vals = [row.raw[idx] for row in rows if (row.load_valid_mask & (1 << idx)) and row.raw[idx] is not None]
    if not vals:
        raise ValueError(f"{path}: no valid {channel} samples")
    return {
        "kind": kind,
        "mass_kg": float(mass),
        "force_n": float(mass) * G,
        "path": str(path),
        "mean": fmean(vals),
        "std": pstdev(vals),
        "coverage": len(vals) / len(rows),
        "duration_s": max(0.0, (rows[-1].t_us - rows[0].t_us) / 1e6),
        "monotonic": all(b.t_us > a.t_us for a, b in zip(rows, rows[1:])),
        "logger_hx711_sps": _logger_sps(text),
        "sha256": _sha(path),
    }


def _fit(points: list[dict]) -> dict:
    xs = [p["force_n"] for p in points]
    ys = [p["mean"] for p in points]
    xb, yb = fmean(xs), fmean(ys)
    sxx = sum((x - xb) ** 2 for x in xs)
    if sxx <= 0:
        raise ValueError("calibration points must span force")
    slope = sum((x - xb) * (y - yb) for x, y in zip(xs, ys)) / sxx
    if abs(slope) < 1e-12:
        raise ValueError("zero calibration slope")
    intercept = yb - slope * xb
    ssr = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    sst = sum((y - yb) ** 2 for y in ys)
    return {"intercept": intercept, "counts_per_n": slope, "r2": 1.0 if sst == 0 else 1 - ssr / sst}


def _force(raw: float, fit: dict) -> float:
    return (raw - fit["intercept"]) / fit["counts_per_n"]


def _limits_from_manifest(manifest: dict) -> tuple[dict, list[str]]:
    limits = dict(LIMITS)
    failures: list[str] = []
    overrides = manifest.get("thresholds", {})
    unknown = sorted(set(overrides) - set(LIMITS))
    if unknown:
        failures.append("unknown threshold override(s): " + ", ".join(unknown))
    for name, value in overrides.items():
        if name not in LIMITS:
            continue
        value = float(value)
        default = LIMITS[name]
        if name in MIN_LIMITS and value < default:
            failures.append(f"threshold {name} may only be made stricter")
        elif name in MAX_LIMITS and value > default:
            failures.append(f"threshold {name} may only be made stricter")
        else:
            limits[name] = value
    return limits, failures


def _validate_hardware_ids(manifest: dict) -> tuple[dict, list[str]]:
    ids = manifest.get("hardware_ids", {})
    failures = []
    for key in ("load_cell_id", "hx711_id", "pod_id", "zone_pad_id"):
        if not isinstance(ids.get(key), str) or not ids[key].strip():
            failures.append(f"hardware_ids.{key} must be a nonempty string")
    return ids, failures


def qualify_manifest(path: Path) -> dict:
    path = Path(path).resolve()
    manifest = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent.resolve()
    if manifest.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")

    limits, failures = _limits_from_manifest(manifest)
    hardware_ids, hardware_id_failures = _validate_hardware_ids(manifest)
    failures.extend(hardware_id_failures)
    channel = manifest["channel"]
    rate = manifest.get("hx711_sps")
    acquisition = manifest.get("acquisition", {})

    obs = [
        _plateau(_resolve_log(base, item["log"]), channel, item["kind"], item["mass_kg"])
        for item in manifest.get("observations", [])
    ]
    val = [
        _plateau(_resolve_log(base, item["log"]), channel, "validation", item["mass_kg"])
        for item in manifest.get("validation", [])
    ]

    kinds = [p["kind"] for p in obs]
    pre = [p for p in obs if p["kind"] == "zero_pre" and p["mass_kg"] == 0]
    post = [p for p in obs if p["kind"] == "zero_post" and p["mass_kg"] == 0]
    up = [p for p in obs if p["kind"] == "load_up" and p["mass_kg"] > 0]
    down = [p for p in obs if p["kind"] == "load_down" and p["mass_kg"] > 0]

    paired = sorted({p["mass_kg"] for p in up} & {p["mass_kg"] for p in down})
    cal_masses = {p["mass_kg"] for p in up}

    if rate not in (10, 80):
        failures.append("hx711_sps must be 10 or 80")
    if acquisition.get("rate_jumper_verified") is not True:
        failures.append("acquisition.rate_jumper_verified must be true")
    if not pre:
        failures.append("missing zero_pre")
    if not post:
        failures.append("missing zero_post")
    if kinds and kinds[0] != "zero_pre":
        failures.append("observation sequence must start with zero_pre")
    if kinds and kinds[-1] != "zero_post":
        failures.append("observation sequence must end with zero_post")
    if len({p["mass_kg"] for p in up}) < 3:
        failures.append("need >=3 ascending masses")
    up_masses = [p["mass_kg"] for p in up]
    down_masses = [p["mass_kg"] for p in down]
    if len(up_masses) >= 2 and not all(b > a for a, b in zip(up_masses, up_masses[1:])):
        failures.append("load_up masses must be strictly ascending")
    if len(down_masses) >= 2 and not all(b < a for a, b in zip(down_masses, down_masses[1:])):
        failures.append("load_down masses must be strictly descending")
    if len(paired) < 2:
        failures.append("need >=2 paired masses for hysteresis")
    if not val:
        failures.append("need independent validation mass")

    for p in obs + val:
        if p["mass_kg"] < 0:
            failures.append("pilot masses must be nonnegative")
        if p["mass_kg"] > HARD_MAX_PILOT_MASS_KG:
            failures.append(f"pilot mass exceeds hard {HARD_MAX_PILOT_MASS_KG:g} kg screening ceiling")
        if p["duration_s"] < limits["min_duration_s"]:
            failures.append(f'{p["path"]}: short plateau')
        if p["coverage"] < limits["min_coverage"]:
            failures.append(f'{p["path"]}: low coverage')
        if not p["monotonic"]:
            failures.append(f'{p["path"]}: non-monotonic timestamps')
        if p["logger_hx711_sps"] is None:
            failures.append(f'{p["path"]}: missing hx711_sps logger header')
        elif rate in (10, 80) and p["logger_hx711_sps"] != rate:
            failures.append(f'{p["path"]}: logger hx711_sps disagrees with manifest')

    for p in val:
        if p["mass_kg"] <= 0:
            failures.append("validation mass must be positive")
        if p["mass_kg"] in cal_masses:
            failures.append("validation mass must be independent of calibration masses")

    metrics = {key: None for key in (
        "r2", "residual_fs", "hysteresis_fs", "zero_return_fs",
        "validation_error", "noise_fs",
    )}
    fit = None
    full_scale_n = max((p["force_n"] for p in up), default=0.0)
    if pre and up and full_scale_n > 0:
        fit = _fit(pre[:1] + up)
        metrics["r2"] = fit["r2"]
        metrics["residual_fs"] = max(
            abs(_force(p["mean"], fit) - p["force_n"]) / full_scale_n
            for p in pre[:1] + up
        )
        metrics["noise_fs"] = max(
            (p["std"] / abs(fit["counts_per_n"])) / full_scale_n
            for p in obs + val
        )
        if paired:
            metrics["hysteresis_fs"] = max(
                abs(
                    fmean(_force(p["mean"], fit) for p in up if p["mass_kg"] == mass)
                    - fmean(_force(p["mean"], fit) for p in down if p["mass_kg"] == mass)
                ) / full_scale_n
                for mass in paired
            )
        if post:
            metrics["zero_return_fs"] = abs(
                _force(fmean(p["mean"] for p in post), fit)
                - _force(fmean(p["mean"] for p in pre), fit)
            ) / full_scale_n
        positive_val = [p for p in val if p["force_n"] > 0]
        if positive_val:
            metrics["validation_error"] = max(
                abs(_force(p["mean"], fit) - p["force_n"]) / p["force_n"]
                for p in positive_val
            )
        checks = [
            ("r2", ">=", "min_r2"),
            ("residual_fs", "<=", "max_residual_fs"),
            ("hysteresis_fs", "<=", "max_hysteresis_fs"),
            ("zero_return_fs", "<=", "max_zero_return_fs"),
            ("validation_error", "<=", "max_validation_error"),
            ("noise_fs", "<=", "max_noise_fs"),
        ]
        for name, op, limit_name in checks:
            value = metrics[name]
            if value is None:
                failures.append(f"{name} unavailable")
            elif op == ">=" and value < limits[limit_name]:
                failures.append(f"{name} below limit")
            elif op == "<=" and value > limits[limit_name]:
                failures.append(f"{name} above limit")

    mechanical = manifest.get("mechanical", {})
    for key in ("vendor_pattern_verified", "fixed_loaded_orientation_verified", "screw_stack_verified"):
        if mechanical.get(key) is not True:
            failures.append(f"mechanical.{key} must be true")
    unloaded_gap = mechanical.get("stop_gap_unloaded_mm")
    loaded_gap = mechanical.get("stop_gap_min_loaded_mm")
    if unloaded_gap is None or not limits["min_unloaded_gap_mm"] <= float(unloaded_gap) <= limits["max_unloaded_gap_mm"]:
        failures.append("unloaded stop gap invalid")
    if loaded_gap is None or float(loaded_gap) < limits["min_loaded_gap_mm"]:
        failures.append("loaded stop gap invalid")
    if unloaded_gap is not None and loaded_gap is not None and float(loaded_gap) > float(unloaded_gap):
        failures.append("loaded gap exceeds unloaded gap")

    sources = {
        str(Path(p["path"]).resolve().relative_to(base)): p["sha256"]
        for p in obs + val
    }
    report = {
        "schema_version": 1,
        "authority": "x1_one_zone_pilot",
        "scope": "unpowered_fit_rig_only",
        "hardware_ids": hardware_ids,
        "channel": channel,
        "hx711_sps": rate,
        "hard_max_pilot_mass_kg": HARD_MAX_PILOT_MASS_KG,
        "acquisition": acquisition,
        "thresholds": limits,
        "metrics": metrics,
        "linear_fit": fit,
        "mechanical": mechanical,
        "source_fingerprints": sources,
        "manifest_sha256": _sha(path),
        "qualification_tool_sha256": _tool_sha256(),
        "failures": sorted(set(failures)),
        "qualified_for_four_zone_duplication": not failures,
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report
