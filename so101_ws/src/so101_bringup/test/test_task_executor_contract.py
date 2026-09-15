#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "task_executor_contract.py"


def load_module():
    spec = importlib.util.spec_from_file_location("task_executor_contract", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TaskExecutorContractTests(unittest.TestCase):
    def test_command_locked_returns_error_status(self):
        module = load_module()

        result = module.evaluate_command_request(
            request_id="req-locked",
            template_id="pick_place_default",
            params={},
            command_execution_enabled=False,
            busy=False,
        )

        self.assertEqual(False, result["accepted"])
        self.assertEqual("异常", result["status"]["state"])
        self.assertEqual("COMMAND_LOCKED", result["status"]["code"])
        self.assertEqual(
            "Execution gate disabled for safe real bringup",
            result["status"]["message"],
        )


if __name__ == "__main__":
    unittest.main()
