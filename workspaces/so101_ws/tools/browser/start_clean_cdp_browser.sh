#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$WORKSPACE_ROOT/.vscode/.runtime"
PROFILE_DIR="$RUNTIME_DIR/cdp-browser-profile"
PORT="${SO101_BROWSER_CDP_PORT:-9223}"
START_URL="${SO101_BROWSER_START_URL:-http://127.0.0.1:5173}"

mkdir -p "$RUNTIME_DIR" "$PROFILE_DIR"

is_wsl() {
  [[ -n "${WSL_DISTRO_NAME:-}" ]] || grep -qiE '(microsoft|wsl)' /proc/version 2>/dev/null
}

is_windows_browser() {
  [[ "$1" == *.exe ]]
}

windows_profile_dir() {
  local local_appdata
  local_appdata="$(cmd.exe /c echo %LOCALAPPDATA% 2>/dev/null | tr -d '\r' | tail -n 1)"
  if [[ -z "$local_appdata" || "$local_appdata" == "%LOCALAPPDATA%" ]]; then
    return 1
  fi
  printf '%s\\so101-mes\\cdp-browser-profile' "$local_appdata"
}

find_browser() {
  if [[ -n "${SO101_CDP_BROWSER_BIN:-}" ]]; then
    if [[ -x "${SO101_CDP_BROWSER_BIN}" || -f "${SO101_CDP_BROWSER_BIN}" ]]; then
      echo "$SO101_CDP_BROWSER_BIN"
      return 0
    fi
  fi

  if is_wsl; then
    local windows_candidates=(
      "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
      "/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe"
      "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
      "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
    )
    local candidate
    for candidate in "${windows_candidates[@]}"; do
      if [[ -f "$candidate" ]]; then
        echo "$candidate"
        return 0
      fi
    done
  fi

  local linux_candidates=(
    "$(command -v google-chrome-stable 2>/dev/null || true)"
    "$(command -v google-chrome 2>/dev/null || true)"
    "$(command -v microsoft-edge-stable 2>/dev/null || true)"
    "$(command -v microsoft-edge 2>/dev/null || true)"
    "$(command -v chromium-browser 2>/dev/null || true)"
    "$(command -v chromium 2>/dev/null || true)"
  )
  local candidate
  for candidate in "${linux_candidates[@]}"; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  done

  local playwright_candidate
  playwright_candidate="$(ls -d "$HOME"/.cache/ms-playwright/chromium-*/chrome-linux64/chrome 2>/dev/null | sort | tail -n 1 || true)"
  if [[ -n "$playwright_candidate" && -x "$playwright_candidate" ]]; then
    echo "$playwright_candidate"
    return 0
  fi

  return 1
}

BROWSER_BIN="$(find_browser || true)"
if [[ -z "$BROWSER_BIN" ]]; then
  echo "No clean CDP browser binary found" >&2
  exit 1
fi

if is_windows_browser "$BROWSER_BIN"; then
  PROFILE_ARG="$(windows_profile_dir || wslpath -w "$PROFILE_DIR")"
else
  PROFILE_ARG="$PROFILE_DIR"
fi

exec "$BROWSER_BIN" \
  --user-data-dir="$PROFILE_ARG" \
  --remote-debugging-address=127.0.0.1 \
  --remote-debugging-port="$PORT" \
  --autoplay-policy=no-user-gesture-required \
  --no-first-run \
  --no-default-browser-check \
  --disable-session-crashed-bubble \
  --disable-infobars \
  "$START_URL"
