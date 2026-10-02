#!/usr/bin/env python3
"""Initialize a private Worcester X1 telemetry flight-recorder session."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "hardware/x1_telemetry_contract_2026-10-01.json"
TEMPLATE = ROOT / "hardware/x1_telemetry_session_template.json"


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _valid_fp(data: dict) -> bool:
    actual = data.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        return False
    unsigned = dict(data)
    unsigned.pop("authority_fingerprint_sha256", None)
    try:
        return actual == _digest(unsigned)
    except (TypeError, ValueError):
        return False


def initialize(
    session_dir: Path,
    *,
    session_id: str,
    board_id: str,
    configuration_id: str,
    stage_id: str,
    power_architecture_path: Path,
    firmware_revision: str,
    reference_clock_id: str,
    started_at_utc: str,
) -> dict:
    session_dir = session_dir.resolve()
    if session_dir.exists() and any(session_dir.iterdir()):
        raise FileExistsError(
            f"session directory is not empty: {session_dir}; use a fresh private directory"
        )
    session_dir.mkdir(parents=True, exist_ok=True)
    streams_dir = session_dir / "streams"
    streams_dir.mkdir()

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if stage_id not in contract.get("stage_requirements", {}):
        raise ValueError("telemetry supports Issue #45 Stage 1-4 only")

    power = json.loads(power_architecture_path.read_text(encoding="utf-8"))
    if (
        power.get("authority") != "x1_power_architecture"
        or power.get("qualified") is not True
        or not _valid_fp(power)
    ):
        raise ValueError("power architecture must be qualified and fingerprint-valid")

    manifest = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    manifest.update(
        {
            "session_id": session_id,
            "board_id": board_id,
            "configuration_id": configuration_id,
            "commissioning_stage_id": stage_id,
            "power_architecture_fingerprint_sha256": power[
                "authority_fingerprint_sha256"
            ],
            "firmware_revision": firmware_revision,
            "reference_clock_id": reference_clock_id,
            "started_at_utc": started_at_utc,
            "ended_at_utc": "",
        }
    )

    specs = {
        item["stream_type"]: item
        for item in contract["streams"]
    }
    required_stream_types = set(
        contract["stage_requirements"][stage_id]["required_stream_types"]
    )
    manifest["streams"] = [
        stream
        for stream in manifest["streams"]
        if stream["stream_type"] in required_stream_types
    ]
    for stream in manifest["streams"]:
        stream_type = stream["stream_type"]
        spec = specs[stream_type]
        stream["sampling_mode"] = spec["sampling_mode"]
        path = session_dir / stream["file_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(spec["required_columns"])

    manifest_path = session_dir / "telemetry_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    workspace = {
        "schema_version": 1,
        "scope": "x1_telemetry_workspace",
        "issue": 47,
        "session_id": session_id,
        "board_id": board_id,
        "configuration_id": configuration_id,
        "commissioning_stage_id": stage_id,
        "manifest": manifest_path.name,
        "streams_directory": streams_dir.name,
        "contract": "hardware/x1_telemetry_contract_2026-10-01.json",
        "validator": "tools/validate_x1_telemetry_session.py",
        "finalizer": "tools/finalize_x1_telemetry_session.py",
        "summarizer": "tools/summarize_x1_commissioning_telemetry.py",
        "telemetry_authority": False,
        "sensor_calibration_authority": False,
        "powered_operation_authority": False,
        "public_operation_authority": False,
        "dog_accompanied_operation_authority": False,
        "next_step": (
            "Fill stream source/clock/synchronization/rate metadata before capture. "
            "Record private telemetry, then set ended_at_utc and run the finalizer "
            "to hash immutable captured files before validation."
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
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--configuration-id", required=True)
    parser.add_argument("--stage-id", required=True)
    parser.add_argument("--power-architecture", type=Path, required=True)
    parser.add_argument("--firmware-revision", required=True)
    parser.add_argument("--reference-clock-id", required=True)
    parser.add_argument("--started-at-utc", required=True)
    args = parser.parse_args()

    print(
        json.dumps(
            initialize(
                args.session_dir,
                session_id=args.session_id,
                board_id=args.board_id,
                configuration_id=args.configuration_id,
                stage_id=args.stage_id,
                power_architecture_path=args.power_architecture,
                firmware_revision=args.firmware_revision,
                reference_clock_id=args.reference_clock_id,
                started_at_utc=args.started_at_utc,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
