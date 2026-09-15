#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from real_hardware_calibration import (
    DEFAULT_PROFILE_ENV,
    resolve_calibration_profile_path,
    sync_calibration_profile,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and sync a real hardware calibration profile into SO101 runtime."
    )
    parser.add_argument("--profile", default="", help="Calibration profile JSON path")
    parser.add_argument(
        "--profile-env",
        default=DEFAULT_PROFILE_ENV,
        help=(
            "Environment variable that may contain the calibration profile path "
            f"(default: {DEFAULT_PROFILE_ENV})"
        ),
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

    root_dir = Path(args.root_dir).resolve()
    runtime_dir = Path(args.runtime_dir).resolve() if args.runtime_dir else root_dir / ".vscode" / ".runtime"
    profile_path, profile_source, resolution_errors = resolve_calibration_profile_path(
        args.profile,
        args.profile_env,
        root_dir,
    )
    if resolution_errors:
        print(
            json.dumps(
                {
                    "ok": False,
                    "errors": resolution_errors,
                    "profileSource": profile_source,
                    "runtimeDir": str(runtime_dir),
                    "runtimeCalibration": str((runtime_dir / "real_hardware_calibration.json").resolve()),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    assert profile_path is not None
    report = sync_calibration_profile(profile_path, runtime_dir)
    report["profileSource"] = profile_source
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] and report["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
