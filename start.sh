#!/usr/bin/env bash
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${0}")/mint_follower_demo" && pwd)"
LOG_DIR="$DEMO_DIR/logs"
PID_FILE="/tmp/so101_monitor.pid"
CONFIG_PATH="$DEMO_DIR/config/serial_config.json"
PYTHON_BIN="$(command -v python3)"
PORT="$("$PYTHON_BIN" -c 'import json; print(json.load(open("'"$CONFIG_PATH"'")).get("http_port", 8765))' 2>/dev/null || echo 8765)"
SERIAL_PORT="$("$PYTHON_BIN" -c 'import json; print(json.load(open("'"$CONFIG_PATH"'")).get("port", "/dev/ttyACM0"))' 2>/dev/null || echo /dev/ttyACM0)"
mapfile -t SERIAL_PORTS < <(
    "$PYTHON_BIN" -c '
import json
import glob

config = json.load(open("'"$CONFIG_PATH"'"))
ports = []
def add(value):
    value = str(value or "").strip()
    if value and value not in ports:
        ports.append(value)
for key in ("port", "leader_port"):
    add(config.get(key, ""))
for pattern in ("/dev/serial/by-id/*", "/dev/ttyACM*", "/dev/ttyUSB*"):
    for value in sorted(glob.glob(pattern)):
        add(value)
for value in ports:
    print(value)
' 2>/dev/null
)
SERVER_PID=""

mkdir -p "$LOG_DIR"

stop_old() {
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
        kill -9 "$OLD_PID" 2>/dev/null || true
        rm -f "$PID_FILE"
    fi
    fuser -k "$PORT"/tcp 2>/dev/null || true
    fuser -k 8765/tcp 2>/dev/null || true
    fuser -k 8766/tcp 2>/dev/null || true
    sleep 1
}

cleanup() {
    if [ -n "${SERVER_PID:-}" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
        sleep 1
        kill -9 "$SERVER_PID" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
}

ensure_serial_access() {
    local port="$1"

    if [ ! -e "$port" ]; then
        echo "Serial port $port not found yet."
        echo "If the arm is plugged in later, click Connect in the web page."
        return 0
    fi

    if [ -r "$port" ] && [ -w "$port" ]; then
        echo "Serial port access OK: $port"
        return 0
    fi

    echo "Serial port needs permission fix: $port"
    if sudo -n chmod 666 "$port" 2>/dev/null; then
        echo "Serial port permission fixed."
        return 0
    fi

    echo ""
    echo "开机后第一次访问机械臂需要输入一次系统密码。"
    echo "This is only used to run: sudo chmod 666 $port"
    echo ""
    if sudo -v && sudo chmod 666 "$port"; then
        echo "Serial port permission fixed."
    else
        echo "WARNING: Could not fix $port permission."
        echo "The web UI will still open, but Connect may fail until permissions are fixed."
    fi
}

case "${1:-start}" in
    stop)
        stop_old
        echo "Stopped."
        ;;
    restart)
        stop_old
        sleep 1
        exec "$0" start
        ;;
    start|*)
        stop_old

        echo "========================================="
        echo "  SO101 机械臂控制台"
        echo "========================================="
        echo ""
        echo "  Frontend: http://127.0.0.1:$PORT"
        echo "  Log:      $LOG_DIR/"
        echo "  Python:   $PYTHON_BIN"
        echo "  Mode:     监视 / 动作"
        echo ""
        echo "  每次启动会先关闭旧服务，然后启动新服务"
        echo "  关闭此窗口 = 停止服务"
        echo ""

        if [ "${#SERIAL_PORTS[@]}" -eq 0 ]; then
            SERIAL_PORTS=("$SERIAL_PORT")
        fi
        for port in "${SERIAL_PORTS[@]}"; do
            ensure_serial_access "$port"
        done

        cd "$DEMO_DIR"
        trap cleanup EXIT INT TERM
        "$PYTHON_BIN" -u app.py &
        SERVER_PID=$!
        echo "$SERVER_PID" > "$PID_FILE"

        sleep 2
        if kill -0 "$SERVER_PID" 2>/dev/null; then
            echo "Server started (PID $SERVER_PID)."
            xdg-open "http://127.0.0.1:$PORT" 2>/dev/null || true
            echo ""
            echo "Press Ctrl+C or close this window to stop."
            echo "========================================="
            wait "$SERVER_PID"
        else
            echo "ERROR: Server failed to start. Check $LOG_DIR/"
            echo "Press Enter to close..."
            read
            exit 1
        fi
        ;;
esac
