#!/usr/bin/env python3
import argparse
import json
import sys
import time
from pathlib import Path

import rclpy
from gazebo_msgs.msg import ModelStates
from rclpy.node import Node
from sensor_msgs.msg import JointState
from tf2_msgs.msg import TFMessage


EXPECTED_MODELS = {"so101", "work_table", "pick_bin", "place_bin"}
EXPECTED_FRAMES = {"base_link", "shoulder_link", "upper_arm_link", "wrist_link", "gripper_frame_link"}


class SceneCapture(Node):
    def __init__(self, summary_log: Path, timeout_sec: float) -> None:
        super().__init__("gzm001_scene_capture")
        self.summary_log = summary_log
        self.deadline = time.time() + timeout_sec
        self.models_seen = set()
        self.joint_names = set()
        self.frames_seen = set()
        self.complete = False

        self.model_sub = self.create_subscription(ModelStates, "/gazebo/model_states", self.on_models, 10)
        self.joint_sub = self.create_subscription(JointState, "/joint_states", self.on_joint_states, 20)
        self.tf_sub = self.create_subscription(TFMessage, "/tf", self.on_tf, 50)
        self.tf_static_sub = self.create_subscription(TFMessage, "/tf_static", self.on_tf, 50)

    def on_models(self, msg: ModelStates) -> None:
        self.models_seen.update(msg.name)
        self._write_snapshot()
        self._check_complete()

    def on_joint_states(self, msg: JointState) -> None:
        self.joint_names.update(msg.name)
        self._write_snapshot()
        self._check_complete()

    def on_tf(self, msg: TFMessage) -> None:
        for transform in msg.transforms:
            self.frames_seen.add(transform.child_frame_id)
            self.frames_seen.add(transform.header.frame_id)
        self._write_snapshot()
        self._check_complete()

    def _check_complete(self) -> None:
        if EXPECTED_MODELS.issubset(self.models_seen) and self.joint_names and EXPECTED_FRAMES & self.frames_seen:
            self.complete = True

    def _write_snapshot(self) -> None:
        self.summary_log.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "models_seen": sorted(self.models_seen),
            "joint_names": sorted(self.joint_names),
            "frames_seen": sorted(self.frames_seen),
        }
        self.summary_log.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary-log", required=True)
    parser.add_argument("--timeout-sec", type=float, default=40.0)
    args = parser.parse_args()

    summary_log = Path(args.summary_log)
    summary_log.write_text("{}", encoding="utf-8")

    rclpy.init()
    node = SceneCapture(summary_log=summary_log, timeout_sec=args.timeout_sec)
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.2)
            if node.complete:
                node.get_logger().info("scene capture complete")
                break
            if time.time() >= node.deadline:
                node.get_logger().error(
                    "timeout models=%s joints=%d frames=%d"
                    % (sorted(node.models_seen), len(node.joint_names), len(node.frames_seen))
                )
                break
    finally:
        ok = EXPECTED_MODELS.issubset(node.models_seen) and bool(node.joint_names) and bool(EXPECTED_FRAMES & node.frames_seen)
        result = {
            "ok": ok,
            "models_seen": sorted(node.models_seen),
            "joint_names": sorted(node.joint_names),
            "frames_seen": sorted(node.frames_seen),
        }
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        print(json.dumps(result, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
