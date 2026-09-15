#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

from real_hardware_contract import normalize_command_gate, normalize_real_hardware_status, write_runtime_contract


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bridge real-hardware adapter payload into SO101 runtime contract files."
    )
    parser.add_argument("--root-dir", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--runtime-dir", default="")
    parser.add_argument("--source", choices=("fake", "file", "command"), required=True)
    parser.add_argument("--input-file", default="")
    parser.add_argument("--command", default="")
    parser.add_argument("--control-interface", default="fake-adapter")
    parser.add_argument("--power-state", default="未上电")
    parser.add_argument("--mode", default="安全待机")
    parser.add_argument("--last-error", default="无")
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--estop-active", action="store_true")
    parser.add_argument("--allow-execute", action="store_true")
    parser.add_argument("--gate-enabled", action="store_true")
    parser.add_argument("--gate-reason-code", default="")
    parser.add_argument("--gate-reason", default="")
    parser.add_argument("--gate-source", default="")
    return parser


def _load_payload(args: argparse.Namespace) -> dict:
    if args.source == "fake":
        return {
            "online": bool(args.online),
            "controlInterface": args.control_interface,
            "powerState": args.power_state,
            "estopActive": bool(args.estop_active),
            "mode": args.mode,
            "lastError": args.last_error,
            "allowExecute": bool(args.allow_execute),
        }
    if args.source == "file":
        if not args.input_file:
            raise SystemExit("--input-file is required when --source=file")
        return json.loads(Path(args.input_file).read_text(encoding="utf-8"))
    if not args.command:
        raise SystemExit("--command is required when --source=command")
    completed = subprocess.run(
        args.command,
        shell=True,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    root_dir = Path(args.root_dir).resolve()
    runtime_dir = Path(args.runtime_dir).resolve() if args.runtime_dir else root_dir / ".vscode" / ".runtime"
    payload = normalize_real_hardware_status(_load_payload(args))
    gate = normalize_command_gate(
        {
            "commandExecutionEnabled": bool(args.gate_enabled),
            "reasonCode": args.gate_reason_code,
            "reason": args.gate_reason,
            "source": args.gate_source or f"{args.source}-adapter",
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
