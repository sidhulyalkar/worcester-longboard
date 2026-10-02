#!/usr/bin/env python3
"""Initialize a private Worcester X1 inert environmental durability session."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "hardware/rev_c_environmental_trial_template.json"


def _valid_authority(data: dict, expected: str) -> bool:
    if data.get("authority") != expected or data.get("qualified") is not True:
        return False
    if data.get("powered_operation_authorized") is not False:
        return False
    actual = data.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        return False
    unsigned = dict(data)
    unsigned.pop("authority_fingerprint_sha256", None)
    try:
        payload = json.dumps(
            unsigned,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return False
    return actual == hashlib.sha256(payload).hexdigest()


def initialize(
    session_dir: Path,
    chassis_authority_path: Path,
    dummy_pack_authority_path: Path,
    candidate_enclosure_id: str,
    harness_revision_id: str,
) -> dict:
    session_dir = session_dir.resolve()
    if session_dir.exists() and any(session_dir.iterdir()):
        raise FileExistsError(
            f"session directory is not empty: {session_dir}; use a fresh private directory"
        )
    session_dir.mkdir(parents=True, exist_ok=True)

    chassis = json.loads(chassis_authority_path.read_text(encoding="utf-8"))
    dummy = json.loads(dummy_pack_authority_path.read_text(encoding="utf-8"))

    if not _valid_authority(chassis, "x1_rolling_chassis_physical"):
        raise ValueError(
            "chassis authority must be qualified, fingerprint-valid "
            "x1_rolling_chassis_physical"
        )
    if not _valid_authority(dummy, "x1_dummy_pack_mount"):
        raise ValueError(
            "dummy-pack authority must be qualified, fingerprint-valid "
            "x1_dummy_pack_mount"
        )

    manifest = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    manifest["session_id"] = session_dir.name
    manifest["chassis_authority_fingerprint_sha256"] = chassis.get(
        "authority_fingerprint_sha256", ""
    )
    manifest["dummy_pack_authority_fingerprint_sha256"] = dummy.get(
        "authority_fingerprint_sha256", ""
    )
    manifest["candidate_enclosure_id"] = candidate_enclosure_id
    manifest["harness_revision_id"] = harness_revision_id

    manifest_path = session_dir / "environmental_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    workspace = {
        "schema_version": 1,
        "scope": "rev_c_environmental_durability_workspace",
        "manifest": manifest_path.name,
        "chassis_authority_source": str(chassis_authority_path),
        "dummy_pack_authority_source": str(dummy_pack_authority_path),
        "reference_snapshot": (
            "hardware/rev_c_environmental_durability_snapshot_2026-10-01.json"
        ),
        "protocol": "docs/rev_c_environmental_durability.md",
        "physical_authority": False,
        "electrical_wet_operation_authority": False,
        "procurement_authority": False,
        "powered_operation_authority": False,
        "next_step": (
            "Inventory every exposed interface, then run only inert/disconnected "
            "contamination cycles from the protocol. No live traction battery or "
            "energized high-voltage interface belongs in this workspace."
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
    parser.add_argument("--chassis-authority", type=Path, required=True)
    parser.add_argument("--dummy-pack-authority", type=Path, required=True)
    parser.add_argument("--candidate-enclosure-id", required=True)
    parser.add_argument("--harness-revision-id", required=True)
    args = parser.parse_args()

    print(
        json.dumps(
            initialize(
                args.session_dir,
                args.chassis_authority,
                args.dummy_pack_authority,
                args.candidate_enclosure_id,
                args.harness_revision_id,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
