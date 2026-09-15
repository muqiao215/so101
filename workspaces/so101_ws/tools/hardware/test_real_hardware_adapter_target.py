#!/usr/bin/env python3
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from real_hardware_adapter_target import load_target_config, run_target_smoke


class RealHardwareAdapterTargetTest(unittest.TestCase):
    def test_load_target_config_requires_source_block(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "target.json"
            config_path.write_text(json.dumps({"adapterId": "demo"}, ensure_ascii=False), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "source"):
                load_target_config(config_path)

    def test_run_target_smoke_with_file_source_writes_report_and_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            runtime_dir = root_dir / ".vscode" / ".runtime"
            runtime_dir.mkdir(parents=True)

            payload_path = root_dir / "status.json"
            payload_path.write_text(
                json.dumps(
                    {
                        "online": True,
                        "controlInterface": "real-dir / ttyACM0",
                        "powerState": "已上电",
                        "estopActive": False,
                        "mode": "保护待机",
                        "lastError": "",
                        "allowExecute": True,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            config_path = root_dir / "target.json"
            config_path.write_text(
                json.dumps(
                    {
                        "adapterId": "real-hw-demo",
                        "source": {"type": "file", "path": str(payload_path)},
                        "gate": {
                            "enabled": False,
                            "reason": "HWS-002 未通过，默认锁执行",
                            "source": "target-test",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = run_target_smoke(load_target_config(config_path), runtime_dir)

            self.assertEqual(result["adapterId"], "real-hw-demo")
            self.assertTrue((runtime_dir / "real_hardware_status.json").exists())
            self.assertTrue((runtime_dir / "real_hardware_command_gate.json").exists())
            self.assertTrue(result["report"].exists())
            self.assertFalse(result["gate"]["commandExecutionEnabled"])
            self.assertEqual(result["normalized"]["controlInterface"], "real-dir / ttyACM0")

    def test_load_target_config_expands_env_vars(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "status.json"
            payload_path.write_text("{}", encoding="utf-8")
            config_path = Path(temp_dir) / "target.json"
            config_path.write_text(
                json.dumps(
                    {
                        "adapterId": "env-demo",
                        "source": {"type": "file", "path": "${SO101_REAL_HW_STATUS_PATH}"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            old_value = os.environ.get("SO101_REAL_HW_STATUS_PATH")
            os.environ["SO101_REAL_HW_STATUS_PATH"] = str(payload_path)
            try:
                config = load_target_config(config_path)
            finally:
                if old_value is None:
                    os.environ.pop("SO101_REAL_HW_STATUS_PATH", None)
                else:
                    os.environ["SO101_REAL_HW_STATUS_PATH"] = old_value

            self.assertEqual(config["source"]["path"], str(payload_path))

    def test_run_target_smoke_with_command_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            runtime_dir = root_dir / ".vscode" / ".runtime"
            runtime_dir.mkdir(parents=True)
            config = {
                "adapterId": "command-demo",
                "source": {
                    "type": "command",
                    "command": "python3 -c \"import json; print(json.dumps({'online': True, 'controlInterface': 'cmd-adapter', 'powerState': '已上电', 'estopActive': False, 'mode': '保护待机', 'lastError': '', 'allowExecute': False}, ensure_ascii=False))\"",
                },
                "gate": {
                    "enabled": False,
                    "reason": "HWS-002 未通过，默认锁执行",
                    "source": "command-test",
                },
            }

            result = run_target_smoke(config, runtime_dir)

            self.assertEqual(result["adapterId"], "command-demo")
            self.assertEqual(result["sourceType"], "command")
            self.assertEqual(result["normalized"]["controlInterface"], "cmd-adapter")
            self.assertFalse(result["gate"]["commandExecutionEnabled"])


if __name__ == "__main__":
    unittest.main()
