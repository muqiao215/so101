#!/usr/bin/env python3
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "merge_leader_waypoints_into_config.py"


def load_module():
    spec = importlib.util.spec_from_file_location("merge_leader_waypoints_into_config", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class MergeLeaderWaypointsIntoConfigTests(unittest.TestCase):
    def test_merge_adds_waypoints_and_template(self):
        module = load_module()
        target_doc = {
            "joint_names": ["j1", "j2"],
            "waypoints": {"home": [0.0, 0.0]},
            "action_templates": {"demo": {"sequence": ["home"], "detection_required": False}},
        }
        draft_doc = {
            "joint_names": ["j1", "j2"],
            "waypoints": {"leader_01": [1.0, 2.0]},
            "action_templates": {"leader_demo": {"sequence": ["leader_01"], "detection_required": False}},
        }

        updated, summary = module.merge_draft_into_waypoints_doc(target_doc, draft_doc)

        self.assertIn("leader_01", updated["waypoints"])
        self.assertIn("leader_demo", updated["action_templates"])
        self.assertEqual(["leader_01"], summary["merged_waypoint_names"])
        self.assertEqual(["leader_demo"], summary["merged_template_names"])

    def test_merge_can_select_single_template(self):
        module = load_module()
        target_doc = {
            "joint_names": ["j1", "j2"],
            "waypoints": {},
            "action_templates": {},
        }
        draft_doc = {
            "joint_names": ["j1", "j2"],
            "waypoints": {"a": [0.0, 0.0], "b": [1.0, 1.0]},
            "action_templates": {
                "template_a": {"sequence": ["a"], "detection_required": False},
                "template_b": {"sequence": ["b"], "detection_required": False},
            },
        }

        updated, summary = module.merge_draft_into_waypoints_doc(target_doc, draft_doc, template_name="template_b")

        self.assertIn("a", updated["waypoints"])
        self.assertIn("b", updated["waypoints"])
        self.assertIn("template_b", updated["action_templates"])
        self.assertNotIn("template_a", updated["action_templates"])
        self.assertEqual(["template_b"], summary["merged_template_names"])

    def test_merge_rejects_joint_name_mismatch(self):
        module = load_module()
        target_doc = {
            "joint_names": ["j1", "j2"],
            "waypoints": {},
            "action_templates": {},
        }
        draft_doc = {
            "joint_names": ["j1", "j3"],
            "waypoints": {"leader_01": [1.0, 2.0]},
            "action_templates": {"leader_demo": {"sequence": ["leader_01"], "detection_required": False}},
        }

        with self.assertRaisesRegex(ValueError, "joint_names mismatch"):
            module.merge_draft_into_waypoints_doc(target_doc, draft_doc)


if __name__ == "__main__":
    unittest.main()
