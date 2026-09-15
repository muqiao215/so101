#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


SNAPSHOT = {
    "shoulder_pan": {
        "id": 1,
        "drive_mode": 0,
        "homing_offset": -1559,
        "range_min": 356,
        "range_max": 3067,
    },
    "shoulder_lift": {
        "id": 2,
        "drive_mode": 0,
        "homing_offset": 280,
        "range_min": 950,
        "range_max": 3317,
    },
    "elbow_flex": {
        "id": 3,
        "drive_mode": 0,
        "homing_offset": 1817,
        "range_min": 819,
        "range_max": 3022,
    },
    "wrist_flex": {
        "id": 4,
        "drive_mode": 0,
        "homing_offset": 420,
        "range_min": 753,
        "range_max": 2362,
    },
    "wrist_roll": {
        "id": 5,
        "drive_mode": 0,
        "homing_offset": 28,
        "range_min": 0,
        "range_max": 4095,
    },
    "gripper": {
        "id": 6,
        "drive_mode": 0,
        "homing_offset": 1318,
        "range_min": 2047,
        "range_max": 2118,
    },
}


def main() -> int:
    target = Path.home() / ".cache" / "huggingface" / "lerobot" / "calibration" / "teleoperators" / "so_leader" / "None.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(SNAPSHOT, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
