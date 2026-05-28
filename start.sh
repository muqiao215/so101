#!/usr/bin/env bash
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${0}")/win7_follower_demo" && pwd)"
LOG_DIR="$DEMO_DIR/logs"
PID_FILE="/tmp/so101_monitor.pid"
PORT="$(python3 -c 'import json; print(json.load(open("'"$DEMO_DIR"'/config/serial_config.json")).get("http_port", 8765))' 2>/dev/null || echo 8765)"
SERIAL_PORT="/dev/ttyACM0"
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
    if [ ! -e "$SERIAL_PORT" ]; then
        echo "Serial port $SERIAL_PORT not found yet."
        echo "If the arm is plugged in later, click Connect in the web page."
        return 0
    fi

    if [ -r "$SERIAL_PORT" ] && [ -w "$SERIAL_PORT" ]; then
        echo "Serial port access OK: $SERIAL_PORT"
        return 0
    fi

    echo "Serial port needs permission fix: $SERIAL_PORT"
    if sudo -n chmod 666 "$SERIAL_PORT" 2>/dev/null; then
        echo "Serial port permission fixed."
        return 0
    fi

    echo ""
    echo "开机后第一次访问机械臂需要输入一次系统密码。"
    echo "This is only used to run: sudo chmod 666 $SERIAL_PORT"
    echo ""
    if sudo -v && sudo chmod 666 "$SERIAL_PORT"; then
        echo "Serial port permission fixed."
    else
        echo "WARNING: Could not fix $SERIAL_PORT permission."
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
        echo "  Mode:     监视 / 动作"
        echo ""
        echo "  每次启动会先关闭旧服务，然后启动新服务"
        echo "  关闭此窗口 = 停止服务"
        echo ""

        ensure_serial_access

        cd "$DEMO_DIR"
        trap cleanup EXIT INT TERM
        python3 -u app.py &
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
