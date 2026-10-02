#!/usr/bin/env python3
"""Initialize a private Worcester X1 lifecycle-health workspace."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_TEMPLATE = ROOT / "hardware/x1_component_registry_template.json"
EVENT_TEMPLATE = ROOT / "hardware/x1_health_event_template.json"


def _valid_authority(data: dict, expected: str) -> bool:
    if data.get("authority") != expected or data.get("qualified") is not True:
        return False
    if data.get("powered_operation_authorized") is not False:
        return False
    actual = data.get("authority_fingerprint_sha256")
    if not isinstance(actual, str) or not actual:
        return False
    unsigned = dict(data)
    unsigned.pop("authority_fingerprint_sha256", None)
    try:
        payload = json.dumps(
            unsigned,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return False
    return actual == hashlib.sha256(payload).hexdigest()


def initialize(
    workspace_dir: Path,
    board_id: str,
    configuration_id: str,
    created_at_utc: str,
    rolling_chassis_authority_path: Path,
) -> dict:
    workspace_dir = workspace_dir.resolve()
    if workspace_dir.exists() and any(workspace_dir.iterdir()):
        raise FileExistsError(
            f"workspace directory is not empty: {workspace_dir}; "
            "use a fresh private directory"
        )
    workspace_dir.mkdir(parents=True, exist_ok=True)
    events_dir = workspace_dir / "events"
    events_dir.mkdir()

    chassis = json.loads(
        rolling_chassis_authority_path.read_text(encoding="utf-8")
    )
    if not _valid_authority(chassis, "x1_rolling_chassis_physical"):
        raise ValueError(
            "rolling chassis authority must be qualified and fingerprint-valid"
        )

    registry = json.loads(REGISTRY_TEMPLATE.read_text(encoding="utf-8"))
    registry["board_id"] = board_id
    registry["configuration_id"] = configuration_id
    registry["created_at_utc"] = created_at_utc
    registry["upstream_authorities"]["rolling_chassis_fingerprint_sha256"] = (
        chassis["authority_fingerprint_sha256"]
    )
    registry["components"] = []
    registry_path = workspace_dir / "component_registry.json"
    registry_path.write_text(
        json.dumps(registry, indent=2) + "\n",
        encoding="utf-8",
    )

    event_template_path = workspace_dir / "event_template.json"
    shutil.copyfile(EVENT_TEMPLATE, event_template_path)

    workspace = {
        "schema_version": 1,
        "scope": "x1_lifecycle_health_workspace",
        "board_id": board_id,
        "initial_configuration_id": configuration_id,
        "registry": registry_path.name,
        "events_directory": events_dir.name,
        "event_template": event_template_path.name,
        "rolling_chassis_authority_source": str(
            rolling_chassis_authority_path
        ),
        "rolling_chassis_fingerprint_sha256": chassis[
            "authority_fingerprint_sha256"
        ],
        "reference_snapshot": (
            "hardware/rev_c_lifecycle_health_snapshot_2026-10-01.json"
        ),
        "protocol": "docs/rev_c_lifecycle_health.md",
        "health_authority": False,
        "powered_operation_authority": False,
        "public_operation_authority": False,
        "dog_accompanied_operation_authority": False,
        "next_step": (
            "Populate the real component registry from the received/qualified "
            "hardware, then create a BASELINE event followed by a fresh PREFLIGHT "
            "before evaluating readiness for any independently allowed activity."
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
    parser.add_argument("--created-at-utc", required=True)
    parser.add_argument(
        "--rolling-chassis-authority",
        type=Path,
        required=True,
    )
    args = parser.parse_args()
    print(
        json.dumps(
            initialize(
                args.workspace_dir,
                args.board_id,
                args.configuration_id,
                args.created_at_utc,
                args.rolling_chassis_authority,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
