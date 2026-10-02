#!/usr/bin/env python3
"""Initialize a private Worcester X1 telemetry-evidence session."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "hardware/x1_telemetry_session_template.json"
SNAPSHOT = ROOT / "hardware/rev_c_telemetry_evidence_snapshot_2026-10-01.json"


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


def _valid_power(data: dict) -> bool:
    return (
        data.get("authority") == "x1_power_architecture"
        and data.get("qualified") is True
        and _valid_fp(data)
    )


def _valid_health(data: dict, board_id: str, configuration_id: str) -> bool:
    return (
        data.get("authority") == "x1_lifecycle_health_state"
        and data.get("valid") is True
        and data.get("health_state") == "READY_FOR_ALLOWED_ACTIVITY"
        and data.get("ready_for_allowed_activity") is True
        and data.get("board_id") == board_id
        and data.get("current_configuration_id") == configuration_id
        and data.get("powered_operation_authorized") is False
        and data.get("public_operation_authorized") is False
        and data.get("dog_accompanied_operation_authorized") is False
        and _valid_fp(data)
    )


def initialize(
    session_dir: Path,
    stage_id: str,
    board_id: str,
    configuration_id: str,
    power_architecture_path: Path,
    pre_health_path: Path,
    logger_build_id: str,
    logger_source_revision: str,
    logger_hardware_id: str,
    storage_type: str,
) -> dict:
    session_dir = session_dir.resolve()
    if session_dir.exists() and any(session_dir.iterdir()):
        raise FileExistsError(
            f"session directory is not empty: {session_dir}; use a fresh private directory"
        )

    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    stages = snapshot.get("stage_requirements", {})
    if stage_id not in stages:
        raise ValueError(
            "telemetry sessions are defined only for Issue #45 energized "
            f"Stages 1-4; unsupported stage: {stage_id}"
        )
    stage = stages[stage_id]

    power = json.loads(power_architecture_path.read_text(encoding="utf-8"))
    health = json.loads(pre_health_path.read_text(encoding="utf-8"))
    if not _valid_power(power):
        raise ValueError("power architecture must be qualified and fingerprint-valid")
    if not _valid_health(health, board_id, configuration_id):
        raise ValueError(
            "pre-health must be fingerprint-valid READY state for board/configuration"
        )

    session_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    manifest.update(
        {
            "session_id": session_dir.name,
            "board_id": board_id,
            "configuration_id": configuration_id,
            "commissioning_stage_id": stage_id,
            "commissioning_stage_index": stage["stage_index"],
            "power_architecture_fingerprint_sha256": power[
                "authority_fingerprint_sha256"
            ],
            "pre_lifecycle_health_fingerprint_sha256": health[
                "authority_fingerprint_sha256"
            ],
        }
    )
    manifest["logger_identity"].update(
        {
            "firmware_build_id": logger_build_id,
            "firmware_source_revision": logger_source_revision,
            "hardware_id": logger_hardware_id,
            "storage_type": storage_type,
        }
    )
    manifest["declared_channels"] = [
        {
            "signal_id": signal_id,
            "source_kind": "",
            "source_id": "",
            "expected_hz": hz,
            "max_source_age_us": int(round(1_000_000.0 / hz)),
            "derivation_method_reference": "",
            "frame_or_sign_convention": "",
            "enabled": True,
        }
        for signal_id, hz in stage["required_signals_hz"].items()
    ]

    manifest_path = session_dir / "telemetry_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    with (session_dir / "telemetry.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "record_seq",
                "mono_us",
                "signal_id",
                "value",
                "source_age_us",
                "quality",
            ]
        )

    (session_dir / "events.jsonl").write_text("", encoding="utf-8")
    (session_dir / "metrics.json").write_text("[]\n", encoding="utf-8")

    workspace = {
        "schema_version": 1,
        "scope": "x1_telemetry_evidence_workspace",
        "issue": 49,
        "stage_id": stage_id,
        "stage_index": stage["stage_index"],
        "manifest": manifest_path.name,
        "telemetry_csv": "telemetry.csv",
        "events_jsonl": "events.jsonl",
        "metrics_json": "metrics.json",
        "reference_snapshot": str(SNAPSHOT.relative_to(ROOT)),
        "qualifier": "tools/qualify_x1_telemetry_evidence.py",
        "powered_operation_authority": False,
        "controller_configuration_authority": False,
        "battery_configuration_authority": False,
        "public_operation_authority": False,
        "dog_accompanied_operation_authority": False,
        "next_step": (
            "Fill source provenance and logger architecture declarations before "
            "collecting stage evidence. Logging must remain outside the hard "
            "real-time control path."
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
    parser.add_argument("--stage-id", required=True)
    parser.add_argument("--board-id", required=True)
    parser.add_argument("--configuration-id", required=True)
    parser.add_argument("--power-architecture", type=Path, required=True)
    parser.add_argument("--pre-health-state", type=Path, required=True)
    parser.add_argument("--logger-build-id", required=True)
    parser.add_argument("--logger-source-revision", required=True)
    parser.add_argument("--logger-hardware-id", required=True)
    parser.add_argument("--storage-type", required=True)
    args = parser.parse_args()

    print(
        json.dumps(
            initialize(
                args.session_dir,
                args.stage_id,
                args.board_id,
                args.configuration_id,
                args.power_architecture,
                args.pre_health_state,
                args.logger_build_id,
                args.logger_source_revision,
                args.logger_hardware_id,
                args.storage_type,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
