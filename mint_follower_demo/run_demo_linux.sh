#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
mkdir -p logs

PYTHON_BIN="${PYTHON_BIN:-python3}"
exec "$PYTHON_BIN" app.py
