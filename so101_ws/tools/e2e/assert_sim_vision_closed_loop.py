#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image, JointState
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory


@dataclass
class Samples:
    image: dict[str, Any] | None = None
    overlay_image: dict[str, Any] | None = None
    camera_info: dict[str, Any] | None = None
    detection: dict[str, Any] | None = None
    vision_target: dict[str, Any] | None = None
    task_statuses: list[dict[str, Any]] = field(default_factory=list)
    joint_state: dict[str, Any] | None = None
    first_joint_state: dict[str, Any] | None = None
    max_joint_delta: float = 0.0
    trajectory_command: dict[str, Any] | None = None
    trajectory_command_count: int = 0


def decode_string(msg: String) -> dict[str, Any]:
    try:
        payload = json.loads(msg.data)
        return payload if isinstance(payload, dict) else {"raw": msg.data}
    except json.JSONDecodeError:
        return {"raw": msg.data}


class SimVisionClosedLoopProbe(Node):
    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__("sim_vision_closed_loop_probe")
        self.args = args
        self.samples = Samples()
        self.create_subscription(Image, args.image_topic, self._on_image, 10)
        self.create_subscription(Image, args.overlay_image_topic, self._on_overlay_image, 10)
        self.create_subscription(CameraInfo, args.camera_info_topic, self._on_camera_info, 10)
        self.create_subscription(String, args.detections_topic, self._on_detection, 20)
        self.create_subscription(String, args.vision_targets_topic, self._on_vision_target, 20)
        self.create_subscription(String, args.task_status_topic, self._on_task_status, 50)
        self.create_subscription(JointState, args.joint_states_topic, self._on_joint_state, 20)
        self.create_subscription(JointTrajectory, args.trajectory_topic, self._on_trajectory, 20)

    def _on_image(self, msg: Image) -> None:
        self.samples.image = {
            "height": int(msg.height),
            "width": int(msg.width),
            "encoding": str(msg.encoding),
            "data_len": len(msg.data),
            "frame_id": str(msg.header.frame_id),
        }

    def _on_overlay_image(self, msg: Image) -> None:
        self.samples.overlay_image = {
            "height": int(msg.height),
            "width": int(msg.width),
            "encoding": str(msg.encoding),
            "data_len": len(msg.data),
            "frame_id": str(msg.header.frame_id),
        }

    def _on_camera_info(self, msg: CameraInfo) -> None:
        self.samples.camera_info = {
            "height": int(msg.height),
            "width": int(msg.width),
            "frame_id": str(msg.header.frame_id),
        }

    def _on_detection(self, msg: String) -> None:
        payload = decode_string(msg)
        self.samples.detection = payload

    def _on_vision_target(self, msg: String) -> None:
        payload = decode_string(msg)
        self.samples.vision_target = payload

    def _on_task_status(self, msg: String) -> None:
        payload = decode_string(msg)
        self.samples.task_statuses.append(payload)
        self.samples.task_statuses = self.samples.task_statuses[-20:]

    def _on_joint_state(self, msg: JointState) -> None:
        payload = {
            "joint_names": list(msg.name),
            "positions": [float(value) for value in msg.position],
        }
        if self.samples.first_joint_state is None:
            self.samples.first_joint_state = payload
        self.samples.joint_state = payload
        self.samples.max_joint_delta = max(
            self.samples.max_joint_delta,
            joint_state_delta(self.samples.first_joint_state, self.samples.joint_state),
        )

    def _on_trajectory(self, msg: JointTrajectory) -> None:
        self.samples.trajectory_command_count += 1
        last_point = msg.points[-1] if msg.points else None
        self.samples.trajectory_command = {
            "joint_names": list(msg.joint_names),
            "point_count": len(msg.points),
            "last_positions": [float(value) for value in last_point.positions] if last_point else [],
            "last_time_from_start_sec": (
                float(last_point.time_from_start.sec) + float(last_point.time_from_start.nanosec) / 1_000_000_000.0
                if last_point
                else 0.0
            ),
            "command_count": self.samples.trajectory_command_count,
        }


def has_detection(payload: dict[str, Any] | None, min_count: int, required_source: str) -> bool:
    if not payload:
        return False
    if required_source and payload.get("source") != required_source:
        return False
    try:
        count = int(payload.get("count", 0))
    except Exception:
        count = 0
    return count >= min_count


def has_vision_target(payload: dict[str, Any] | None, min_count: int) -> bool:
    if not payload:
        return False
    try:
        count = int(payload.get("count", 0))
    except Exception:
        count = 0
    return count >= min_count


def task_closed(statuses: list[dict[str, Any]], request_prefix: str) -> bool:
    for payload in statuses:
        request_id = str(payload.get("requestId", ""))
        code = str(payload.get("code", ""))
        if request_id.startswith(request_prefix) and code in {"OK", "EXECUTION_ERROR", "DETECTION_MISMATCH"}:
            return True
    return False


def joint_state_delta(first: dict[str, Any] | None, latest: dict[str, Any] | None) -> float:
    if not first or not latest:
        return 0.0
    first_names = first.get("joint_names") or []
    latest_names = latest.get("joint_names") or []
    first_positions = first.get("positions") or []
    latest_positions = latest.get("positions") or []
    if not isinstance(first_names, list) or not isinstance(latest_names, list):
        return 0.0
    first_by_name = {
        str(name): float(first_positions[idx])
        for idx, name in enumerate(first_names)
        if idx < len(first_positions)
    }
    deltas = []
    for idx, name in enumerate(latest_names):
        key = str(name)
        if key not in first_by_name or idx >= len(latest_positions):
            continue
        deltas.append(abs(float(latest_positions[idx]) - first_by_name[key]))
    return max(deltas) if deltas else 0.0


