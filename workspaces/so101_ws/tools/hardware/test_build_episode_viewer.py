#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "build_episode_viewer.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_episode_viewer", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class EpisodeViewerTests(unittest.TestCase):
    def test_builds_html_and_viewer_data_from_dataset_index(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            samples = root / "samples.jsonl"
            samples.write_text(
                json.dumps(
                    {
                        "sample_index": 7,
                        "anchor": {
                            "image_path": str(root / "frame.png"),
                            "width": 320,
                            "height": 240,
                        },
                        "alignment": {"detection_delta_sec": 0.01},
                        "detection": {"detections": [{"category": "red"}]},
                        "vision_target": {"targets": [{"category": "red", "world_xyz": [0.1, 0.2, 0.8]}]},
                        "benchmark_result": {
                            "target_object": {
                                "category": "red",
                                "raw_world_xyz": [0.65, 0.18, 0.8],
                                "world_xyz": [0.32, 0.18, 0.8],
                            },
                            "grasp_candidate": {"candidate_id": "red_reach_baseline"},
                            "evaluation_result": {"metrics": {"reach_success": True, "min_distance_m": 0.07}},
                        },
                        "joint_state": {"joint_names": ["j1"], "positions": [0.1]},
                        "task_status": {"state": "DONE"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            index = root / "dataset-index.json"
            index.write_text(
                json.dumps(
                    {
                        "source_episode_id": "ep01",
                        "sample_count": 1,
                        "samples_path": str(samples),
                        "validation": {"status": "passed"},
                    }
                ),
                encoding="utf-8",
            )

            manifest = module.build_viewer(index)

            html_path = Path(manifest["viewer_html"])
            data_path = Path(manifest["viewer_data"])
            self.assertTrue(html_path.exists())
            self.assertTrue(data_path.exists())
            self.assertIn("SO101 Episode Viewer", html_path.read_text(encoding="utf-8"))
            data = json.loads(data_path.read_text(encoding="utf-8"))
            self.assertEqual(1, data["shown_sample_count"])
            self.assertEqual(7, data["samples"][0]["sample_index"])
            self.assertTrue(data["samples"][0]["benchmark_summary"]["reach_success"])
            self.assertEqual(0.07, data["samples"][0]["benchmark_summary"]["min_distance_m"])
            self.assertEqual("red_reach_baseline", data["samples"][0]["benchmark_summary"]["selected_candidate_id"])
            self.assertEqual([0.32, 0.18, 0.8], data["samples"][0]["benchmark_summary"]["canonical_target_xyz"])
            self.assertEqual([0.65, 0.18, 0.8], data["samples"][0]["benchmark_summary"]["raw_target_xyz"])


if __name__ == "__main__":
    unittest.main()
