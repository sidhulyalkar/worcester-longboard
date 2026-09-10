#!/usr/bin/env python3
"""Capture RuView pose frames to a private JSONL file.

Example:
  python tools/capture_ruview_pose.py --seconds 30 --hz 10

Default output is under rider/private/ and is ignored by Git.
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
from urllib.request import urlopen

from fit.ruview_adapter import normalize_pose


def fetch_json(url: str, timeout_s: float) -> dict:
    with urlopen(url, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:3000/api/v1/pose/current")
    p.add_argument("--seconds", type=float, default=20.0)
    p.add_argument("--hz", type=float, default=10.0)
    p.add_argument("--timeout", type=float, default=1.0)
    p.add_argument("--out", type=Path, default=Path("rider/private/ruview_pose.jsonl"))
    args = p.parse_args()
    if args.seconds <= 0 or args.hz <= 0:
        raise SystemExit("--seconds and --hz must be positive")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    period = 1.0 / args.hz
    deadline = time.monotonic() + args.seconds
    next_t = time.monotonic()
    captured = 0
    errors = 0

    with args.out.open("w", encoding="utf-8") as f:
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now < next_t:
                time.sleep(next_t - now)
            host_time_s = time.time()
            try:
                payload = fetch_json(args.url, args.timeout)
                normalized = normalize_pose(payload)
                record = {"host_time_s": host_time_s, **normalized}
                captured += 1
            except Exception as exc:
                record = {"host_time_s": host_time_s, "error": type(exc).__name__}
                errors += 1
            f.write(json.dumps(record, separators=(",", ":")) + "\n")
            f.flush()
            next_t += period

    print(json.dumps({"out": str(args.out), "captured": captured, "errors": errors}, indent=2))


if __name__ == "__main__":
    main()
