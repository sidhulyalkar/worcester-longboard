#!/usr/bin/env python3
"""Initialize a private Worcester X1 powered-test venue evidence session."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "hardware/powered_test_venue_template.json"


def initialize(session_dir: Path) -> dict:
    session_dir = session_dir.resolve()
    if session_dir.exists() and any(session_dir.iterdir()):
        raise FileExistsError(
            f"session directory is not empty: {session_dir}; use a fresh private directory"
        )
    session_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = session_dir / "venue_manifest.json"
    shutil.copyfile(TEMPLATE, manifest_path)

    workspace = {
        "schema_version": 1,
        "scope": "x1_powered_test_venue_workspace",
        "venue_permission_authority": False,
        "vehicle_powered_operation_authority": False,
        "public_operation_authority": False,
        "dog_accompanied_operation_authority": False,
        "manifest": manifest_path.name,
        "constraints_snapshot": (
            "hardware/rev_c_public_use_constraints_2026-10-01.json"
        ),
        "protocol": "docs/rev_c_public_use_and_test_venues.md",
        "next_step": (
            "Record the actual owner/jurisdiction, permission basis, course control "
            "and restrictions. Do not treat this workspace as vehicle authority."
        ),
    }
    (session_dir / "workspace_manifest.json").write_text(
        json.dumps(workspace, indent=2) + "\n",
        encoding="utf-8",
    )
    return workspace


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "session_dir",
        type=Path,
        help="use a gitignored path such as rider/private/venues/test-01",
    )
    args = parser.parse_args()
    print(json.dumps(initialize(args.session_dir), indent=2))


if __name__ == "__main__":
    main()
