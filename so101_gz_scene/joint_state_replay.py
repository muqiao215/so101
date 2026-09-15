#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path

import rclpy
import yaml
from rclpy.node import Node
from sensor_msgs.msg import JointState

from so101_units import apply_urdf_map


DEFAULT_ACTIONS = str(Path(__file__).resolve().parents[1] / "mint_follower_demo/config/action_templates.json")
DEFAULT_MAP = str(Path(__file__).resolve().parent / "so101_official_to_urdf.yaml")


def load_actions(path: str):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise RuntimeError("action templates json must be an object")
    return data


def load_map(path: str):
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise RuntimeError("joint map yaml must be an object")
    return data


def convert_positions(raw_positions, source_names, joint_map):
    if list(source_names) != ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]:
        raise ValueError("actions joint_names must use official SO101 order before URDF mapping")
    names, positions, _clamped = apply_urdf_map(raw_positions, joint_map, clamp_enabled=True)
    return names, positions


class JointStateReplay(Node):
    def __init__(self, args):
        super().__init__("mint_joint_state_replay")
        self.publisher = self.create_publisher(JointState, "/joint_states", 10)
        self.actions = load_actions(args.actions_json)
        self.joint_map = load_map(args.joint_map)
        self.source_names = list(self.actions["joint_names"])
        self.waypoints = self.actions["waypoints"]
        self.sequence = list(self.actions["templates"][args.template])
        if args.start_frame > 1:
            self.sequence = self.sequence[args.start_frame - 1 :]
        if args.max_frames > 0:
            self.sequence = self.sequence[: args.max_frames]
        if args.frame_index > 0:
            frame_idx = min(args.frame_index - 1, len(self.sequence) - 1)
            self.sequence = [self.sequence[frame_idx]]
        self.fps = max(float(args.fps), 0.1)
        self.loop = bool(args.loop)
        self.index = 0
        self.get_logger().info(
            f"Loaded template={args.template}, frames={len(self.sequence)}, fps={self.fps}, loop={self.loop}"
        )
        self.timer = self.create_timer(1.0 / self.fps, self.tick)

    def tick(self):
        if self.index >= len(self.sequence):
            self.index = 0 if self.loop else len(self.sequence) - 1
        frame_index = self.index
        frame_name = self.sequence[frame_index]
        raw_positions = self.waypoints[frame_name]
        names, positions = convert_positions(raw_positions, self.source_names, self.joint_map)

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = names
        msg.position = positions
        self.publisher.publish(msg)

        if frame_index == 0 or frame_index % 20 == 0:
            self.get_logger().info(f"{frame_index + 1}/{len(self.sequence)} {frame_name}: {positions}")
        if self.loop or self.index < len(self.sequence):
            self.index += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--actions-json", default=DEFAULT_ACTIONS)
    parser.add_argument("--joint-map", default=DEFAULT_MAP)
    parser.add_argument("--template", default="product_2_2_exec")
    parser.add_argument("--frame-index", type=int, default=1, help="1-based frame index. 0 plays the sequence.")
    parser.add_argument("--start-frame", type=int, default=1, help="1-based frame to start sequence playback.")
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--fps", type=float, default=2.0)
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args()

    rclpy.init()
    node = JointStateReplay(args)
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
