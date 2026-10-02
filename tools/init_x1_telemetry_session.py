#!/usr/bin/env python3
"""Initialize a private Worcester X1 telemetry flight-recorder session."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "hardware/x1_telemetry_session_template.json"
REGISTRY = ROOT / "hardware/x1_telemetry_signal_registry.json"
SNAPSHOT = ROOT / "hardware/rev_c_telemetry_snapshot_2026-10-02.json"


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


def _validate_power(data: dict) -> None:
    if (
        data.get("authority") != "x1_power_architecture"
        or data.get("qualified") is not True
        or not _valid_fp(data)
    ):
        raise ValueError(
            "power architecture must be qualified fingerprint-valid "
            "x1_power_architecture"
        )


def _validate_health(data: dict, board_id: str, configuration_id: str) -> None:
    if (
        data.get("authority") != "x1_lifecycle_health_state"
        or data.get("valid") is not True
        or data.get("health_state") != "READY_FOR_ALLOWED_ACTIVITY"
        or data.get("ready_for_allowed_activity") is not True
        or data.get("board_id") != board_id
        or data.get("current_configuration_id") != configuration_id
        or not _valid_fp(data)
    ):
        raise ValueError(
            "pre-health must be fingerprint-valid READY lifecycle health "
            "for the requested board/configuration"
        )


def initialize(
    session_dir: Path,
    *,
    board_id: str,
    configuration_id: str,
    stage_id: str,
    started_at_utc: str,
    power_architecture_path: Path,
    pre_health_path: Path,
) -> dict:
    session_dir = session_dir.resolve()
    if session_dir.exists() and any(session_dir.iterdir()):
        raise FileExistsError(
            f"session directory is not empty: {session_dir}; use a fresh private directory"
        )

    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    power = json.loads(power_architecture_path.read_text(encoding="utf-8"))
    health = json.loads(pre_health_path.read_text(encoding="utf-8"))

    stages = snapshot["stage_requirements"]
    if stage_id not in stages:
        raise ValueError(f"unknown commissioning stage_id: {stage_id}")
    _validate_power(power)
    _validate_health(health, board_id, configuration_id)

    session_dir.mkdir(parents=True, exist_ok=True)
    manifest = template
    manifest.update(
        {
            "session_id": session_dir.name,
            "board_id": board_id,
            "configuration_id": configuration_id,
            "commissioning_stage_id": stage_id,
            "started_at_utc": started_at_utc,
            "power_architecture_fingerprint_sha256": power[
                "authority_fingerprint_sha256"
            ],
            "pre_lifecycle_health_fingerprint_sha256": health[
                "authority_fingerprint_sha256"
            ],
        }
    )

    required_streams = stages[stage_id]["required_streams"]
    stream_templates = {
        item["stream_id"]: item
        for item in template["streams"]
    }
    manifest["streams"] = []
    manifest["clocks"] = []
    manifest["sources"] = []

    for stream_id in required_streams:
        if stream_id == "events":
            continue
        stream = dict(stream_templates[stream_id])
        stream["clock_id"] = f"{stream_id}-clock"
        stream["source_id"] = f"{stream_id}-source"
        manifest["streams"].append(stream)
        manifest["clocks"].append(
            {
                "clock_id": stream["clock_id"],
                "source_id": stream["source_id"],
                "timestamp_unit": "s",
                "synchronization_method": "",
                "synchronization_uncertainty_s": None,
            }
        )
        manifest["sources"].append(
            {
                "source_id": stream["source_id"],
                "device_role": stream_id,
                "qualification_status": "DECLARED",
                "calibration_evidence_ref": "",
            }
        )

        columns = [
            item["name"]
            for item in registry["streams"][stream_id]["required_columns"]
        ]
        (session_dir / stream["file_path"]).write_text(
            ",".join(columns) + "\n",
            encoding="utf-8",
        )

    if "events" in required_streams:
        manifest["event_log"]["clock_id"] = "events-clock"
        manifest["event_log"]["source_id"] = "events-source"
        manifest["clocks"].append(
            {
                "clock_id": "events-clock",
                "source_id": "events-source",
                "timestamp_unit": "s",
                "synchronization_method": "",
                "synchronization_uncertainty_s": None,
            }
        )
        manifest["sources"].append(
            {
                "source_id": "events-source",
                "device_role": "event_logger",
                "qualification_status": "DECLARED",
                "calibration_evidence_ref": "",
            }
        )
        (session_dir / manifest["event_log"]["file_path"]).write_text(
            "",
            encoding="utf-8",
        )

    manifest_path = session_dir / "telemetry_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    workspace = {
        "schema_version": 1,
        "scope": "x1_telemetry_workspace",
        "manifest": manifest_path.name,
        "signal_registry": str(REGISTRY.relative_to(ROOT)),
        "reference_snapshot": str(SNAPSHOT.relative_to(ROOT)),
        "stage_id": stage_id,
        "raw_data_private": True,
        "telemetry_authority": False,
        "powered_operation_authority": False,
        "public_operation_authority": False,
        "dog_accompanied_operation_authority": False,
        "next_step": (
            "Fill real source/clock provenance and qualification evidence before "
            "recording. After capture, hash every stream and event file in the "
            "manifest, then validate before deriving commissioning metrics."
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
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--configuration-id", required=True)
    parser.add_argument("--stage-id", required=True)
    parser.add_argument("--started-at-utc", required=True)
    parser.add_argument("--power-architecture", type=Path, required=True)
    parser.add_argument("--pre-health-state", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            initialize(
                args.session_dir,
                board_id=args.board_id,
                configuration_id=args.configuration_id,
                stage_id=args.stage_id,
                started_at_utc=args.started_at_utc,
                power_architecture_path=args.power_architecture,
                pre_health_path=args.pre_health_state,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
