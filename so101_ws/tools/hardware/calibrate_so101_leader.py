#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path


def _serialize_calibration(calibration: dict) -> dict:
    payload = {}
    for key, value in calibration.items():
        if is_dataclass(value):
            payload[str(key)] = asdict(value)
        else:
            payload[str(key)] = {
                "id": int(getattr(value, "id")),
                "drive_mode": int(getattr(value, "drive_mode")),
                "homing_offset": int(getattr(value, "homing_offset")),
                "range_min": int(getattr(value, "range_min")),
                "range_max": int(getattr(value, "range_max")),
            }
    return payload


def _save_calibration_fallback(device) -> Path:
    path = Path(device.calibration_fpath)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _serialize_calibration(device.calibration)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run official SO-101 leader calibration interactively.")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Leader serial port")
    args = parser.parse_args()

    from lerobot.teleoperators.so_leader.so_leader import SOLeader
    from lerobot.teleoperators.so_leader.config_so_leader import SOLeaderTeleopConfig

    config = SOLeaderTeleopConfig(port=args.port)
    device = SOLeader(config)

    try:
        device.connect(calibrate=False)
        print(f"[leader-calibrate] connected on {args.port}", flush=True)
        print("[leader-calibrate] follow the interactive prompts below.", flush=True)
        try:
            device.calibrate()
        except Exception as exc:
            if device.calibration:
                saved_path = _save_calibration_fallback(device)
                print(
                    f"[leader-calibrate] draccus save failed, fallback JSON written to {saved_path}: {exc}",
                    flush=True,
                )
            else:
                raise
        print("[leader-calibrate] calibration done", flush=True)
    finally:
        try:
            device.disconnect()
            print("[leader-calibrate] disconnected", flush=True)
        except Exception as exc:  # pragma: no cover - best effort cleanup
            print(f"[leader-calibrate] disconnect warning: {exc}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
