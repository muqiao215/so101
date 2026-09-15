#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "validate_vision_episode.py"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_vision_episode", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ValidateVisionEpisodeTests(unittest.TestCase):
    def test_validates_minimal_episode(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            episode_dir = Path(temp_dir)
            (episode_dir / "images").mkdir()
            (episode_dir / "images" / "frame-000001.jpg").write_bytes(b"fake")
            events = [
                {"stream": "image", "received_wall_ms": 1000, "snapshot_path": "images/frame-000001.jpg"},
                {"stream": "detections", "received_wall_ms": 1001, "payload": {"detections": [{"category": "red"}]}},
                {"stream": "vision_targets", "received_wall_ms": 1002, "payload": {"targets": [{"category": "red", "world_xyz": [0.1, 0.2, 0.8]}]}},
                {"stream": "task_status", "received_wall_ms": 1003},
                {"stream": "joint_states", "received_wall_ms": 1004},
            ]
            (episode_dir / "events.jsonl").write_text(
                "\n".join(json.dumps(item) for item in events) + "\n",
                encoding="utf-8",
            )
            (episode_dir / "manifest.json").write_text(
                json.dumps({
                    "schema": "so101_vision_episode_v1",
                    "duration_sec": 0.004,
                    "image_snapshot_count": 1,
                    "event_counts": {
                        "image": 1,
                        "detections": 1,
                        "vision_targets": 1,
                        "task_status": 1,
                        "joint_states": 1,
                    },
                }),
                encoding="utf-8",
            )

            result = module.validate_episode(episode_dir)

        self.assertEqual("passed", result.status)
        self.assertEqual(1, result.summary["snapshot_count"])
        self.assertEqual("red", result.summary["first_target"]["category"])

    def test_fails_when_required_stream_missing(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            episode_dir = Path(temp_dir)
            (episode_dir / "events.jsonl").write_text(
                json.dumps({"stream": "image", "received_wall_ms": 1000}) + "\n",
                encoding="utf-8",
            )
            (episode_dir / "manifest.json").write_text(
                json.dumps({"schema": "so101_vision_episode_v1", "event_counts": {"image": 1}}),
                encoding="utf-8",
            )

            result = module.validate_episode(episode_dir)

        self.assertEqual("failed", result.status)
        self.assertTrue(any("detections" in error for error in result.errors))


if __name__ == "__main__":
    unittest.main()
