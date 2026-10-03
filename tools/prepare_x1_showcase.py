#!/usr/bin/env python3
"""Build the local Worcester X1 digital-twin artifacts in dependency order."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command_plan(
    skip_cad: bool = False,
    skip_assets: bool = False,
    evidence: list[Path] | None = None,
    snowdeck_signature: Path | None = None,
    snowdeck_comparison: Path | None = None,
) -> list[list[str]]:
    py = sys.executable
    commands: list[list[str]] = []

    if not skip_cad:
        commands.extend(
            [
                [py, "cad/generate_rolling_chassis.py"],
                [py, "cad/generate_fit_rig.py"],
                [py, "cad/generate_one_zone_pilot.py"],
                [py, "cad/generate_snowdeck_study.py"],
            ]
        )

    if not skip_assets:
        commands.append([py, "tools/export_showcase_assets.py"])

    manifest = [py, "tools/build_showcase_manifest.py"]
    for path in evidence or []:
        manifest.extend(["--evidence", str(path)])
    if snowdeck_signature is not None:
        manifest.extend(["--snowdeck-signature", str(snowdeck_signature)])
    if snowdeck_comparison is not None:
        manifest.extend(["--snowdeck-comparison", str(snowdeck_comparison)])
    commands.append(manifest)
    return commands


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--skip-cad", action="store_true")
    p.add_argument("--skip-assets", action="store_true")
    p.add_argument("--evidence", action="append", default=[], type=Path)
    p.add_argument("--snowdeck-signature", type=Path)
    p.add_argument("--snowdeck-comparison", type=Path)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    for command in command_plan(
        args.skip_cad,
        args.skip_assets,
        args.evidence,
        args.snowdeck_signature,
        args.snowdeck_comparison,
    ):
        print("+", " ".join(command))
        subprocess.run(command, cwd=ROOT, check=True)

    print()
    print("Showcase prepared.")
    print("Serve from the repository root with: python -m http.server 8000")
    print("Then open: http://localhost:8000/showcase/")
    print("No fabrication or powered-operation authority is created by this command.")


if __name__ == "__main__":
    main()
