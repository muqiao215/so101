#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "source_episode_quality_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("source_episode_quality_gate", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_recording(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


class SourceEpisodeQualityGateTests(unittest.TestCase):
    def test_passes_when_positions_and_velocity_are_inside_limits(self):
        module = load_module()
        frames = [
            module.Frame(stamp_ns=0, joint_names=["j1"], positions=[0.0]),
            module.Frame(stamp_ns=1_000_000_000, joint_names=["j1"], positions=[0.5]),
        ]

        report = module.evaluate_source_quality(
            frames,
            {"j1": {"lower": -1.0, "upper": 1.0, "velocity": 1.0}},
            position_tolerance_rad=1e-6,
            velocity_scale=1.0,
        )

        self.assertEqual("passed", report["status"])
        self.assertEqual([], report["reasons"])

    def test_detects_position_and_velocity_violations(self):
        module = load_module()
        frames = [
            module.Frame(stamp_ns=0, joint_names=["j1"], positions=[0.0]),
            module.Frame(stamp_ns=100_000_000, joint_names=["j1"], positions=[1.2]),
        ]

        report = module.evaluate_source_quality(
            frames,
            {"j1": {"lower": -1.0, "upper": 1.0, "velocity": 1.0}},
            position_tolerance_rad=1e-6,
            velocity_scale=1.0,
        )

        self.assertEqual("source_quality_failed", report["status"])
        self.assertIn("j1:position_limit_violation", report["reasons"])
        self.assertIn("j1:velocity_limit_violation", report["reasons"])
        self.assertEqual(1, report["joints"]["j1"]["position"]["above_upper_count"])
        self.assertEqual(1, report["joints"]["j1"]["velocity"]["violation_count"])

    def test_main_returns_nonzero_when_fail_on_violation(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            recording = root / "recording.jsonl"
            urdf = root / "robot.urdf"
            output = root / "source-quality.json"
            write_recording(
                recording,
                [
                    {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]},
                    {"stamp_ns": 100_000_000, "joint_names": ["j1"], "positions": [1.2]},
                ],
            )
            urdf.write_text(
                '<robot name="r"><joint name="j1" type="revolute">'
                '<limit lower="-1.0" upper="1.0" velocity="1.0" effort="1.0"/>'
                "</joint></robot>",
                encoding="utf-8",
            )

            code = module.main(
                [
                    "--recording",
                    str(recording),
                    "--urdf",
                    str(urdf),
                    "--output",
                    str(output),
                    "--fail-on-violation",
                ]
            )

        self.assertEqual(2, code)


if __name__ == "__main__":
    unittest.main()
