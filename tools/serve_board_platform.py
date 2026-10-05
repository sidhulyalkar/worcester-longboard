#!/usr/bin/env python3
"""Serve the Worcester Board Platform from the repository root."""
from __future__ import annotations

import argparse
import http.server
import os
import socketserver
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReusableThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--prepare-showcase",
        action="store_true",
        help="Regenerate the authority-aware twin before serving.",
    )
    parser.add_argument(
        "--synthetic-snowdeck-demo",
        action="store_true",
        help="When preparing the showcase, include the synthetic SnowDeck demo.",
    )
    args = parser.parse_args()

    if args.prepare_showcase:
        command = [sys.executable, str(ROOT / "tools" / "prepare_x1_showcase.py")]
        if args.synthetic_snowdeck_demo:
            command.append("--synthetic-snowdeck-demo")
        subprocess.run(command, cwd=ROOT, check=True)

    os.chdir(ROOT)
    handler = http.server.SimpleHTTPRequestHandler

    with ReusableThreadingTCPServer((args.host, args.port), handler) as server:
        base = f"http://{args.host}:{args.port}"
        print("")
        print("Worcester Board Platform")
        print("========================")
        print(f"Home:    {base}/")
        print(f"Builder: {base}/builder/")
        print(f"Twin:    {base}/showcase/")
        print("")
        print("Keep this terminal running. Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
