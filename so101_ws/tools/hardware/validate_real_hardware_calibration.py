#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from real_hardware_calibration import (
    DEFAULT_PROFILE_ENV,
    build_validation_report,
    load_calibration_profile,
    resolve_calibration_profile_path,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SO101 real hardware calibration profile.")
    parser.add_argument("profile", nargs="?", default="", help="Calibration profile JSON path")
    parser.add_argument(
        "--profile-env",
        default=DEFAULT_PROFILE_ENV,
        help=(
            "Environment variable that may contain the calibration profile path "
            f"(default: {DEFAULT_PROFILE_ENV})"
        ),
    )
    args = parser.parse_args()

    profile_path, profile_source, resolution_errors = resolve_calibration_profile_path(
        args.profile,
        args.profile_env,
        root_dir=Path(__file__).resolve().parents[2],
    )
    if resolution_errors:
        print(
            json.dumps(
                {
                    "ok": False,
                    "errors": resolution_errors,
                    "profileSource": profile_source,
                    "profileEnv": args.profile_env,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    assert profile_path is not None
    normalized, errors = load_calibration_profile(profile_path)
    report = build_validation_report(profile_path, normalized, errors)
    report["profileSource"] = profile_source
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
