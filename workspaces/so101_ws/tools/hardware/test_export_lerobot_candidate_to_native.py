#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "export_lerobot_candidate_to_native.py"


def load_module():
    spec = importlib.util.spec_from_file_location("export_lerobot_candidate_to_native", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


class FakeArrayModule:
    float32 = "float32"

    @staticmethod
    def asarray(value, dtype=None):
        return {"array": value, "dtype": dtype}


class FakeImage:
    @staticmethod
    def open(path):
        return FakeOpenedImage(path)


class FakeOpenedImage:
    def __init__(self, path):
        self.path = path

    def convert(self, mode):
        return {"image_path": str(self.path), "mode": mode}


class FakeDataset:
    created = None

    def __init__(self):
        self.frames = []
        self.saved = False
        self.finalized = False

    @classmethod
    def create(cls, **kwargs):
        dataset = cls()
        dataset.kwargs = kwargs
        cls.created = dataset
        kwargs["root"].mkdir(parents=True, exist_ok=False)
        return dataset

    def add_frame(self, frame):
        self.frames.append(frame)

    def save_episode(self, parallel_encoding=True):
        self.saved = True
        self.parallel_encoding = parallel_encoding

    def finalize(self):
        self.finalized = True


class ExportLeRobotCandidateToNativeTests(unittest.TestCase):
    def test_dry_run_resolves_manifest_and_features_without_importing_lerobot(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = self._write_candidate(root)

            report = module.export_native(candidate["manifest_path"], output_dir=root / "native", dry_run=True)

        self.assertEqual("dry_run", report["status"])
        self.assertEqual(1, report["sample_count"])
        self.assertEqual((480, 640, 3), report["features"]["observation.images.overhead"]["shape"])
        self.assertEqual(["j1", "j2"], report["features"]["observation.state"]["names"])
        self.assertEqual(str(candidate["train_path"]), report["train_samples_path"])

    def test_blocked_report_contains_uv_bootstrap_advice(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = module.blocked_report(
                root / "manifest.json",
                output_dir=root / "native",
                reason="ImportError: pandas/numpy conflict",
                details={"traceback": "example"},
            )

            self.assertEqual("blocked", report["status"])
            self.assertEqual("uv_run_isolated", report["bootstrap_advice"]["environment_mode"])
            self.assertIn("uv run --isolated --python 3.10", "\n".join(report["bootstrap_advice"]["commands"]))
            self.assertTrue((root / "native" / "native-export-blocked-report.json").exists())
            self.assertIn("pandas", "\n".join(report["bootstrap_advice"]["requirements_lock_suggestion"]))
            self.assertIn("numpy>=2,<3", "\n".join(report["bootstrap_advice"]["requirements_lock_suggestion"]))

    def test_success_path_uses_lerobot_create_and_copies_sidecar(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = self._write_candidate(root)

            original_importer = module.import_native_dependencies
            try:
                module.import_native_dependencies = lambda: {
                    "np": FakeArrayModule,
                    "Image": FakeImage,
                    "LeRobotDataset": FakeDataset,
                }
                report = module.export_native(
                    candidate["manifest_path"],
                    output_dir=root / "native",
                    repo_id="so101/test",
                )
            finally:
                module.import_native_dependencies = original_importer

            self.assertEqual("done", report["status"])
            self.assertEqual("so101/test", FakeDataset.created.kwargs["repo_id"])
            self.assertEqual(False, FakeDataset.created.kwargs["use_videos"])
            self.assertEqual(1, len(FakeDataset.created.frames))
            self.assertTrue(FakeDataset.created.saved)
            self.assertTrue(FakeDataset.created.finalized)
            self.assertTrue((root / "native" / "sidecars" / "candidate-manifest.json").exists())
            self.assertTrue((root / "native" / "native-export-report.json").exists())

    def test_success_path_uses_joint_position_action_when_present(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = self._write_candidate(root)
            rows = module.load_jsonl(candidate["train_path"])
            rows[0]["action"] = {
                "type": "joint_positions",
                "joint_names": ["j1", "j2"],
                "positions": [0.3, 0.4],
            }
            write_jsonl(candidate["train_path"], rows)

            original_importer = module.import_native_dependencies
            try:
                module.import_native_dependencies = lambda: {
                    "np": FakeArrayModule,
                    "Image": FakeImage,
                    "LeRobotDataset": FakeDataset,
                }
                report = module.export_native(candidate["manifest_path"], output_dir=root / "native")
            finally:
                module.import_native_dependencies = original_importer

        self.assertEqual("done", report["status"])
        self.assertEqual((2,), report["features"]["action"]["shape"])
        self.assertEqual(["j1", "j2"], report["features"]["action"]["names"])
        self.assertEqual({"array": [0.3, 0.4], "dtype": "float32"}, FakeDataset.created.frames[0]["action"])

    def test_cli_returns_zero_on_blocked_by_default(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = self._write_candidate(root)

            original_importer = module.import_native_dependencies
            original_argv = sys.argv[:]
            try:
                module.import_native_dependencies = lambda: (_ for _ in ()).throw(
                    module.NativeExportBlocked("ImportError: pandas/numpy conflict")
                )
                sys.argv = ["export_lerobot_candidate_to_native.py", str(candidate["manifest_path"])]
                rc = module.main()
            finally:
                module.import_native_dependencies = original_importer
                sys.argv = original_argv

            self.assertEqual(0, rc)
            self.assertTrue((root / "dataset" / "lerobot-native" / "native-export-blocked-report.json").exists())

    def _write_candidate(self, root: Path) -> dict:
        image_path = root / "frame.jpg"
        image_path.write_bytes(b"fake")
        candidate_dir = root / "dataset" / "lerobot-candidate"
        candidate_dir.mkdir(parents=True)
        train_path = candidate_dir / "train_samples.jsonl"
        write_jsonl(
            train_path,
            [
                {
                    "sample_index": 0,
                    "timestamp": 0.0,
                    "task": "pick visible target",
                    "observation": {
                        "images": {
                            "overhead": {
                                "path": str(image_path),
                                "relative_path": "images/frame.jpg",
                                "width": 640,
                                "height": 480,
                                "encoding": "rgb8",
                            }
                        },
                        "state": {"joint_names": ["j1", "j2"], "positions": [0.1, 0.2]},
                    },
                    "action": {"target_xyz": [0.3, 0.4, 0.8]},
                }
            ],
        )
        manifest_path = candidate_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "schema": "so101_lerobot_candidate_v1",
                    "fps": 5,
                    "paths": {"train_samples": str(train_path)},
                }
            ),
            encoding="utf-8",
        )
        return {"manifest_path": manifest_path, "train_path": train_path}


if __name__ == "__main__":
    unittest.main()
