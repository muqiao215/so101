#!/usr/bin/env python3
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from real_hardware_calibration import (
    DEFAULT_PROFILE_ENV,
    DEFAULT_LOCAL_PROFILE_RELATIVE,
    default_local_calibration_profile_path,
    load_calibration_profile,
    resolve_calibration_profile_path,
    sync_calibration_profile,
    validate_calibration_profile,
)


class RealHardwareCalibrationTest(unittest.TestCase):
    def test_validate_calibration_profile_accepts_ready_profile(self):
        payload = {
            "schemaVersion": "1.0",
            "profileName": "so101-default",
            "calibrated": True,
            "homed": True,
            "poses": {
                "home": {"joints": [0, 0, 0, 0, 0, 0]},
                "pick": {"joints": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]},
                "place": {"joints": [0.6, 0.5, 0.4, 0.3, 0.2, 0.1]},
                "gripper_open": {"value": 0.0},
                "gripper_close": {"value": 1.0},
            },
        }

        normalized, errors = validate_calibration_profile(payload)

        self.assertEqual(errors, [])
        self.assertTrue(normalized["calibrated"])
        self.assertTrue(normalized["homed"])
        self.assertEqual(normalized["profileName"], "so101-default")

    def test_validate_calibration_profile_rejects_missing_required_poses(self):
        payload = {
            "schemaVersion": "1.0",
            "profileName": "broken",
            "calibrated": True,
            "homed": False,
            "poses": {
                "home": {"joints": [0, 0, 0, 0, 0, 0]},
                "gripper_open": {"value": 0.0},
            },
        }

        _, errors = validate_calibration_profile(payload)

        self.assertTrue(errors)
        self.assertTrue(any("pick" in error for error in errors))
        self.assertTrue(any("place" in error for error in errors))

    def test_validate_calibration_profile_rejects_non_object_payload(self):
        normalized, errors = validate_calibration_profile(["not", "an", "object"])

        self.assertTrue(errors)
        self.assertTrue(any("JSON object" in error for error in errors))
        self.assertFalse(normalized["calibrated"])
        self.assertFalse(normalized["homed"])

    def test_validate_calibration_profile_rejects_homed_without_calibrated(self):
        payload = {
            "schemaVersion": "1.0",
            "profileName": "homed-without-calibration",
            "calibrated": False,
            "homed": True,
            "poses": {
                "home": {"joints": [0, 0, 0, 0, 0, 0]},
                "pick": {"joints": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]},
                "place": {"joints": [0.6, 0.5, 0.4, 0.3, 0.2, 0.1]},
                "gripper_open": {"value": 0.0},
                "gripper_close": {"value": 1.0},
            },
        }

        normalized, errors = validate_calibration_profile(payload)

        self.assertTrue(errors)
        self.assertTrue(any("homed" in error for error in errors))
        self.assertFalse(normalized["calibrated"])
        self.assertFalse(normalized["homed"])

    def test_validate_calibration_profile_rejects_non_numeric_joint_values(self):
        payload = {
            "schemaVersion": "1.0",
            "profileName": "bad-joints",
            "calibrated": True,
            "homed": False,
            "poses": {
                "home": {"joints": [0, 0, 0, 0, 0, 0]},
                "pick": {"joints": [0.1, 0.2, 0.3, "bad", 0.5, 0.6]},
                "place": {"joints": [0.6, 0.5, 0.4, 0.3, 0.2, 0.1]},
                "gripper_open": {"value": 0.0},
                "gripper_close": {"value": 1.0},
            },
        }

        normalized, errors = validate_calibration_profile(payload)

        self.assertTrue(any("poses.pick.joints must contain only numeric values" in error for error in errors))
        self.assertFalse(normalized["calibrated"])
        self.assertFalse(normalized["homed"])

    def test_load_calibration_profile_reports_missing_file(self):
        missing_path = Path(__file__).resolve().parent / "does-not-exist.json"

        normalized, errors = load_calibration_profile(missing_path)

        self.assertTrue(errors)
        self.assertTrue(any("calibration profile not found" in error for error in errors))
        self.assertFalse(normalized["calibrated"])
        self.assertFalse(normalized["homed"])

    def test_load_calibration_profile_reports_invalid_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / "invalid.json"
            profile_path.write_text("{ invalid json\n", encoding="utf-8")

            normalized, errors = load_calibration_profile(profile_path)

        self.assertTrue(errors)
        self.assertTrue(any("invalid JSON in calibration profile" in error for error in errors))
        self.assertFalse(normalized["calibrated"])
        self.assertFalse(normalized["homed"])

    def test_load_calibration_profile_preserves_valid_profile(self):
        payload = {
            "schemaVersion": "1.0",
            "profileName": "from-file",
            "calibrated": True,
            "homed": False,
            "poses": {
                "home": {"joints": [0, 0, 0, 0, 0, 0]},
                "pick": {"joints": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]},
                "place": {"joints": [0.6, 0.5, 0.4, 0.3, 0.2, 0.1]},
                "gripper_open": {"value": 0.0},
                "gripper_close": {"value": 1.0},
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / "valid.json"
            profile_path.write_text(json.dumps(payload), encoding="utf-8")

            normalized, errors = load_calibration_profile(profile_path)

        self.assertEqual(errors, [])
        self.assertTrue(normalized["calibrated"])
        self.assertFalse(normalized["homed"])
        self.assertEqual(normalized["profileName"], "from-file")

    def test_resolve_calibration_profile_path_prefers_explicit_argument(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / "profile.json"
            profile_path.write_text("{}", encoding="utf-8")

            resolved_path, profile_source, errors = resolve_calibration_profile_path(
                str(profile_path),
                "IGNORED_PROFILE_ENV",
            )

        self.assertEqual(errors, [])
        self.assertEqual(resolved_path, profile_path.resolve())
        self.assertEqual(profile_source["mode"], "arg")
        self.assertEqual(profile_source["value"], str(profile_path))

    def test_resolve_calibration_profile_path_supports_environment_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / "profile.json"
            profile_path.write_text("{}", encoding="utf-8")
            env_name = "SO101_TEST_CALIBRATION_PROFILE"
            original_value = os.environ.get(env_name)
            os.environ[env_name] = str(profile_path)
            try:
                resolved_path, profile_source, errors = resolve_calibration_profile_path("", env_name)
            finally:
                if original_value is None:
                    os.environ.pop(env_name, None)
                else:
                    os.environ[env_name] = original_value

        self.assertEqual(errors, [])
        self.assertEqual(resolved_path, profile_path.resolve())
        self.assertEqual(profile_source["mode"], "env")
        self.assertEqual(profile_source["value"], env_name)
        self.assertEqual(profile_source["resolvedValue"], str(profile_path))

    def test_resolve_calibration_profile_path_uses_local_default_when_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            local_profile = default_local_calibration_profile_path(root_dir)
            local_profile.parent.mkdir(parents=True, exist_ok=True)
            local_profile.write_text("{}", encoding="utf-8")

            resolved_path, profile_source, errors = resolve_calibration_profile_path(
                "",
                "IGNORED_ENV",
                root_dir=root_dir,
            )

        self.assertEqual(errors, [])
        self.assertEqual(resolved_path, local_profile.resolve())
        self.assertEqual(profile_source["mode"], "local_default")
        self.assertEqual(profile_source["value"], DEFAULT_LOCAL_PROFILE_RELATIVE)

    def test_resolve_calibration_profile_path_reports_missing_input(self):
        original_value = os.environ.get(DEFAULT_PROFILE_ENV)
        os.environ.pop(DEFAULT_PROFILE_ENV, None)
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                resolved_path, profile_source, errors = resolve_calibration_profile_path(
                    "",
                    DEFAULT_PROFILE_ENV,
                    root_dir=Path(temp_dir),
                )
            finally:
                if original_value is not None:
                    os.environ[DEFAULT_PROFILE_ENV] = original_value

        self.assertIsNone(resolved_path)
        self.assertEqual(profile_source["mode"], "missing")
        self.assertEqual(profile_source["localDefault"], DEFAULT_LOCAL_PROFILE_RELATIVE)
        self.assertTrue(errors)
        self.assertIn(DEFAULT_PROFILE_ENV, errors[0])

    def test_sync_calibration_profile_writes_and_verifies_runtime_file(self):
        payload = {
            "schemaVersion": "1.0",
            "profileName": "runtime-sync",
            "calibrated": True,
            "homed": True,
            "poses": {
                "home": {"joints": [0, 0, 0, 0, 0, 0]},
                "pick": {"joints": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]},
                "place": {"joints": [0.6, 0.5, 0.4, 0.3, 0.2, 0.1]},
                "gripper_open": {"value": 0.0},
                "gripper_close": {"value": 1.0},
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            profile_path = temp_root / "profile.json"
            runtime_dir = temp_root / ".runtime"
            profile_path.write_text(json.dumps(payload), encoding="utf-8")

            report = sync_calibration_profile(profile_path, runtime_dir)

            runtime_path = runtime_dir / "real_hardware_calibration.json"
            self.assertTrue(runtime_path.exists())
            self.assertTrue(report["ok"])
            self.assertTrue(report["synced"])
            self.assertTrue(report["verified"])
            self.assertFalse(report["executionGate"]["allowExecute"])
            self.assertEqual(report["runtimeCalibration"], str(runtime_path.resolve()))


if __name__ == "__main__":
    unittest.main()
