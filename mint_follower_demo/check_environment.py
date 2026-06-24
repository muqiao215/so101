#!/usr/bin/env python
"""Lightweight environment check for the SO101 follower demo package."""

from __future__ import print_function

import json
import os
import platform
import shutil
import sys


ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config", "serial_config.json")


def main():
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    port = config.get("port", "")
    camera = os.environ.get("SO101_VISION_CAMERA") or "/dev/v4l/by-id/usb-Clxet_UVCCamera_12345678-video-index0"
    modules = {}
    for name in ("cv2", "numpy"):
        try:
            module = __import__(name)
            modules[name] = {
                "available": True,
                "version": getattr(module, "__version__", ""),
            }
        except Exception as exc:
            modules[name] = {
                "available": False,
                "error": "%s: %s" % (type(exc).__name__, exc),
            }
    result = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "dry_run": bool(config.get("dry_run", True)),
        "backend": config.get("backend"),
        "port": port,
        "port_exists": bool(port and (os.name == "nt" or os.path.exists(port))),
        "leader_port": config.get("leader_port", ""),
        "leader_port_exists": bool(config.get("leader_port") and (os.name == "nt" or os.path.exists(config.get("leader_port")))),
        "vision_camera": camera,
        "vision_camera_exists": bool(camera and os.path.exists(camera)),
        "vision_modules": modules,
        "v4l2_ctl": shutil.which("v4l2-ctl") or "",
        "cwd": ROOT,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
