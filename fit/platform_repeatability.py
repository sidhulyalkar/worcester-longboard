"""Issue #63 off-axis platform repeatability qualification."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from statistics import fmean

from fit.pilot_qualification import G, LIMITS
from fit.raw_log import CHANNELS, parse_text

REQUIRED_POSITIONS = ("CENTER", "+X", "-X", "+Y", "-Y")
MIN_REPEATS_PER_POSITION = 3
PAD_LENGTH_MM = 105.0
PAD_WIDTH_MM = 78.0


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _valid_authority(report: dict, expected: str) -> bool:
    if report.get("authority") != expected:
        return False
    actual = report.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        return False
    unsigned = dict(report)
    unsigned.pop("authority_fingerprint_sha256", None)
    return actual == _digest(unsigned)


def _resolve(base: Path, relative: str, label: str) -> Path:
    candidate = (base / relative).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"{label} escapes session directory: {relative}") from exc
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


def _read_plateau(
    path: Path,
    channel: str,
    expected_sps: int,
    min_duration_s: float,
    min_coverage: float,
) -> tuple[dict, list[str]]:
    failures: list[str] = []
    text = path.read_text(encoding="utf-8")
    rows = parse_text(text)
    if not rows:
        return {}, [f"{path}: empty log"]

    try:
        idx = CHANNELS.index(channel)
    except ValueError as exc:
        raise ValueError(f"unknown channel {channel!r}") from exc

    vals = [
        row.raw[idx]
        for row in rows
        if (row.load_valid_mask & (1 << idx)) and row.raw[idx] is not None
    ]
    if not vals:
        return {}, [f"{path}: no valid {channel} samples"]

    coverage = len(vals) / len(rows)
    duration_s = max(0.0, (rows[-1].t_us - rows[0].t_us) / 1e6)
    monotonic = all(b.t_us > a.t_us for a, b in zip(rows, rows[1:]))
    header_sps = _logger_sps(text)

    if duration_s < min_duration_s:
        failures.append(f"{path}: short plateau")
    if coverage < min_coverage:
        failures.append(f"{path}: low coverage")
    if not monotonic:
        failures.append(f"{path}: non-monotonic timestamps")
    if header_sps is None:
        failures.append(f"{path}: missing hx711_sps logger header")
    elif header_sps != expected_sps:
        failures.append(f"{path}: logger hx711_sps disagrees with one-zone authority")

    return {
        "path": str(path),
        "mean_raw": fmean(vals),
        "coverage": coverage,
        "duration_s": duration_s,
        "logger_hx711_sps": header_sps,
        "sha256": _sha(path),
    }, failures


def _force(raw: float, fit: dict) -> float:
    return (raw - float(fit["intercept"])) / float(fit["counts_per_n"])


def _one_zone_contract(authority: dict) -> tuple[dict, list[str]]:
    failures: list[str] = []
    if not _valid_authority(authority, "x1_one_zone_pilot"):
        failures.append("one-zone authority fingerprint/type is invalid")
    if authority.get("scope") != "unpowered_fit_rig_only":
        failures.append("one-zone authority scope mismatch")
    if authority.get("qualified_for_four_zone_duplication") is not True:
        failures.append("one-zone authority must have passed Issue #4")
    if authority.get("powered_operation_authorized") is not False:
        failures.append("one-zone authority violates powered-operation boundary")

    fit = authority.get("linear_fit")
    if not isinstance(fit, dict):
        failures.append("one-zone authority linear_fit must be an object")
        fit = {}
    for key in ("intercept", "counts_per_n"):
        value = fit.get(key)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
        ):
            failures.append(f"one-zone linear_fit.{key} must be finite")
    if isinstance(fit.get("counts_per_n"), (int, float)) and abs(float(fit["counts_per_n"])) < 1e-12:
        failures.append("one-zone counts_per_n cannot be zero")

    channel = authority.get("channel")
    if channel not in CHANNELS:
        failures.append("one-zone authority channel is invalid")

    sps = authority.get("hx711_sps")
    if sps not in (10, 80):
        failures.append("one-zone authority hx711_sps must be 10 or 80")

    provenance = authority.get("mass_reference_provenance")
    if not isinstance(provenance, dict):
        failures.append("one-zone mass_reference_provenance must be an object")
        provenance = {}
    entries = provenance.get("mass_entries")
    if not isinstance(entries, list):
        failures.append("one-zone mass_reference_provenance.mass_entries must be a list")
        entries = []

    validation = [
        item
        for item in entries
        if isinstance(item, dict) and item.get("role") == "VALIDATION"
    ]
    if len(validation) != 1:
        failures.append("one-zone authority must expose exactly one validation mass")
        validation_entry = {}
    else:
        validation_entry = validation[0]

    for key in ("mass_id", "mass_kg", "uncertainty_kg"):
        value = validation_entry.get(key)
        if key == "mass_id":
            if not isinstance(value, str) or not value.strip():
                failures.append("validation mass_id must be nonempty")
        elif (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or float(value) <= 0
        ):
            failures.append(f"validation {key} must be positive")

    thresholds = authority.get("thresholds")
    if not isinstance(thresholds, dict):
        failures.append("one-zone thresholds must be an object")
        thresholds = {}

    contract = {
        "channel": channel,
        "hx711_sps": sps,
        "linear_fit": fit,
        "validation_mass": validation_entry,
        "min_duration_s": max(
            LIMITS["min_duration_s"],
            float(thresholds.get("min_duration_s", LIMITS["min_duration_s"])),
        ),
        "min_coverage": max(
            LIMITS["min_coverage"],
            float(thresholds.get("min_coverage", LIMITS["min_coverage"])),
        ),
        "max_validation_error": min(
            LIMITS["max_validation_error"],
            float(
                thresholds.get(
                    "max_validation_error",
                    LIMITS["max_validation_error"],
                )
            ),
        ),
        "max_zero_return_fs": min(
            LIMITS["max_zero_return_fs"],
            float(
                thresholds.get(
                    "max_zero_return_fs",
                    LIMITS["max_zero_return_fs"],
                )
            ),
        ),
        "min_loaded_gap_mm": max(
            LIMITS["min_loaded_gap_mm"],
            float(
                thresholds.get(
                    "min_loaded_gap_mm",
                    LIMITS["min_loaded_gap_mm"],
                )
            ),
        ),
    }

    calibration = [
        item
        for item in entries
        if isinstance(item, dict)
        and item.get("role") == "CALIBRATION"
        and isinstance(item.get("mass_kg"), (int, float))
    ]
    if not calibration:
        failures.append("one-zone authority has no calibration masses")
        contract["full_scale_force_n"] = None
    else:
        contract["full_scale_force_n"] = max(
            float(item["mass_kg"]) * G for item in calibration
        )

    return contract, failures


def qualify(manifest: dict, one_zone_authority: dict, base: Path) -> dict:
    failures: list[str] = []
    if manifest.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    if manifest.get("scope") != "x1_fit_platform_repeatability_trial":
        failures.append("wrong platform repeatability scope")
    if manifest.get("issue") != 63:
        failures.append("platform repeatability issue must be 63")
    if not isinstance(manifest.get("session_id"), str) or not manifest["session_id"].strip():
        failures.append("session_id must be nonempty")

    for key in (
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if manifest.get(key) is not False:
            failures.append(f"{key} must be false")

    contract, contract_failures = _one_zone_contract(one_zone_authority)
    failures.extend(contract_failures)

    linked_fp = manifest.get("one_zone_authority_fingerprint_sha256")
    if linked_fp != one_zone_authority.get("authority_fingerprint_sha256"):
        failures.append("manifest does not link the supplied one-zone authority")

    authority_path = manifest.get("one_zone_authority_path")
    if not isinstance(authority_path, str) or not authority_path.strip():
        failures.append("one_zone_authority_path must be nonempty")
    else:
        copied_path = _resolve(base, authority_path, "one-zone authority")
        try:
            copied = json.loads(copied_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(f"copied one-zone authority unreadable: {exc}")
        else:
            if copied != one_zone_authority:
                failures.append("copied one-zone authority does not match supplied authority")

    pad = manifest.get("zone_pad")
    if not isinstance(pad, dict):
        failures.append("zone_pad must be an object")
        pad = {}
    for key, expected in (
        ("length_mm", PAD_LENGTH_MM),
        ("width_mm", PAD_WIDTH_MM),
    ):
        value = pad.get(key)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or not math.isclose(float(value), expected, abs_tol=1e-9)
        ):
            failures.append(
                f"zone_pad.{key} must match {expected:g} mm pilot pad"
            )

    interface = manifest.get("load_interface")
    if not isinstance(interface, dict):
        failures.append("load_interface must be an object")
        interface = {}
    if not isinstance(interface.get("interface_id"), str) or not interface["interface_id"].strip():
        failures.append("load_interface.interface_id must be nonempty")
    for key in ("contact_length_mm", "contact_width_mm"):
        value = interface.get(key)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or float(value) <= 0
        ):
            failures.append(f"load_interface.{key} must be positive")

    acquisition = manifest.get("acquisition")
    if not isinstance(acquisition, dict):
        failures.append("acquisition must be an object")
        acquisition = {}
    for key in (
        "no_rezero_between_position_runs",
        "no_recalibration_between_position_runs",
        "fixture_remained_secured",
    ):
        if acquisition.get(key) is not True:
            failures.append(f"acquisition.{key} must be true")

    placements = manifest.get("placements")
    if not isinstance(placements, list):
        failures.append("placements must be a list")
        placements = []

    by_id: dict[str, dict] = {}
    for item in placements:
        if not isinstance(item, dict):
            failures.append("placement entries must be objects")
            continue
        pid = item.get("position_id")
        if pid not in REQUIRED_POSITIONS:
            failures.append(f"invalid position_id: {pid!r}")
            continue
        if pid in by_id:
            failures.append(f"duplicate position_id: {pid}")
            continue
        by_id[pid] = item

    if set(by_id) != set(REQUIRED_POSITIONS):
        failures.append("placements must contain exactly CENTER,+X,-X,+Y,-Y")

    def numeric(item: dict, key: str, pid: str) -> float | None:
        value = item.get(key)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
        ):
            failures.append(f"{pid}.{key} must be finite")
            return None
        return float(value)

    position_geometry: dict[str, tuple[float, float]] = {}
    all_run_results: list[dict] = []
    position_results: dict[str, dict] = {}
    source_fingerprints: dict[str, str] = {}

    mass = contract.get("validation_mass", {}).get("mass_kg")
    uncertainty = contract.get("validation_mass", {}).get("uncertainty_kg")
    reference_force = (
        float(mass) * G
        if isinstance(mass, (int, float)) and float(mass) > 0
        else None
    )
    uncertainty_force = (
        float(uncertainty) * G
        if isinstance(uncertainty, (int, float)) and float(uncertainty) > 0
        else None
    )

    for pid in REQUIRED_POSITIONS:
        item = by_id.get(pid)
        if item is None:
            continue
        cx = numeric(item, "centroid_x_mm", pid)
        cy = numeric(item, "centroid_y_mm", pid)
        clen = numeric(item, "contact_length_mm", pid)
        cwid = numeric(item, "contact_width_mm", pid)
        gap = numeric(item, "stop_clearance_min_mm", pid)
        if cx is not None and cy is not None:
            position_geometry[pid] = (cx, cy)

        if clen is not None and isinstance(interface.get("contact_length_mm"), (int, float)):
            if not math.isclose(clen, float(interface["contact_length_mm"]), abs_tol=1e-9):
                failures.append(f"{pid}: contact_length_mm differs from load interface")
        if cwid is not None and isinstance(interface.get("contact_width_mm"), (int, float)):
            if not math.isclose(cwid, float(interface["contact_width_mm"]), abs_tol=1e-9):
                failures.append(f"{pid}: contact_width_mm differs from load interface")

        if None not in (cx, cy, clen, cwid):
            if abs(cx) + clen / 2.0 > PAD_LENGTH_MM / 2.0 + 1e-9:
                failures.append(f"{pid}: contact footprint exceeds pad length")
            if abs(cy) + cwid / 2.0 > PAD_WIDTH_MM / 2.0 + 1e-9:
                failures.append(f"{pid}: contact footprint exceeds pad width")

        if gap is not None and gap < contract.get("min_loaded_gap_mm", LIMITS["min_loaded_gap_mm"]):
            failures.append(f"{pid}: stop clearance below qualified minimum")

        if item.get("fully_supported") is not True:
            failures.append(f"{pid}: load footprint must be fully supported")
        for key in (
            "rocking_observed",
            "interference_observed",
            "cable_force_observed",
        ):
            if item.get(key) is not False:
                failures.append(f"{pid}: {key} must be false")

        logs = item.get("logs")
        if not isinstance(logs, list) or len(logs) < MIN_REPEATS_PER_POSITION:
            failures.append(
                f"{pid}: need at least {MIN_REPEATS_PER_POSITION} repeated logs"
            )
            logs = []

        run_results: list[dict] = []
        for index, relative in enumerate(logs):
            if not isinstance(relative, str) or not relative.strip():
                failures.append(f"{pid}: log path must be nonempty")
                continue
            path = _resolve(base, relative, f"{pid} log")
            try:
                plateau, p_failures = _read_plateau(
                    path,
                    contract.get("channel"),
                    contract.get("hx711_sps"),
                    contract.get("min_duration_s", LIMITS["min_duration_s"]),
                    contract.get("min_coverage", LIMITS["min_coverage"]),
                )
            except (OSError, ValueError) as exc:
                failures.append(f"{pid}: unreadable log {relative}: {exc}")
                continue
            failures.extend(p_failures)
            source_fingerprints[relative] = plateau.get("sha256")
            if not plateau:
                continue

            fit = contract.get("linear_fit", {})
            try:
                predicted_force = _force(plateau["mean_raw"], fit)
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                failures.append(f"{pid}: one-zone linear fit cannot be applied")
                continue

            nominal_error = None
            conservative_error = None
            if reference_force is not None and uncertainty_force is not None:
                nominal_error = abs(predicted_force - reference_force) / reference_force
                lower_reference = reference_force - uncertainty_force
                if lower_reference <= 0:
                    failures.append("validation reference uncertainty leaves no positive lower bound")
                else:
                    conservative_error = (
                        abs(predicted_force - reference_force) + uncertainty_force
                    ) / lower_reference
                    if conservative_error > contract.get(
                        "max_validation_error",
                        LIMITS["max_validation_error"],
                    ):
                        failures.append(
                            f"{pid}: run {index + 1} conservative validation error above limit"
                        )

            run = {
                "position_id": pid,
                "repeat_index": index + 1,
                "log": relative,
                "mean_raw": plateau["mean_raw"],
                "predicted_force_n": predicted_force,
                "predicted_mass_kg": predicted_force / G,
                "nominal_validation_error": nominal_error,
                "conservative_validation_error": conservative_error,
                "duration_s": plateau["duration_s"],
                "coverage": plateau["coverage"],
                "sha256": plateau["sha256"],
            }
            run_results.append(run)
            all_run_results.append(run)

        if run_results:
            predicted_forces = [r["predicted_force_n"] for r in run_results]
            conservative_errors = [
                r["conservative_validation_error"]
                for r in run_results
                if r["conservative_validation_error"] is not None
            ]
            position_results[pid] = {
                "repeat_count": len(run_results),
                "mean_predicted_force_n": fmean(predicted_forces),
                "mean_predicted_mass_kg": fmean(predicted_forces) / G,
                "force_repeatability_half_range_n": (
                    max(predicted_forces) - min(predicted_forces)
                ) / 2.0,
                "max_conservative_validation_error": (
                    max(conservative_errors) if conservative_errors else None
                ),
            }

    if all(pid in position_geometry for pid in REQUIRED_POSITIONS):
        radii = {
            pid: math.hypot(*position_geometry[pid])
            for pid in REQUIRED_POSITIONS
        }
        if any(
            radii["CENTER"] > radii[pid] + 1e-9
            for pid in REQUIRED_POSITIONS
            if pid != "CENTER"
        ):
            failures.append("CENTER must have the smallest radial centroid offset")
        if position_geometry["+X"][0] <= 0:
            failures.append("+X centroid_x_mm must be positive")
        if position_geometry["-X"][0] >= 0:
            failures.append("-X centroid_x_mm must be negative")
        if position_geometry["+Y"][1] <= 0:
            failures.append("+Y centroid_y_mm must be positive")
        if position_geometry["-Y"][1] >= 0:
            failures.append("-Y centroid_y_mm must be negative")

    zero_results: dict[str, dict] = {}
    for key in ("zero_pre_log", "zero_post_log"):
        relative = manifest.get(key)
        if not isinstance(relative, str) or not relative.strip():
            failures.append(f"{key} must be nonempty")
            continue
        path = _resolve(base, relative, key)
        try:
            plateau, p_failures = _read_plateau(
                path,
                contract.get("channel"),
                contract.get("hx711_sps"),
                contract.get("min_duration_s", LIMITS["min_duration_s"]),
                contract.get("min_coverage", LIMITS["min_coverage"]),
            )
        except (OSError, ValueError) as exc:
            failures.append(f"{key}: unreadable log: {exc}")
            continue
        failures.extend(p_failures)
        source_fingerprints[relative] = plateau.get("sha256")
        zero_results[key] = plateau

    zero_return_fs = None
    full_scale_force = contract.get("full_scale_force_n")
    if (
        "zero_pre_log" in zero_results
        and "zero_post_log" in zero_results
        and isinstance(full_scale_force, (int, float))
        and full_scale_force > 0
    ):
        try:
            pre_force = _force(
                zero_results["zero_pre_log"]["mean_raw"],
                contract["linear_fit"],
            )
            post_force = _force(
                zero_results["zero_post_log"]["mean_raw"],
                contract["linear_fit"],
            )
            zero_return_fs = abs(post_force - pre_force) / full_scale_force
            if zero_return_fs > contract.get(
                "max_zero_return_fs",
                LIMITS["max_zero_return_fs"],
            ):
                failures.append("zero_return_fs above qualified Issue #4 limit")
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            failures.append("could not compute zero return from one-zone fit")

    cross_position_spread_relative = None
    center_bias: dict[str, float | None] = {}
    if set(position_results) == set(REQUIRED_POSITIONS) and reference_force:
        means = {
            pid: position_results[pid]["mean_predicted_force_n"]
            for pid in REQUIRED_POSITIONS
        }
        cross_position_spread_relative = (
            max(means.values()) - min(means.values())
        ) / reference_force
        center = means["CENTER"]
        center_bias = {
            pid: (means[pid] - center) / reference_force
            for pid in REQUIRED_POSITIONS
        }

    report = {
        "schema_version": 1,
        "authority": "x1_fit_platform_repeatability",
        "scope": "unpowered_fit_platform_repeatability_only",
        "qualified": not failures,
        "position_repeatability_qualified": not failures,
        "issue": 63,
        "session_id": manifest.get("session_id"),
        "one_zone_authority_fingerprint_sha256": one_zone_authority.get(
            "authority_fingerprint_sha256"
        ),
        "validation_reference": {
            "mass_id": contract.get("validation_mass", {}).get("mass_id"),
            "mass_kg": mass,
            "uncertainty_kg": uncertainty,
        },
        "channel": contract.get("channel"),
        "hx711_sps": contract.get("hx711_sps"),
        "thresholds": {
            "max_validation_error": contract.get("max_validation_error"),
            "max_zero_return_fs": contract.get("max_zero_return_fs"),
            "min_loaded_gap_mm": contract.get("min_loaded_gap_mm"),
            "min_duration_s": contract.get("min_duration_s"),
            "min_coverage": contract.get("min_coverage"),
        },
        "position_results": position_results,
        "run_results": all_run_results,
        "zero_return_fs": zero_return_fs,
        "cross_position_spread_relative": cross_position_spread_relative,
        "bias_vs_center_relative": center_bias,
        "source_fingerprints": source_fingerprints,
        "errors": sorted(set(failures)),
        "four_zone_duplication_authorized": False,
        "ride_hardware_authority": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": (
            "A passing report verifies only that the tested one-zone assembly "
            "preserves the existing Issue #4 validation envelope across the declared "
            "platform positions. Cross-position spread is diagnostic and is not a "
            "new vendor accuracy specification or ride-structure authority."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report
