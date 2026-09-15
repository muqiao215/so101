#!/usr/bin/env python3
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

from real_hardware_calibration import validate_calibration_profile


STATUS_FILE_NAME = "real_hardware_status.json"
GATE_FILE_NAME = "real_hardware_command_gate.json"
CALIBRATION_FILE_NAME = "real_hardware_calibration.json"
REPORT_FILE_NAME = "real_hardware_preflight_report.json"


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_updated_at(text: str) -> datetime | None:
    if not text or not str(text).strip():
        return None
    text = str(text).strip()
    for parser in (
        lambda value: datetime.strptime(value, "%Y-%m-%d %H:%M:%S %z"),
        lambda value: datetime.fromisoformat(value),
    ):
        try:
            return parser(text)
        except ValueError:
            continue
    return None


def _read_backend_real_hardware(api_url: str, timeout_sec: float) -> Dict[str, Any] | None:
    request = urllib.request.Request(api_url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8"))
        real_hardware = payload.get("realHardware")
        return real_hardware if isinstance(real_hardware, dict) else None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def run_preflight(
    runtime_dir: Path,
    max_status_age_sec: int = 15,
    now: datetime | None = None,
    api_url: str = "",
    api_timeout_sec: float = 1.5,
) -> Dict[str, Any]:
    runtime_dir = Path(runtime_dir).resolve()
    now = now or datetime.now().astimezone()

    status_path = runtime_dir / STATUS_FILE_NAME
    gate_path = runtime_dir / GATE_FILE_NAME
    calibration_path = runtime_dir / CALIBRATION_FILE_NAME

    checks: list[Dict[str, Any]] = []

    def add_check(key: str, label: str, ok: bool, detail: str) -> None:
        checks.append({"key": key, "label": label, "ok": bool(ok), "detail": detail})

    status_exists = status_path.exists()
    gate_exists = gate_path.exists()
    calibration_exists = calibration_path.exists()

    add_check("status_file", "状态文件存在", status_exists, str(status_path) if status_exists else "缺少 real_hardware_status.json")
    add_check("gate_file", "门控文件存在", gate_exists, str(gate_path) if gate_exists else "缺少 real_hardware_command_gate.json")
    add_check(
        "calibration_file",
        "校准文件存在",
        calibration_exists,
        str(calibration_path) if calibration_exists else "缺少 real_hardware_calibration.json",
    )

    status_payload = _load_json(status_path) if status_exists else {}
    gate_payload = _load_json(gate_path) if gate_exists else {}
    calibration_payload = _load_json(calibration_path) if calibration_exists else {}

    updated_at = _parse_updated_at(status_payload.get("updatedAt", ""))
    status_age_sec = None if updated_at is None else max(0.0, (now - updated_at).total_seconds())
    status_fresh = updated_at is not None and status_age_sec is not None and status_age_sec <= float(max_status_age_sec)

    if updated_at is None:
      add_check("status_fresh", "状态新鲜", False, "updatedAt 缺失或无法解析")
    else:
      add_check(
          "status_fresh",
          "状态新鲜",
          status_fresh,
          f"状态年龄 {status_age_sec:.1f}s，阈值 {max_status_age_sec}s",
      )

    online = bool(status_payload.get("online", False))
    power_on = str(status_payload.get("powerState", "")).strip() == "已上电"
    estop_clear = not bool(status_payload.get("estopActive", False))
    allow_execute = bool(status_payload.get("allowExecute", False))
    gate_enabled = bool(gate_payload.get("commandExecutionEnabled", False))
    gate_reason_code = str(gate_payload.get("reasonCode", "")).strip() or str(status_payload.get("gateReasonCode", "")).strip()
    control_interface = str(status_payload.get("controlInterface", "")).strip() or "待接入"

    add_check("driver_online", "主臂在线", online, control_interface if online else "真机当前离线")
    add_check("power_on", "上电状态", power_on, status_payload.get("powerState", "未上电"))
    add_check("estop_clear", "急停正常", estop_clear, "急停未触发" if estop_clear else "急停已触发")

    normalized_calibration, calibration_errors = validate_calibration_profile(
        calibration_payload if calibration_exists and isinstance(calibration_payload, dict) else {}
    )
    calibration_valid = calibration_exists and not calibration_errors and bool(normalized_calibration.get("calibrated", False))
    homed = calibration_valid and bool(normalized_calibration.get("homed", False))
    calibration_detail = (
        "校准文件缺失"
        if not calibration_exists
        else (
            "校准配置已通过校验"
            if calibration_valid
            else ("; ".join(calibration_errors) if calibration_errors else "校准文件未完成 calibrated 标记")
        )
    )

    add_check(
        "calibration_valid",
        "校准有效",
        calibration_valid,
        calibration_detail,
    )
    add_check("homed", "已安全回中", homed, "homed=true" if homed else "homed=false 或校准无效")

    execution_lock_correct = (not allow_execute) and (not gate_enabled)
    add_check(
        "execution_lock",
        "执行仍被锁定",
        execution_lock_correct,
        "当前保护态正确" if execution_lock_correct else "检测到 allowExecute=true 或 commandExecutionEnabled=true",
    )

    backend_real_hardware = _read_backend_real_hardware(api_url, api_timeout_sec) if api_url else None
    backend_match = None
    if backend_real_hardware is not None:
        backend_match = (
            bool(backend_real_hardware.get("online")) == online
            and bool(backend_real_hardware.get("allowExecute")) == allow_execute
            and str(backend_real_hardware.get("gateReasonCode", "")).strip() == gate_reason_code
        )
        add_check(
            "backend_match",
            "后端状态一致",
            backend_match,
            "与 /api/system/status.realHardware 关键字段一致"
            if backend_match
            else "runtime 与 backend 关键字段不一致",
        )

    ready_for_next_phase = all(
        (
            online,
            status_fresh,
            power_on,
            estop_clear,
            calibration_valid,
            homed,
            execution_lock_correct,
        )
    )

    summary = {
        "runtimeDir": str(runtime_dir),
        "readyForNextPhase": ready_for_next_phase,
        "statusFresh": status_fresh,
        "statusAgeSec": status_age_sec,
        "online": online,
        "controlInterface": control_interface,
        "powerState": status_payload.get("powerState", "未上电"),
        "estopActive": bool(status_payload.get("estopActive", False)),
        "allowExecute": allow_execute,
        "commandExecutionEnabled": gate_enabled,
        "gateReasonCode": gate_reason_code,
        "calibrationValid": calibration_valid,
        "homed": homed,
        "checks": checks,
    }
    if backend_real_hardware is not None:
        summary["backendRealHardware"] = backend_real_hardware
        summary["backendMatch"] = backend_match
    report_path = runtime_dir / REPORT_FILE_NAME
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary["reportPath"] = str(report_path)
    return summary


def _print_human_summary(summary: Dict[str, Any]) -> None:
    headline = "PASS" if summary["readyForNextPhase"] else "FAIL"
    print(f"[real-hardware-preflight] {headline}")
    print(f"  controlInterface: {summary['controlInterface']}")
    print(f"  powerState: {summary['powerState']}")
    print(f"  gateReasonCode: {summary['gateReasonCode']}")
    print(f"  statusFresh: {summary['statusFresh']}")
    print(
        "  statusAgeSec: "
        + ("unknown" if summary["statusAgeSec"] is None else f"{summary['statusAgeSec']:.1f}")
    )
    print(f"  estopActive: {summary['estopActive']}")
    print(f"  calibrationValid: {summary['calibrationValid']}")
    print(f"  homed: {summary['homed']}")
    print(f"  allowExecute: {summary['allowExecute']}")
    print(f"  commandExecutionEnabled: {summary['commandExecutionEnabled']}")
    if "backendMatch" in summary:
        print(f"  backendMatch: {summary['backendMatch']}")
    print("  checks:")
    for check in summary["checks"]:
        mark = "OK" if check["ok"] else "FAIL"
        print(f"    - [{mark}] {check['label']}: {check['detail']}")
    print(f"  report: {summary['reportPath']}")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run CLI-first preflight for current real-hardware runtime artifacts."
    )
    parser.add_argument(
        "--root-dir",
        default=str(Path(__file__).resolve().parents[2]),
        help="Workspace root used to derive the default runtime dir",
    )
    parser.add_argument(
        "--runtime-dir",
        default="",
        help="Override runtime dir; default is <workspace>/.vscode/.runtime",
    )
    parser.add_argument(
        "--max-status-age-sec",
        "--max-age-seconds",
        dest="max_status_age_sec",
        type=int,
        default=15,
        help="Maximum accepted age for real_hardware_status.updatedAt",
    )
    parser.add_argument(
        "--api-url",
        default="",
        help="Optional /api/system/status URL for backend comparison",
    )
    parser.add_argument(
        "--skip-backend-compare",
        action="store_true",
        help="Skip the optional backend /api/system/status comparison even if --api-url is provided",
    )
    parser.add_argument(
        "--api-timeout-sec",
        type=float,
        default=1.5,
        help="Timeout for optional backend comparison",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON instead of the human-readable summary",
    )
    args = parser.parse_args()

    runtime_dir = (
        Path(args.runtime_dir).resolve()
        if args.runtime_dir
        else Path(args.root_dir).resolve() / ".vscode" / ".runtime"
    )
    summary = run_preflight(
        runtime_dir=runtime_dir,
        max_status_age_sec=args.max_status_age_sec,
        api_url="" if args.skip_backend_compare else args.api_url,
        api_timeout_sec=args.api_timeout_sec,
    )
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        _print_human_summary(summary)
    return 0 if summary["readyForNextPhase"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
