#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "leader_recording_to_waypoints.py"


def load_module():
    spec = importlib.util.spec_from_file_location("leader_recording_to_waypoints", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_recording(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


class LeaderRecordingToWaypointsTests(unittest.TestCase):
    def test_detects_stable_segments_and_dedupes(self):
        module = load_module()
        joint_names = ["j1", "j2"]
        rows = []
        stamp_ns = 0
        for _ in range(20):
            rows.append({"stamp_ns": stamp_ns, "joint_names": joint_names, "positions": [0.0, 0.0]})
            stamp_ns += 50_000_000
        for step in range(1, 6):
            rows.append({"stamp_ns": stamp_ns, "joint_names": joint_names, "positions": [step * 0.1, step * 0.1]})
            stamp_ns += 50_000_000
        for _ in range(18):
            rows.append({"stamp_ns": stamp_ns, "joint_names": joint_names, "positions": [0.5, 0.5]})
            stamp_ns += 50_000_000

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.jsonl"
            write_recording(path, rows)
            frames = module.load_recording(path)
            segments, method = module.choose_segments(
                frames,
                motion_epsilon_rad=0.02,
                min_stable_sec=0.4,
                dedupe_epsilon_rad=0.05,
                max_waypoints=12,
            )

        self.assertEqual("stable_segments", method)
        self.assertEqual(2, len(segments))
        self.assertEqual([0.0, 0.0], segments[0].representative_positions)
        self.assertEqual([0.5, 0.5], segments[1].representative_positions)

    def test_falls_back_when_no_stable_segments(self):
        module = load_module()
        joint_names = ["j1", "j2"]
        rows = []
        for index in range(12):
            rows.append(
                {
                    "stamp_ns": index * 100_000_000,
                    "joint_names": joint_names,
                    "positions": [index * 0.1, index * 0.2],
                }
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "moving.jsonl"
            write_recording(path, rows)
            frames = module.load_recording(path)
            segments, method = module.choose_segments(
                frames,
                motion_epsilon_rad=0.02,
                min_stable_sec=0.4,
                dedupe_epsilon_rad=0.05,
                max_waypoints=4,
            )

        self.assertEqual("fallback_sampling", method)
        self.assertEqual(4, len(segments))
        self.assertEqual(0.0, segments[0].representative_positions[0])
        self.assertEqual(1.1, segments[-1].representative_positions[0])

    def test_build_yaml_snippet_contains_waypoints_and_template(self):
        module = load_module()
        text = module.build_yaml_snippet(
            joint_names=["j1", "j2"],
            template_name="demo_pick",
            waypoint_names=["demo_pick_01", "demo_pick_02"],
            waypoint_positions=[[0.0, 0.2], [0.5, 0.7]],
            source_recording=Path("/tmp/demo.jsonl"),
        )
        self.assertIn("joint_names:", text)
        self.assertIn("waypoints:", text)
        self.assertIn("action_templates:", text)
        self.assertIn("demo_pick_01", text)
        self.assertIn("demo_pick_02", text)
        self.assertIn("demo_pick:", text)


if __name__ == "__main__":
    unittest.main()
