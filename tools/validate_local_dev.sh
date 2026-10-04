#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python tools/check_dev_environment.py
python -m pip check
python -m compileall -q tools cad fit simulation
python -m pytest -q tests

if command -v node >/dev/null 2>&1; then
  cp showcase/app.js /tmp/x1-showcase-app.mjs
  node --check /tmp/x1-showcase-app.mjs
  echo "Browser module syntax: PASS"
else
  echo "Node is not installed; skipping browser module syntax check."
fi

echo "Local Worcester X1 software validation: PASS"
