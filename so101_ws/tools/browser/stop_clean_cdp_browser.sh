#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$WORKSPACE_ROOT/.vscode/.runtime"
PROFILE_DIR="$RUNTIME_DIR/cdp-browser-profile"
PORT="${SO101_BROWSER_CDP_PORT:-9223}"

is_wsl() {
  [[ -n "${WSL_DISTRO_NAME:-}" ]] || grep -qiE '(microsoft|wsl)' /proc/version 2>/dev/null
}

windows_profile_dir() {
  local local_appdata
  local_appdata="$(cmd.exe /c echo %LOCALAPPDATA% 2>/dev/null | tr -d '\r' | tail -n 1)"
  if [[ -z "$local_appdata" || "$local_appdata" == "%LOCALAPPDATA%" ]]; then
    return 1
  fi
  printf '%s\\so101-mes\\cdp-browser-profile' "$local_appdata"
}

kill_linux_browsers() {
  local pid args
  for pid in $(pgrep -f -- "--remote-debugging-port=$PORT" 2>/dev/null || true); do
    args="$(ps -p "$pid" -o args= 2>/dev/null || true)"
    if [[ "$args" == *"--user-data-dir=$PROFILE_DIR"* ]]; then
      kill "$pid" 2>/dev/null || true
      sleep 0.2
      kill -9 "$pid" 2>/dev/null || true
    fi
  done
}

kill_windows_browsers() {
  if ! is_wsl; then
    return 0
  fi

  local profile_dir_win profile_ps
  profile_dir_win="$(windows_profile_dir || wslpath -w "$PROFILE_DIR")"
  profile_ps="${profile_dir_win//\'/''}"

  powershell.exe -NoProfile -Command "\
    \$profileDir = '$profile_ps'; \
    \$port = '$PORT'; \
    Get-CimInstance Win32_Process | \
      Where-Object { \
        \$_.CommandLine -and \
        \$_.CommandLine -like \"*--remote-debugging-port=\$port*\" -and \
        \$_.CommandLine -like \"*--user-data-dir=\$profileDir*\" \
      } | \
      ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }\
  " >/dev/null 2>&1 || true
}

kill_windows_browsers
kill_linux_browsers
