#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "export_vision_dataset_to_lerobot_candidate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("export_vision_dataset_to_lerobot_candidate", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


class ExportVisionDatasetToLeRobotCandidateTests(unittest.TestCase):
    def test_warn_samples_are_debug_only_by_default(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "frame.jpg"
            image_path.write_bytes(b"fake")
            samples_path = root / "samples.jsonl"
            rows = [
                self._sample(image_path, sample_index=0, joint_delta=0.01, status_delta=0.02),
                self._sample(image_path, sample_index=1, joint_delta=0.50, status_delta=0.02),
            ]
            write_jsonl(samples_path, rows)
            index_path = root / "dataset-index.json"
            index_path.write_text(
                json.dumps(
                    {
                        "schema": "so101_vision_dataset_adapter_v1",
                        "source_episode_id": "demo",
                        "samples_path": str(samples_path),
                        "max_delta_sec": 0.25,
                    }
                ),
                encoding="utf-8",
            )

            result = module.export_candidate(index_path)
            manifest = result["manifest"]
            train_rows = module.load_jsonl(Path(manifest["paths"]["train_samples"]))
            debug_rows = module.load_jsonl(Path(manifest["paths"]["debug_samples"]))

        self.assertEqual("so101_lerobot_candidate_v1", manifest["schema"])
        self.assertEqual(1, manifest["train_sample_count"])
        self.assertEqual(1, manifest["debug_sample_count"])
        self.assertEqual(0, manifest["rejected_sample_count"])
        self.assertEqual("passed", train_rows[0]["quality"]["status"])
        self.assertEqual("warn", debug_rows[0]["quality"]["status"])
        self.assertEqual([0.11, 0.22, 0.8], train_rows[0]["action"]["target_xyz"])
        self.assertEqual([0.1, 0.2, 0.8], train_rows[0]["action"]["raw_target_xyz"])
        self.assertEqual("trainable_smoke", train_rows[0]["action"]["result_label"])
        self.assertEqual("red_reach_baseline", train_rows[0]["action"]["selected_candidate_id"])

    def test_warn_policy_rejects_warn_samples_when_requested(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "frame.jpg"
            image_path.write_bytes(b"fake")
            samples_path = root / "samples.jsonl"
            write_jsonl(samples_path, [self._sample(image_path, sample_index=0, joint_delta=0.40, status_delta=0.02)])
            index_path = root / "dataset-index.json"
            index_path.write_text(
                json.dumps(
                    {
                        "schema": "so101_vision_dataset_adapter_v1",
                        "source_episode_id": "demo",
                        "samples_path": str(samples_path),
                        "max_delta_sec": 0.25,
                    }
                ),
                encoding="utf-8",
            )

            result = module.export_candidate(index_path, warn_policy="reject")
            manifest = result["manifest"]

        self.assertEqual(0, manifest["train_sample_count"])
        self.assertEqual(0, manifest["debug_sample_count"])
        self.assertEqual(1, manifest["rejected_sample_count"])

    def test_non_default_category_keeps_action_target_aligned(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "frame.jpg"
            image_path.write_bytes(b"fake")
            samples_path = root / "samples.jsonl"
            sample = self._sample(image_path, sample_index=0, joint_delta=0.01, status_delta=0.02)
            sample["vision_target"]["targets"] = [
                {"category": "red", "confidence": 0.9, "world_xyz": [0.1, 0.2, 0.8]},
                {"category": "blue", "confidence": 0.8, "world_xyz": [0.4, -0.2, 0.8]},
            ]
            sample["benchmark_result"]["target_object"] = {
                "category": "red",
                "raw_world_xyz": [0.1, 0.2, 0.8],
                "world_xyz": [0.11, 0.22, 0.8],
            }
            write_jsonl(samples_path, [sample])
            index_path = root / "dataset-index.json"
            index_path.write_text(
                json.dumps(
                    {
                        "schema": "so101_vision_dataset_adapter_v1",
                        "source_episode_id": "demo",
                        "samples_path": str(samples_path),
                        "max_delta_sec": 0.25,
                    }
                ),
                encoding="utf-8",
            )

            result = module.export_candidate(index_path, target_category="blue")
            manifest = result["manifest"]
            train_rows = module.load_jsonl(Path(manifest["paths"]["train_samples"]))

        action = train_rows[0]["action"]
        self.assertEqual("blue", action["target_category"])
        self.assertEqual([0.4, -0.2, 0.8], action["target_xyz"])
        self.assertEqual([0.4, -0.2, 0.8], action["raw_target_xyz"])
        self.assertIsNone(action["selected_candidate_id"])
        self.assertIsNone(action["result_label"])
        self.assertIsNone(action["reach_success"])
        self.assertIsNone(action["min_distance_m"])

    def _sample(self, image_path: Path, *, sample_index: int, joint_delta: float, status_delta: float) -> dict:
        return {
            "sample_index": sample_index,
            "anchor": {
                "stamp_ns": 1_000_000_000 + sample_index * 200_000_000,
                "image_path": str(image_path),
                "image_relative_path": image_path.name,
                "width": 640,
                "height": 480,
                "encoding": "rgb8",
                "frame_id": "camera",
            },
            "alignment": {
                "detection_delta_sec": 0.01,
                "vision_target_delta_sec": 0.01,
                "joint_state_delta_sec": joint_delta,
                "task_status_delta_sec": status_delta,
            },
            "detection": {"source": "gazebo_color_detector", "count": 1, "detections": [{"category": "red"}]},
            "vision_target": {
                "source": "gazebo_projection",
                "target_frame": "world",
                "targets": [{"category": "red", "confidence": 0.9, "world_xyz": [0.1, 0.2, 0.8]}],
            },
            "benchmark_result": {
                "target_object": {"category": "red", "raw_world_xyz": [0.1, 0.2, 0.8], "world_xyz": [0.11, 0.22, 0.8]},
                "grasp_candidate": {"candidate_id": "red_reach_baseline"},
                "plan_result": {"trajectory": {"joint_names": ["j1"], "points": [{"positions": [0.0], "time_from_start_sec": 0.0}]}},
                "evaluation_result": {"metrics": {"reach_success": True, "min_distance_m": 0.07}, "result_label": "trainable_smoke"},
            },
            "joint_state": {"joint_names": ["j1"], "positions": [0.0], "velocities": [0.0]},
            "task_status": {"state": "执行中", "code": "STEP"},
        }


if __name__ == "__main__":
    unittest.main()
