#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "clean_leader_recording.py"


def load_module():
    spec = importlib.util.spec_from_file_location("clean_leader_recording", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CleanLeaderRecordingTests(unittest.TestCase):
    def test_clean_timestamp_sequence_removes_duplicate_and_non_monotonic_frames(self):
        module = load_module()
        records = [
            module.RecordingLine(1, 100, {"stamp_ns": 100, "positions": [0.0], "joint_names": ["j1"]}),
            module.RecordingLine(2, 110, {"stamp_ns": 110, "positions": [0.1], "joint_names": ["j1"]}),
            module.RecordingLine(3, 110, {"stamp_ns": 110, "positions": [0.2], "joint_names": ["j1"]}),
            module.RecordingLine(4, 105, {"stamp_ns": 105, "positions": [0.3], "joint_names": ["j1"]}),
            module.RecordingLine(5, 120, {"stamp_ns": 120, "positions": [0.4], "joint_names": ["j1"]}),
        ]

        kept, removed, counters = module.clean_timestamp_sequence(records)

        self.assertEqual([1, 2, 5], [record.line_no for record in kept])
        self.assertEqual(2, counters["removed_frame_count"])
        self.assertEqual(1, counters["duplicate_timestamp_count"])
        self.assertEqual(1, counters["non_monotonic_timestamp_count"])
        self.assertEqual("duplicate_timestamp", removed[0]["reason"])
        self.assertEqual("non_monotonic_timestamp", removed[1]["reason"])

    def test_main_writes_cleaned_recording_report_and_annotation(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            input_path = workspace / "input.jsonl"
            input_lines = [
                {
                    "stamp_ns": 100,
                    "joint_names": ["j1"],
                    "positions": [0.0],
                },
                {
                    "stamp_ns": 120,
                    "joint_names": ["j1"],
                    "positions": [0.2],
                },
                {
                    "stamp_ns": 115,
                    "joint_names": ["j1"],
                    "positions": [0.3],
                },
            ]
            input_path.write_text(
                "\n".join(json.dumps(item) for item in input_lines) + "\n",
                encoding="utf-8",
            )
            cleaned_path = workspace / "cleaned.jsonl"
            report_path = workspace / "cleaning-report.json"
            annotation_path = workspace / "annotation.json"

            status = module.main(
                [
                    "--input",
                    str(input_path),
                    "--cleaned-output",
                    str(cleaned_path),
                    "--report-output",
                    str(report_path),
                    "--annotation-output",
                    str(annotation_path),
                ]
            )
            self.assertEqual(0, status)

            cleaned_lines = [json.loads(line) for line in cleaned_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            report = json.loads(report_path.read_text(encoding="utf-8"))
            annotation = json.loads(annotation_path.read_text(encoding="utf-8"))

        self.assertEqual([100, 120], [item["stamp_ns"] for item in cleaned_lines])
        self.assertEqual(1, report["summary"]["removed_frame_count"])
        self.assertEqual(1, report["summary"]["non_monotonic_timestamp_count"])
        self.assertEqual("invalid_result", annotation["source_status"])
        self.assertEqual("cleaned_from_invalid", annotation["cleaned_status"])
        self.assertTrue(annotation["source_sha256"])


if __name__ == "__main__":
    unittest.main()
