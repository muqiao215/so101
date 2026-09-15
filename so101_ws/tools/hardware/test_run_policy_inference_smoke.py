#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "run_policy_inference_smoke.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_policy_inference_smoke", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_candidate(root: Path, row: dict) -> Path:
    candidate = root / "candidate"
    candidate.mkdir()
    train = candidate / "train_samples.jsonl"
    train.write_text(json.dumps(row) + "\n", encoding="utf-8")
    debug = candidate / "debug_samples.jsonl"
    rejected = candidate / "rejected_samples.jsonl"
    debug.write_text("", encoding="utf-8")
    rejected.write_text("", encoding="utf-8")
    (candidate / "manifest.json").write_text(
        json.dumps(
            {
                "paths": {
                    "train_samples": str(train),
                    "debug_samples": str(debug),
                    "rejected_samples": str(rejected),
                }
            }
        ),
        encoding="utf-8",
    )
    return candidate


class PolicyInferenceSmokeTests(unittest.TestCase):
    def test_replay_action_outputs_joint_position_command(self):
        module = load_module()
        row = {
            "sample_index": 3,
            "timestamp": 0.25,
            "observation": {"state": {"joint_names": ["j1", "j2"], "positions": [0.1, 0.2]}},
            "action": {"type": "joint_positions", "joint_names": ["j1", "j2"], "positions": [0.3, 0.4]},
            "quality": {"status": "passed"},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = write_candidate(Path(temp_dir), row)

            result = module.run_smoke(candidate)

            commands = Path(result["commands_path"]).read_text(encoding="utf-8").strip().splitlines()
            first = json.loads(commands[0])

        self.assertEqual("done", result["report"]["status"])
        self.assertEqual(["j1", "j2"], first["command"]["joint_names"])
        self.assertEqual([0.3, 0.4], first["command"]["positions"])

    def test_hold_position_blocks_when_state_is_missing(self):
        module = load_module()
        row = {"sample_index": 3, "observation": {}, "action": {}, "quality": {"status": "passed"}}
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = write_candidate(Path(temp_dir), row)

            result = module.run_smoke(candidate, mode="hold_position")

        self.assertEqual("blocked", result["report"]["status"])
        self.assertEqual(1, result["report"]["invalid_command_count"])


if __name__ == "__main__":
    unittest.main()
