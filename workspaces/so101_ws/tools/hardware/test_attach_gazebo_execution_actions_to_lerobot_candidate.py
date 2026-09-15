#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "attach_gazebo_execution_actions_to_lerobot_candidate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("attach_gazebo_execution_actions_to_lerobot_candidate", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


class AttachGazeboExecutionActionsTests(unittest.TestCase):
    def test_attaches_next_joint_state_as_action_and_rejects_terminal_train_row(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image = root / "frame.jpg"
            image.write_bytes(b"fake")
            candidate = root / "lerobot-candidate"
            candidate.mkdir()
            train = candidate / "train_samples.jsonl"
            debug = candidate / "debug_samples.jsonl"
            rejected = candidate / "rejected_samples.jsonl"
            write_jsonl(
                train,
                [
                    self._row(0, image, timestamp=0.0, position=0.1),
                    self._row(1, image, timestamp=0.2, position=0.4),
                ],
            )
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

            result = module.attach_actions(candidate / "manifest.json", output_dir=root / "exec")
            out_manifest = result["manifest"]
            train_rows = module.load_jsonl(Path(out_manifest["paths"]["train_samples"]))
            rejected_rows = module.load_jsonl(Path(out_manifest["paths"]["rejected_samples"]))

        self.assertEqual("so101_lerobot_candidate_exec_actions_v1", out_manifest["schema"])
        self.assertEqual(1, out_manifest["train_sample_count"])
        self.assertEqual(1, out_manifest["rejected_sample_count"])
        self.assertEqual("joint_positions", train_rows[0]["action"]["type"])
        self.assertEqual([0.4], train_rows[0]["action"]["positions"])
        self.assertEqual([0.3], train_rows[0]["action"]["deltas"])
        self.assertEqual([0.2, 0.0, 0.8], train_rows[0]["target_metadata"]["target_xyz"])
        self.assertEqual("missing_next_sample", rejected_rows[0]["quality"]["execution_action"]["status"])

    def test_joint_name_mismatch_rejects_row(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image = root / "frame.jpg"
            image.write_bytes(b"fake")
            candidate = root / "lerobot-candidate"
            candidate.mkdir()
            rows = [self._row(0, image, timestamp=0.0, position=0.1), self._row(1, image, timestamp=0.2, position=0.4)]
            rows[1]["observation"]["state"]["joint_names"] = ["other"]
            write_jsonl(candidate / "train_samples.jsonl", rows)
            write_jsonl(candidate / "debug_samples.jsonl", [])
            write_jsonl(candidate / "rejected_samples.jsonl", [])
            (candidate / "manifest.json").write_text(json.dumps({"schema": "so101_lerobot_candidate_v1"}), encoding="utf-8")

            result = module.attach_actions(candidate, output_dir=root / "exec")

        self.assertEqual(0, result["manifest"]["train_sample_count"])
        self.assertEqual(2, result["manifest"]["rejected_sample_count"])

    def _row(self, sample_index: int, image: Path, *, timestamp: float, position: float) -> dict:
        return {
            "schema": "so101_lerobot_candidate_v1",
            "sample_index": sample_index,
            "timestamp": timestamp,
            "task": "pick visible target",
            "observation": {
                "images": {
                    "overhead": {
                        "path": str(image),
                        "relative_path": image.name,
                        "width": 640,
                        "height": 480,
                        "encoding": "rgb8",
                    }
                },
                "state": {"joint_names": ["j1"], "positions": [position], "velocities": [0.0]},
            },
            "action": {
                "type": "vision_target_xyz",
                "target_category": "red",
                "target_xyz": [0.2, 0.0, 0.8],
                "confidence": 0.9,
                "note": "vision only",
            },
            "source": {},
            "quality": {"status": "passed", "reasons": []},
        }


if __name__ == "__main__":
    unittest.main()
