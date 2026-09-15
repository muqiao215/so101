#!/usr/bin/env python3
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "analyze_leader_replay_distortion.py"


def load_module():
    spec = importlib.util.spec_from_file_location("analyze_leader_replay_distortion", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AnalyzeLeaderReplayDistortionTests(unittest.TestCase):
    def test_estimate_best_lag_detects_shift(self):
        module = load_module()
        reference = [
            {"t_sec": 0.0, "positions": [0.0]},
            {"t_sec": 0.1, "positions": [1.0]},
            {"t_sec": 0.2, "positions": [2.0]},
        ]
        candidate = [
            {"t_sec": 0.05, "positions": [0.0]},
            {"t_sec": 0.15, "positions": [1.0]},
            {"t_sec": 0.25, "positions": [2.0]},
        ]

        result = module.estimate_best_lag(
            reference,
            candidate,
            0,
            lag_range_sec=0.1,
            lag_step_sec=0.05,
        )

        self.assertEqual(0.05, result["best_lag_sec"])

    def test_linear_fit_detects_sign_flip_like_pattern(self):
        module = load_module()
        fit = module.linear_fit([0.0, 1.0, 2.0], [0.0, -1.0, -2.0])
        issue = module.classify_joint_issue(
            slope=fit["slope"],
            offset=fit["offset"],
            best_lag_sec=0.0,
            moving_mae_rad=1.0,
            steady_mae_rad=0.1,
        )

        self.assertEqual(-1.0, fit["slope"])
        self.assertEqual("sign_flip_like", issue)

    def test_rank_player_joint_matches_sorts_by_mae(self):
        module = load_module()
        rows = module.rank_player_joint_matches(
            target_values=[1.0, 2.0, 3.0],
            player_joint_names=["j1", "j2"],
            player_series_by_joint={
                "j1": [1.0, 2.0, 3.0],
                "j2": [3.0, 2.0, 1.0],
            },
        )

        self.assertEqual("j1", rows[0]["player_joint"])
        self.assertEqual(0.0, rows[0]["mae_rad"])

    def test_interpolate_positions_by_stamp(self):
        module = load_module()
        samples = [
            {"stamp_ns": 1_000_000_000, "positions": [0.0]},
            {"stamp_ns": 2_000_000_000, "positions": [2.0]},
        ]

        self.assertEqual([1.0], module.interpolate_positions_by_stamp(samples, 1_500_000_000))

    def test_parse_urdf_joint_limits(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "robot.urdf"
            path.write_text(
                '<robot name="r"><joint name="elbow_flex" type="revolute">'
                '<limit lower="-1.0" upper="1.0" velocity="2.0" effort="3.0"/>'
                "</joint></robot>",
                encoding="utf-8",
            )

            limits = module.parse_urdf_joint_limits(path)

        self.assertEqual(-1.0, limits["elbow_flex"]["lower"])
        self.assertEqual(2.0, limits["elbow_flex"]["velocity"])

    def test_limit_profile_counts_violations(self):
        module = load_module()
        profile = module.limit_profile([-1.2, 0.0, 1.3], {"lower": -1.0, "upper": 1.0})

        self.assertEqual(1, profile["below_lower_count"])
        self.assertEqual(1, profile["above_upper_count"])
        self.assertEqual(0.2, profile["max_lower_violation_rad"])
        self.assertEqual(0.3, profile["max_upper_violation_rad"])


if __name__ == "__main__":
    unittest.main()
