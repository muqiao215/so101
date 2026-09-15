#!/usr/bin/env python3
import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "assert_sim_vision_closed_loop.py"


def load_module():
    spec = importlib.util.spec_from_file_location("assert_sim_vision_closed_loop", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SimVisionClosedLoopAssertionTests(unittest.TestCase):
    def test_joint_state_delta_uses_joint_names_not_order(self):
        module = load_module()

        delta = module.joint_state_delta(
            {"joint_names": ["a", "b"], "positions": [1.0, 2.0]},
            {"joint_names": ["b", "a"], "positions": [2.25, 0.9]},
        )

        self.assertAlmostEqual(0.25, delta)

    def test_task_closed_accepts_only_matching_request_prefix(self):
        module = load_module()

        self.assertFalse(module.task_closed([{"requestId": "manual-1", "code": "OK"}], "det-"))
        self.assertTrue(module.task_closed([{"requestId": "det-red-1", "code": "OK"}], "det-"))
        self.assertTrue(module.task_closed([{"requestId": "bench-red-1", "code": "OK"}], "bench-"))


if __name__ == "__main__":
    unittest.main()