def build_report(args: argparse.Namespace, probe: SimVisionClosedLoopProbe, status: str, checks: dict[str, bool]) -> dict[str, Any]:
    return {
        "schema": "so101_sim_vision_closed_loop_assertion_v1",
        "status": status,
        "timeout_sec": args.timeout_sec,
        "detection_backend": args.detection_backend,
        "topics": {
            "image": args.image_topic,
            "overlay_image": args.overlay_image_topic,
            "camera_info": args.camera_info_topic,
            "detections": args.detections_topic,
            "vision_targets": args.vision_targets_topic,
            "task_status": args.task_status_topic,
            "joint_states": args.joint_states_topic,
            "trajectory": args.trajectory_topic,
        },
        "checks": checks,
        "samples": {
            "image": probe.samples.image,
            "overlay_image": probe.samples.overlay_image,
            "camera_info": probe.samples.camera_info,
            "detection": probe.samples.detection,
            "vision_target": probe.samples.vision_target,
            "trajectory_command": probe.samples.trajectory_command,
            "trajectory_command_count": probe.samples.trajectory_command_count,
            "first_joint_state": probe.samples.first_joint_state,
            "joint_state": probe.samples.joint_state,
            "max_joint_delta": round(probe.samples.max_joint_delta, 6),
            "task_status_tail": probe.samples.task_statuses[-8:],
        },
        "promotion_note": (
            "This validates Gazebo camera to detector to programmatic task execution plumbing, including trajectory publication "
            "and Gazebo joint-state movement when the execution checks are enabled. It is a simulation closed-loop smoke, "
            "not a real follower execution, real grasp, or trainable_real dataset claim."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assert Gazebo sim camera -> detector -> task status closed-loop smoke.")
    parser.add_argument("--timeout-sec", type=float, default=45.0)
    parser.add_argument("--image-topic", default="/camera/color/image_raw")
    parser.add_argument("--overlay-image-topic", default="/vision/debug/image_overlay")
    parser.add_argument("--camera-info-topic", default="/camera/color/camera_info")
    parser.add_argument("--detections-topic", default="/detections")
    parser.add_argument("--vision-targets-topic", default="/vision/targets")
    parser.add_argument("--task-status-topic", default="/mes_task_status")
    parser.add_argument("--joint-states-topic", default="/joint_states")
    parser.add_argument("--trajectory-topic", default="/joint_trajectory_controller/joint_trajectory")
    parser.add_argument("--detection-backend", default="gazebo_color")
    parser.add_argument("--required-detection-source", default="")
    parser.add_argument("--min-detections", type=int, default=1)
    parser.add_argument("--min-targets", type=int, default=1)
    parser.add_argument("--require-task-close", action="store_true")
    parser.add_argument("--require-trajectory-command", action="store_true")
    parser.add_argument("--require-joint-motion", action="store_true")
    parser.add_argument("--require-overlay-image", action="store_true")
    parser.add_argument("--min-joint-delta", type=float, default=0.03)
    parser.add_argument("--report-path", default="docs/generated/vision-episodes/sim-vision-closed-loop-assertion.json")
    parser.add_argument("--task-request-prefix", default="det-")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    required_source = args.required_detection_source
    if not required_source and args.detection_backend == "gazebo_color":
        required_source = "gazebo_color_detector"
    elif not required_source and args.detection_backend == "yolo":
        required_source = "real_yolo"

    rclpy.init()
    probe = SimVisionClosedLoopProbe(args)
    deadline = time.time() + args.timeout_sec
    checks = {
        "image": False,
        "overlay_image": not args.require_overlay_image,
        "camera_info": False,
        "detection": False,
        "vision_target": False,
        "joint_state": False,
        "task_close": not args.require_task_close,
        "trajectory_command": not args.require_trajectory_command,
        "joint_motion": not args.require_joint_motion,
    }
    try:
        while rclpy.ok() and time.time() < deadline:
            rclpy.spin_once(probe, timeout_sec=0.1)
            checks["image"] = bool(probe.samples.image and probe.samples.image.get("data_len", 0) > 0)
            if args.require_overlay_image:
                checks["overlay_image"] = bool(
                    probe.samples.overlay_image and probe.samples.overlay_image.get("data_len", 0) > 0
                )
            checks["camera_info"] = bool(probe.samples.camera_info)
            checks["detection"] = has_detection(probe.samples.detection, args.min_detections, required_source)
            checks["vision_target"] = has_vision_target(probe.samples.vision_target, args.min_targets)
            checks["joint_state"] = bool(probe.samples.joint_state)
            if args.require_task_close:
                checks["task_close"] = task_closed(probe.samples.task_statuses, args.task_request_prefix)
            if args.require_trajectory_command:
                checks["trajectory_command"] = bool(
                    probe.samples.trajectory_command
                    and probe.samples.trajectory_command.get("point_count", 0) > 0
                )
            if args.require_joint_motion:
                checks["joint_motion"] = probe.samples.max_joint_delta >= args.min_joint_delta
            if all(checks.values()):
                break
    finally:
        status = "passed" if all(checks.values()) else "failed"
        report = build_report(args, probe, status, checks)
        path = Path(args.report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        probe.destroy_node()
        rclpy.shutdown()

    print(json.dumps({"status": status, "checks": checks, "report": str(Path(args.report_path))}, ensure_ascii=False))
    return 0 if status == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
