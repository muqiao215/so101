#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import serial


def now_string() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %z")


def build_payload(
    port: str,
    online: bool,
    last_error: str,
    power_state: str,
    mode: str,
    *,
    allow_execute: bool,
) -> dict:
    return {
        "online": online,
        "controlInterface": f"main-arm serial {port}",
        "powerState": power_state,
        "estopActive": False,
        "mode": mode,
        "lastError": last_error,
        "allowExecute": bool(allow_execute and online),
        "updatedAt": now_string(),
    }


def probe_serial_port(port: str, baud_rate: int, timeout: float) -> tuple[bool, str]:
    if not Path(port).exists():
        return False, f"serial device not found: {port}"

    try:
        with serial.Serial(port=port, baudrate=baud_rate, timeout=timeout):
            return True, ""
    except Exception as exc:  # pragma: no cover - depends on host serial driver state
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a conservative main-arm serial presence status as SO101 hardware JSON."
    )
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baud-rate", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=0.3)
    parser.add_argument("--power-state", default="未上电")
    parser.add_argument("--mode", default="串口在线 / 保护待机")
    parser.add_argument("--allow-execute", action="store_true")
    args = parser.parse_args()

    online, last_error = probe_serial_port(args.port, args.baud_rate, args.timeout)
    if online:
        payload = build_payload(
            port=args.port,
            online=True,
            last_error="无",
            power_state=args.power_state,
            mode=args.mode,
            allow_execute=args.allow_execute,
        )
    else:
        payload = build_payload(
            port=args.port,
            online=False,
            last_error=last_error,
            power_state="未上电",
            mode="串口未就绪 / 保护待机",
            allow_execute=False,
        )

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
