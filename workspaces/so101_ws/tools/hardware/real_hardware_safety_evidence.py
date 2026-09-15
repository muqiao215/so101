#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from real_hardware_preflight import run_preflight


REPORT_FILE_NAME = "real_hardware_safety_evidence.json"


def _check(key: str, label: str, ok: bool, detail: str) -> Dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "ok": bool(ok),
        "detail": detail,
    }


def collect_safety_evidence(
    runtime_dir: Path,
    *,
    estop_ok: bool,
    controlled_stop_ok: bool,
    limit_guard_ok: bool,
    speed_scaling_ok: bool,
    operator: str = "",
    scenario: str = "",
    notes: str = "",
    max_status_age_sec: int = 15,
) -> Dict[str, Any]:
    runtime_dir = Path(runtime_dir).resolve()
    preflight = run_preflight(runtime_dir=runtime_dir, max_status_age_sec=max_status_age_sec)

    manual_checks = [
        _check(
            "estop_manual",
            "急停人工验证",
            estop_ok,
            "已验证急停触发后系统进入保护态" if estop_ok else "尚未完成急停人工验证",
        ),
        _check(
            "controlled_stop_manual",
            "停机人工验证",
            controlled_stop_ok,
            "已验证停机动作可控且可恢复" if controlled_stop_ok else "尚未完成停机人工验证",
        ),
        _check(
            "limit_guard_manual",
            "限位人工验证",
            limit_guard_ok,
            "已确认危险边界/限位策略" if limit_guard_ok else "尚未完成限位人工验证",
        ),
        _check(
            "speed_scaling_manual",
            "速度缩放人工验证",
            speed_scaling_ok,
            "已确认低速验证档位可用" if speed_scaling_ok else "尚未完成速度缩放人工验证",
        ),
    ]

    manual_ready = all(item["ok"] for item in manual_checks)
    ready_for_manual_motion_review = bool(preflight["readyForNextPhase"]) and manual_ready

    report = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "runtimeDir": str(runtime_dir),
        "operator": operator.strip(),
        "scenario": scenario.strip(),
        "notes": notes.strip(),
        "preflight": preflight,
        "manualChecks": manual_checks,
        "manualSafetyReady": manual_ready,
        "readyForManualMotionReview": ready_for_manual_motion_review,
        "reportPath": str((runtime_dir / REPORT_FILE_NAME).resolve()),
    }

    report_path = runtime_dir / REPORT_FILE_NAME
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def print_human_summary(report: Dict[str, Any]) -> None:
    print("[real-hardware-safety-evidence]")
    print(f"  operator: {report.get('operator') or '-'}")
    print(f"  scenario: {report.get('scenario') or '-'}")
    print(f"  manualSafetyReady: {report['manualSafetyReady']}")
    print(f"  readyForManualMotionReview: {report['readyForManualMotionReview']}")
    print("  manualChecks:")
    for check in report["manualChecks"]:
        mark = "OK" if check["ok"] else "PENDING"
        print(f"    - [{mark}] {check['label']}: {check['detail']}")
    print(f"  report: {report['reportPath']}")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Collect CLI-first real hardware safety evidence on top of current preflight status."
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
    parser.add_argument("--max-status-age-sec", type=int, default=15, help="Max accepted status age for preflight")
    parser.add_argument("--operator", default="", help="Operator name for this evidence record")
    parser.add_argument("--scenario", default="HWS-001 baseline", help="Scenario label")
    parser.add_argument("--notes", default="", help="Free-form notes")
    parser.add_argument("--estop-ok", action="store_true", help="Mark emergency stop manual validation as passed")
    parser.add_argument("--controlled-stop-ok", action="store_true", help="Mark controlled stop validation as passed")
    parser.add_argument("--limit-guard-ok", action="store_true", help="Mark limit guard validation as passed")
    parser.add_argument("--speed-scaling-ok", action="store_true", help="Mark speed scaling validation as passed")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of human summary")
    args = parser.parse_args()

    runtime_dir = Path(args.runtime_dir).resolve() if args.runtime_dir else Path(args.root_dir).resolve() / ".vscode" / ".runtime"
    report = collect_safety_evidence(
        runtime_dir,
        estop_ok=args.estop_ok,
        controlled_stop_ok=args.controlled_stop_ok,
        limit_guard_ok=args.limit_guard_ok,
        speed_scaling_ok=args.speed_scaling_ok,
        operator=args.operator,
        scenario=args.scenario,
        notes=args.notes,
        max_status_age_sec=args.max_status_age_sec,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human_summary(report)
    return 0 if report["readyForManualMotionReview"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
