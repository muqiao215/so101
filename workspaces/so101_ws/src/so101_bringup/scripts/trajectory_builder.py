#!/usr/bin/env python3
"""Trajectory message builders extracted from task executor."""

from types import SimpleNamespace
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
except Exception:  # pragma: no cover - test/runtime fallback for non-ROS env
    class JointTrajectoryPoint:  # type: ignore[no-redef]
        def __init__(self) -> None:
            self.positions: List[float] = []
            self.time_from_start = SimpleNamespace(sec=0, nanosec=0)

    class JointTrajectory:  # type: ignore[no-redef]
        def __init__(self) -> None:
            self.joint_names: List[str] = []
            self.points: List[JointTrajectoryPoint] = []


def _to_duration_fields(duration_sec: float) -> Tuple[int, int]:
    normalized = max(float(duration_sec), 0.0)
    return int(normalized), int((normalized % 1.0) * 1_000_000_000)


SO101_JOINT_LIMITS = {
    "shoulder_pan": (-1.91986, 1.91986),
    "shoulder_lift": (-1.74533, 1.74533),
    "elbow_flex": (-1.69, 1.69),
    "wrist_flex": (-1.65806, 1.65806),
    "wrist_roll": (-2.74385, 2.84121),
    "gripper": (-0.174533, 1.74533),
}


def _clamp_positions(joint_names: Sequence[str], positions: Sequence[float]) -> List[float]:
    clamped = []
    for name, value in zip(joint_names, positions):
        numeric = float(value)
        limits = SO101_JOINT_LIMITS.get(str(name))
        if limits:
            low, high = limits
            numeric = min(max(numeric, low), high)
        clamped.append(numeric)
    return clamped


def create_single_point_trajectory_message(
    joint_names: Sequence[str],
    positions: Sequence[float],
    duration_sec: float,
) -> JointTrajectory:
    if len(joint_names) != len(positions):
        raise ValueError("joint_names and positions length mismatch")

    msg = JointTrajectory()
    msg.joint_names = [str(name) for name in joint_names]
    point = JointTrajectoryPoint()
    point.positions = _clamp_positions(msg.joint_names, positions)
    sec, nanosec = _to_duration_fields(duration_sec)
    point.time_from_start.sec = sec
    point.time_from_start.nanosec = nanosec
    msg.points.append(point)
    return msg


def build_mapped_trajectory_message(
    step_mapping: Dict,
    default_joint_names: Optional[Iterable[str]] = None,
) -> Optional[Tuple[JointTrajectory, float]]:
    planned = step_mapping.get("planned_trajectory")
    if not isinstance(planned, dict):
        return None

    joint_names = planned.get("joint_names", list(default_joint_names or []))
    points = planned.get("points", [])
    if not isinstance(joint_names, list) or not joint_names:
        return None
    if not isinstance(points, list) or not points:
        return None

    msg = JointTrajectory()
    msg.joint_names = [str(name) for name in joint_names]
    last_t = 0.0
    for raw_point in points:
        if not isinstance(raw_point, dict):
            return None
        positions = raw_point.get("positions", [])
        if not isinstance(positions, list) or len(positions) != len(msg.joint_names):
            return None
        t = float(raw_point.get("t", 0.0))
        point = JointTrajectoryPoint()
        point.positions = _clamp_positions(msg.joint_names, positions)
        sec, nanosec = _to_duration_fields(t)
        point.time_from_start.sec = sec
        point.time_from_start.nanosec = nanosec
        msg.points.append(point)
        last_t = max(last_t, t)

    return msg, last_t
