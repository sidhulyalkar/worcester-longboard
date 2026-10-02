#!/usr/bin/env python3
"""Finalize Worcester X1 telemetry file hashes after capture."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finalize(manifest_path: Path, ended_at_utc: str) -> dict:
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("scope") != "x1_telemetry_session":
        raise ValueError("wrong telemetry manifest scope")
    if not ended_at_utc.strip():
        raise ValueError("ended_at_utc must be nonempty")

    base_dir = manifest_path.parent.resolve()
    for stream in manifest.get("streams", []):
        raw = stream.get("file_path")
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("every stream requires file_path")
        path = (base_dir / raw).resolve()
        try:
            path.relative_to(base_dir)
        except ValueError as exc:
            raise ValueError(f"stream path escapes session: {raw}") from exc
        if not path.is_file():
            raise FileNotFoundError(path)
        stream["file_sha256"] = _sha256_file(path)

    manifest["ended_at_utc"] = ended_at_utc
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--ended-at-utc", required=True)
    args = parser.parse_args()
    result = finalize(args.manifest, args.ended_at_utc)
    print(
        json.dumps(
            {
                "session_id": result.get("session_id"),
                "ended_at_utc": result.get("ended_at_utc"),
                "stream_hashes": {
                    stream["stream_type"]: stream["file_sha256"]
                    for stream in result.get("streams", [])
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
