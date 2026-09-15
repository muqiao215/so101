#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PS1_PATH="$ROOT_DIR/tools/hardware/windows_usbipd_recover_attach.ps1"
BUSID="${BUSID:-2-2}"
HARDWARE_ID="${HARDWARE_ID:-1A86:7523}"
WSL_DISTRO_NAME="${WSL_DISTRO_NAME:-Ubuntu-22.04}"
WAIT_SECONDS="${WAIT_SECONDS:-12}"
TTY_GLOB="${TTY_GLOB:-/dev/ttyUSB* /dev/ttyACM*}"

WHAT_IF=0
RESTART_USBIPD_SERVICE=0
NO_ATTACH=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --what-if)
      WHAT_IF=1
      ;;
    --restart-service)
      RESTART_USBIPD_SERVICE=1
      ;;
    --no-attach)
      NO_ATTACH=1
      ;;
    --busid)
      BUSID="$2"
      shift
      ;;
    --hardware-id)
      HARDWARE_ID="$2"
      shift
      ;;
    --distro)
      WSL_DISTRO_NAME="$2"
      shift
      ;;
    --wait-seconds)
      WAIT_SECONDS="$2"
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
  shift
done

PS1_WIN="$(wslpath -w "$PS1_PATH")"
ARGS=(
  "-NoProfile"
  "-ExecutionPolicy" "Bypass"
  "-File" "$PS1_WIN"
  "-BusId" "$BUSID"
  "-HardwareId" "$HARDWARE_ID"
  "-Distro" "$WSL_DISTRO_NAME"
)

if [[ "$RESTART_USBIPD_SERVICE" == "1" ]]; then
  ARGS+=("-RestartUsbipdService")
fi
if [[ "$NO_ATTACH" == "1" ]]; then
  ARGS+=("-NoAttach")
fi
if [[ "$WHAT_IF" == "1" ]]; then
  ARGS+=("-WhatIf")
fi

echo "[main-arm-usbipd] invoking Windows recovery script"
powershell.exe "${ARGS[@]}"

if [[ "$WHAT_IF" == "1" || "$NO_ATTACH" == "1" ]]; then
  exit 0
fi

echo "[main-arm-usbipd] waiting for Linux serial node"
for _ in $(seq 1 "$WAIT_SECONDS"); do
  for candidate in /dev/ttyUSB* /dev/ttyACM*; do
    if [[ -e "$candidate" ]]; then
      echo "[main-arm-usbipd] detected serial node: $candidate"
      echo "export SO101_MAIN_ARM_PORT=$candidate"
      exit 0
    fi
  done
  sleep 1
done

echo "[main-arm-usbipd] no /dev/ttyUSB* or /dev/ttyACM* detected after ${WAIT_SECONDS}s" >&2
echo "[main-arm-usbipd] check 'dmesg | tail' and rerun with --restart-service if needed" >&2
exit 1
