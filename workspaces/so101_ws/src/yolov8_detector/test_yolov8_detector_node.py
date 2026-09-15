#!/usr/bin/env python3
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = Path(__file__).resolve().parent / "scripts" / "yolov8_detector_node.py"


def load_module():
    spec = importlib.util.spec_from_file_location("yolov8_detector_node", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeScalar:
    def __init__(self, value):
        self._value = value

    def item(self):
        return self._value


class FakeBox:
    def __init__(self, cls_id, conf, xyxy):
        self.cls = [FakeScalar(cls_id)]
        self.conf = [FakeScalar(conf)]
        self.xyxy = [xyxy]


class YoloV8DetectorNodeTests(unittest.TestCase):
    def test_normalize_target_classes_accepts_json_and_csv(self):
        module = load_module()

        self.assertEqual(["red", "blue"], module.normalize_target_classes('["Red", "blue"]'))
        self.assertEqual(["red", "blue"], module.normalize_target_classes("red, blue"))

    def test_extract_detections_filters_threshold_and_target_classes(self):
        module = load_module()
        result = SimpleNamespace(
            names={0: "red", 1: "blue"},
            boxes=[
                FakeBox(0, 0.91, [10.0, 20.0, 30.0, 50.0]),
                FakeBox(1, 0.2, [1.0, 2.0, 3.0, 4.0]),
            ],
        )

        detections = module.extract_detections_from_results(
            [result],
            conf_threshold=0.5,
            target_classes=["red"],
        )

        self.assertEqual(1, len(detections))
        self.assertEqual("red", detections[0]["category"])
        self.assertEqual([10.0, 20.0, 30.0, 50.0], detections[0]["bbox_xyxy"])
        self.assertEqual([20.0, 35.0, 20.0, 30.0], detections[0]["bbox_xywh"])

    def test_status_payload_is_json_serializable(self):
        module = load_module()
        payload = module.build_status_payload(
            module.DetectorStatus(
                state="READY",
                model_path="model.pt",
                image_topic="/image",
                detections_topic="/detections",
                detail="ok",
                frame_count=3,
                detection_count=2,
                last_inference_ms=12.3456,
            ),
            ts_ms=123,
        )

        encoded = json.dumps(payload)
        self.assertIn("READY", encoded)
        self.assertEqual(12.346, payload["last_inference_ms"])


if __name__ == "__main__":
    unittest.main()
