#!/usr/bin/env python3
import unittest
from pathlib import Path

import yaml


WAYPOINTS_PATH = Path(__file__).resolve().parents[1] / "config" / "waypoints.yaml"


class WaypointsConfigTests(unittest.TestCase):
    def load_doc(self):
        return yaml.safe_load(WAYPOINTS_PATH.read_text(encoding="utf-8"))

    def test_demo_templates_exist(self):
        doc = self.load_doc()
        templates = doc.get("action_templates", {})

        self.assertIn("inspection_sweep", templates)
        self.assertIn("wave_hello", templates)
        self.assertIn("pick_present_place", templates)
        self.assertIn("dance_demo", templates)

    def test_all_template_sequences_reference_existing_waypoints(self):
        doc = self.load_doc()
        waypoints = doc.get("waypoints", {})
        templates = doc.get("action_templates", {})

        for template_id, template in templates.items():
            sequence = template.get("sequence", [])
            self.assertTrue(sequence, f"template '{template_id}' must have non-empty sequence")
            for step_name in sequence:
                self.assertIn(
                    step_name,
                    waypoints,
                    f"template '{template_id}' references missing waypoint '{step_name}'",
                )

    def test_demo_templates_have_showcase_length(self):
        doc = self.load_doc()
        templates = doc.get("action_templates", {})

        self.assertGreaterEqual(len(templates["inspection_sweep"]["sequence"]), 6)
        self.assertGreaterEqual(len(templates["wave_hello"]["sequence"]), 8)
        self.assertGreaterEqual(len(templates["pick_present_place"]["sequence"]), 10)
        self.assertGreaterEqual(len(templates["dance_demo"]["sequence"]), 10)


if __name__ == "__main__":
    unittest.main()
