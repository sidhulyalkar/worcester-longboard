#!/usr/bin/env python3
"""Initialize a private Worcester X1 telemetry session workspace."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "hardware/x1_telemetry_session_template.json"
SNAPSHOT = ROOT / "hardware/rev_c_telemetry_reference_snapshot_2026-10-02.json"


def _digest(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _valid_authority(data: dict, expected: str) -> bool:
    if data.get("authority") != expected or data.get("qualified") is not True:
        return False
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
    workspace_dir: Path,
    *,
    board_id: str,
    configuration_id: str,
    stage_id: str,
    started_at_utc: str,
    power_architecture_path: Path,
) -> dict:
    workspace_dir = workspace_dir.resolve()
    if workspace_dir.exists() and any(workspace_dir.iterdir()):
        raise FileExistsError(
            f"workspace directory is not empty: {workspace_dir}; "
            "use a fresh private directory"
        )
    workspace_dir.mkdir(parents=True, exist_ok=True)
    streams_dir = workspace_dir / "streams"
    events_dir = workspace_dir / "events"
    streams_dir.mkdir()
    events_dir.mkdir()

    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    stage = snapshot["commissioning_integration"].get(stage_id)
    if not isinstance(stage, dict) or stage.get("telemetry_required") is not True:
        raise ValueError(
            f"stage {stage_id!r} is not a telemetry-required commissioning stage"
        )

    power = json.loads(power_architecture_path.read_text(encoding="utf-8"))
    if not _valid_authority(power, "x1_power_architecture"):
        raise ValueError(
            "power architecture must be a qualified, fingerprint-valid "
            "x1_power_architecture authority"
        )

    manifest = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    manifest["session_id"] = workspace_dir.name
    manifest["board_id"] = board_id
    manifest["configuration_id"] = configuration_id
    manifest["commissioning_stage_id"] = stage_id
    manifest["started_at_utc"] = started_at_utc
    manifest["power_architecture_fingerprint_sha256"] = power[
        "authority_fingerprint_sha256"
    ]

    for stream in manifest["streams"]:
        path = workspace_dir / stream["file"]
        fieldnames = [
            stream["sequence_column"],
            stream["timestamp_column"],
            *[signal["column"] for signal in stream["signals"]],
        ]
        path.write_text(",".join(fieldnames) + "\n", encoding="utf-8")

    event_path = workspace_dir / manifest["event_log"]["file"]
    event_path.write_text("", encoding="utf-8")

    manifest_path = workspace_dir / "telemetry_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    workspace = {
        "schema_version": 1,
        "scope": "x1_telemetry_workspace",
        "session_id": manifest["session_id"],
        "board_id": board_id,
        "configuration_id": configuration_id,
        "commissioning_stage_id": stage_id,
        "manifest": manifest_path.name,
        "streams_directory": streams_dir.name,
        "events_directory": events_dir.name,
        "reference_snapshot": (
            "hardware/rev_c_telemetry_reference_snapshot_2026-10-02.json"
        ),
        "signal_registry": "hardware/x1_telemetry_signal_registry_2026-10-02.json",
        "telemetry_authority": False,
        "powered_operation_authority": False,
        "public_operation_authority": False,
        "dog_accompanied_operation_authority": False,
        "next_step": (
            "Fill real device/source/clock/synchronization provenance before "
            "recording. Record raw private streams, then seal and validate the "
            "session. Logger failure invalidates evidence but must never become "
            "a control-loop dependency."
        ),
    }
    (workspace_dir / "workspace_manifest.json").write_text(
        json.dumps(workspace, indent=2) + "\n",
        encoding="utf-8",
    )
    return workspace


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace_dir", type=Path)
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--configuration-id", required=True)
    parser.add_argument("--stage-id", required=True)
    parser.add_argument("--started-at-utc", required=True)
    parser.add_argument("--power-architecture", type=Path, required=True)
    args = parser.parse_args()

    print(
        json.dumps(
            initialize(
                args.workspace_dir,
                board_id=args.board_id,
                configuration_id=args.configuration_id,
                stage_id=args.stage_id,
                started_at_utc=args.started_at_utc,
                power_architecture_path=args.power_architecture,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
