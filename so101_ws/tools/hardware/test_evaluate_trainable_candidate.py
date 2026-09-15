#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "evaluate_trainable_candidate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("evaluate_trainable_candidate", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def make_row(action: dict, quality_status: str = "passed") -> dict:
    return {
        "sample_index": 0,
        "timestamp": 0.0,
        "observation": {
            "images": {"overhead": {"relative_path": "images/frame.png", "width": 320, "height": 240}},
            "state": {"joint_names": ["j1", "j2"], "positions": [0.1, 0.2]},
        },
        "action": action,
        "quality": {"status": quality_status, "reasons": []},
    }


def write_candidate(root: Path, rows: list[dict]) -> Path:
    candidate = root / "candidate"
    candidate.mkdir()
    train = candidate / "train_samples.jsonl"
    debug = candidate / "debug_samples.jsonl"
    rejected = candidate / "rejected_samples.jsonl"
    write_jsonl(train, rows)
    write_jsonl(debug, [])
    write_jsonl(rejected, [])
    manifest = {
        "schema": "so101_lerobot_candidate_v1",
        "paths": {
            "train_samples": str(train),
            "debug_samples": str(debug),
            "rejected_samples": str(rejected),
        },
    }
    (candidate / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return candidate


class TrainableCandidateGateTests(unittest.TestCase):
    def test_blocks_vision_target_only_action(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = write_candidate(
                Path(temp_dir),
                [make_row({"type": "vision_target_xyz", "target_xyz": [0.1, 0.2, 0.3]})],
            )

            result = module.evaluate_candidate(candidate)

        self.assertEqual("blocked", result["report"]["status"])
        self.assertEqual(0, result["report"]["trainable_sample_count"])
        self.assertIn("unsupported_action_type:vision_target_xyz", result["report"]["issue_counts"])

    def test_allows_gazebo_joint_positions_for_smoke(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = write_candidate(
                Path(temp_dir),
                [make_row({"type": "joint_positions", "joint_names": ["j1", "j2"], "positions": [0.2, 0.3]})],
            )

            result = module.evaluate_candidate(candidate)

        self.assertEqual("trainable_smoke", result["report"]["status"])
        self.assertEqual(1, result["report"]["trainable_sample_count"])

    def test_requires_real_action_when_requested(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = write_candidate(
                Path(temp_dir),
                [make_row({"type": "joint_positions", "joint_names": ["j1", "j2"], "positions": [0.2, 0.3]})],
            )

            result = module.evaluate_candidate(candidate, require_real_action=True)

        self.assertEqual("blocked", result["report"]["status"])
        self.assertIn("unsupported_action_type:joint_positions", result["report"]["issue_counts"])


if __name__ == "__main__":
    unittest.main()
