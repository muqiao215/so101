#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "task_preview_utils.py"


def load_module():
    spec = importlib.util.spec_from_file_location("task_preview_utils", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TaskPreviewUtilsTests(unittest.TestCase):
    def test_parse_preview_pose_accepts_valid_payload(self):
        module = load_module()
        payload = {
            "previewPose": {
                "name": "debug_pose_1",
                "durationSec": 1.4,
                "positions": [0.0, -0.2, 0.4, -0.2, 0.0, 0.2],
            }
        }

        parsed = module.parse_preview_pose(payload)

        self.assertEqual("debug_pose_1", parsed["name"])
        self.assertEqual(1.4, parsed["duration_sec"])
        self.assertEqual(6, len(parsed["positions"]))

    def test_parse_preview_pose_rejects_invalid_joint_count(self):
        module = load_module()
        payload = {
            "previewPose": {
                "name": "bad",
                "durationSec": 1.0,
                "positions": [0.0, 0.1],
            }
        }

        parsed = module.parse_preview_pose(payload)
        self.assertIsNone(parsed)


if __name__ == "__main__":
    unittest.main()
