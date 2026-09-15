#!/usr/bin/env python3
import contextlib
import io
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "leader_replay_validator.py"


def load_module():
    spec = importlib.util.spec_from_file_location("leader_replay_validator", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_recording(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


class LeaderReplayValidatorTests(unittest.TestCase):
    def test_identity_validation_passes_for_monotonic_same_file(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.jsonl"
            rows = [
                {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]},
                {"stamp_ns": 1_000_000_000, "joint_names": ["j1"], "positions": [1.0]},
            ]
            write_recording(source_path, rows)
            thresholds = module.load_threshold_profiles(Path("tools/hardware/replay_validator_thresholds.json"))

            report = module.build_validation_report(
                module.load_recording(source_path),
                module.load_recording(source_path),
                profile_name="identity_strict",
                thresholds=thresholds,
                top_k=5,
                edge_window_sec=0.1,
            )

        self.assertEqual("passed", report["judgment"]["status"])
        self.assertEqual(0.0, report["metrics"]["overall"]["mae_rad"])
        self.assertEqual(0.0, report["metrics"]["overall"]["max_error_rad"])
        self.assertEqual(0.0, report["metrics"]["overall"]["duration_delta_sec"])
        self.assertEqual(2, report["run"]["reference_clean_frame_count"])
        self.assertTrue(report["run"]["alignment"]["can_compare_positions"])
        self.assertEqual(0, report["run"]["alignment"]["reference_removed_frame_count"])
        self.assertEqual(0, report["diagnostics"]["data_quality"]["aggregate"]["missing_value_count"])
        self.assertEqual("pass", report["judgment"]["checks"]["diagnostics.edge_region.non_edge_max_error_rad"]["result"])
        self.assertEqual([], report["diagnostics"]["top_k_worst_samples"])
        self.assertIsNone(report["diagnostics"]["worst_point"]["joint"])

    def test_identity_validation_marks_non_monotonic_sequence_invalid(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.jsonl"
            rows = [
                {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]},
                {"stamp_ns": 2_000_000_000, "joint_names": ["j1"], "positions": [2.0]},
                {"stamp_ns": 1_000_000_000, "joint_names": ["j1"], "positions": [1.0]},
            ]
            write_recording(source_path, rows)
            thresholds = module.load_threshold_profiles(Path("tools/hardware/replay_validator_thresholds.json"))

            report = module.build_validation_report(
                module.load_recording(source_path),
                module.load_recording(source_path),
                profile_name="identity_strict",
                thresholds=thresholds,
                top_k=5,
                edge_window_sec=0.1,
            )

        self.assertEqual("invalid_result", report["judgment"]["status"])
        self.assertGreater(report["run"]["alignment"]["non_monotonic_timestamp_count"], 0)
        self.assertGreater(report["run"]["alignment"]["reference_non_monotonic_timestamp_count"], 0)
        self.assertTrue(report["judgment"]["invalid_reasons"])

    def test_replay_validation_reports_metrics_and_diagnostics(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.jsonl"
            replay_path = Path(temp_dir) / "replay.jsonl"
            write_recording(
                source_path,
                [
                    {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]},
                    {"stamp_ns": 1_000_000_000, "joint_names": ["j1"], "positions": [1.0]},
                ],
            )
            write_recording(
                replay_path,
                [
                    {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.2]},
                    {"stamp_ns": 1_000_000_000, "joint_names": ["j1"], "positions": [1.2]},
                ],
            )
            thresholds = module.load_threshold_profiles(Path("tools/hardware/replay_validator_thresholds.json"))

            report = module.build_validation_report(
                module.load_recording(source_path),
                module.load_recording(replay_path),
                profile_name="replay_default",
                thresholds=thresholds,
                top_k=1,
                edge_window_sec=0.1,
            )

        self.assertIn("metrics", report)
        self.assertIn("diagnostics", report)
        self.assertIn("judgment", report)
        self.assertEqual(0.2, report["metrics"]["overall"]["mae_rad"])
        self.assertEqual(0.2, report["metrics"]["overall"]["rmse_rad"])
        self.assertEqual(0.2, report["metrics"]["overall"]["max_error_rad"])
        self.assertEqual(0.2, report["metrics"]["overall"]["p95_error_rad"])
        self.assertEqual("j1", report["diagnostics"]["worst_point"]["joint"])
        self.assertEqual(1, len(report["diagnostics"]["top_k_worst_samples"]))
        self.assertTrue(report["run"]["alignment"]["can_compare_positions"])
        self.assertEqual(2, report["run"]["alignment"]["evaluated_sample_count"])
        self.assertIn("reference", report["diagnostics"]["data_quality"])
        self.assertIn("candidate", report["diagnostics"]["data_quality"])
        self.assertIn("aggregate", report["diagnostics"]["data_quality"])
        self.assertEqual(2, report["diagnostics"]["edge_region"]["edge_sample_count"])
        self.assertEqual(0, report["diagnostics"]["edge_region"]["non_edge_sample_count"])
        self.assertIsNone(report["diagnostics"]["edge_region"]["edge_spike_ratio"])

    def test_joint_name_mismatch_is_invalid_result(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.jsonl"
            replay_path = Path(temp_dir) / "replay.jsonl"
            write_recording(source_path, [{"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]}])
            write_recording(replay_path, [{"stamp_ns": 0, "joint_names": ["j2"], "positions": [0.0]}])
            thresholds = module.load_threshold_profiles(Path("tools/hardware/replay_validator_thresholds.json"))

            report = module.build_validation_report(
                module.load_recording(source_path),
                module.load_recording(replay_path),
                profile_name="identity_strict",
                thresholds=thresholds,
                top_k=5,
                edge_window_sec=0.1,
            )

        self.assertEqual("invalid_result", report["judgment"]["status"])
        self.assertTrue(report["diagnostics"]["joint_coverage"]["joint_name_mismatch"])
        self.assertFalse(report["run"]["alignment"]["can_compare_positions"])
        self.assertEqual(0, report["run"]["alignment"]["evaluated_sample_count"])

    def test_missing_value_count_triggers_invalid_result(self):
        module = load_module()
        reference_frames = [
            module.RecordingFrame(stamp_ns=0, joint_names=["j1"], positions=[0.0]),
            module.RecordingFrame(stamp_ns=1_000_000_000, joint_names=["j1"], positions=[1.0]),
        ]
        candidate_frames = [
            module.RecordingFrame(stamp_ns=0, joint_names=["j1"], positions=[0.0]),
            module.RecordingFrame(stamp_ns=1_000_000_000, joint_names=["j1", "j2"], positions=[1.0]),
        ]
        thresholds = module.load_threshold_profiles(Path("tools/hardware/replay_validator_thresholds.json"))

        report = module.build_validation_report(
            reference_frames,
            candidate_frames,
            profile_name="identity_strict",
            thresholds=thresholds,
            top_k=5,
            edge_window_sec=0.1,
        )

        self.assertEqual("invalid_result", report["judgment"]["status"])
        self.assertEqual("fail", report["judgment"]["checks"]["diagnostics.data_quality.missing_value_count"]["result"])
        self.assertEqual(1, report["diagnostics"]["data_quality"]["candidate"]["missing_value_count"])

    def test_joint_order_swap_is_invalid_result(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.jsonl"
            replay_path = Path(temp_dir) / "replay.jsonl"
            write_recording(
                source_path,
                [
                    {"stamp_ns": 0, "joint_names": ["j1", "j2"], "positions": [0.0, 0.5]},
                    {"stamp_ns": 1_000_000_000, "joint_names": ["j1", "j2"], "positions": [1.0, 1.5]},
                ],
            )
            write_recording(
                replay_path,
                [
                    {"stamp_ns": 0, "joint_names": ["j2", "j1"], "positions": [0.5, 0.0]},
                    {"stamp_ns": 1_000_000_000, "joint_names": ["j2", "j1"], "positions": [1.5, 1.0]},
                ],
            )
            thresholds = module.load_threshold_profiles(Path("tools/hardware/replay_validator_thresholds.json"))

            report = module.build_validation_report(
                module.load_recording(source_path),
                module.load_recording(replay_path),
                profile_name="identity_strict",
                thresholds=thresholds,
                top_k=5,
                edge_window_sec=0.1,
            )

        self.assertEqual("invalid_result", report["judgment"]["status"])
        self.assertTrue(report["diagnostics"]["joint_coverage"]["joint_name_mismatch"])
        self.assertFalse(report["run"]["alignment"]["can_compare_positions"])

    def test_sign_flip_is_hard_failed(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.jsonl"
            replay_path = Path(temp_dir) / "replay.jsonl"
            write_recording(
                source_path,
                [
                    {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]},
                    {"stamp_ns": 1_000_000_000, "joint_names": ["j1"], "positions": [0.6]},
                    {"stamp_ns": 2_000_000_000, "joint_names": ["j1"], "positions": [1.0]},
                ],
            )
            write_recording(
                replay_path,
                [
                    {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]},
                    {"stamp_ns": 1_000_000_000, "joint_names": ["j1"], "positions": [-0.6]},
                    {"stamp_ns": 2_000_000_000, "joint_names": ["j1"], "positions": [-1.0]},
                ],
            )
            thresholds = module.load_threshold_profiles(Path("tools/hardware/replay_validator_thresholds.json"))

            report = module.build_validation_report(
                module.load_recording(source_path),
                module.load_recording(replay_path),
                profile_name="replay_default",
                thresholds=thresholds,
                top_k=5,
                edge_window_sec=0.1,
            )

        self.assertEqual("hard_failed", report["judgment"]["status"])
        self.assertTrue(report["judgment"]["hard_fail_reasons"])
        self.assertEqual("fail", report["judgment"]["checks"]["metrics.overall.max_error_rad"]["result"])

    def test_duplicate_timestamp_is_invalid_result(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.jsonl"
            replay_path = Path(temp_dir) / "replay.jsonl"
            write_recording(
                source_path,
                [
                    {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]},
                    {"stamp_ns": 1_000_000_000, "joint_names": ["j1"], "positions": [0.5]},
                    {"stamp_ns": 2_000_000_000, "joint_names": ["j1"], "positions": [1.0]},
                ],
            )
            write_recording(
                replay_path,
                [
                    {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]},
                    {"stamp_ns": 1_000_000_000, "joint_names": ["j1"], "positions": [0.5]},
                    {"stamp_ns": 1_000_000_000, "joint_names": ["j1"], "positions": [0.6]},
                    {"stamp_ns": 2_000_000_000, "joint_names": ["j1"], "positions": [1.0]},
                ],
            )
            thresholds = module.load_threshold_profiles(Path("tools/hardware/replay_validator_thresholds.json"))

            report = module.build_validation_report(
                module.load_recording(source_path),
                module.load_recording(replay_path),
                profile_name="identity_strict",
                thresholds=thresholds,
                top_k=5,
                edge_window_sec=0.1,
            )

        self.assertEqual("invalid_result", report["judgment"]["status"])
        self.assertGreater(report["run"]["alignment"]["candidate_duplicate_timestamp_count"], 0)
        self.assertIn("candidate timestamps are not strictly monotonic", report["judgment"]["invalid_reasons"])

    def test_duration_trim_is_hard_failed(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.jsonl"
            replay_path = Path(temp_dir) / "replay.jsonl"
            write_recording(
                source_path,
                [
                    {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]},
                    {"stamp_ns": 1_000_000_000, "joint_names": ["j1"], "positions": [0.2]},
                    {"stamp_ns": 2_000_000_000, "joint_names": ["j1"], "positions": [0.4]},
                    {"stamp_ns": 3_000_000_000, "joint_names": ["j1"], "positions": [0.6]},
                ],
            )
            write_recording(
                replay_path,
                [
                    {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]},
                    {"stamp_ns": 1_000_000_000, "joint_names": ["j1"], "positions": [0.2]},
                ],
            )
            thresholds = module.load_threshold_profiles(Path("tools/hardware/replay_validator_thresholds.json"))

            report = module.build_validation_report(
                module.load_recording(source_path),
                module.load_recording(replay_path),
                profile_name="replay_default",
                thresholds=thresholds,
                top_k=5,
                edge_window_sec=0.1,
            )

        self.assertEqual("hard_failed", report["judgment"]["status"])
        self.assertEqual("fail", report["judgment"]["checks"]["metrics.overall.duration_delta_abs_sec"]["result"])

    def test_sparse_dropped_frames_is_hard_failed_for_non_linear_motion(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.jsonl"
            replay_path = Path(temp_dir) / "replay.jsonl"
            write_recording(
                source_path,
                [
                    {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]},
                    {"stamp_ns": 1_000_000_000, "joint_names": ["j1"], "positions": [1.0]},
                    {"stamp_ns": 2_000_000_000, "joint_names": ["j1"], "positions": [0.0]},
                    {"stamp_ns": 3_000_000_000, "joint_names": ["j1"], "positions": [1.0]},
                ],
            )
            write_recording(
                replay_path,
                [
                    {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]},
                    {"stamp_ns": 3_000_000_000, "joint_names": ["j1"], "positions": [1.0]},
                ],
            )
            thresholds = module.load_threshold_profiles(Path("tools/hardware/replay_validator_thresholds.json"))

            report = module.build_validation_report(
                module.load_recording(source_path),
                module.load_recording(replay_path),
                profile_name="replay_default",
                thresholds=thresholds,
                top_k=5,
                edge_window_sec=0.1,
            )

        self.assertEqual("hard_failed", report["judgment"]["status"])
        self.assertEqual("fail", report["judgment"]["checks"]["metrics.overall.max_error_rad"]["result"])

    def test_fail_on_hard_returns_non_zero_for_invalid_result(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.jsonl"
            rows = [
                {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]},
                {"stamp_ns": 2_000_000_000, "joint_names": ["j1"], "positions": [2.0]},
                {"stamp_ns": 1_000_000_000, "joint_names": ["j1"], "positions": [1.0]},
            ]
            write_recording(source_path, rows)
            with contextlib.redirect_stdout(io.StringIO()):
                status = module.main(
                    [
                        "--reference",
                        str(source_path),
                        "--candidate",
                        str(source_path),
                        "--profile",
                        "identity_strict",
                        "--thresholds",
                        "tools/hardware/replay_validator_thresholds.json",
                        "--fail-on",
                        "hard",
                    ]
                )

        self.assertEqual(1, status)

    def test_fail_on_soft_returns_zero_for_passed_identity(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.jsonl"
            rows = [
                {"stamp_ns": 0, "joint_names": ["j1"], "positions": [0.0]},
                {"stamp_ns": 1_000_000_000, "joint_names": ["j1"], "positions": [1.0]},
            ]
            write_recording(source_path, rows)
            with contextlib.redirect_stdout(io.StringIO()):
                status = module.main(
                    [
                        "--reference",
                        str(source_path),
                        "--candidate",
                        str(source_path),
                        "--profile",
                        "identity_strict",
                        "--thresholds",
                        "tools/hardware/replay_validator_thresholds.json",
                        "--fail-on",
                        "soft",
                    ]
                )

        self.assertEqual(0, status)

    def test_replay_validation_soft_failed_when_only_soft_thresholds_trip(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.jsonl"
            replay_path = Path(temp_dir) / "replay.jsonl"
            source_rows = []
            replay_rows = []
            for index, value in enumerate([0.0, 0.1, 0.2, 0.3, 0.4]):
                stamp_ns = index * 1_000_000_000
                source_rows.append({"stamp_ns": stamp_ns, "joint_names": ["j1"], "positions": [value]})
                replay_rows.append({"stamp_ns": stamp_ns, "joint_names": ["j1"], "positions": [value + (0.11 if index == 4 else 0.0)]})
            write_recording(source_path, source_rows)
            write_recording(replay_path, replay_rows)
            thresholds = module.load_threshold_profiles(Path("tools/hardware/replay_validator_thresholds.json"))

            report = module.build_validation_report(
                module.load_recording(source_path),
                module.load_recording(replay_path),
                profile_name="replay_default",
                thresholds=thresholds,
                top_k=5,
                edge_window_sec=0.1,
            )

        self.assertEqual("soft_failed", report["judgment"]["status"])
        self.assertEqual([], report["judgment"]["hard_fail_reasons"])
        self.assertTrue(report["judgment"]["soft_fail_reasons"])
        self.assertEqual("fail", report["judgment"]["checks"]["metrics.overall.p95_error_rad"]["result"])

    def test_fail_on_soft_returns_non_zero_for_soft_failed_result(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.jsonl"
            replay_path = Path(temp_dir) / "replay.jsonl"
            source_rows = []
            replay_rows = []
            for index, value in enumerate([0.0, 0.1, 0.2, 0.3, 0.4]):
                stamp_ns = index * 1_000_000_000
                source_rows.append({"stamp_ns": stamp_ns, "joint_names": ["j1"], "positions": [value]})
                replay_rows.append({"stamp_ns": stamp_ns, "joint_names": ["j1"], "positions": [value + (0.11 if index == 4 else 0.0)]})
            write_recording(source_path, source_rows)
            write_recording(replay_path, replay_rows)

            with contextlib.redirect_stdout(io.StringIO()):
                hard_status = module.main(
                    [
                        "--reference",
                        str(source_path),
                        "--candidate",
                        str(replay_path),
                        "--profile",
                        "replay_default",
                        "--thresholds",
                        "tools/hardware/replay_validator_thresholds.json",
                        "--fail-on",
                        "hard",
                    ]
                )
                soft_status = module.main(
                    [
                        "--reference",
                        str(source_path),
                        "--candidate",
                        str(replay_path),
                        "--profile",
                        "replay_default",
                        "--thresholds",
                        "tools/hardware/replay_validator_thresholds.json",
                        "--fail-on",
                        "soft",
                    ]
                )

        self.assertEqual(0, hard_status)
        self.assertEqual(1, soft_status)


if __name__ == "__main__":
    unittest.main()
