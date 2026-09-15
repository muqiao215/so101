#!/usr/bin/env python3
import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "task_execution_service.py"


def load_module():
    spec = importlib.util.spec_from_file_location("task_execution_service", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TaskExecutionServiceTests(unittest.TestCase):
    def test_execute_preview_pose_publishes_started_step_and_ok(self):
        module = load_module()
        statuses = []
        trajectories = []

        service = module.TaskExecutionService(
            templates={},
            waypoints={"waypoints": {}},
            joint_names=["j1", "j2", "j3", "j4", "j5", "j6"],
            default_step_duration=1.8,
            resolve_step_mapping=lambda *_args, **_kwargs: None,
            parse_preview_pose=lambda params: params.get("previewPose"),
            publish_status=lambda **payload: statuses.append(payload),
            publish_trajectory=lambda msg: trajectories.append(msg),
            sleep_fn=lambda _seconds: None,
        )

        service.execute(
            request_id="req-preview",
            template_id="preview_pose",
            params={
                "previewPose": {
                    "name": "pose-a",
                    "positions": [0, 1, 2, 3, 4, 5],
                    "duration_sec": 0.6,
                }
            },
        )

        self.assertEqual("STARTED", statuses[0]["code"])
        self.assertEqual("STEP", statuses[1]["code"])
        self.assertEqual("OK", statuses[2]["code"])
        self.assertEqual(1, len(trajectories))


if __name__ == "__main__":
    unittest.main()
