#!/usr/bin/env python3
"""Attach a physical X1 telemetry replay to an Issue #45 stage manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def attach(manifest: dict, replay: dict, snapshot: dict | None = None) -> dict:
    snapshot = snapshot or json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    if manifest.get("scope") != "rev_c_powered_commissioning_stage_trial":
        raise ValueError("wrong commissioning manifest scope")
    if replay.get("authority") != "x1_commissioning_telemetry_replay":
        raise ValueError("replay must be x1_commissioning_telemetry_replay")
    if replay.get("qualified") is not True or not _valid_fp(replay):
        raise ValueError("replay must be qualified and fingerprint-valid")
    if replay.get("synthetic_fixture") is True:
        raise ValueError("synthetic telemetry cannot attach to physical commissioning")
    if replay.get("physical_evidence_eligible") is not True:
        raise ValueError("telemetry replay is not eligible as physical evidence")

    for manifest_key, replay_key in (
        ("board_id", "board_id"),
        ("configuration_id", "configuration_id"),
        ("stage_id", "commissioning_stage_id"),
        (
            "power_architecture_fingerprint_sha256",
            "power_architecture_fingerprint_sha256",
        ),
    ):
        if manifest.get(manifest_key) != replay.get(replay_key):
            raise ValueError(
                f"manifest/replay lineage mismatch: {manifest_key}"
            )

    stage = next(
        (
            item
            for item in snapshot.get("stages", [])
            if item.get("stage_id") == manifest.get("stage_id")
        ),
        None,
    )
    if stage is None:
        raise ValueError("unknown commissioning stage")
    if stage.get("telemetry_replay_required") is not True:
        raise ValueError("this stage does not accept telemetry replay attachment")

    replay_by_id = {
        item.get("metric_id"): item
        for item in replay.get("metrics", [])
        if isinstance(item, dict) and item.get("metric_id")
    }
    measurements = []
    for metric_id in stage.get("required_measurements", []):
        item = replay_by_id.get(metric_id)
        if item is None:
            raise ValueError(f"replay missing required metric: {metric_id}")
        measurements.append(
            {
                "metric_id": metric_id,
                "value": item.get("value"),
                "unit": item.get("unit"),
                "source": "x1_commissioning_telemetry_replay",
                "evidence_ref": item.get("evidence_ref"),
            }
        )

    output = dict(manifest)
    output["telemetry_replay_fingerprint_sha256"] = replay[
        "authority_fingerprint_sha256"
    ]
    output["measurements"] = measurements
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--telemetry-replay", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    result = attach(
        json.loads(args.manifest.read_text(encoding="utf-8")),
        json.loads(args.telemetry_replay.read_text(encoding="utf-8")),
        json.loads(args.snapshot.read_text(encoding="utf-8")),
    )
    destination = args.out or args.manifest
    destination.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
