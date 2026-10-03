"""Canonical Issue #61 fit-pilot calibration-mass reference validation."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from statistics import fmean
from typing import Any

HARD_MAX_PILOT_MASS_KG = 20.0
MIN_CALIBRATION_MASS_COUNT = 3
VALIDATION_MASS_COUNT = 1
MAX_RELATIVE_REFERENCE_UNCERTAINTY = 0.005
ALLOWED_EVIDENCE_TYPES = {"REFERENCE_MASS", "INDEPENDENT_SCALE"}
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


def _timestamp_ok(value: Any) -> bool:
    if not _nonempty(value):
        return False
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return dt.tzinfo is not None and dt.utcoffset() is not None


def _close(a: float, b: float, *, abs_tol: float = 1e-9) -> bool:
    return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=abs_tol)


def _validate_reference_mass(
    item: dict,
    prefix: str,
    errors: list[str],
) -> dict:
    evidence = item.get("reference_mass_evidence")
    if not isinstance(evidence, dict):
        errors.append(f"{prefix}.reference_mass_evidence must be an object")
        return {}

    source = evidence.get("source_reference")
    documented_mass = evidence.get("documented_mass_kg")
    documented_uncertainty = evidence.get("documented_uncertainty_kg")
    if not _nonempty(source):
        errors.append(f"{prefix}: reference mass requires source_reference")
    if not _positive(documented_mass):
        errors.append(f"{prefix}: documented_mass_kg must be positive")
    if not _positive(documented_uncertainty):
        errors.append(f"{prefix}: documented_uncertainty_kg must be positive")

    declared_mass = item.get("declared_mass_kg")
    declared_uncertainty = item.get("declared_uncertainty_kg")
    if _positive(documented_mass) and _positive(declared_mass):
        if not _close(float(documented_mass), float(declared_mass)):
            errors.append(
                f"{prefix}: declared_mass_kg must match documented_mass_kg"
            )
    if _positive(documented_uncertainty) and _positive(declared_uncertainty):
        if float(declared_uncertainty) + 1e-12 < float(documented_uncertainty):
            errors.append(
                f"{prefix}: declared_uncertainty_kg cannot be smaller than "
                "documented_uncertainty_kg"
            )

    return {
        "evidence_type": "REFERENCE_MASS",
        "source_reference": source,
        "uncertainty_floor_kg": (
            float(documented_uncertainty)
            if _positive(documented_uncertainty)
            else None
        ),
    }


def _validate_scale_mass(
    item: dict,
    prefix: str,
    errors: list[str],
) -> dict:
    evidence = item.get("independent_scale_evidence")
    if not isinstance(evidence, dict):
        errors.append(f"{prefix}.independent_scale_evidence must be an object")
        return {}

    for key in (
        "scale_manufacturer",
        "scale_model",
        "stated_accuracy_source",
    ):
        if not _nonempty(evidence.get(key)):
            errors.append(f"{prefix}: independent scale requires {key}")

    for key in (
        "capacity_kg",
        "resolution_kg",
        "conservative_accuracy_limit_kg",
    ):
        if not _positive(evidence.get(key)):
            errors.append(f"{prefix}: {key} must be positive")

    if evidence.get("zero_check_before") is not True:
        errors.append(f"{prefix}: zero_check_before must be true")
    if evidence.get("zero_check_after") is not True:
        errors.append(f"{prefix}: zero_check_after must be true")

    readings = evidence.get("repeated_readings_kg")
    if not isinstance(readings, list) or len(readings) < 3:
        errors.append(f"{prefix}: at least three repeated_readings_kg are required")
        readings = []
    elif not all(_positive(value) for value in readings):
        errors.append(f"{prefix}: repeated_readings_kg must all be positive")
        readings = []

    mean_reading = fmean(float(v) for v in readings) if readings else None
    half_range = (
        (max(float(v) for v in readings) - min(float(v) for v in readings)) / 2.0
        if readings
        else None
    )

    declared_mass = item.get("declared_mass_kg")
    declared_uncertainty = item.get("declared_uncertainty_kg")
    if mean_reading is not None and _positive(declared_mass):
        # Do not require matching every displayed digit. Require consistency within
        # half of one declared display increment.
        resolution = evidence.get("resolution_kg")
        tolerance = (
            float(resolution) / 2.0
            if _positive(resolution)
            else 1e-9
        )
        if not math.isclose(
            float(declared_mass),
            mean_reading,
            rel_tol=0.0,
            abs_tol=tolerance + 1e-12,
        ):
            errors.append(
                f"{prefix}: declared_mass_kg is inconsistent with repeated reading mean"
            )

    uncertainty_floor = None
    if (
        _positive(evidence.get("conservative_accuracy_limit_kg"))
        and _positive(evidence.get("resolution_kg"))
        and half_range is not None
    ):
        uncertainty_floor = (
            float(evidence["conservative_accuracy_limit_kg"])
            + float(evidence["resolution_kg"]) / 2.0
            + float(half_range)
        )
        if _positive(declared_uncertainty):
            if float(declared_uncertainty) + 1e-12 < uncertainty_floor:
                errors.append(
                    f"{prefix}: declared_uncertainty_kg is smaller than conservative "
                    "scale uncertainty floor (accuracy + half-resolution + repeatability half-range)"
                )

    capacity = evidence.get("capacity_kg")
    if _positive(capacity) and _positive(declared_mass):
        if float(declared_mass) > float(capacity):
            errors.append(f"{prefix}: declared mass exceeds scale capacity")

    return {
        "evidence_type": "INDEPENDENT_SCALE",
        "scale_manufacturer": evidence.get("scale_manufacturer"),
        "scale_model": evidence.get("scale_model"),
        "stated_accuracy_source": evidence.get("stated_accuracy_source"),
        "reading_count": len(readings),
        "reading_mean_kg": mean_reading,
        "repeatability_half_range_kg": half_range,
        "uncertainty_floor_kg": uncertainty_floor,
    }


def validate(record: dict) -> dict:
    errors: list[str] = []

    if record.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if record.get("scope") != "x1_fit_pilot_mass_reference_record":
        errors.append("wrong mass-reference record scope")
    if record.get("issue") != 61:
        errors.append("mass-reference issue must be 61")
    if not _nonempty(record.get("reference_set_id")):
        errors.append("reference_set_id must be nonempty")
    if not _timestamp_ok(record.get("measured_at_utc")):
        errors.append("measured_at_utc must be an offset-aware ISO-8601 timestamp")

    policy = record.get("screening_policy")
    if not isinstance(policy, dict):
        errors.append("screening_policy must be an object")
        policy = {}
    if policy.get("max_mass_kg") != HARD_MAX_PILOT_MASS_KG:
        errors.append("screening_policy.max_mass_kg must equal canonical 20 kg limit")
    if policy.get("min_calibration_mass_count") != MIN_CALIBRATION_MASS_COUNT:
        errors.append("screening_policy.min_calibration_mass_count mismatch")
    if policy.get("validation_mass_count") != VALIDATION_MASS_COUNT:
        errors.append("screening_policy.validation_mass_count mismatch")
    if policy.get("max_relative_reference_uncertainty") != MAX_RELATIVE_REFERENCE_UNCERTAINTY:
        errors.append("screening_policy.max_relative_reference_uncertainty mismatch")

    masses = record.get("masses")
    if not isinstance(masses, list) or not masses:
        errors.append("masses must be a nonempty list")
        masses = []

    mass_ids: set[str] = set()
    normalized: list[dict] = []
    calibration_values: list[float] = []
    validation_values: list[float] = []

    for index, item in enumerate(masses):
        prefix = f"masses[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue

        mass_id = item.get("mass_id")
        if not _nonempty(mass_id):
            errors.append(f"{prefix}.mass_id must be nonempty")
            mass_id = f"<mass-{index}>"
        elif mass_id in mass_ids:
            errors.append(f"duplicate mass_id: {mass_id}")
        else:
            mass_ids.add(mass_id)

        role = item.get("role")
        evidence_type = item.get("evidence_type")
        mass = item.get("declared_mass_kg")
        uncertainty = item.get("declared_uncertainty_kg")

        if role not in ALLOWED_ROLES:
            errors.append(f"{mass_id}: role must be CALIBRATION or VALIDATION")
        if evidence_type not in ALLOWED_EVIDENCE_TYPES:
            errors.append(
                f"{mass_id}: evidence_type must be REFERENCE_MASS or INDEPENDENT_SCALE"
            )
        if not _positive(mass):
            errors.append(f"{mass_id}: declared_mass_kg must be positive")
        elif float(mass) > HARD_MAX_PILOT_MASS_KG:
            errors.append(
                f"{mass_id}: declared mass exceeds hard {HARD_MAX_PILOT_MASS_KG:g} kg limit"
            )
        if not _positive(uncertainty):
            errors.append(f"{mass_id}: declared_uncertainty_kg must be positive")

        relative_uncertainty = None
        if _positive(mass) and _positive(uncertainty):
            relative_uncertainty = float(uncertainty) / float(mass)
            if relative_uncertainty > MAX_RELATIVE_REFERENCE_UNCERTAINTY + 1e-12:
                errors.append(
                    f"{mass_id}: relative reference uncertainty exceeds "
                    f"{MAX_RELATIVE_REFERENCE_UNCERTAINTY:.3%} screening limit"
                )
            if float(uncertainty) >= float(mass):
                errors.append(f"{mass_id}: uncertainty must be smaller than mass")

        evidence_summary = {}
        if evidence_type == "REFERENCE_MASS":
            evidence_summary = _validate_reference_mass(item, mass_id, errors)
        elif evidence_type == "INDEPENDENT_SCALE":
            evidence_summary = _validate_scale_mass(item, mass_id, errors)

        if role == "CALIBRATION" and _positive(mass):
            calibration_values.append(float(mass))
        if role == "VALIDATION" and _positive(mass):
            validation_values.append(float(mass))

        normalized.append(
            {
                "mass_id": mass_id,
                "role": role,
                "evidence_type": evidence_type,
                "mass_kg": float(mass) if _positive(mass) else None,
                "uncertainty_kg": (
                    float(uncertainty) if _positive(uncertainty) else None
                ),
                "relative_uncertainty": relative_uncertainty,
                "evidence_summary": evidence_summary,
            }
        )

    if len(calibration_values) < MIN_CALIBRATION_MASS_COUNT:
        errors.append(
            f"need at least {MIN_CALIBRATION_MASS_COUNT} calibration masses"
        )
    if len(set(calibration_values)) != len(calibration_values):
        errors.append("calibration masses must be unique")
    if len(validation_values) != VALIDATION_MASS_COUNT:
        errors.append("need exactly one validation mass")
    if (
        len(validation_values) == 1
        and any(
            _close(validation_values[0], value)
            for value in calibration_values
        )
    ):
        errors.append("validation mass must be independent of calibration masses")

    claims = record.get("claims")
    if not isinstance(claims, dict):
        errors.append("claims must be an object")
        claims = {}
    for key in (
        "nist_traceable",
        "legal_metrology",
        "commercial_measurement_authority",
        "load_cell_performance_authority",
        "four_zone_duplication_authorized",
        "fabrication_authority",
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if claims.get(key) is not False:
            errors.append(f"claims.{key} must be false")

    calibration = sorted(
        (m for m in normalized if m["role"] == "CALIBRATION"),
        key=lambda m: (float("inf") if m["mass_kg"] is None else m["mass_kg"]),
    )
    validation = [m for m in normalized if m["role"] == "VALIDATION"]

    report = {
        "schema_version": 1,
        "authority": "x1_fit_pilot_mass_reference",
        "valid": not errors,
        "errors": sorted(set(errors)),
        "reference_set_id": record.get("reference_set_id"),
        "record_sha256": _digest(record),
        "screening_policy": {
            "hard_max_pilot_mass_kg": HARD_MAX_PILOT_MASS_KG,
            "minimum_calibration_mass_count": MIN_CALIBRATION_MASS_COUNT,
            "validation_mass_count": VALIDATION_MASS_COUNT,
            "max_relative_reference_uncertainty": MAX_RELATIVE_REFERENCE_UNCERTAINTY,
        },
        "calibration_masses": calibration,
        "validation_masses": validation,
        "nist_traceable": False,
        "legal_metrology": False,
        "commercial_measurement_authority": False,
        "load_cell_performance_authority": False,
        "four_zone_duplication_authorized": False,
        "fabrication_authority": False,
        "powered_operation_authorized": False,
        "public_operation_authorized": False,
        "dog_accompanied_operation_authorized": False,
        "interpretation_boundary": (
            "This authority establishes only the recorded X1 screening mass values "
            "and conservative uncertainty evidence. It is not a NIST traceability, "
            "legal-metrology, load-cell performance, fabrication, or ride authority."
        ),
    }
    report["authority_fingerprint_sha256"] = _digest(report)
    return report


