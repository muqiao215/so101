#!/usr/bin/env python3
"""Assert the ROS trajectory -> SO101 follower adapter software link.

This smoke test runs without touching hardware by expecting the follower adapter
to be launched with `dry_run:=true`.
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


class FollowerSoftwareLinkProbe(Node):
    def __init__(self, trajectory_topic: str, status_topic: str) -> None:
        super().__init__("follower_software_link_probe")
        self.publisher = self.create_publisher(JointTrajectory, trajectory_topic, 10)
        self.create_subscription(String, status_topic, self._on_status, 20)
        self.statuses = []

    def _on_status(self, msg: String) -> None:
        try:
            self.statuses.append(json.loads(msg.data))
        except json.JSONDecodeError:
            self.statuses.append({"raw": msg.data})

    def publish_probe_trajectory(self) -> None:
        msg = JointTrajectory()
        msg.joint_names = list(JOINT_NAMES)
        point = JointTrajectoryPoint()
        point.positions = [0.03, -0.04, 0.06, -0.03, 0.02, 0.4]
        point.time_from_start.sec = 1
        msg.points.append(point)
        self.publisher.publish(msg)


def run_probe(args: argparse.Namespace) -> dict:
    rclpy.init()
    node = FollowerSoftwareLinkProbe(args.trajectory_topic, args.status_topic)
    try:
        deadline = time.monotonic() + args.timeout_sec
        last_publish = 0.0
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now - last_publish >= 0.5:
                node.publish_probe_trajectory()
                last_publish = now
            rclpy.spin_once(node, timeout_sec=0.1)
            if any(int(status.get("sent_command_count") or 0) >= 1 for status in node.statuses):
                break
        latest = node.statuses[-1] if node.statuses else {}
        passed = bool(
            latest.get("schema") == "so101_real_follower_status_v1"
            and latest.get("software_ready") is True
            and int(latest.get("received_trajectory_count") or 0) >= 1
            and int(latest.get("sent_command_count") or 0) >= 1
            and isinstance(latest.get("last_sent_action"), dict)
            and latest["last_sent_action"]
        )
        return {
            "schema": "so101_follower_software_link_smoke.v1",
            "passed": passed,
            "status_count": len(node.statuses),
            "latest_status": latest,
            "boundary": "dry_run software link only; not real follower closed loop and not real grasp",
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
