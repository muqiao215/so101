#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "run_yolo_train_infer_smoke.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_yolo_train_infer_smoke", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RunYoloTrainInferSmokeTests(unittest.TestCase):
    def test_smoke_yaml_falls_back_to_train_when_val_is_empty(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = self._dataset(root)
            info = module.build_smoke_data_yaml(dataset, root / "data.smoke.yaml")

            self.assertEqual("train", info["val_split"])
            self.assertEqual("train", info["test_split"])
            self.assertEqual(1, info["split_counts"]["train"])
            self.assertIn("val: images/train", (root / "data.smoke.yaml").read_text(encoding="utf-8"))

    def test_dry_run_writes_report_without_importing_ultralytics(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = self._dataset(root)
            report = module.run_smoke(dataset, output_dir=root / "out", dry_run=True)

            self.assertEqual("dry_run", report["status"])
            self.assertTrue((root / "out" / "yolo-smoke-report.json").exists())
            self.assertEqual("train", report["data_yaml"]["val_split"])

    def _dataset(self, root: Path) -> Path:
        dataset = root / "yolo-dataset"
        (dataset / "images" / "train").mkdir(parents=True)
        (dataset / "labels" / "train").mkdir(parents=True)
        (dataset / "images" / "train" / "frame.jpg").write_bytes(b"fake")
        (dataset / "labels" / "train" / "frame.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
        (dataset / "manifest.json").write_text(
            json.dumps({"classes": ["red"], "split_counts": {"train": {"written_images": 1}}}),
            encoding="utf-8",
        )
        (dataset / "data.yaml").write_text(
            f"path: {dataset}\ntrain: images/train\nval: images/debug\nnames: [\"red\"]\n",
            encoding="utf-8",
        )
        return dataset


if __name__ == "__main__":
    unittest.main()
