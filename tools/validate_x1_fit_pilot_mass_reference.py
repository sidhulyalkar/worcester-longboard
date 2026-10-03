#!/usr/bin/env python3
"""Validate Issue #61 mass-reference evidence for the X1 one-zone fit pilot."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_METHODS = {
    "INDEPENDENT_SCALE_MANUFACTURER_SPEC",
    "CALIBRATED_REFERENCE_MASSES",
}
ALLOWED_ROLES = {"CALIBRATION", "VALIDATION"}


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _positive(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0
    )


def _nonnegative(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) >= 0
    )


def _parse_time(errors: list[str], label: str, value: Any) -> None:
    if not _nonempty(value):
        errors.append(f"{label} must be a nonempty timezone-aware ISO-8601 timestamp")
        return
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label} is not valid ISO-8601")
        return
    if dt.tzinfo is None or dt.utcoffset() is None:
        errors.append(f"{label} must include a timezone offset")
        return
    dt.astimezone(timezone.utc)


def validate(data: dict) -> dict:
    errors: list[str] = []

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("scope") != "x1_fit_pilot_mass_reference_record":
        errors.append("wrong mass-reference scope")
    if data.get("issue") != 61:
        errors.append("mass-reference issue must be 61")
    if not _nonempty(data.get("reference_set_id")):
        errors.append("reference_set_id must be nonempty")
    _parse_time(errors, "measured_at_utc", data.get("measured_at_utc"))

    method = data.get("method")
    if method not in ALLOWED_METHODS:
        errors.append(
            "method must be one of " + ", ".join(sorted(ALLOWED_METHODS))
        )

    policy = data.get("uncertainty_policy")
    if not isinstance(policy, dict):
        errors.append("uncertainty_policy must be an object")
        max_rel = None
    else:
        max_rel = policy.get("max_relative_uncertainty_fraction")
        if not _positive(max_rel) or float(max_rel) > 0.005:
            errors.append(
                "max_relative_uncertainty_fraction must be positive and <=0.005"
            )

    for key in (
        "nist_traceability_claimed",
        "commercial_legal_metrology_claimed",
        "physical_sensor_qualification_authority",
        "four_zone_duplication_authorized",
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if data.get(key) is not False:
            errors.append(f"{key} must be false")

    instrument = data.get("instrument")
    if not isinstance(instrument, dict):
        errors.append("instrument must be an object")
        instrument = {}

    for key in ("manufacturer", "model"):
        if not _nonempty(instrument.get(key)):
            errors.append(f"instrument.{key} must be nonempty")

    capacity = instrument.get("capacity_kg")
    resolution = instrument.get("resolution_kg")
    if not _positive(capacity):
        errors.append("instrument.capacity_kg must be positive")
    if not _positive(resolution):
        errors.append("instrument.resolution_kg must be positive")

    stated_accuracy = instrument.get("stated_accuracy_abs_kg")
    certificate_u = instrument.get("certificate_expanded_uncertainty_kg")

    if method == "INDEPENDENT_SCALE_MANUFACTURER_SPEC":
        if not _positive(stated_accuracy):
            errors.append(
                "manufacturer-spec scale path requires positive stated_accuracy_abs_kg"
            )
        if not _nonempty(instrument.get("accuracy_source_reference")):
            errors.append(
                "manufacturer-spec scale path requires accuracy_source_reference"
            )
    elif method == "CALIBRATED_REFERENCE_MASSES":
        if not _positive(certificate_u):
            errors.append(
                "calibrated-reference path requires positive certificate_expanded_uncertainty_kg"
            )
        if not _nonempty(instrument.get("calibration_certificate_reference")):
            errors.append(
                "calibrated-reference path requires calibration_certificate_reference"
            )

    zero_checks = instrument.get("zero_checks_kg")
    if not isinstance(zero_checks, list) or len(zero_checks) < 3:
        errors.append("instrument.zero_checks_kg requires at least three checks")
        zero_span = None
    elif not all(
        isinstance(x, (int, float))
        and not isinstance(x, bool)
        and math.isfinite(float(x))
        for x in zero_checks
    ):
        errors.append("instrument.zero_checks_kg must contain finite numeric values")
        zero_span = None
    else:
        zero_span = max(float(x) for x in zero_checks) - min(
            float(x) for x in zero_checks
        )
        if _positive(resolution) and zero_span > 2.0 * float(resolution):
            errors.append("zero-check span exceeds two scale divisions")

    masses = data.get("masses")
    if not isinstance(masses, list) or len(masses) < 4:
        errors.append("masses must contain at least three calibration masses and one validation mass")
        masses = []

    seen_ids: set[str] = set()
    calibration_rows: list[dict] = []
    validation_rows: list[dict] = []
    accepted_values: list[float] = []
    mass_summaries: list[dict] = []

    for index, row in enumerate(masses):
        label = f"masses[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label} must be an object")
            continue
        mass_id = row.get("mass_id")
        if not _nonempty(mass_id):
            errors.append(f"{label}.mass_id must be nonempty")
            mass_id = f"<mass-{index}>"
        elif mass_id in seen_ids:
            errors.append(f"duplicate mass_id: {mass_id}")
        else:
            seen_ids.add(mass_id)

        role = row.get("role")
        if role not in ALLOWED_ROLES:
            errors.append(f"{mass_id}: role must be CALIBRATION or VALIDATION")
        elif role == "CALIBRATION":
            calibration_rows.append(row)
        else:
            validation_rows.append(row)

        if not _nonempty(row.get("object_description")):
            errors.append(f"{mass_id}: object_description must be nonempty")
        if not _nonempty(row.get("source_reference")):
            errors.append(f"{mass_id}: source_reference must be nonempty")

        accepted = row.get("accepted_mass_kg")
        declared_u = row.get("declared_expanded_uncertainty_kg")
        if not _positive(accepted):
            errors.append(f"{mass_id}: accepted_mass_kg must be positive")
            continue
        accepted = float(accepted)
        if accepted > 20.0:
            errors.append(f"{mass_id}: accepted_mass_kg exceeds Issue #4 hard 20 kg ceiling")
        accepted_values.append(accepted)

        if _positive(capacity) and accepted > float(capacity):
            errors.append(f"{mass_id}: accepted mass exceeds instrument capacity")

        if not _positive(declared_u):
            errors.append(
                f"{mass_id}: declared_expanded_uncertainty_kg must be positive"
            )
            continue
        declared_u = float(declared_u)

        repeats = row.get("repeat_measurements_kg")
        if method == "INDEPENDENT_SCALE_MANUFACTURER_SPEC":
            if not isinstance(repeats, list) or len(repeats) < 5:
                errors.append(
                    f"{mass_id}: scale path requires at least five repeat measurements"
                )
                repeats = []
            elif not all(_positive(x) for x in repeats):
                errors.append(f"{mass_id}: repeat measurements must be positive finite values")
                repeats = []
            if repeats:
                values = [float(x) for x in repeats]
                mean = statistics.fmean(values)
                span = max(values) - min(values)
                if abs(mean - accepted) > max(float(resolution or 0), 1e-12):
                    errors.append(
                        f"{mass_id}: accepted mass differs from repeat mean by more than one scale division"
                    )
                floor = max(
                    float(stated_accuracy or 0),
                    float(resolution or 0) / 2.0,
                    span / 2.0,
                    (zero_span or 0.0) / 2.0,
                )
            else:
                mean = None
                span = None
                floor = max(
                    float(stated_accuracy or 0),
                    float(resolution or 0) / 2.0,
                    (zero_span or 0.0) / 2.0,
                )
        else:
            mean = accepted
            span = 0.0
            floor = max(
                float(certificate_u or 0),
                float(resolution or 0) / 2.0,
                (zero_span or 0.0) / 2.0,
            )

        if declared_u + 1e-12 < floor:
            errors.append(
                f"{mass_id}: declared uncertainty {declared_u:g} kg is below conservative floor {floor:g} kg"
            )

        rel_u = declared_u / accepted
        if _positive(max_rel) and rel_u > float(max_rel) + 1e-12:
            errors.append(
                f"{mass_id}: relative uncertainty {rel_u:.6f} exceeds X1 limit {float(max_rel):.6f}"
            )

        mass_summaries.append(
            {
                "mass_id": mass_id,
                "role": role,
                "accepted_mass_kg": round(accepted, 9),
                "declared_expanded_uncertainty_kg": round(declared_u, 9),
                "relative_uncertainty_fraction": round(rel_u, 9),
                "repeat_mean_kg": None if mean is None else round(float(mean), 9),
                "repeat_span_kg": None if span is None else round(float(span), 9),
                "conservative_uncertainty_floor_kg": round(float(floor), 9),
            }
        )

    if len(calibration_rows) < 3:
        errors.append("at least three CALIBRATION masses are required")
    if len(validation_rows) != 1:
        errors.append("exactly one VALIDATION mass is required")
    if len(accepted_values) != len(set(round(x, 9) for x in accepted_values)):
        errors.append("all accepted mass values must be unique")

    calibration_values = sorted(
        float(row["accepted_mass_kg"])
        for row in calibration_rows
        if _positive(row.get("accepted_mass_kg"))
    )
    validation_value = (
        float(validation_rows[0]["accepted_mass_kg"])
        if len(validation_rows) == 1
        and _positive(validation_rows[0].get("accepted_mass_kg"))
        else None
    )
    if validation_value is not None and any(
        math.isclose(validation_value, value, rel_tol=0.0, abs_tol=1e-9)
        for value in calibration_values
    ):
        errors.append("validation mass must be independent from calibration masses")

    report = {
        "schema_version": 1,
        "authority": "x1_fit_pilot_mass_reference",
        "scope": "issue4_mass_reference_only",
        "valid": not errors,
        "errors": errors,
        "reference_set_id": data.get("reference_set_id"),
        "mass_reference_record_sha256": _digest(data),
        "method": method,
        "calibration_masses_kg": calibration_values,
        "validation_mass_kg": validation_value,
        "mass_summaries": mass_summaries,
        "max_relative_uncertainty_fraction": (
            max(
                (row["relative_uncertainty_fraction"] for row in mass_summaries),
                default=None,
            )
        ),
        "nist_traceability_claimed": False,
        "commercial_legal_metrology_claimed": False,
        "physical_sensor_qualification_authority": False,
        "four_zone_duplication_authorized": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": (
            "A valid report establishes only the Issue #4 reference mass values and "
            "their declared conservative uncertainty. It is not a NIST traceability "
            "claim, legal-metrology certification, or load-cell performance authority."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = validate(json.loads(args.record.read_text(encoding="utf-8")))
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
