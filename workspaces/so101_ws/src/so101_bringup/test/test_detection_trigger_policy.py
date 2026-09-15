#!/usr/bin/env python3
import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "detection_trigger_policy.py"


def load_module():
    spec = importlib.util.spec_from_file_location("detection_trigger_policy", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class DetectionTriggerPolicyTests(unittest.TestCase):
    def test_same_category_respects_cooldown(self):
        module = load_module()
        policy = module.DetectionTriggerPolicy(
            enabled=True,
            threshold=0.5,
            cooldown_sec=8.0,
            template_map={"red": "pick_place_red"},
        )

        first = policy.try_trigger([("red", 0.9)], busy=False, now=100.0)
        second = policy.try_trigger([("red", 0.9)], busy=False, now=103.0)

        self.assertEqual("pick_place_red", first.template_id)
        self.assertIsNone(second)


if __name__ == "__main__":
    unittest.main()
