#!/usr/bin/env python
"""Lightweight environment check for the SO101 follower demo package."""

from __future__ import print_function

import json
import os
import platform
import sys


ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config", "serial_config.json")


def main():
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    port = config.get("port", "")
    result = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "dry_run": bool(config.get("dry_run", True)),
        "backend": config.get("backend"),
        "port": port,
        "port_exists": bool(port and (os.name == "nt" or os.path.exists(port))),
        "cwd": ROOT,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
