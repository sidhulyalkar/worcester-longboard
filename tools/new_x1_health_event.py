#!/usr/bin/env python3
"""Create a new Worcester X1 health event from a private component registry."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENT_TEMPLATE = ROOT / "hardware/x1_health_event_template.json"

EVENT_TYPES = {
    "BASELINE",
    "PREFLIGHT",
    "POST_ACTIVITY",
    "INSPECTION",
    "SERVICE",
    "COMPONENT_REPLACEMENT",
    "CONTAMINATION_EXPOSURE",
    "IMPACT",
    "FAULT",
    "CONFIGURATION_CHANGE",
}


def create_event(
    registry_path: Path,
    output_path: Path,
    event_id: str,
    timestamp_utc: str,
    event_type: str,
    activity_type: str,
) -> dict:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("scope") != "x1_vehicle_component_registry":
        raise ValueError("registry must use x1_vehicle_component_registry scope")
    if not registry.get("board_id") or not registry.get("configuration_id"):
        raise ValueError("registry requires board_id and configuration_id")
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unsupported event_type: {event_type}")
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing event: {output_path}")

    event = json.loads(EVENT_TEMPLATE.read_text(encoding="utf-8"))
    event.update(
        {
            "event_id": event_id,
            "board_id": registry["board_id"],
            "configuration_id": registry["configuration_id"],
            "timestamp_utc": timestamp_utc,
            "event_type": event_type,
            "activity_type": activity_type,
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(event, indent=2) + "\n",
        encoding="utf-8",
    )
    return event


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--timestamp-utc", required=True)
    parser.add_argument("--event-type", required=True)
    parser.add_argument("--activity-type", required=True)
    args = parser.parse_args()

    print(
        json.dumps(
            create_event(
                args.registry,
                args.output,
                args.event_id,
                args.timestamp_utc,
                args.event_type,
                args.activity_type,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
