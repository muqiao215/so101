#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from real_hardware_preflight import run_preflight


def _now_text(offset_seconds: int = 0) -> str:
    tz = timezone(timedelta(hours=8))
    return (datetime.now(tz) + timedelta(seconds=offset_seconds)).strftime("%Y-%m-%d %H:%M:%S %z")


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class RealHardwarePreflightTest(unittest.TestCase):
    def test_preflight_passes_when_runtime_is_fresh_calibrated_and_locked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
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

            report = run_preflight(runtime_dir=runtime_dir, max_status_age_sec=15)

        self.assertTrue(report["readyForNextPhase"])
        self.assertTrue(next(item for item in report["checks"] if item["key"] == "execution_lock")["ok"])

    def test_preflight_fails_when_calibration_file_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
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
                    "reasonCode": "CAL_002_PENDING",
                    "reason": "校准骨架已就位，待真实校准完成",
                    "source": "unit-test",
                    "updatedAt": _now_text(),
                },
            )

            report = run_preflight(runtime_dir=runtime_dir, max_status_age_sec=15)

        self.assertFalse(report["readyForNextPhase"])
        self.assertFalse(report["calibrationValid"])

    def test_preflight_fails_when_status_is_stale(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
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
                    "updatedAt": _now_text(offset_seconds=-120),
                },
            )
            _write_json(
                runtime_dir / "real_hardware_command_gate.json",
                {
                    "commandExecutionEnabled": False,
                    "reasonCode": "HWS_002_PENDING",
                    "reason": "安全基线未完成，继续锁执行",
                    "source": "unit-test",
                    "updatedAt": _now_text(offset_seconds=-120),
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

            report = run_preflight(runtime_dir=runtime_dir, max_status_age_sec=15)

        self.assertFalse(report["readyForNextPhase"])
        self.assertFalse(report["statusFresh"])

    def test_cli_accepts_max_age_seconds_alias(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
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

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve().parent / "run_real_hardware_preflight.py"),
                    "--runtime-dir",
                    str(runtime_dir),
                    "--max-age-seconds",
                    "15",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        self.assertIn("statusAgeSec:", result.stdout)
        self.assertIn("powerState: 已上电", result.stdout)


if __name__ == "__main__":
    unittest.main()
