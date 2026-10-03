#!/usr/bin/env python3
"""Initialize a private Issue #63 one-zone platform-repeatability session."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "hardware/x1_fit_platform_repeatability_template.json"


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _valid_one_zone(authority: dict) -> None:
    if authority.get("authority") != "x1_one_zone_pilot":
        raise ValueError("authority must be x1_one_zone_pilot")
    actual = authority.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        raise ValueError("one-zone authority fingerprint is missing")
    unsigned = dict(authority)
    unsigned.pop("authority_fingerprint_sha256", None)
    if actual != _digest(unsigned):
        raise ValueError("one-zone authority fingerprint is invalid")
    if authority.get("scope") != "unpowered_fit_rig_only":
        raise ValueError("one-zone authority scope mismatch")
    if authority.get("qualified_for_four_zone_duplication") is not True:
        raise ValueError("one-zone authority must have passed Issue #4")
    if authority.get("powered_operation_authorized") is not False:
        raise ValueError("one-zone authority violates powered-operation boundary")

    mass = authority.get("mass_reference_provenance", {})
    entries = mass.get("mass_entries")
    if not isinstance(entries, list):
        raise ValueError("one-zone authority lacks mass-reference entries")
    validation = [
        item
        for item in entries
        if isinstance(item, dict) and item.get("role") == "VALIDATION"
    ]
    if len(validation) != 1:
        raise ValueError("one-zone authority must expose exactly one validation mass")

    fit = authority.get("linear_fit")
    if not isinstance(fit, dict):
        raise ValueError("one-zone authority lacks linear fit")
    if not isinstance(fit.get("counts_per_n"), (int, float)):
        raise ValueError("one-zone authority lacks counts_per_n")


def initialize(
    session_dir: Path,
    one_zone_authority_path: Path,
    session_id: str,
) -> dict:
    session_dir = session_dir.resolve()
    if session_dir.exists() and any(session_dir.iterdir()):
        raise FileExistsError(
            f"session directory is not empty: {session_dir}; use a fresh directory"
        )
    if not session_id.strip():
        raise ValueError("session_id must be nonempty")

    authority = json.loads(
        one_zone_authority_path.read_text(encoding="utf-8")
    )
    _valid_one_zone(authority)

    session_dir.mkdir(parents=True, exist_ok=True)
    raw = session_dir / "raw"
    provenance = session_dir / "provenance"
    raw.mkdir()
    provenance.mkdir()

    copied_authority = provenance / "one_zone_pilot_authority.json"
    shutil.copyfile(one_zone_authority_path, copied_authority)

    manifest = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    manifest["session_id"] = session_id
    manifest["one_zone_authority_fingerprint_sha256"] = authority[
        "authority_fingerprint_sha256"
    ]

    manifest_path = session_dir / "platform_repeatability_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    workspace = {
        "schema_version": 1,
        "scope": "x1_fit_platform_repeatability_workspace",
        "issue": 63,
        "session_id": session_id,
        "manifest": manifest_path.name,
        "one_zone_authority_fingerprint_sha256": authority[
            "authority_fingerprint_sha256"
        ],
        "one_zone_authority_path": str(one_zone_authority_path),
        "validation_mass": next(
            item
            for item in authority["mass_reference_provenance"]["mass_entries"]
            if item.get("role") == "VALIDATION"
        ),
        "linear_fit": authority["linear_fit"],
        "channel": authority["channel"],
        "hx711_sps": authority["hx711_sps"],
        "four_zone_duplication_authority": False,
        "fabrication_authority": False,
        "powered_operation_authority": False,
        "next_step": (
            "Fill measured contact geometry and mechanical checks, then capture "
            "three settled validation-mass plateaus at CENTER,+X,-X,+Y,-Y without "
            "re-zeroing or recalibrating between positions."
        ),
    }
    (session_dir / "workspace_manifest.json").write_text(
        json.dumps(workspace, indent=2) + "\n",
        encoding="utf-8",
    )
    return workspace


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir", type=Path)
    parser.add_argument("--one-zone-authority", type=Path, required=True)
    parser.add_argument("--session-id", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            initialize(
                args.session_dir,
                args.one_zone_authority,
                args.session_id,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
