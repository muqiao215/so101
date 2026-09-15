#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from real_hardware_contract import (
    normalize_command_gate,
    normalize_real_hardware_status,
    write_runtime_contract,
)


class RealHardwareContractTest(unittest.TestCase):
    def test_write_runtime_contract_writes_status_and_gate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
            status = normalize_real_hardware_status(
                {
                    "online": True,
                    "controlInterface": "fake-adapter",
                    "powerState": "已上电",
                    "estopActive": False,
                    "mode": "手动低速",
                    "lastError": "",
                    "allowExecute": True,
                    "updatedAt": "2026-03-25 21:00:00 +0800",
                }
            )
            gate = normalize_command_gate(
                {
                    "commandExecutionEnabled": False,
                    "reason": "HWS-002 未通过",
                    "source": "fake",
                    "updatedAt": "2026-03-25 21:00:01 +0800",
                }
            )

            paths = write_runtime_contract(runtime_dir, status, gate)

            self.assertEqual(paths["status"], runtime_dir / "real_hardware_status.json")
            self.assertEqual(paths["gate"], runtime_dir / "real_hardware_command_gate.json")
            self.assertTrue(paths["status"].exists())
            self.assertTrue(paths["gate"].exists())
            self.assertEqual(json.loads(paths["status"].read_text(encoding="utf-8"))["allowExecute"], True)
            self.assertEqual(
                json.loads(paths["gate"].read_text(encoding="utf-8"))["commandExecutionEnabled"], False
            )

    def test_normalize_real_hardware_status_blocks_execute_when_estop_active(self):
        payload = normalize_real_hardware_status(
            {
                "online": True,
                "controlInterface": "real-dir",
                "powerState": "已上电",
                "estopActive": True,
                "mode": "保护待机",
                "lastError": "急停触发",
                "allowExecute": True,
            }
        )
        self.assertTrue(payload["online"])
        self.assertTrue(payload["estopActive"])
        self.assertFalse(payload["allowExecute"])


if __name__ == "__main__":
    unittest.main()
