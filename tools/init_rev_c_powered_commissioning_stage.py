#!/usr/bin/env python3
"""Initialize a private Worcester X1 powered-commissioning stage session."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "hardware/rev_c_powered_commissioning_stage_template.json"
SNAPSHOT = ROOT / "hardware/rev_c_powered_commissioning_snapshot_2026-10-01.json"


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
    stage_id: str,
    board_id: str,
    configuration_id: str,
    power_architecture_path: Path,
    pre_health_path: Path,
    previous_stage_path: Path | None = None,
    venue_authority_path: Path | None = None,
) -> dict:
    session_dir = session_dir.resolve()
    if session_dir.exists() and any(session_dir.iterdir()):
        raise FileExistsError(
            f"session directory is not empty: {session_dir}; use a fresh private directory"
        )
    session_dir.mkdir(parents=True, exist_ok=True)

    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    stage_map = {item["stage_id"]: item for item in snapshot["stages"]}
    if stage_id not in stage_map:
        raise ValueError(f"unknown commissioning stage: {stage_id}")
    stage = stage_map[stage_id]

    power = json.loads(power_architecture_path.read_text(encoding="utf-8"))
    health = json.loads(pre_health_path.read_text(encoding="utf-8"))
    previous = (
        json.loads(previous_stage_path.read_text(encoding="utf-8"))
        if previous_stage_path is not None
        else None
    )
    venue = (
        json.loads(venue_authority_path.read_text(encoding="utf-8"))
        if venue_authority_path is not None
        else None
    )

    if (
        power.get("authority") != "x1_power_architecture"
        or power.get("qualified") is not True
        or not _valid_fp(power)
    ):
        raise ValueError("power architecture must be qualified and fingerprint-valid")

    if (
        health.get("authority") != "x1_lifecycle_health_state"
        or health.get("valid") is not True
        or health.get("health_state") != "READY_FOR_ALLOWED_ACTIVITY"
        or health.get("ready_for_allowed_activity") is not True
        or health.get("board_id") != board_id
        or health.get("current_configuration_id") != configuration_id
        or not _valid_fp(health)
    ):
        raise ValueError(
            "pre-health must be fingerprint-valid READY state for board/configuration"
        )

    if stage["previous_stage_required"]:
        if previous is None:
            raise ValueError("previous stage authority is required")
        if (
            previous.get("authority") != "x1_powered_commissioning_stage"
            or previous.get("qualified") is not True
            or previous.get("stage_index") != stage["stage_index"] - 1
            or previous.get("board_id") != board_id
            or previous.get("configuration_id") != configuration_id
            or not _valid_fp(previous)
        ):
            raise ValueError(
                "previous stage must be exact fingerprint-valid preceding stage"
            )
        if (
            previous.get("post_lifecycle_health_fingerprint_sha256")
            != health.get("authority_fingerprint_sha256")
        ):
            raise ValueError(
                "pre-health must match previous stage post-health fingerprint"
            )
    elif previous is not None:
        raise ValueError("Stage 0 must not include previous stage authority")

    if stage["venue_authority_required"]:
        if venue is None:
            raise ValueError("qualified venue authority is required")
        if (
            venue.get("authority") != "x1_powered_test_venue_evidence"
            or venue.get("qualified") is not True
            or venue.get("venue_permission_qualified") is not True
            or not _valid_fp(venue)
        ):
            raise ValueError("venue authority must be qualified and fingerprint-valid")
    elif venue is not None:
        raise ValueError(f"stage {stage_id} does not use venue authority")

    manifest = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    manifest.update(
        {
            "session_id": session_dir.name,
            "board_id": board_id,
            "configuration_id": configuration_id,
            "stage_id": stage_id,
            "power_architecture_fingerprint_sha256": power[
                "authority_fingerprint_sha256"
            ],
            "pre_lifecycle_health_fingerprint_sha256": health[
                "authority_fingerprint_sha256"
            ],
            "post_lifecycle_health_fingerprint_sha256": (
                health["authority_fingerprint_sha256"]
                if stage["stage_index"] == 0
                else ""
            ),
            "previous_stage_fingerprint_sha256": (
                previous["authority_fingerprint_sha256"]
                if previous is not None
                else ""
            ),
            "venue_authority_fingerprint_sha256": (
                venue["authority_fingerprint_sha256"]
                if venue is not None
                else ""
            ),
            "energized": stage["energized"],
            "free_ground_travel": stage["free_ground_travel"],
            "rider_present": stage["rider_present"],
            "dog_present": stage["dog_present"],
            "public_area": False,
        }
    )
    manifest["checks"] = {
        check: {"status": "UNSET", "notes": ""}
        for check in stage["required_checks"]
    }
    manifest["measurements"] = [
        {
            "metric_id": metric,
            "value": None,
            "unit": "",
            "source": "",
            "evidence_ref": "",
        }
        for metric in stage["required_measurements"]
    ]

    manifest_path = session_dir / "commissioning_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    workspace = {
        "schema_version": 1,
        "scope": "rev_c_powered_commissioning_workspace",
        "issue": 45,
        "stage_index": stage["stage_index"],
        "stage_id": stage_id,
        "manifest": manifest_path.name,
        "reference_snapshot": str(SNAPSHOT.relative_to(ROOT)),
        "qualifier": "tools/qualify_rev_c_powered_commissioning_stage.py",
        "general_powered_operation_authority": False,
        "public_operation_authority": False,
        "dog_accompanied_operation_authority": False,
        "next_step": (
            "Complete only the declared commissioning stage. Stop on any universal "
            "stop condition. Energized stages require post-stage inspection and a "
            "fresh READY lifecycle-health report before qualification."
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
    parser.add_argument("--previous-stage", type=Path)
    parser.add_argument("--venue-authority", type=Path)
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
                args.previous_stage,
                args.venue_authority,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
