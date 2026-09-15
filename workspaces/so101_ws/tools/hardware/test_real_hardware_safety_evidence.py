#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from real_hardware_safety_evidence import collect_safety_evidence


def _now_text(offset_seconds: int = 0) -> str:
    tz = timezone(timedelta(hours=8))
    return (datetime.now(tz) + timedelta(seconds=offset_seconds)).strftime("%Y-%m-%d %H:%M:%S %z")


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class RealHardwareSafetyEvidenceTest(unittest.TestCase):
    def _seed_runtime(self, runtime_dir: Path) -> None:
        _write_json(
            runtime_dir / "real_hardware_status.json",
            {
                "online": True,
                "controlInterface": "main-arm serial /dev/ttyUSB0",
                "powerState": "已上电",
                "estopActive": False,
                "mode": "主臂在线 / 待命",
                "lastError": "无",
                "allowExecute": False,
                "updatedAt": _now_text(),
            },
        )
        _write_json(
            runtime_dir / "real_hardware_command_gate.json",
            {
                "commandExecutionEnabled": False,
                "reasonCode": "HWS_002_PENDING",
                "reason": "安全基线未完成，继续锁执行",
                "source": "unit-test",
                "updatedAt": _now_text(),
            },
        )
        _write_json(
            runtime_dir / "real_hardware_calibration.json",
            {
                "schemaVersion": "1.0",
                "profileName": "safe-home",
                "calibrated": True,
                "homed": True,
                "updatedAt": _now_text(),
                "poses": {
                    "home": {"joints": [0, 0, 0, 0, 0, 0]},
                    "pick": {"joints": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]},
                    "place": {"joints": [0.6, 0.5, 0.4, 0.3, 0.2, 0.1]},
                    "gripper_open": {"value": 0.0},
                    "gripper_close": {"value": 1.0},
                },
            },
        )

    def test_ready_when_preflight_ready_and_manual_checks_all_pass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
            self._seed_runtime(runtime_dir)

            report = collect_safety_evidence(
                runtime_dir,
                estop_ok=True,
                controlled_stop_ok=True,
                limit_guard_ok=True,
                speed_scaling_ok=True,
                operator="muqiao",
            )

            self.assertTrue((runtime_dir / "real_hardware_safety_evidence.json").exists())

        self.assertTrue(report["preflight"]["readyForNextPhase"])
        self.assertTrue(report["manualSafetyReady"])
        self.assertTrue(report["readyForManualMotionReview"])

    def test_not_ready_when_manual_checks_incomplete(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
            self._seed_runtime(runtime_dir)

            report = collect_safety_evidence(
                runtime_dir,
                estop_ok=True,
                controlled_stop_ok=False,
                limit_guard_ok=True,
                speed_scaling_ok=False,
            )

        self.assertTrue(report["preflight"]["readyForNextPhase"])
        self.assertFalse(report["manualSafetyReady"])
        self.assertFalse(report["readyForManualMotionReview"])


if __name__ == "__main__":
    unittest.main()
