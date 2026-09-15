#!/usr/bin/env python3
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

from real_hardware_contract import (
    normalize_command_gate,
    normalize_real_hardware_status,
    write_runtime_contract,
)


def _expand_env(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, str):
        return os.path.expandvars(value)
    return value


def load_target_config(config_path: Path) -> Dict[str, Any]:
    config_path = Path(config_path).resolve()
    config = _expand_env(json.loads(config_path.read_text(encoding="utf-8")))
    if not isinstance(config, dict):
        raise ValueError("target config must be a JSON object")
    if "source" not in config or not isinstance(config["source"], dict):
        raise ValueError("target config must contain source block")
    source_type = str(config["source"].get("type", "")).strip()
    if source_type not in {"file", "command"}:
        raise ValueError("source.type must be file or command")
    if source_type == "file" and not str(config["source"].get("path", "")).strip():
        raise ValueError("source.path is required when source.type=file")
    if source_type == "command" and not str(config["source"].get("command", "")).strip():
        raise ValueError("source.command is required when source.type=command")
    return config


def _load_payload_from_source(source: Dict[str, Any]) -> Dict[str, Any]:
    source_type = str(source.get("type", "")).strip()
    if source_type == "file":
        path = Path(str(source["path"])).resolve()
        return json.loads(path.read_text(encoding="utf-8"))
    completed = subprocess.run(
        str(source["command"]),
        shell=True,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _write_report(runtime_dir: Path, report: Dict[str, Any]) -> Path:
    report_path = Path(runtime_dir).resolve() / "real_hardware_adapter_smoke_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report_path


def run_target_smoke(config: Dict[str, Any], runtime_dir: Path) -> Dict[str, Any]:
    adapter_id = str(config.get("adapterId", "real-hardware-adapter")).strip() or "real-hardware-adapter"
    source = config["source"]
    raw_payload = _load_payload_from_source(source)
    normalized = normalize_real_hardware_status(raw_payload)
    gate = normalize_command_gate(
        {
            "commandExecutionEnabled": bool(config.get("gate", {}).get("enabled", False)),
            "reasonCode": config.get("gate", {}).get("reasonCode", ""),
            "reason": config.get("gate", {}).get("reason", ""),
            "source": config.get("gate", {}).get("source", adapter_id),
            "updatedAt": normalized["updatedAt"],
        }
    )
    paths = write_runtime_contract(Path(runtime_dir), normalized, gate)
    report = {
        "adapterId": adapter_id,
        "sourceType": source["type"],
        "checks": {
            "sourceLoaded": True,
            "statusFileWritten": True,
            "gateFileWritten": True,
            "gateLocked": not gate["commandExecutionEnabled"],
        },
        "rawPayload": raw_payload,
        "normalized": normalized,
        "gate": gate,
        "statusFile": str(paths["status"]),
        "gateFile": str(paths["gate"]),
    }
    report_path = _write_report(runtime_dir, report)
    report["report"] = report_path
    return report


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run smoke validation for a real-hardware adapter target config."
    )
    parser.add_argument("--config", required=True, help="Path to real hardware adapter target config JSON")
    parser.add_argument(
        "--root-dir",
        default=str(Path(__file__).resolve().parents[2]),
        help="Workspace root used to derive default runtime dir",
    )
    parser.add_argument("--runtime-dir", default="", help="Override runtime dir; default is <workspace>/.vscode/.runtime")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_target_config(config_path)
    runtime_dir = (
        Path(args.runtime_dir).resolve()
        if args.runtime_dir
        else Path(args.root_dir).resolve() / ".vscode" / ".runtime"
    )
    result = run_target_smoke(config, runtime_dir)
    printable = dict(result)
    printable["report"] = str(result["report"])
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
