#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUIREMENTS="$SCRIPT_DIR/scripts/requirements.txt"
GUIDE="$SCRIPT_DIR/scripts/presentation_guide.py"
VENV="$SCRIPT_DIR/.venv"

# Find python3
PYTHON=$(command -v python3 || command -v python || true)
if [[ -z "$PYTHON" ]]; then
  echo "[ERROR] Python 3 not found. Install it and try again."
  exit 1
fi

# Create venv if missing
if [[ ! -d "$VENV" ]]; then
  echo "[INFO] Creating virtual environment..."
  "$PYTHON" -m venv "$VENV"
fi

VENV_PYTHON="$VENV/bin/python"

# Install/upgrade dependencies if requirements changed
STAMP="$VENV/.installed_stamp"
if [[ ! -f "$STAMP" ]] || [[ "$REQUIREMENTS" -nt "$STAMP" ]]; then
  echo "[INFO] Installing dependencies..."
  "$VENV_PYTHON" -m pip install -q -r "$REQUIREMENTS"
  touch "$STAMP"
fi

cd "$SCRIPT_DIR"
exec env PYTHONPATH="$SCRIPT_DIR" "$VENV_PYTHON" "$GUIDE" "$@"
