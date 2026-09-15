#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path

import yaml

from so101_units import apply_urdf_map


DEFAULT_ACTIONS = str(Path(__file__).resolve().parents[1] / "mint_follower_demo/config/action_templates.json")
DEFAULT_MAP = str(Path(__file__).resolve().parent / "so101_official_to_urdf.yaml")
TOPIC = "/joint_trajectory_controller/joint_trajectory"
DEFAULT_LEAD_IN_SEC = 2.0
DEFAULT_SPEED_SCALE = 0.25
DEFAULT_CLAMP_THRESHOLD = 0.05


def convert_positions(raw_positions, source_names, joint_map):
    if list(source_names) != ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]:
        raise ValueError("actions joint_names must use official SO101 order before URDF mapping")
    return apply_urdf_map(raw_positions, joint_map, clamp_enabled=True)


def to_duration(seconds):
    from builtin_interfaces.msg import Duration

    ns = int(round(seconds * 1e9))
    return Duration(sec=ns // 1000000000, nanosec=ns % 1000000000)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--actions-json", default=DEFAULT_ACTIONS)
    parser.add_argument("--joint-map", default=DEFAULT_MAP)
    parser.add_argument("--template", default="product_2_2_exec")
    parser.add_argument("--topic", default=TOPIC)
    parser.add_argument("--frame-delay", type=float, default=0.08)
    parser.add_argument("--lead-in-sec", type=float, default=DEFAULT_LEAD_IN_SEC)
    parser.add_argument("--speed-scale", type=float, default=DEFAULT_SPEED_SCALE)
    parser.add_argument("--clamp-threshold", type=float, default=DEFAULT_CLAMP_THRESHOLD)
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--hold-first-frame", action="store_true")
    parser.add_argument("--hold-duration", type=float, default=5.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.speed_scale <= 0.0:
        raise ValueError("--speed-scale must be greater than 0")
    if args.lead_in_sec < 0.0:
        raise ValueError("--lead-in-sec must be non-negative")
    if args.hold_duration <= 0.0:
        raise ValueError("--hold-duration must be greater than 0")

    with open(args.actions_json, encoding="utf-8") as fh:
        actions = json.load(fh)
    with open(args.joint_map, encoding="utf-8") as fh:
        joint_map = yaml.safe_load(fh)

    source_names = list(actions["joint_names"])
    sequence = list(actions["templates"][args.template])
    if args.max_frames > 0:
        sequence = sequence[: args.max_frames]
    if args.hold_first_frame:
        sequence = sequence[:1]

    joint_names = list(joint_map["joint_order"])
    points = []
    clamp_hits = {name: 0 for name in joint_names}
    for index, frame_name in enumerate(sequence):
        _names, positions, clamped_names = convert_positions(
            actions["waypoints"][frame_name], source_names, joint_map
        )
        for name in clamped_names:
            clamp_hits[name] += 1
        if args.hold_first_frame:
            time_from_start = args.hold_duration
        else:
            time_from_start = args.lead_in_sec + index * args.frame_delay / args.speed_scale
        points.append((positions, time_from_start))

    point_count = len(points)
    blocked = []
    for name in joint_names:
        count = clamp_hits[name]
        ratio = count / max(point_count, 1)
        print(f"[clamp] {name}: {count}/{point_count} = {ratio * 100:.1f}%")
        if ratio > args.clamp_threshold:
            blocked.append((name, count, ratio))

    if blocked:
        details = ", ".join(
            f"{name} {count}/{point_count} ({ratio * 100:.1f}%)"
            for name, count, ratio in blocked
        )
        raise RuntimeError(
            f"clamp too high: {details}. Refusing to publish; fix sign/offset/limits first."
        )

    if args.dry_run:
        mode = "hold-first-frame" if args.hold_first_frame else "full trajectory"
        print(
            f"dry-run ok: {point_count} points, mode={mode}, first point at {points[0][1]:.3f}s, "
            f"speed_scale={args.speed_scale:.3f}"
        )
        return

    import rclpy
    from rclpy.node import Node
    from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

    msg = JointTrajectory()
    msg.joint_names = joint_names
    for positions, time_from_start in points:
        point = JointTrajectoryPoint()
        point.positions = positions
        point.time_from_start = to_duration(time_from_start)
        msg.points.append(point)

    rclpy.init()
    node = Node("mapped_mint_traj_publisher")
    pub = node.create_publisher(JointTrajectory, args.topic, 10)
    node.get_logger().info(f"publishing {len(msg.points)} mapped/clamped points to {args.topic}")
    time.sleep(1.0)
    pub.publish(msg)
    time.sleep(1.0)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
