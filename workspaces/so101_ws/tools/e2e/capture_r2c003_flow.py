#!/usr/bin/env python3
import argparse
import json
import sys
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory


class FlowCapture(Node):
    def __init__(self, status_log: Path, traj_log: Path, timeout_sec: float) -> None:
        super().__init__("r2c003_flow_capture")
        self.status_log = status_log
        self.traj_log = traj_log
        self.deadline = time.time() + timeout_sec
        self.timeout_sec = timeout_sec
        self.started = False
        self.ok = False
        self.step_count = 0
        self.traj_count = 0
        self.complete = False
        self.status_sub = self.create_subscription(String, "/mes_task_status", self.on_status, 20)
        self.traj_sub = self.create_subscription(
            JointTrajectory,
            "/joint_trajectory_controller/joint_trajectory",
            self.on_traj,
            20,
        )

    def on_status(self, msg: String) -> None:
        self.status_log.parent.mkdir(parents=True, exist_ok=True)
        with self.status_log.open("a", encoding="utf-8") as f:
            f.write(msg.data + "\n")
        try:
            payload = json.loads(msg.data)
        except Exception:
            return
        code = str(payload.get("code", "")).strip().upper()
        if code == "STARTED":
            self.started = True
        elif code == "STEP":
            self.step_count += 1
        elif code == "OK":
            self.ok = True
        self._check_complete()

    def on_traj(self, msg: JointTrajectory) -> None:
        self.traj_count += 1
        payload = {
            "joint_names": list(msg.joint_names),
            "point_count": len(msg.points),
            "points": [
                {
                    "positions": list(point.positions),
                    "time_from_start": {
                        "sec": int(point.time_from_start.sec),
                        "nanosec": int(point.time_from_start.nanosec),
                    },
                }
                for point in msg.points[:1]
            ],
        }
        self.traj_log.parent.mkdir(parents=True, exist_ok=True)
        with self.traj_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._check_complete()

    def _check_complete(self) -> None:
        if self.started and self.ok and self.step_count >= 8 and self.traj_count >= 1:
            self.get_logger().info("capture complete")
            self.complete = True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status-log", required=True)
    parser.add_argument("--traj-log", required=True)
    parser.add_argument("--timeout-sec", type=float, default=30.0)
    args = parser.parse_args()

    status_log = Path(args.status_log)
    traj_log = Path(args.traj_log)
    status_log.write_text("", encoding="utf-8")
    traj_log.write_text("", encoding="utf-8")

    rclpy.init()
    node = FlowCapture(status_log=status_log, traj_log=traj_log, timeout_sec=args.timeout_sec)
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.2)
            if node.complete:
                break
            if time.time() >= node.deadline:
                node.get_logger().error(
                    f"timeout({node.timeout_sec}s) started={node.started} ok={node.ok} step_count={node.step_count} traj_count={node.traj_count}"
                )
                break
    finally:
        ok = node.started and node.ok and node.step_count >= 8 and node.traj_count >= 1
        summary = {
            "started": node.started,
            "ok": node.ok,
            "step_count": node.step_count,
            "traj_count": node.traj_count,
        }
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        print(json.dumps(summary, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
