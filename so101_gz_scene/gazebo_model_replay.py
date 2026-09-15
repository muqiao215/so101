#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path

import rclpy
import yaml
from gazebo_msgs.srv import SetModelConfiguration
from rclpy.node import Node
from sensor_msgs.msg import JointState

from so101_units import apply_urdf_map


DEFAULT_ACTIONS = str(Path(__file__).resolve().parents[1] / "mint_follower_demo/config/action_templates.json")
DEFAULT_MAP = str(Path(__file__).resolve().parent / "so101_official_to_urdf.yaml")


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_yaml(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def convert_positions(raw_positions, source_names, joint_map):
    if list(source_names) != ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]:
        raise ValueError("actions joint_names must use official SO101 order before URDF mapping")
    names, positions, _clamped = apply_urdf_map(raw_positions, joint_map, clamp_enabled=True)
    return names, positions


class GazeboModelReplay(Node):
    def __init__(self, args):
        super().__init__("gazebo_model_replay")
        self.args = args
        self.client = self.create_client(SetModelConfiguration, "/gazebo/set_model_configuration")
        self.joint_pub = self.create_publisher(JointState, "/joint_states", 10)

        actions = load_json(args.actions_json)
        self.joint_map = load_yaml(args.joint_map)
        self.source_names = list(actions["joint_names"])
        sequence = list(actions["templates"][args.template])
        if args.max_frames > 0:
            sequence = sequence[: args.max_frames]
        self.frames = [actions["waypoints"][name] for name in sequence]
        self.frame_names = sequence
        self.get_logger().info(
            f"loaded template={args.template}, frames={len(self.frames)}, fps={args.fps}, model={args.model}"
        )

    def wait_for_service(self):
        self.get_logger().info("waiting for /gazebo/set_model_configuration ...")
        if not self.client.wait_for_service(timeout_sec=self.args.service_timeout):
            raise RuntimeError("/gazebo/set_model_configuration is not available")

    def apply_frame(self, frame_idx):
        names, positions = convert_positions(self.frames[frame_idx], self.source_names, self.joint_map)

        req = SetModelConfiguration.Request()
        req.model_name = self.args.model
        req.urdf_param_name = ""
        req.joint_names = names
        req.joint_positions = positions

        future = self.client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
        if not future.done():
            raise RuntimeError("set_model_configuration timed out")
        result = future.result()
        if result is None or not result.success:
            message = "" if result is None else result.status_message
            raise RuntimeError(f"set_model_configuration failed: {message}")

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = names
        msg.position = positions
        self.joint_pub.publish(msg)

        if frame_idx == 0 or frame_idx % 20 == 0:
            self.get_logger().info(f"{frame_idx + 1}/{len(self.frames)} {self.frame_names[frame_idx]}: {positions}")

    def replay_once(self):
        self.wait_for_service()
        period = 1.0 / max(float(self.args.fps), 0.1)
        for idx in range(len(self.frames)):
            start = time.monotonic()
            self.apply_frame(idx)
            elapsed = time.monotonic() - start
            if elapsed < period:
                time.sleep(period - elapsed)
        self.get_logger().info("replay complete")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--actions-json", default=DEFAULT_ACTIONS)
    parser.add_argument("--joint-map", default=DEFAULT_MAP)
    parser.add_argument("--template", default="product_2_2_exec")
    parser.add_argument("--model", default="follower_arm")
    parser.add_argument("--fps", type=float, default=12.5)
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--service-timeout", type=float, default=60.0)
    args = parser.parse_args()

    rclpy.init()
    node = GazeboModelReplay(args)
    try:
        node.replay_once()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
