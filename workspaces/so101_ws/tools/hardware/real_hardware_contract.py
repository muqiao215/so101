#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


STATUS_FILE_NAME = "real_hardware_status.json"
COMMAND_GATE_FILE_NAME = "real_hardware_command_gate.json"
DEFAULT_GATE_REASON_LABELS = {
    "WAITING_FOR_HARDWARE": "真机尚未接入",
    "STATUS_TIMEOUT": "状态超时，保持保护态",
    "NOT_POWERED": "真机已接入，但尚未上电",
    "UNCALIBRATED": "尚未完成真机校准",
    "CALIBRATION_INVALID": "校准配置无效，保持保护态",
    "NOT_HOMED": "尚未完成安全回中",
    "ESTOP_ACTIVE": "急停触发，保持保护态",
    "MANUAL_LOCK": "默认保护态，需人工确认后放行",
    "HWS_002_PENDING": "安全基线未完成，继续锁执行",
    "CAL_002_PENDING": "校准骨架已就位，待真实校准完成",
    "STATUS_FILE_INVALID": "真机状态文件解析失败",
    "GATE_FILE_INVALID": "命令门控文件解析失败",
    "READY_FOR_MIN_MOTION": "已满足最小动作验证前提",
}
KNOWN_GATE_REASON_CODES = frozenset(DEFAULT_GATE_REASON_LABELS.keys())


def _now_text() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def _text(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def normalize_real_hardware_status(payload: Dict[str, Any]) -> Dict[str, Any]:
    online = bool(payload.get("online", False))
    estop_active = bool(payload.get("estopActive", False))
    power_state = _text(payload.get("powerState"), "未上电")
    allow_execute = (
        bool(payload.get("allowExecute", False))
        and online
        and not estop_active
        and power_state == "已上电"
    )

    return {
        "online": online,
        "controlInterface": _text(payload.get("controlInterface"), "待接入"),
        "powerState": power_state,
        "estopActive": estop_active,
        "mode": _text(payload.get("mode"), "安全待机"),
        "lastError": _text(payload.get("lastError"), "待接入真机状态源"),
        "allowExecute": allow_execute,
        "updatedAt": _text(payload.get("updatedAt"), _now_text()),
    }


def normalize_gate_reason_code(reason_code: Any, command_enabled: bool) -> str:
    fallback = "READY_FOR_MIN_MOTION" if command_enabled else "MANUAL_LOCK"
    normalized = _text(reason_code, fallback)
    if normalized not in KNOWN_GATE_REASON_CODES:
        return fallback
    if command_enabled and normalized != "READY_FOR_MIN_MOTION":
        return normalized
    if not command_enabled and normalized == "READY_FOR_MIN_MOTION":
        return "MANUAL_LOCK"
    return normalized


def normalize_command_gate(payload: Dict[str, Any]) -> Dict[str, Any]:
    requested_enabled = bool(payload.get("commandExecutionEnabled", False))
    reason_code = normalize_gate_reason_code(payload.get("reasonCode"), requested_enabled)
    command_enabled = requested_enabled and reason_code == "READY_FOR_MIN_MOTION"
    return {
        "commandExecutionEnabled": command_enabled,
        "reasonCode": reason_code,
        "reason": _text(
            payload.get("reason"),
            DEFAULT_GATE_REASON_LABELS[reason_code],
        ),
        "source": _text(payload.get("source"), "unknown"),
        "updatedAt": _text(payload.get("updatedAt"), _now_text()),
    }


def write_runtime_contract(
    runtime_dir: Path, status: Dict[str, Any], gate: Dict[str, Any]
) -> Dict[str, Path]:
    runtime_dir = Path(runtime_dir).resolve()
    runtime_dir.mkdir(parents=True, exist_ok=True)

    status_file = runtime_dir / STATUS_FILE_NAME
    gate_file = runtime_dir / COMMAND_GATE_FILE_NAME

    status_file.write_text(
        json.dumps(normalize_real_hardware_status(status), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    gate_file.write_text(
        json.dumps(normalize_command_gate(gate), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"status": status_file, "gate": gate_file}
