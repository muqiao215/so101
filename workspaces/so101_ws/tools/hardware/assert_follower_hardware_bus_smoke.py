#!/usr/bin/env python3
"""Assert SO101 follower hardware bus and optional uncalibrated raw-hold command.

This probe expects `so101_follower_trajectory_adapter.py` to be running against
real hardware. It can verify connection-only status or publish one trajectory
that the adapter turns into a raw hold when uncalibrated raw hold is enabled.
"""

import argparse
import json
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


JOINT_NAMES = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]


class FollowerHardwareProbe(Node):
    def __init__(self, trajectory_topic: str, status_topic: str) -> None:
        super().__init__("follower_hardware_bus_probe")
        self.publisher = self.create_publisher(JointTrajectory, trajectory_topic, 10)
        self.create_subscription(String, status_topic, self._on_status, 20)
        self.statuses = []

    def _on_status(self, msg: String) -> None:
        try:
            self.statuses.append(json.loads(msg.data))
        except json.JSONDecodeError:
            self.statuses.append({"raw": msg.data})

    def publish_hold_probe(self) -> None:
        msg = JointTrajectory()
        msg.joint_names = list(JOINT_NAMES)
        point = JointTrajectoryPoint()
        # The adapter ignores these normalized targets in uncalibrated raw-hold mode.
        point.positions = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        point.time_from_start.sec = 1
        msg.points.append(point)
        self.publisher.publish(msg)


def run_probe(args: argparse.Namespace) -> dict:
    rclpy.init()
    node = FollowerHardwareProbe(args.trajectory_topic, args.status_topic)
    try:
        deadline = time.monotonic() + args.timeout_sec
        publish_sent = False
        while time.monotonic() < deadline:
            if args.send_raw_hold and not publish_sent and any(
                status.get("hardware_bus_ready") is True for status in node.statuses
            ):
                node.publish_hold_probe()
                publish_sent = True
            rclpy.spin_once(node, timeout_sec=0.1)
            latest = node.statuses[-1] if node.statuses else {}
            if latest.get("hardware_bus_ready") is True:
                if not args.send_raw_hold:
                    break
                if int(latest.get("raw_hold_command_count") or 0) >= 1:
                    break

        latest = node.statuses[-1] if node.statuses else {}
        connected = latest.get("hardware_bus_ready") is True and latest.get("connected") is True
        raw_hold_ok = (not args.send_raw_hold) or int(latest.get("raw_hold_command_count") or 0) >= 1
        passed = bool(
            latest.get("schema") == "so101_real_follower_status_v1"
            and connected
            and latest.get("dry_run") is False
            and raw_hold_ok
        )
        return {
            "schema": "so101_follower_hardware_bus_smoke.v1",
            "passed": passed,
            "send_raw_hold": args.send_raw_hold,
            "status_count": len(node.statuses),
            "latest_status": latest,
            "boundary": (
                "hardware bus / optional raw-hold smoke only; "
                "not calibrated trajectory execution and not grasp success"
            ),
        }
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectory-topic", default="/joint_trajectory_controller/joint_trajectory")
    parser.add_argument("--status-topic", default="/real_follower/status")
    parser.add_argument("--timeout-sec", type=float, default=8.0)
    parser.add_argument("--send-raw-hold", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()

    report = run_probe(args)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report_path:
        path = Path(args.report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
