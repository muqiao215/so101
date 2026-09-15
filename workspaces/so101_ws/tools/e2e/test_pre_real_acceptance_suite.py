#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_pre_real_acceptance_suite import build_dashboard
from run_vision_projection_quality_smoke import build_quality_report


class VisionProjectionQualitySmokeTest(unittest.TestCase):
    def test_quality_report_uses_benchmark_raw_and_canonical_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            events_path = Path(tmp) / "events.jsonl"
            rows = [
                {
                    "stream": "detections",
                    "received_wall_ms": 1,
                    "payload": {
                        "detections": [{"category": "red", "bbox_xyxy": [0, 0, 10, 10]}],
                    },
                },
                {
                    "stream": "vision_targets",
                    "received_wall_ms": 1,
                    "payload": {
                        "targets": [{"category": "red", "pixel_center": [5.0, 5.0], "world_xyz": [0.65, 0.18, 0.8]}],
                    },
                },
                {
                    "stream": "benchmark_result",
                    "received_wall_ms": 2,
                    "payload": {
                        "target_object": {
                            "category": "red",
                            "pixel_center": [5.0, 5.0],
                            "raw_world_xyz": [0.65, 0.18, 0.8],
                            "world_xyz": [0.32, 0.18, 0.8],
                        }
                    },
                },
            ]
            events_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            report = build_quality_report(events_path)
            self.assertEqual("passed", report["status"])
            self.assertEqual(
                {"raw_world_xyz_adjusted_to_canonical_workspace": 1},
                report["summary"]["clamp_reason_counts"],
            )
            self.assertGreater(report["summary"]["raw_world_error_m"]["max"], 0.3)
            self.assertEqual(0.0, report["summary"]["canonical_world_error_m"]["max"])


class PreRealDashboardTest(unittest.TestCase):
    def test_dashboard_states_boundary(self) -> None:
        report = {
            "status": "passed",
            "timestamp": "20260508-120000",
            "scope": "pre-real",
            "vision_smoke": {"classification": "passed_smoke", "status": "passed"},
            "vision_projection_quality": {"classification": "passed_smoke", "report": {"summary": {}}},
            "mtc_reach_smoke": {"classification": "passed_smoke", "summary": {"reach_success_rate": 1.0}},
            "jitter_suite": {
                "classification": "passed_smoke",
                "summary": {
                    "reach_success_rate": 1.0,
                    "mean_min_distance_m": 0.01,
                    "p50_min_distance_m": 0.01,
                    "p90_min_distance_m": 0.02,
                    "max_min_distance_m": 0.03,
                    "failure_reason_counts": {},
                },
            },
            "dataset_trainability": {"classification": "passed_smoke", "report": {"status": "trainable_smoke"}},
            "contact_lift_diagnostic": {"classification": "blocked_deferred", "contact_success": 0.0, "lift_success": 0.0},
            "artifacts": {"acceptance_report": "report.yaml"},
        }
        dashboard = build_dashboard(report)
        self.assertIn("not `trainable_real`", dashboard)
        self.assertIn("Contact and lift remain blocked/deferred", dashboard)


if __name__ == "__main__":
    unittest.main()
