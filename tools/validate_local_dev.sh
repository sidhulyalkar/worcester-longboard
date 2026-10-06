#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python tools/check_dev_environment.py
python -m pip check
python -m compileall -q tools cad fit simulation configurator
python -m pytest -q tests
python tools/validate_board_builder.py

if command -v node >/dev/null 2>&1; then
  cp showcase/app.js /tmp/x1-showcase-app.mjs
  cp builder/app.js /tmp/x1-builder-app.mjs
  node --check /tmp/x1-showcase-app.mjs
  node --check /tmp/x1-builder-app.mjs
  node --check builder/engine.mjs
  node --check builder/platform_engine.mjs
  node --check builder/composer.mjs
  node --check builder/swap_engine.mjs
  node --check builder/visual_state.mjs
  node --check builder/preview_renderer.mjs
  node --check tools/generate_board_candidates.mjs
  node --test tests/js/test_board_builder_engine.mjs tests/js/test_board_catalog_composer.mjs tests/js/test_board_builder_swap_lab.mjs tests/js/test_board_builder_visuals.mjs

  env -u PYTHONPATH python tools/generate_board_candidates.py     configurator/examples/trail_rider_profile.json     --out /tmp/x1-board-builder-python.json
  node tools/generate_board_candidates.mjs     configurator/examples/trail_rider_profile.json     > /tmp/x1-board-builder-browser.json
  python tools/compare_board_builder_engines.py     /tmp/x1-board-builder-python.json     /tmp/x1-board-builder-browser.json
  echo "Browser modules and Board Builder parity: PASS"
else
  echo "Node is not installed; skipping browser module and Board Builder browser-engine checks."
fi

echo "Local Worcester X1 software validation: PASS"
