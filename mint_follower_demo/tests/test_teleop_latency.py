from __future__ import print_function

import os
import sys
import unittest
from unittest.mock import patch


DEMO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if DEMO_DIR not in sys.path:
    sys.path.insert(0, DEMO_DIR)

import app as demo


class TeleopStepLimitTests(unittest.TestCase):
    def test_import_does_not_initialize_hardware_runtime(self):
        self.assertIsNone(demo.RUNTIME)

    def test_explicit_global_step_wins_over_configured_joint_steps(self):
        config = {
            "teleop_max_step_raw": 48,
            "teleop_step_raw_by_joint": [48, 48, 48, 56, 48, 40],
        }
        _, limits = demo.resolve_teleop_step_limits({"max_step_raw": 77}, config, 6)
        self.assertEqual(limits, [77.0] * 6)

    def test_configured_joint_steps_apply_without_explicit_api_step(self):
        config = {
            "teleop_max_step_raw": 48,
            "teleop_step_raw_by_joint": [48, 48, 48, 56, 48, 40],
        }
        _, limits = demo.resolve_teleop_step_limits({}, config, 6)
        self.assertEqual(limits, [48.0, 48.0, 48.0, 56.0, 48.0, 40.0])


class FakeLeaderBus(object):
    positions = {}

    def __init__(self, config):
        self.config = config

    def connect(self):
        pass

    def disconnect(self):
        pass

    def scan_expected(self, ids):
        return dict((int(motor_id), demo.STS_MODEL_NUMBER) for motor_id in ids)

    def read_present_positions(self, ids):
        return dict((int(motor_id), int(self.positions[int(motor_id)])) for motor_id in ids)


class FakeFollowerBus(object):
    def __init__(self, positions):
        self.positions = dict(positions)
        self.read_count = 0
        self.sync_count = 0
        self.session = None

    def read_present_positions(self, ids):
        self.read_count += 1
        return dict((int(motor_id), int(self.positions[int(motor_id)])) for motor_id in ids)

    def sync_write_word(self, address, values):
        self.sync_count += 1
        self.positions.update(values)
        # Four startup writes plus eight control frames.
        if self.sync_count >= 12 and self.session is not None:
            self.session.stop_event.set()

    def write_byte(self, motor_id, address, value):
        pass

    def write_word(self, motor_id, address, value):
        self.positions[int(motor_id)] = int(value)


class TeleopLoopTests(unittest.TestCase):
    def test_feedback_is_decimated_without_decimating_commands(self):
        config = {"backend": "native_posix", "dry_run": True, "monitor_mode": False}
        config.update({
            "serial_settle_sec": 0,
            "auto_apply_gripper_angle_limits": False,
            "teleop_frequency_hz": 50,
            "teleop_feedback_frequency_hz": 5,
            "teleop_gripper_rewrite_frequency_hz": 5,
        })
        calibration = {name: {"id": i + 1, "range_min": 0, "range_max": 4095,
                              "homing_offset": 0, "drive_mode": 0}
                       for i, name in enumerate(demo.JOINT_NAMES)}
        midpoint = {str(i + 1): 2048 for i in range(6)}
        fixture = {"calibrated": True, "leader_raw": midpoint, "follower_raw": midpoint}
        with patch.object(demo, 'load_teleop_calibration', return_value=fixture), \
                patch.object(demo, 'read_json', return_value=calibration):
            session = demo.RawTeleopSession(config, calibration)
        leader_positions = demo.normalize_raw_by_id(session.teleop_calibration["leader_raw"])
        follower_positions = demo.normalize_raw_by_id(session.teleop_calibration["follower_raw"])
        FakeLeaderBus.positions = leader_positions
        follower_bus = FakeFollowerBus(follower_positions)
        follower_bus.session = session
        follower = demo.NativeSTSFollowerDriver(config, calibration, config.get("mapping", {}))
        follower.bus = follower_bus
        follower.connected = True
        original_bus_class = demo.NativeFeetechSTSBus
        demo.NativeFeetechSTSBus = FakeLeaderBus
        try:
            session.follower_driver = follower
            session._run({
                "frequency_hz": 50,
                "feedback_frequency_hz": 5,
                "gripper_rewrite_frequency_hz": 5,
                "max_step_raw": 77,
                "gripper_start_hold_sec": 0,
            })
        finally:
            demo.NativeFeetechSTSBus = original_bus_class

        self.assertEqual(session.last_error, "")
        self.assertEqual(session.frames, 8)
        self.assertEqual(session.active_step_raw_by_joint, [77.0] * 6)
        self.assertEqual(follower_bus.sync_count, 12)
        self.assertLess(follower_bus.read_count, session.frames)
        self.assertGreater(session.actual_frequency_hz, 0)


if __name__ == "__main__":
    unittest.main()
