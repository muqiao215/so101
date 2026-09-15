#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "episode_manifest.py"


def load_module():
    spec = importlib.util.spec_from_file_location("episode_manifest", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class EpisodeManifestTests(unittest.TestCase):
    def test_load_recording_meta_maps_quality_fields(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            meta_path = Path(temp_dir) / "recording.meta.json"
            payload = {
                "duration_sec": 61.2,
                "frame_count": 1800,
                "sample_rate_hz": 29.4,
                "invalid_frame_count": 0,
                "joint_name_mismatch_count": 0,
                "non_monotonic_stamp_count": 1,
                "large_interval_count": 2,
                "frame_interval_stats": {
                    "avg_sec": 0.034,
                    "max_sec": 0.18,
                },
                "invalid_reason_counts": {
                    "positions_non_finite": 1,
                },
                "quality_metrics": {
                    "total_motion_rad": 12.3,
                },
                "warnings": ["non_monotonic_stamps_detected"],
            }
            meta_path.write_text(json.dumps(payload), encoding="utf-8")

            summary = module.load_recording_meta(str(meta_path))

        self.assertEqual("warn", summary["status"])
        self.assertEqual(1800, summary["frame_count"])
        self.assertEqual(2, summary["large_interval_count"])
        self.assertEqual(0.034, summary["avg_frame_gap_sec"])
        self.assertEqual(0.18, summary["max_frame_gap_sec"])
        self.assertEqual(1, summary["invalid_reason_counts"]["positions_non_finite"])
        self.assertEqual(12.3, summary["quality_metrics"]["total_motion_rad"])
        self.assertEqual(["non_monotonic_stamps_detected"], summary["warnings"])
        self.assertIsInstance(summary["quality_score"], float)

    def test_default_output_path_uses_episode_directory(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            output_path = module.build_default_manifest_path(workspace, "pick_demo_001")

        self.assertEqual("manifest.json", output_path.name)
        self.assertIn("docs/generated/leader-episodes/pick_demo_001", str(output_path))

    def test_load_replay_result_maps_validator_fields(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            result_path = Path(temp_dir) / "replay-raw.json"
            result_path.write_text(
                json.dumps(
                    {
                        "judgment": {"status": "soft_failed", "profile": "replay_default"},
                        "metrics": {
                            "overall": {
                                "mae_rad": 0.01,
                                "rmse_rad": 0.02,
                                "max_error_rad": 0.05,
                                "p95_error_rad": 0.03,
                                "duration_delta_sec": 0.1,
                                "duration_delta_abs_sec": 0.1,
                                "duration_ratio": 1.01,
                            }
                        },
                        "diagnostics": {
                            "worst_point": {"joint": "j1", "t_sec": 0.2}
                        },
                    }
                ),
                encoding="utf-8",
            )

            summary = module.load_replay_result(str(result_path))

        self.assertEqual("soft_failed", summary["status"])
        self.assertEqual("replay_default", summary["profile"])
        self.assertEqual(0.01, summary["summary"]["mae_rad"])
        self.assertEqual(0.1, summary["duration_delta_sec"])
        self.assertEqual("j1", summary["summary"]["worst_joint"])
        self.assertEqual(0.2, summary["summary"]["worst_t_sec"])

    def test_load_replay_result_handles_empty_worst_point(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            result_path = Path(temp_dir) / "replay-raw.json"
            result_path.write_text(
                json.dumps(
                    {
                        "judgment": {"status": "invalid_result", "profile": "identity_strict"},
                        "metrics": {
                            "overall": {
                                "mae_rad": 0.0,
                                "rmse_rad": 0.0,
                                "max_error_rad": 0.0,
                                "p95_error_rad": 0.0,
                                "duration_delta_sec": 0.0,
                                "duration_delta_abs_sec": 0.0,
                                "duration_ratio": 1.0,
                            }
                        },
                        "diagnostics": {
                            "worst_point": {
                                "joint": None,
                                "t_sec": None,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            summary = module.load_replay_result(str(result_path))

        self.assertEqual("invalid_result", summary["status"])
        self.assertEqual("identity_strict", summary["profile"])
        self.assertIsNone(summary["summary"]["worst_joint"])
        self.assertIsNone(summary["summary"]["worst_t_sec"])

    def test_load_cleaning_report_and_annotation(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "cleaning-report.json"
            annotation_path = Path(temp_dir) / "annotation.json"
            report_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "removed_frame_count": 1,
                            "duplicate_timestamp_count": 0,
                            "non_monotonic_timestamp_count": 1,
                            "changed": True,
                            "labels": ["non_monotonic_timestamp"],
                        },
                        "input": {
                            "sha256": "abc123",
                        },
                        "output": {
                            "frame_count": 10,
                            "duration_sec": 1.2,
                            "sample_rate_hz": 8.3,
                            "avg_frame_gap_sec": 0.12,
                            "max_frame_gap_sec": 0.2,
                        },
                    }
                ),
                encoding="utf-8",
            )
            annotation_path.write_text(
                json.dumps(
                    {
                        "source_status": "invalid_result",
                        "cleaned_status": "cleaned_from_invalid",
                        "usable_for_regression": True,
                        "reasons": ["non_monotonic_timestamp"],
                        "source_sha256": "abc123",
                    }
                ),
                encoding="utf-8",
            )

            cleaning = module.load_cleaning_report(str(report_path))
            annotation = module.load_annotation(str(annotation_path))

        self.assertEqual("cleaned_from_invalid", cleaning["status"])
        self.assertEqual("abc123", cleaning["source_sha256"])
        self.assertEqual(10, cleaning["summary"]["cleaned_frame_count"])
        self.assertEqual("invalid_result", annotation["source_status"])
        self.assertEqual("cleaned_from_invalid", annotation["cleaned_status"])
        self.assertEqual(["non_monotonic_timestamp"], annotation["reasons"])

    def test_load_source_quality_report(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "source-quality.json"
            report_path.write_text(
                json.dumps(
                    {
                        "quality": {
                            "status": "source_quality_failed",
                            "reasons": ["elbow_flex:velocity_limit_violation"],
                            "frame_count": 12,
                            "duration_sec": 1.2,
                            "joints": {
                                "elbow_flex": {},
                                "wrist_flex": {},
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )

            summary = module.load_source_quality_report(str(report_path))

        self.assertEqual("source_quality_failed", summary["status"])
        self.assertEqual(["elbow_flex:velocity_limit_violation"], summary["reasons"])
        self.assertEqual(12, summary["frame_count"])
        self.assertEqual(2, summary["joint_count"])

    def test_main_writes_manifest_json(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "AGENTS.md").write_text("test", encoding="utf-8")
            (workspace / "docs").mkdir()
            (workspace / "src").mkdir()
            tools_dir = workspace / "tools" / "hardware"
            tools_dir.mkdir(parents=True)

            raw_record_path = workspace / "docs" / "generated" / "leader-episodes" / "ep01" / "episode.jsonl"
            raw_record_path.parent.mkdir(parents=True, exist_ok=True)
            raw_record_path.write_text("{}", encoding="utf-8")
            replay_result_path = workspace / "docs" / "generated" / "leader-episodes" / "ep01" / "replay-raw.json"
            cleaned_record_path = workspace / "docs" / "generated" / "leader-episodes" / "ep01" / "cleaned.jsonl"
            cleaned_record_path.write_text("{}", encoding="utf-8")
            cleaning_report_path = workspace / "docs" / "generated" / "leader-episodes" / "ep01" / "cleaning-report.json"
            cleaning_report_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "removed_frame_count": 1,
                            "duplicate_timestamp_count": 0,
                            "non_monotonic_timestamp_count": 1,
                            "changed": True,
                            "labels": ["non_monotonic_timestamp"],
                        },
                        "input": {
                            "sha256": "abc123",
                        },
                        "output": {
                            "frame_count": 11,
                            "duration_sec": 0.33,
                            "sample_rate_hz": 33.3,
                            "avg_frame_gap_sec": 0.03,
                            "max_frame_gap_sec": 0.04,
                        },
                    }
                ),
                encoding="utf-8",
            )
            annotation_path = workspace / "docs" / "generated" / "leader-episodes" / "ep01" / "annotation.json"
            annotation_path.write_text(
                json.dumps(
                    {
                        "source_status": "invalid_result",
                        "cleaned_status": "cleaned_from_invalid",
                        "usable_for_regression": True,
                        "reasons": ["non_monotonic_timestamp"],
                        "source_sha256": "abc123",
                    }
                ),
                encoding="utf-8",
            )
            replay_result_path.write_text(
                json.dumps(
                    {
                        "status": "ok",
                        "overall": {"mae_rad": 0.0, "max_error_rad": 0.0},
                        "duration_delta_sec": 0.0,
                        "duration_delta_abs_sec": 0.0,
                    }
                ),
                encoding="utf-8",
            )

            output_path = workspace / "docs" / "generated" / "leader-episodes" / "ep01" / "manifest.json"
            args = [
                "--episode-id",
                "ep01",
                "--task-name",
                "pick_place",
                "--raw-record-path",
                str(raw_record_path),
                "--cleaned-record-path",
                str(cleaned_record_path),
                "--cleaning-report-path",
                str(cleaning_report_path),
                "--annotation-path",
                str(annotation_path),
                "--output-path",
                str(output_path),
                "--operator",
                "muqiao",
                "--source-mode",
                "leader_only",
                "--robot-profile",
                "so101_leader",
                "--calibration-version",
                "cal_v1",
                "--replay-raw-result-path",
                str(replay_result_path),
            ]

            status = module.main(args)
            self.assertEqual(0, status)
            manifest = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual("ep01", manifest["episode_id"])
        self.assertEqual("pick_place", manifest["task_name"])
        self.assertEqual("muqiao", manifest["operator"])
        self.assertEqual("so101_leader", manifest["robot_profile"])
        self.assertEqual("cleaned_from_invalid", manifest["asset_status"])
        self.assertEqual("abc123", manifest["source_sha256"])
        self.assertEqual("cleaned_report", manifest["quality_summary"]["source"])
        self.assertEqual(11, manifest["quality_summary"]["frame_count"])
        self.assertIn("system_metadata", manifest)
        self.assertIn("quality_metadata", manifest)
        self.assertIn("quality_summary", manifest)
        self.assertEqual("ok", manifest["quality_metadata"]["replay_validation"]["raw"]["status"])
        self.assertEqual("invalid_result", manifest["recording_layers"]["raw"]["status"])
        self.assertEqual("cleaned_from_invalid", manifest["recording_layers"]["cleaned"]["status"])


if __name__ == "__main__":
    unittest.main()
