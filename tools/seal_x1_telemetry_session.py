#!/usr/bin/env python3
"""Seal Worcester X1 telemetry raw files by hashing the exact recorded bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def seal(manifest_path: Path, *, ended_at_utc: str, output_path: Path | None = None) -> dict:
    manifest_path = manifest_path.resolve()
    base_dir = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest.get("scope") != "x1_telemetry_session_manifest":
        raise ValueError("wrong telemetry manifest scope")
    if manifest.get("sealed") is True:
        raise ValueError("telemetry session is already sealed")

    for stream in manifest.get("streams", []):
        path = base_dir / str(stream.get("file", ""))
        if not path.is_file():
            raise FileNotFoundError(f"missing telemetry stream: {path}")
        stream["file_sha256"] = _sha256(path)

    event = manifest.get("event_log", {})
    event_path = base_dir / str(event.get("file", ""))
    if not event_path.is_file():
        raise FileNotFoundError(f"missing telemetry event log: {event_path}")
    event["file_sha256"] = _sha256(event_path)

    manifest["ended_at_utc"] = ended_at_utc
    manifest["sealed"] = True
    manifest["sealed_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    destination = output_path.resolve() if output_path else manifest_path
    destination.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--ended-at-utc", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            seal(
                args.manifest,
                ended_at_utc=args.ended_at_utc,
                output_path=args.out,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
