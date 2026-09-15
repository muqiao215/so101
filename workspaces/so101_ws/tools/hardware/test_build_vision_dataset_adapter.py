#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "build_vision_dataset_adapter.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_vision_dataset_adapter", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BuildVisionDatasetAdapterTests(unittest.TestCase):
    def test_build_dataset_from_minimal_episode(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            episode_dir = Path(temp_dir)
            (episode_dir / "images").mkdir()
            (episode_dir / "images" / "frame-000030.jpg").write_bytes(b"fake")
            events = [
                {"stream": "image", "received_wall_ms": 1000, "stamp_ns": 1_000_000_000, "width": 640, "height": 480, "encoding": "rgb8", "snapshot_path": "images/frame-000030.jpg"},
                {"stream": "detections", "received_wall_ms": 1001, "payload": {"stamp": {"sec": 1, "nanosec": 0}, "detections": [{"category": "red"}], "count": 1}},
                {"stream": "vision_targets", "received_wall_ms": 1002, "payload": {"stamp": {"sec": 1, "nanosec": 0}, "targets": [{"category": "red", "world_xyz": [0.1, 0.2, 0.8]}], "count": 1}},
                {"stream": "joint_states", "received_wall_ms": 1003, "stamp_ns": 1_000_000_000, "joint_names": ["j1"], "positions": [0.1], "velocities": [0.0]},
                {"stream": "task_status", "received_wall_ms": 1004, "payload": {"requestId": "r1", "state": "执行中", "code": "STEP", "ts": 1004}},
                {
                    "stream": "benchmark_result",
                    "received_wall_ms": 1005,
                    "payload": {
                        "schema": "so101_sim_grasp_benchmark_v1",
                        "target_object": {"category": "red", "raw_world_xyz": [0.65, 0.18, 0.8], "world_xyz": [0.32, 0.18, 0.8]},
                        "grasp_candidate": {"candidate_id": "red_reach_baseline"},
                        "plan_result": {"trajectory": {"joint_names": ["j1"], "points": [{"positions": [0.2], "time_from_start_sec": 1.0}]}},
                        "evaluation_result": {"metrics": {"reach_success": True, "min_distance_m": 0.07}, "result_label": "trainable_smoke"},
                    },
                },
            ]
            (episode_dir / "events.jsonl").write_text("\n".join(json.dumps(item) for item in events) + "\n", encoding="utf-8")
            (episode_dir / "manifest.json").write_text(json.dumps({"episode_id": "demo", "event_counts": {}}), encoding="utf-8")

            result = module.build_dataset(episode_dir, max_delta_sec=0.25)
            index = result["index"]
            samples = [json.loads(line) for line in Path(index["samples_path"]).read_text(encoding="utf-8").splitlines()]

        self.assertEqual("so101_vision_dataset_adapter_v1", index["schema"])
        self.assertEqual(1, index["sample_count"])
        self.assertEqual("passed", index["validation"]["status"])
        self.assertEqual("red", samples[0]["vision_target"]["targets"][0]["category"])
        self.assertEqual(["j1"], samples[0]["joint_state"]["joint_names"])
        self.assertEqual("red", samples[0]["benchmark_result"]["target_object"]["category"])
        self.assertEqual("trainable_smoke", samples[0]["benchmark_result"]["evaluation_result"]["result_label"])

    def test_validation_fails_when_target_missing(self):
        module = load_module()
        sample = {
            "detection": {},
            "vision_target": None,
            "joint_state": {},
            "task_status": {},
            "alignment": {},
        }

        validation = module.validate_samples([sample], max_delta_sec=0.25)

        self.assertEqual("failed", validation["status"])
        self.assertEqual(1, validation["missing"]["vision_target"])

    def test_task_status_can_use_context_threshold(self):
        module = load_module()
        sample = {
            "detection": {},
            "vision_target": {},
            "joint_state": {},
            "task_status": {},
            "alignment": {
                "detection_delta_sec": 0.01,
                "vision_target_delta_sec": 0.01,
                "joint_state_delta_sec": 0.01,
                "task_status_delta_sec": 1.5,
            },
        }

        validation = module.validate_samples([sample], max_delta_sec=0.25, max_task_status_delta_sec=2.0)

        self.assertEqual("passed", validation["status"])
        self.assertEqual(2.0, validation["thresholds"]["task_status"])

    def test_detection_still_uses_strict_threshold(self):
        module = load_module()
        sample = {
            "detection": {},
            "vision_target": {},
            "joint_state": {},
            "task_status": {},
            "alignment": {
                "detection_delta_sec": 0.4,
                "vision_target_delta_sec": 0.01,
                "joint_state_delta_sec": 0.01,
                "task_status_delta_sec": 0.01,
            },
        }

        validation = module.validate_samples([sample], max_delta_sec=0.25, max_task_status_delta_sec=2.0)

        self.assertEqual("warn", validation["status"])
        self.assertEqual(1, validation["large_delta"]["detection"])


if __name__ == "__main__":
    unittest.main()
