#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "build_yolo_dataset_from_vision_candidate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_yolo_dataset_from_vision_candidate", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


class BuildYoloDatasetFromVisionCandidateTests(unittest.TestCase):
    def test_exports_yolo_labels_from_candidate_detection_boxes(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image = root / "frame-000001.jpg"
            image.write_bytes(b"fake")
            rows = [
                {
                    "sample_index": 0,
                    "observation": {
                        "images": {
                            "overhead": {
                                "path": str(image),
                                "width": 640,
                                "height": 480,
                            }
                        }
                    },
                    "source": {
                        "detection": {
                            "detections": [
                                {"category": "red", "bbox_xyxy": [64, 48, 192, 144]},
                                {"category": "blue", "bbox_xyxy": [320, 240, 480, 360]},
                            ]
                        }
                    },
                }
            ]
            rows_by_split = {"train": rows, "debug": [], "rejected": []}
            output_dir = root / "yolo"

            manifest = module.write_yolo_dataset(
                rows_by_split,
                output_dir=output_dir,
                classes=["red", "blue"],
                copy_images=True,
                allow_missing_images=False,
            )

            label = (output_dir / "labels" / "train" / "frame-000001.txt").read_text(encoding="utf-8").splitlines()
            data_yaml_exists = (output_dir / "data.yaml").exists()

        self.assertEqual(["red", "blue"], manifest["classes"])
        self.assertEqual(2, manifest["split_counts"]["train"]["written_boxes"])
        self.assertEqual("0 0.200000 0.200000 0.200000 0.200000", label[0])
        self.assertEqual("1 0.625000 0.625000 0.250000 0.250000", label[1])
        self.assertTrue(data_yaml_exists)


if __name__ == "__main__":
    unittest.main()
