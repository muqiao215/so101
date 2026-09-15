#!/usr/bin/env python3
import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "build_single_joint_probe_recording.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_single_joint_probe_recording", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BuildSingleJointProbeRecordingTests(unittest.TestCase):
    def test_build_probe_rows_freezes_other_joints(self):
        module = load_module()
        rows = [
            {"stamp_ns": 0, "joint_names": ["j1", "j2"], "positions": [0.0, 1.0], "velocities": [0.0, 0.2]},
            {"stamp_ns": 10, "joint_names": ["j1", "j2"], "positions": [0.5, 2.0], "velocities": [0.1, 0.3]},
        ]

        probe_rows, summary = module.build_probe_rows(rows, joint_name="j2")

        self.assertEqual([0.0, 1.0], probe_rows[0]["positions"])
        self.assertEqual([0.0, 2.0], probe_rows[1]["positions"])
        self.assertEqual([0.0, 0.3], probe_rows[1]["velocities"])
        self.assertEqual("j2", summary["joint_name"])
        self.assertEqual(1.0, summary["target_min_rad"])
        self.assertEqual(2.0, summary["target_max_rad"])


if __name__ == "__main__":
    unittest.main()
