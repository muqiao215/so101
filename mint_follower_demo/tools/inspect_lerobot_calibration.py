#!/usr/bin/env python3
"""Inspect official LeRobot calibration cache files without importing LeRobot."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
DEFAULT_CACHE = Path("~/.cache/huggingface/lerobot/calibration").expanduser()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def calibration_dir() -> Path:
    env_path = os.environ.get("HF_LEROBOT_CALIBRATION")
    return Path(env_path).expanduser() if env_path else DEFAULT_CACHE


def find_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.json") if path.is_file())


def summarize(path: Path) -> dict:
    payload = load_json(path)
    joints = {}
    for name in JOINT_NAMES:
        item = payload.get(name)
        if isinstance(item, dict):
            joints[name] = {
                "id": item.get("id"),
                "homing_offset": item.get("homing_offset"),
                "range_min": item.get("range_min"),
                "range_max": item.get("range_max"),
            }
    return {
        "file": str(path),
        "complete_so101": set(joints.keys()) == set(JOINT_NAMES),
        "joints": joints,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List official LeRobot calibration JSON files and summarize SO101 joint fields."
    )
    parser.add_argument("--root", default=str(calibration_dir()), help="Calibration cache root")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    root = Path(args.root).expanduser()
    files = find_files(root)
    summaries = [summarize(path) for path in files]
    if args.json:
        print(json.dumps({"root": str(root), "files": summaries}, ensure_ascii=False, indent=2))
        return 0

    print("LeRobot calibration root:", root)
    if not summaries:
        print("No calibration JSON files found.")
        return 0
    for item in summaries:
        print()
        print(item["file"])
        print("  complete_so101:", item["complete_so101"])
        for name in JOINT_NAMES:
            joint = item["joints"].get(name)
            if joint:
                print(
                    "  {name}: id={id} homing={homing_offset} range=[{range_min},{range_max}]".format(
                        name=name, **joint
                    )
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
