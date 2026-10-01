#!/usr/bin/env python3
"""Initialize a private inert Rev-C passive charge-cradle session."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "hardware/rev_c_charge_dock_mechanical_template.json"


def initialize(session_dir: Path) -> dict:
    session_dir = session_dir.resolve()
    if session_dir.exists() and any(session_dir.iterdir()):
        raise FileExistsError(
            f"session directory is not empty: {session_dir}; use a fresh private directory"
        )
    session_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = session_dir / "dock_manifest.json"
    shutil.copyfile(TEMPLATE, manifest_path)

    workspace = {
        "schema_version": 1,
        "scope": "rev_c_passive_charge_cradle_workspace",
        "physical_authority": False,
        "procurement_authority": False,
        "live_battery_test_authorized": False,
        "electrical_charge_authorized": False,
        "powered_operation_authorized": False,
        "manifest": manifest_path.name,
        "reference_snapshot": "hardware/rev_c_energy_charge_snapshot_2026-10-01.json",
        "protocol": "docs/rev_c_energy_and_charging.md",
        "next_step": (
            "Use only inert pack/connector fixtures; fill the manifest from the "
            "selected future battery/charger geometry before running the qualifier."
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
        help="use a gitignored path such as rider/private/energy/dock-01",
    )
    args = parser.parse_args()
    print(json.dumps(initialize(args.session_dir), indent=2))


if __name__ == "__main__":
    main()
