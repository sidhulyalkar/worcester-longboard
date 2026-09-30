#!/usr/bin/env python3
"""Initialize a private Worcester X1 Rev-C chassis-release workspace."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from cad.generate_rev_c_deck_templates import generate as generate_deck_templates

ROOT = Path(__file__).resolve().parents[1]

TEMPLATES = {
    "deck_comparison.json": ROOT / "hardware/rev_c_deck_comparison_private_template.json",
    "topology_trade.json": ROOT / "hardware/rev_c_topology_trade_template.json",
    "inert_pack_envelope.json": ROOT / "hardware/rev_c_inert_pack_envelope_template.json",
    "chassis_release.json": ROOT / "hardware/rev_c_chassis_release_template.json",
}


def initialize(session_dir: Path) -> dict:
    session_dir = session_dir.resolve()
    if session_dir.exists() and any(session_dir.iterdir()):
        raise FileExistsError(
            f"session directory is not empty: {session_dir}; use a fresh private directory"
        )
    session_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    for output_name, source in TEMPLATES.items():
        destination = session_dir / output_name
        shutil.copyfile(source, destination)
        copied.append(destination.name)

    deck_dir = session_dir / "deck_templates"
    deck_paths = generate_deck_templates(deck_dir)

    manifest = {
        "schema_version": 1,
        "scope": "rev_c_chassis_release_workspace",
        "physical_authority": False,
        "powered_operation_authorized": False,
        "session_dir": str(session_dir),
        "templates": copied,
        "deck_templates": [str(path.relative_to(session_dir)) for path in deck_paths],
        "next_step": "complete Issue #4 authority, then follow docs/rev_c_chassis_release_playbook.md",
    }
    manifest_path = session_dir / "workspace_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "session_dir",
        type=Path,
        help="use a gitignored path such as rider/private/rev_c_release",
    )
    args = parser.parse_args()
    manifest = initialize(args.session_dir)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
