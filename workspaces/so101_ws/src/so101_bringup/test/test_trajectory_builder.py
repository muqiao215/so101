#!/usr/bin/env python3
import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "trajectory_builder.py"


def load_module():
    spec = importlib.util.spec_from_file_location("trajectory_builder", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TrajectoryBuilderTests(unittest.TestCase):
    def test_builds_multi_point_joint_trajectory(self):
        module = load_module()

        msg, duration = module.build_mapped_trajectory_message(
            {
                "planned_trajectory": {
                    "joint_names": ["a"],
                    "points": [{"positions": [1.0], "t": 0.8}],
                }
            }
        )

        self.assertEqual(["a"], msg.joint_names)
        self.assertAlmostEqual(0.8, duration)


if __name__ == "__main__":
    unittest.main()
