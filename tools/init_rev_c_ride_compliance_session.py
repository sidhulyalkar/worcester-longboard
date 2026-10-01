#!/usr/bin/env python3
"""Initialize a private Rev-C unpowered ride-compliance session."""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "hardware/rev_c_ride_compliance_run_template.json"

OBSERVATION_FIELDS = (
    "run_id",
    "config_id",
    "carve_response",
    "trail_chatter",
    "recentering",
    "steering_effort",
    "stability",
    "foot_fatigue",
    "confidence",
    "emergency_stepoff_ok",
    "notes",
)

SENSOR_FIELDS = (
    "time_s",
    "speed_mps",
    "accel_z_mps2",
    "gyro_roll_dps",
    "gyro_yaw_dps",
)


def initialize(session_dir: Path) -> dict:
    session_dir = session_dir.resolve()
    if session_dir.exists() and any(session_dir.iterdir()):
        raise FileExistsError(
            f"session directory is not empty: {session_dir}; use a fresh private directory"
        )
    session_dir.mkdir(parents=True, exist_ok=True)
    data_dir = session_dir / "data"
    data_dir.mkdir()

    manifest = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    manifest["session_id"] = session_dir.name

    for run in manifest["runs"]:
        csv_name = Path(str(run["csv_path"])).name
        run["csv_path"] = str(Path("data") / csv_name)
        with (data_dir / csv_name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=SENSOR_FIELDS)
            writer.writeheader()

    manifest_path = session_dir / "ride_compliance_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    observations = session_dir / "rider_observations.csv"
    with observations.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OBSERVATION_FIELDS)
        writer.writeheader()
        for run in manifest["runs"]:
            writer.writerow(
                {
                    "run_id": run["id"],
                    "config_id": run["config_id"],
                    "carve_response": "",
                    "trail_chatter": "",
                    "recentering": "",
                    "steering_effort": "",
                    "stability": "",
                    "foot_fatigue": "",
                    "confidence": "",
                    "emergency_stepoff_ok": "",
                    "notes": "",
                }
            )

    workspace = {
        "schema_version": 1,
        "scope": "rev_c_ride_compliance_workspace",
        "physical_authority": False,
        "procurement_authority": False,
        "powered_operation_authorized": False,
        "manifest": manifest_path.name,
        "observations": observations.name,
        "data_dir": data_dir.name,
        "next_step": "fill setup identifiers, collect only unpowered low-energy runs, and follow docs/rev_c_ride_compliance_program.md",
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
        help="use a gitignored directory such as rider/private/ride_compliance/session-01",
    )
    args = parser.parse_args()
    print(json.dumps(initialize(args.session_dir), indent=2))


if __name__ == "__main__":
    main()
