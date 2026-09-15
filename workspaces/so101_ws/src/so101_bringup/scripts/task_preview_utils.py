#!/usr/bin/env python3
"""Helpers for preview pose execution from MES workbench."""

from typing import Dict, List, Optional


def parse_preview_pose(params: Optional[Dict]) -> Optional[Dict]:
    if not isinstance(params, dict):
        return None
    raw = params.get("previewPose")
    if not isinstance(raw, dict):
        return None
    positions = raw.get("positions")
    if not isinstance(positions, list) or len(positions) != 6:
        return None

    try:
        normalized_positions = [float(value) for value in positions]
        duration_sec = float(raw.get("durationSec", 1.2))
    except Exception as exc:
        raise ValueError(f"invalid preview pose payload: {exc}") from exc

    return {
        "name": str(raw.get("name", "preview_pose")).strip() or "preview_pose",
        "positions": normalized_positions,
        "duration_sec": max(duration_sec, 0.1),
    }
