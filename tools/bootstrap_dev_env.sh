#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3.12}"
RECREATE=0
if [[ "${1:-}" == "--recreate" ]]; then
  RECREATE=1
elif [[ -n "${1:-}" ]]; then
  echo "usage: bash tools/bootstrap_dev_env.sh [--recreate]" >&2
  exit 2
fi

if [[ -n "${CONDA_PREFIX:-}" ]]; then
  cat >&2 <<'EOF'
Conda is currently active.

Run:
  deactivate 2>/dev/null || true
  conda deactivate

Then rerun this bootstrap script.

If python3.12 still resolves to Miniconda/Anaconda, install/use a standalone
Python 3.12, for example Homebrew Python, and pass it explicitly:

  PYTHON_BIN=/opt/homebrew/bin/python3.12 bash tools/bootstrap_dev_env.sh --recreate
EOF
  exit 2
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Cannot find $PYTHON_BIN. Install Python 3.12 or set PYTHON_BIN=/path/to/python3.12." >&2
  exit 2
fi

BASE_PREFIX="$("$PYTHON_BIN" -c 'import sys; print(sys.base_prefix)')"
BASE_LOWER="$(printf '%s' "$BASE_PREFIX" | tr '[:upper:]' '[:lower:]')"
case "$BASE_LOWER" in
  *conda*|*miniconda*|*anaconda*|*miniforge*|*mambaforge*|*micromamba*)
    cat >&2 <<EOF
$PYTHON_BIN resolves to a Conda-family interpreter:
  $BASE_PREFIX

Use a standalone Python 3.12 interpreter instead. On Apple Silicon with
Homebrew this is commonly:

  PYTHON_BIN=/opt/homebrew/bin/python3.12 bash tools/bootstrap_dev_env.sh --recreate
EOF
    exit 2
    ;;
esac

if [[ -d .venv ]]; then
  if [[ "$RECREATE" -eq 1 ]]; then
    echo "Removing existing .venv ..."
    rm -rf .venv
  else
    echo ".venv already exists."
    echo "Use --recreate to rebuild it from $PYTHON_BIN."
    exit 2
  fi
fi

echo "Creating .venv from $PYTHON_BIN ..."
"$PYTHON_BIN" -m venv .venv

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

echo
python tools/check_dev_environment.py
echo
echo "Environment ready."
echo "Activate it later with:"
echo "  source .venv/bin/activate"
