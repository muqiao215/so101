#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_PATH="${1:-$ROOT_DIR/tools/hardware/real_hardware_adapter_target.example.json}"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"

mkdir -p "$RUNTIME_DIR"

python3 "$ROOT_DIR/tools/hardware/real_hardware_adapter_target.py" \
  --root-dir "$ROOT_DIR" \
  --config "$CONFIG_PATH"

echo
echo "Smoke report: $RUNTIME_DIR/real_hardware_adapter_smoke_report.json"
echo "Runtime status: $RUNTIME_DIR/real_hardware_status.json"
echo "Runtime gate: $RUNTIME_DIR/real_hardware_command_gate.json"
