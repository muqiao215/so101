#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Dict, List, Tuple


SCHEMA_VERSION = "1.0"
REQUIRED_JOINT_POSES = ("home", "pick", "place")
REQUIRED_GRIPPER_POSES = ("gripper_open", "gripper_close")
REQUIRED_POSE_NAMES = REQUIRED_JOINT_POSES + REQUIRED_GRIPPER_POSES
JOINT_COUNT = 6
RUNTIME_FILE_NAME = "real_hardware_calibration.json"
EXECUTION_GATE_NOTE = (
    "Calibration data only prepares runtime state. Motion execution must stay blocked "
    "until the separate real-hardware safety gates explicitly allow it."
)
DEFAULT_PROFILE_ENV = "SO101_MAIN_ARM_CALIBRATION_PROFILE"
DEFAULT_LOCAL_PROFILE_RELATIVE = "tools/hardware/real_hardware_calibration.local.json"


def empty_calibration_profile() -> Dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "profileName": "",
        "calibrated": False,
        "homed": False,
        "updatedAt": "",
        "poses": {},
    }


def _text(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _failure(errors: List[str]) -> Tuple[Dict[str, Any], List[str]]:
    normalized = empty_calibration_profile()
    return normalized, errors


def build_execution_gate_status() -> Dict[str, Any]:
    return {
        "allowExecute": False,
        "reason": "CALIBRATION_SYNC_NEVER_ENABLES_EXECUTION",
        "note": EXECUTION_GATE_NOTE,
    }


def build_validation_report(profile_path: Path, normalized: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
    resolved_path = str(Path(profile_path).resolve())
    return {
        "ok": not errors,
        "profile": resolved_path,
        "errors": errors,
        "requiredPoses": list(REQUIRED_POSE_NAMES),
        "profileEnv": DEFAULT_PROFILE_ENV,
        "normalized": normalized,
        "executionGate": build_execution_gate_status(),
    }


def runtime_calibration_path(root_dir: Path, runtime_dir_override: str = "") -> Path:
    root_path = Path(root_dir).resolve()
    runtime_dir = Path(runtime_dir_override).resolve() if runtime_dir_override else root_path / ".vscode" / ".runtime"
    return runtime_dir / RUNTIME_FILE_NAME


def default_local_calibration_profile_path(root_dir: Path | str) -> Path:
    return Path(root_dir).resolve() / DEFAULT_LOCAL_PROFILE_RELATIVE


def resolve_calibration_profile_path(
    profile: str = "",
    profile_env: str = DEFAULT_PROFILE_ENV,
    root_dir: Path | str | None = None,
) -> Tuple[Path | None, Dict[str, str], List[str]]:
    profile_value = str(profile).strip()
    env_name = str(profile_env).strip() or DEFAULT_PROFILE_ENV

    if profile_value:
        return (
            Path(profile_value).expanduser().resolve(),
            {"mode": "arg", "value": profile_value},
            [],
        )

    env_value = os.environ.get(env_name, "").strip()
    if env_value:
        return (
            Path(env_value).expanduser().resolve(),
            {"mode": "env", "value": env_name, "resolvedValue": env_value},
            [],
        )

    if root_dir:
        local_profile = default_local_calibration_profile_path(root_dir)
        if local_profile.exists():
            return (
                local_profile,
                {
                    "mode": "local_default",
                    "value": DEFAULT_LOCAL_PROFILE_RELATIVE,
                    "resolvedValue": str(local_profile),
                },
                [],
            )

    return (
        None,
        {
            "mode": "missing",
            "value": env_name,
            "localDefault": DEFAULT_LOCAL_PROFILE_RELATIVE,
        },
        [
            (
                "calibration profile path is required. Pass a JSON file path directly "
                f"or set {env_name} to that path before running the calibration tool. "
                f"If you prefer a project-local default, create {DEFAULT_LOCAL_PROFILE_RELATIVE}"
            )
        ],
    )


def validate_calibration_profile(payload: Any) -> Tuple[Dict[str, Any], List[str]]:
    if not isinstance(payload, dict):
        return _failure(["calibration profile must be a JSON object"])

    errors: List[str] = []
    source = payload
    normalized = empty_calibration_profile()
    normalized.update(
        {
            "schemaVersion": _text(source.get("schemaVersion"), SCHEMA_VERSION),
            "profileName": _text(source.get("profileName"), ""),
            "calibrated": bool(source.get("calibrated", False)),
            "homed": bool(source.get("homed", False)),
            "updatedAt": _text(source.get("updatedAt"), ""),
        }
    )

    if normalized["schemaVersion"] != SCHEMA_VERSION:
        errors.append(f"schemaVersion must be '{SCHEMA_VERSION}'")
    if not normalized["profileName"]:
        errors.append("profileName is required")

    poses = source.get("poses")
    if not isinstance(poses, dict):
        errors.append(
            "poses must be an object containing home, pick, place, gripper_open, and gripper_close"
        )
        poses = {}

    for pose_name in REQUIRED_JOINT_POSES:
        pose = poses.get(pose_name)
        pose_path = f"poses.{pose_name}"
        if not isinstance(pose, dict):
            errors.append(f"{pose_path} is required")
            continue

        joints = pose.get("joints")
        if not isinstance(joints, list):
            errors.append(f"{pose_path}.joints must be an array with {JOINT_COUNT} numeric values")
            continue
        if len(joints) != JOINT_COUNT:
            errors.append(f"{pose_path}.joints must contain exactly {JOINT_COUNT} values")
            continue

        joint_values = [_number(item) for item in joints]
        if any(item is None for item in joint_values):
            errors.append(f"{pose_path}.joints must contain only numeric values")
            continue

        normalized["poses"][pose_name] = {"joints": joint_values}

    for pose_name in REQUIRED_GRIPPER_POSES:
        pose = poses.get(pose_name)
        pose_path = f"poses.{pose_name}"
        if not isinstance(pose, dict):
            errors.append(f"{pose_path} is required")
            continue

        value = _number(pose.get("value"))
        if value is None:
            errors.append(f"{pose_path}.value must be numeric")
            continue

        normalized["poses"][pose_name] = {"value": value}

    if normalized["homed"] and not normalized["calibrated"]:
        errors.append("homed cannot be true when calibrated is false")

    if errors:
        normalized["calibrated"] = False
        normalized["homed"] = False

    return normalized, errors


def load_calibration_profile(path: Path) -> Tuple[Dict[str, Any], List[str]]:
    profile_path = Path(path)

    if not profile_path.exists():
        return _failure([f"calibration profile not found: {profile_path.resolve()}"])
    if not profile_path.is_file():
        return _failure([f"Calibration profile is not a regular file: {profile_path.resolve()}"])

    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        return _failure(
            [
                (
                    f"invalid JSON in calibration profile {profile_path.resolve()}: "
                    f"line {exc.lineno}, column {exc.colno}: {exc.msg}"
                )
            ]
        )
    except OSError as exc:
        return _failure([f"Failed to read calibration profile {profile_path.resolve()}: {exc}"])

    return validate_calibration_profile(payload)


def sync_calibration_profile(profile_path: Path, runtime_dir: Path) -> Dict[str, Any]:
    resolved_profile = Path(profile_path).resolve()
    resolved_runtime_dir = Path(runtime_dir).resolve()
    normalized, errors = load_calibration_profile(resolved_profile)
    report = build_validation_report(resolved_profile, normalized, list(errors))
    target = resolved_runtime_dir / RUNTIME_FILE_NAME
    report.update(
        {
            "runtimeDir": str(resolved_runtime_dir),
            "runtimeCalibration": str(target),
            "synced": False,
            "verified": False,
        }
    )

    if report["errors"]:
        return report

    resolved_runtime_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["synced"] = True

    try:
        runtime_payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, JSONDecodeError) as exc:
        report["errors"].append(f"Failed to verify runtime calibration file {target}: {exc}")
        return report

    report["verified"] = runtime_payload == normalized
    if not report["verified"]:
        report["errors"].append(
            f"Runtime calibration file verification failed for {target}: written content did not match the normalized profile"
        )
        report["synced"] = False
        return report

    return report
