#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "action_template_mapping.py"


def load_module():
    spec = importlib.util.spec_from_file_location("action_template_mapping", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ActionTemplateMappingTests(unittest.TestCase):
    def test_merge_export_into_templates_persists_mapping_and_aliases(self):
        module = load_module()
        waypoints_doc = {
            "joint_names": ["j1", "j2"],
            "waypoints": {
                "home": [0.0, 0.0],
                "pick": [1.0, 1.0],
            },
            "action_templates": {
                "pick_place_default": {
                    "sequence": ["home", "pick"],
                    "detection_required": False,
                },
                "pick_place_red": {
                    "sequence": ["home", "pick"],
                    "detection_required": True,
                    "expected_category": "red",
                },
            },
        }
        export_doc = {
            "source_action_template": "pick_place_default",
            "joint_names": ["j1", "j2"],
            "steps": {
                "home": {
                    "target_positions": [0.0, 0.0],
                    "planning_time": 0.01,
                    "planned_trajectory": {
                        "joint_names": ["j1", "j2"],
                        "points": [
                            {"t": 0.0, "positions": [0.1, 0.2]},
                            {"t": 0.2, "positions": [0.0, 0.0]},
                        ],
                    },
                },
                "pick": {
                    "target_positions": [1.0, 1.0],
                    "planning_time": 0.02,
                    "planned_trajectory": {
                        "joint_names": ["j1", "j2"],
                        "points": [
                            {"t": 0.0, "positions": [0.0, 0.0]},
                            {"t": 0.3, "positions": [1.0, 1.0]},
                        ],
                    },
                },
            },
        }

        updated = module.merge_export_into_waypoints_doc(
            waypoints_doc,
            export_doc,
            target_template="pick_place_default",
            alias_templates=["pick_place_red"],
        )

        default_template = updated["action_templates"]["pick_place_default"]
        red_template = updated["action_templates"]["pick_place_red"]

        self.assertIn("mapped_steps", default_template)
        self.assertEqual(["home", "pick"], list(default_template["mapped_steps"].keys()))
        self.assertEqual(
            "pick_place_default",
            red_template["trajectory_source_template"],
        )

    def test_resolve_step_mapping_follows_trajectory_source_template(self):
        module = load_module()
        templates = {
            "pick_place_default": {
                "mapped_steps": {
                    "home": {
                        "planned_trajectory": {
                            "joint_names": ["j1"],
                            "points": [{"t": 0.0, "positions": [0.0]}],
                        }
                    }
                }
            },
            "pick_place_blue": {
                "trajectory_source_template": "pick_place_default"
            },
        }

        step_mapping = module.resolve_step_mapping(templates, "pick_place_blue", "home")
        self.assertEqual(
            [0.0],
            step_mapping["planned_trajectory"]["points"][0]["positions"],
        )

    def test_merge_rejects_export_steps_not_matching_template_sequence(self):
        module = load_module()
        waypoints_doc = {
            "joint_names": ["j1"],
            "waypoints": {
                "home": [0.0],
            },
            "action_templates": {
                "pick_place_default": {
                    "sequence": ["home"],
                    "detection_required": False,
                }
            },
        }
        export_doc = {
            "source_action_template": "pick_place_default",
            "joint_names": ["j1"],
            "steps": {
                "home": {
                    "target_positions": [0.0],
                    "planning_time": 0.0,
                    "planned_trajectory": {
                        "joint_names": ["j1"],
                        "points": [{"t": 0.0, "positions": [0.0]}],
                    },
                },
                "pick": {
                    "target_positions": [1.0],
                    "planning_time": 0.0,
                    "planned_trajectory": {
                        "joint_names": ["j1"],
                        "points": [{"t": 0.0, "positions": [1.0]}],
                    },
                },
            },
        }

        with self.assertRaises(ValueError):
            module.merge_export_into_waypoints_doc(
                waypoints_doc,
                export_doc,
                target_template="pick_place_default",
                alias_templates=[],
            )

    def test_merge_allows_reused_step_names_in_template_sequence(self):
        module = load_module()
        waypoints_doc = {
            "joint_names": ["j1"],
            "waypoints": {
                "home": [0.0],
                "pick": [1.0],
            },
            "action_templates": {
                "pick_place_default": {
                    "sequence": ["home", "pick", "home"],
                    "detection_required": False,
                }
            },
        }
        export_doc = {
            "source_action_template": "pick_place_default",
            "joint_names": ["j1"],
            "steps": {
                "home": {
                    "target_positions": [0.0],
                    "planning_time": 0.0,
                    "planned_trajectory": {
                        "joint_names": ["j1"],
                        "points": [{"t": 0.0, "positions": [0.0]}],
                    },
                },
                "pick": {
                    "target_positions": [1.0],
                    "planning_time": 0.0,
                    "planned_trajectory": {
                        "joint_names": ["j1"],
                        "points": [{"t": 0.0, "positions": [1.0]}],
                    },
                },
            },
        }

        updated = module.merge_export_into_waypoints_doc(
            waypoints_doc,
            export_doc,
            target_template="pick_place_default",
            alias_templates=[],
        )

        self.assertIn("home", updated["action_templates"]["pick_place_default"]["mapped_steps"])
        self.assertIn("pick", updated["action_templates"]["pick_place_default"]["mapped_steps"])


if __name__ == "__main__":
    unittest.main()
