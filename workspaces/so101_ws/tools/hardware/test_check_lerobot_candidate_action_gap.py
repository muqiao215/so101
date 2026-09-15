#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "check_lerobot_candidate_action_gap.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_lerobot_candidate_action_gap", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


class CheckLeRobotCandidateActionGapTests(unittest.TestCase):
    def test_reports_vision_target_only_gap(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_jsonl(
                root / "train_samples.jsonl",
                [
                    {
                        "sample_index": 0,
                        "action": {"type": "vision_target_xyz", "target_xyz": [0.1, 0.2, 0.3]},
                    }
                ],
            )
            write_jsonl(root / "debug_samples.jsonl", [])
            write_jsonl(root / "rejected_samples.jsonl", [])
            (root / "manifest.json").write_text(json.dumps({"schema": "so101_lerobot_candidate_v1"}), encoding="utf-8")

            report = module.inspect_candidate(root)

        self.assertEqual("gap_confirmed", report["gap_status"])
        self.assertTrue(report["only_vision_target_xyz"])
        self.assertFalse(report["has_execution_action_labels"])
        self.assertEqual({"vision_target_xyz": 1}, report["action_type_counts"])

    def test_detects_execution_action_labels(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_jsonl(
                root / "train_samples.jsonl",
                [
                    {
                        "sample_index": 0,
                        "action": {"type": "gazebo_joint_trajectory", "joint_names": ["j1"], "points": []},
                    }
                ],
            )
            write_jsonl(root / "debug_samples.jsonl", [])
            write_jsonl(root / "rejected_samples.jsonl", [])

            report = module.inspect_candidate(root)

        self.assertEqual("execution_action_present", report["gap_status"])
        self.assertTrue(report["has_execution_action_labels"])
        self.assertEqual(["gazebo_joint_trajectory"], report["execution_action_types_present"])


if __name__ == "__main__":
    unittest.main()
