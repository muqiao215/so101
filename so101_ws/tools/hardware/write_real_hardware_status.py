#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from real_hardware_contract import normalize_command_gate, normalize_real_hardware_status, write_runtime_contract


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write safe real-hardware status for SO101 frontend/backend display."
    )
    parser.add_argument("--root-dir", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--runtime-dir", default="")
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--control-interface", default="待接入")
    parser.add_argument("--power-state", default="未上电")
    parser.add_argument("--estop-active", action="store_true")
    parser.add_argument("--mode", default="安全待机")
    parser.add_argument("--last-error", default="待接入真机状态源")
    parser.add_argument("--allow-execute", action="store_true")
    parser.add_argument("--lock-execute", action="store_true")
    parser.add_argument("--updated-at", default="")
    parser.add_argument("--gate-reason-code", default="")
    parser.add_argument("--gate-reason", default="")
    parser.add_argument("--gate-source", default="write_real_hardware_status.py")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    root_dir = Path(args.root_dir).resolve()
    runtime_dir = Path(args.runtime_dir).resolve() if args.runtime_dir else root_dir / ".vscode" / ".runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    online = bool(args.online and not args.offline)
    allow_execute = bool(args.allow_execute and not args.lock_execute and online and not args.estop_active)

    payload = normalize_real_hardware_status(
        {
            "online": online,
            "controlInterface": args.control_interface,
            "powerState": args.power_state,
            "estopActive": bool(args.estop_active),
            "mode": args.mode,
            "lastError": args.last_error,
            "allowExecute": allow_execute,
            "updatedAt": args.updated_at,
        }
    )
    gate = normalize_command_gate(
        {
            "commandExecutionEnabled": allow_execute,
            "reasonCode": args.gate_reason_code,
            "reason": args.gate_reason,
            "source": args.gate_source,
            "updatedAt": payload["updatedAt"],
        }
    )
    paths = write_runtime_contract(runtime_dir, payload, gate)
    print(paths["status"])
    print(json.dumps(payload, ensure_ascii=False))
    print(paths["gate"])
    print(json.dumps(gate, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
