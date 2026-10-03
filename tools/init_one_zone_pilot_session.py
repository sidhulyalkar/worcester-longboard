#!/usr/bin/env python3
"""Create a private one-zone pilot session from actual measured calibration masses."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path

HARD_MAX_PILOT_MASS_KG = 20.0


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _valid_selection(selection: dict, authority: dict) -> None:
    if authority.get("authority") != "x1_fit_pilot_hardware_selection":
        raise ValueError(
            "hardware selection authority must be x1_fit_pilot_hardware_selection"
        )
    actual = authority.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        raise ValueError("hardware selection authority fingerprint is missing")
    unsigned = dict(authority)
    unsigned.pop("authority_fingerprint_sha256", None)
    if actual != _digest(unsigned):
        raise ValueError("hardware selection authority fingerprint is invalid")
    if authority.get("valid") is not True:
        raise ValueError("hardware selection authority must be valid")
    if authority.get("selection_record_sha256") != _digest(selection):
        raise ValueError("hardware selection authority does not match selection record")
    if authority.get("exact_evidence_hardware_verified") is not True:
        raise ValueError("selection authority must verify exact evidence hardware")
    if authority.get("untouched_spares_preserved") is not True:
        raise ValueError("selection authority must preserve untouched spares")
    for key in (
        "physical_qualification_authority",
        "four_zone_duplication_authorized",
        "fabrication_authority",
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"hardware selection authority boundary violated: {key}")


def _selected_ids(authority: dict) -> tuple[str, str, str, str, str]:
    hardware = authority.get("hardware", {})
    load = hardware.get("load_cell", {})
    adc = hardware.get("hx711", {})
    mcu = hardware.get("mcu", {})
    values = (
        load.get("active_hardware_id"),
        load.get("spare_hardware_id"),
        adc.get("active_hardware_id"),
        adc.get("spare_hardware_id"),
        mcu.get("active_hardware_id") or "",
    )
    if any(not isinstance(value, str) for value in values):
        raise ValueError("hardware selection authority contains invalid hardware IDs")
    if not all(value.strip() for value in values[:4]):
        raise ValueError("hardware selection authority requires active/spare load-cell and HX711 IDs")
    if len(set(values[:4])) != 4:
        raise ValueError("active/spare load-cell and HX711 IDs must be distinct")
    return values


def _valid_mass_reference(record: dict, authority: dict) -> None:
    if authority.get("authority") != "x1_fit_pilot_mass_reference":
        raise ValueError(
            "mass reference authority must be x1_fit_pilot_mass_reference"
        )
    actual = authority.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        raise ValueError("mass reference authority fingerprint is missing")
    unsigned = dict(authority)
    unsigned.pop("authority_fingerprint_sha256", None)
    if actual != _digest(unsigned):
        raise ValueError("mass reference authority fingerprint is invalid")
    if authority.get("valid") is not True:
        raise ValueError("mass reference authority must be valid")
    if authority.get("mass_reference_record_sha256") != _digest(record):
        raise ValueError("mass reference authority does not match mass reference record")
    for key in (
        "nist_traceability_claimed",
        "commercial_legal_metrology_claimed",
        "physical_sensor_qualification_authority",
        "four_zone_duplication_authorized",
        "powered_operation_authorized",
        "public_operation_authorized",
        "dog_accompanied_operation_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"mass reference authority boundary violated: {key}")


def _mass_rows(authority: dict) -> tuple[list[dict], dict]:
    rows = authority.get("mass_summaries")
    if not isinstance(rows, list):
        raise ValueError("mass reference authority mass_summaries must be a list")
    calibration = [
        row for row in rows
        if isinstance(row, dict) and row.get("role") == "CALIBRATION"
    ]
    validation = [
        row for row in rows
        if isinstance(row, dict) and row.get("role") == "VALIDATION"
    ]
    if len(calibration) < 3 or len(validation) != 1:
        raise ValueError(
            "mass reference authority requires >=3 calibration masses and exactly one validation mass"
        )
    calibration = sorted(calibration, key=lambda row: float(row["accepted_mass_kg"]))
    values = [float(row["accepted_mass_kg"]) for row in calibration]
    if len(values) != len(set(values)):
        raise ValueError("mass reference calibration masses must be unique")
    val = float(validation[0]["accepted_mass_kg"])
    if any(math.isclose(val, x, rel_tol=0.0, abs_tol=1e-9) for x in values):
        raise ValueError("mass reference validation mass must be independent")
    return calibration, validation[0]


def _mass_slug(value: float) -> str:
    return f"{value:.10g}".replace(".", "p")


def build_manifest(
    args,
    selection: dict,
    selection_authority: dict,
    mass_reference: dict,
    mass_reference_authority: dict,
) -> dict:
    _valid_selection(selection, selection_authority)
    _valid_mass_reference(mass_reference, mass_reference_authority)
    (
        load_cell_id,
        load_cell_spare_id,
        hx711_id,
        hx711_spare_id,
        mcu_id,
    ) = _selected_ids(selection_authority)
    calibration_rows, validation_row = _mass_rows(mass_reference_authority)
    observations = [{"kind": "zero_pre", "mass_kg": 0.0, "mass_id": None, "log": "raw/zero_pre.csv"}]
    observations.extend(
        {
            "kind": "load_up",
            "mass_kg": float(row["accepted_mass_kg"]),
            "mass_id": row["mass_id"],
            "reference_uncertainty_kg": float(row["declared_expanded_uncertainty_kg"]),
            "log": f"raw/up_{_mass_slug(float(row['accepted_mass_kg']))}kg.csv",
        }
        for row in calibration_rows
    )
    observations.extend(
        {
            "kind": "load_down",
            "mass_kg": float(row["accepted_mass_kg"]),
            "mass_id": row["mass_id"],
            "reference_uncertainty_kg": float(row["declared_expanded_uncertainty_kg"]),
            "log": f"raw/down_{_mass_slug(float(row['accepted_mass_kg']))}kg.csv",
        }
        for row in reversed(calibration_rows[:-1])
    )
    observations.append({"kind": "zero_post", "mass_kg": 0.0, "mass_id": None, "log": "raw/zero_post.csv"})

    return {
        "schema_version": 1,
        "hardware_selection": {
            "selection_id": selection_authority["selection_id"],
            "selection_record_sha256": selection_authority["selection_record_sha256"],
            "selection_authority_fingerprint_sha256": selection_authority[
                "authority_fingerprint_sha256"
            ],
            "selection_record_path": "provenance/hardware_selection.json",
            "selection_authority_path": "provenance/hardware_selection_authority.json",
        },
        "mass_reference": {
            "reference_set_id": mass_reference_authority["reference_set_id"],
            "mass_reference_record_sha256": mass_reference_authority[
                "mass_reference_record_sha256"
            ],
            "mass_reference_authority_fingerprint_sha256": mass_reference_authority[
                "authority_fingerprint_sha256"
            ],
            "mass_reference_record_path": "provenance/mass_reference.json",
            "mass_reference_authority_path": "provenance/mass_reference_authority.json",
            "max_relative_uncertainty_fraction": mass_reference_authority[
                "max_relative_uncertainty_fraction"
            ],
        },
        "hardware_ids": {
            "load_cell_id": load_cell_id,
            "hx711_id": hx711_id,
            "pod_id": args.pod_id,
            "zone_pad_id": args.zone_pad_id,
            "mcu_id": mcu_id,
        },
        "spare_hardware_ids": {
            "load_cell_id": load_cell_spare_id,
            "hx711_id": hx711_spare_id,
        },
        "channel": args.channel,
        "hx711_sps": args.sps,
        "acquisition": {"rate_jumper_verified": False},
        "observations": observations,
        "validation": [
            {
                "mass_kg": float(validation_row["accepted_mass_kg"]),
                "mass_id": validation_row["mass_id"],
                "reference_uncertainty_kg": float(
                    validation_row["declared_expanded_uncertainty_kg"]
                ),
                "log": (
                    "raw/validation_"
                    + _mass_slug(float(validation_row["accepted_mass_kg"]))
                    + "kg.csv"
                ),
            }
        ],
        "mechanical": {
            "vendor_pattern_verified": False,
            "fixed_loaded_orientation_verified": False,
            "screw_stack_verified": False,
            "stop_gap_unloaded_mm": None,
            "stop_gap_min_loaded_mm": None,
        },
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("session_dir", type=Path)
    p.add_argument("--hardware-selection", type=Path, required=True)
    p.add_argument("--hardware-selection-authority", type=Path, required=True)
    p.add_argument("--pod-id", required=True)
    p.add_argument("--zone-pad-id", required=True)
    p.add_argument("--channel", choices=("left_heel", "left_forefoot", "right_heel", "right_forefoot"), default="left_heel")
    p.add_argument("--sps", type=int, choices=(10, 80), default=10)
    p.add_argument("--mass-reference", type=Path, required=True)
    p.add_argument("--mass-reference-authority", type=Path, required=True)
    args = p.parse_args()

    try:
        selection = json.loads(
            args.hardware_selection.read_text(encoding="utf-8")
        )
        selection_authority = json.loads(
            args.hardware_selection_authority.read_text(encoding="utf-8")
        )
        mass_reference = json.loads(
            args.mass_reference.read_text(encoding="utf-8")
        )
        mass_reference_authority = json.loads(
            args.mass_reference_authority.read_text(encoding="utf-8")
        )
        manifest = build_manifest(
            args,
            selection,
            selection_authority,
            mass_reference,
            mass_reference_authority,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    root = args.session_dir.resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"Refusing to overwrite nonempty session directory: {root}")
    (root / "raw").mkdir(parents=True, exist_ok=True)
    provenance = root / "provenance"
    provenance.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        args.hardware_selection,
        provenance / "hardware_selection.json",
    )
    shutil.copyfile(
        args.hardware_selection_authority,
        provenance / "hardware_selection_authority.json",
    )
    shutil.copyfile(
        args.mass_reference,
        provenance / "mass_reference.json",
    )
    shutil.copyfile(
        args.mass_reference_authority,
        provenance / "mass_reference_authority.json",
    )
    (root / "pilot_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    sequence = [
        f"{row['kind']}:{row['mass_kg']:g}kg" for row in manifest["observations"]
    ] + [f"validation:{manifest['validation'][0]['mass_kg']:g}kg"]
    (root / "NOTES.md").write_text(
        "# Private X1 one-zone pilot notes\n\n"
        "The manifest was generated from the fingerprinted Issue #61 mass-reference authority.\n"
        "Do not replace those values with nominal plate labels after capture.\n"
        "Keep transient load/unload periods out of plateau CSVs.\n"
        "The active load-cell/HX711 IDs are locked by Issue #59 selection evidence.\n"
        "Do not swap to the untouched spare inside this session; create a new selection authority and session instead.\n"
        "Set rate_jumper_verified=true only after physically checking the HX711 RATE state.\n\n"
        "## Capture order\n\n- " + "\n- ".join(sequence) + "\n",
        encoding="utf-8",
    )
    print(root)


if __name__ == "__main__":
    main()
