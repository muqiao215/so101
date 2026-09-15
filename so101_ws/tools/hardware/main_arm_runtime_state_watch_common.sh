#!/usr/bin/env bash

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.vscode/.runtime"
WATCH_PID_FILE="$RUNTIME_DIR/main_arm_runtime_watch.pid"
WATCH_LOG_FILE="$RUNTIME_DIR/main_arm_runtime_watch.log"
WATCH_META_FILE="$RUNTIME_DIR/main_arm_runtime_watch.meta"
WATCH_LOOP_SCRIPT="$ROOT_DIR/tools/hardware/main_arm_runtime_state_watch_loop.sh"

ensure_runtime_dir() {
  mkdir -p "$RUNTIME_DIR"
}

timestamp_now() {
  date '+%Y-%m-%d %H:%M:%S %z'
}

detect_main_arm_port() {
  for candidate in /dev/ttyUSB* /dev/ttyACM*; do
    if [[ -e "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

resolve_main_arm_port() {
  if [[ -n "${SO101_MAIN_ARM_PORT:-}" ]]; then
    echo "$SO101_MAIN_ARM_PORT"
    return 0
  fi
  detect_main_arm_port
}

is_pid_alive() {
  local pid="${1:-}"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null
}

pid_matches_watch_loop() {
  local pid="${1:-}"
  local cmdline
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  [[ -r "/proc/$pid/cmdline" ]] || return 1
  cmdline="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
  [[ "$cmdline" == *"$WATCH_LOOP_SCRIPT"* ]]
}

write_watch_meta() {
  local pid="$1"
  local port="$2"
  local interval="$3"
  ensure_runtime_dir
  cat >"$WATCH_META_FILE" <<META
PID=$pid
PORT=$port
INTERVAL_SEC=$interval
STARTED_AT=$(timestamp_now)
LOOP_SCRIPT=$WATCH_LOOP_SCRIPT
META
}

clear_watch_meta() {
  rm -f "$WATCH_META_FILE"
}

read_watch_meta() {
  WATCH_META_PID=""
  WATCH_META_PORT=""
  WATCH_META_INTERVAL_SEC=""
  WATCH_META_STARTED_AT=""
  WATCH_META_LOOP_SCRIPT=""

  [[ -f "$WATCH_META_FILE" ]] || return 0

  while IFS='=' read -r key value; do
    case "$key" in
      PID) WATCH_META_PID="$value" ;;
      PORT) WATCH_META_PORT="$value" ;;
      INTERVAL_SEC) WATCH_META_INTERVAL_SEC="$value" ;;
      STARTED_AT) WATCH_META_STARTED_AT="$value" ;;
      LOOP_SCRIPT) WATCH_META_LOOP_SCRIPT="$value" ;;
    esac
  done <"$WATCH_META_FILE"
}

get_watcher_pids() {
  ensure_runtime_dir
  local pid=""
  declare -A seen=()

  if [[ -f "$WATCH_PID_FILE" ]]; then
    pid="$(cat "$WATCH_PID_FILE" 2>/dev/null || true)"
    if is_pid_alive "$pid" && pid_matches_watch_loop "$pid"; then
      seen["$pid"]=1
      printf '%s\n' "$pid"
    fi
  fi

  if command -v pgrep >/dev/null 2>&1; then
    while IFS= read -r pid; do
      [[ -n "$pid" ]] || continue
      if [[ -z "${seen[$pid]:-}" ]] && is_pid_alive "$pid" && pid_matches_watch_loop "$pid"; then
        seen["$pid"]=1
        printf '%s\n' "$pid"
      fi
    done < <(pgrep -f "$WATCH_LOOP_SCRIPT" || true)
  fi
}

cleanup_stale_watch_artifacts() {
  local pid=""
  if [[ -f "$WATCH_PID_FILE" ]]; then
    pid="$(cat "$WATCH_PID_FILE" 2>/dev/null || true)"
    if ! (is_pid_alive "$pid" && pid_matches_watch_loop "$pid"); then
      rm -f "$WATCH_PID_FILE"
    fi
  fi

  read_watch_meta
  if [[ -n "$WATCH_META_PID" ]] && ! (is_pid_alive "$WATCH_META_PID" && pid_matches_watch_loop "$WATCH_META_PID"); then
    clear_watch_meta
  fi
}
