#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

from real_hardware_calibration import (
    build_execution_gate_status,
    build_validation_report,
    load_calibration_profile,
    runtime_calibration_path,
    sync_calibration_profile,
)


def resolve_profile_path(profile: str, profile_env: str) -> tuple[Path | None, dict, list[str]]:
    errors: list[str] = []

    if profile:
        return Path(profile).resolve(), {"mode": "arg", "value": profile}, errors

    env_name = profile_env.strip()
    if not env_name:
        return None, {"mode": "unset", "value": ""}, ["profile path is required via --profile or --profile-env"]

    env_value = os.environ.get(env_name, "").strip()
    if not env_value:
        return None, {"mode": "env", "value": env_name}, [f"Environment variable {env_name} is not set"]

    return Path(env_value).resolve(), {"mode": "env", "value": env_name, "resolvedValue": env_value}, errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect or smoke-test whether a calibration profile is synced into SO101 runtime."
    )
    parser.add_argument("--profile", default="", help="Calibration profile JSON path")
    parser.add_argument(
        "--profile-env",
        default="",
        help="Environment variable that should contain the calibration profile path (for example SO101_MAIN_ARM_CALIBRATION_PROFILE)",
    )
    parser.add_argument(
        "--sync-first",
        action="store_true",
        help="Validate and sync the profile before inspecting the runtime calibration file",
    )
    parser.add_argument(
        "--root-dir",
        default=str(Path(__file__).resolve().parents[2]),
        help="Workspace root used to derive default runtime dir",
    )
    parser.add_argument(
        "--runtime-dir",
        default="",
        help="Override runtime dir; default is <workspace>/.vscode/.runtime",
    )
    args = parser.parse_args()

    if not args.profile and not args.profile_env:
        parser.error("one of --profile or --profile-env is required")

    profile_path, profile_source, resolution_errors = resolve_profile_path(args.profile, args.profile_env)
    runtime_path = runtime_calibration_path(Path(args.root_dir).resolve(), args.runtime_dir)

    if resolution_errors:
        payload = {
            "ok": False,
            "errors": resolution_errors,
            "profileSource": profile_source,
            "runtimeCalibration": str(runtime_path),
            "executionGate": build_execution_gate_status(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    assert profile_path is not None
    sync_report = None
    if args.sync_first:
        sync_report = sync_calibration_profile(profile_path, runtime_path.parent)

    normalized, errors = load_calibration_profile(profile_path)
    runtime_exists = runtime_path.exists()
    runtime_normalized = None
    runtime_errors: list[str] = []
    if runtime_exists:
        runtime_normalized, runtime_errors = load_calibration_profile(runtime_path)

    runtime_matches_profile = runtime_exists and not errors and not runtime_errors and runtime_normalized == normalized
    payload = build_validation_report(profile_path, normalized, list(errors))
    payload.update(
        {
            "profileSource": profile_source,
            "runtimeCalibration": str(runtime_path),
            "runtimeCalibrationExists": runtime_exists,
            "runtimeCalibrationErrors": runtime_errors,
            "runtimeMatchesProfile": runtime_matches_profile,
            "runtimeNormalized": runtime_normalized,
            "syncRequested": bool(args.sync_first),
            "syncReport": sync_report,
        }
    )
    payload["ok"] = payload["ok"] and runtime_matches_profile
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
