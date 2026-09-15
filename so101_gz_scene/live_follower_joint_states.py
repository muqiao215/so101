#!/usr/bin/env python3
import argparse
import json
import math
import sys
import time
from pathlib import Path

import yaml

from so101_units import (
    JOINT_NAMES,
    STS_MAX_RESOLUTION,
    apply_urdf_map,
    format_values,
    raw_to_lerobot_degrees,
    raw_to_lerobot_normalized,
)

DEFAULT_DEMO_ROOT = Path(__file__).resolve().parents[1] / "mint_follower_demo"
DEFAULT_JOINT_MAP = Path(__file__).resolve().parent / "so101_official_to_urdf.yaml"


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_demo_runtime(demo_root):
    sys.path.insert(0, str(demo_root))
    from app import (  # pylint: disable=import-error,import-outside-toplevel
        NativeFeetechSTSBus,
        raw_present_to_manual_positions,
    )

    return NativeFeetechSTSBus, raw_present_to_manual_positions


def raw_to_motor_source_positions(raw_by_id, calibration, sts_max_resolution):
    positions = []
    for name in JOINT_NAMES:
        cal = calibration[name]
        raw = float(raw_by_id[int(cal["id"])])
        if name == "gripper":
            low = float(cal["range_min"])
            high = float(cal["range_max"])
            positions.append((raw - low) / max(1.0, high - low))
        else:
            mid = (float(cal["range_min"]) + float(cal["range_max"])) / 2.0
            positions.append((raw - mid) * 2.0 * math.pi / float(sts_max_resolution))
    return positions


def source_positions(raw_by_id, calibration, serial_mapping, input_space, raw_present_to_manual_positions):
    if input_space == "official-normalized":
        return raw_to_lerobot_normalized(raw_by_id, calibration)
    if input_space == "official-degrees":
        return raw_to_lerobot_degrees(raw_by_id, calibration)
    if input_space == "motor":
        return raw_to_motor_source_positions(raw_by_id, calibration, STS_MAX_RESOLUTION)
    observation = {"present_positions": {str(k): int(v) for k, v in raw_by_id.items()}}
    positions = raw_present_to_manual_positions(observation, calibration, serial_mapping)
    if positions is None:
        raise RuntimeError("missing one or more follower present position values")
    return positions

def main():
    parser = argparse.ArgumentParser(
        description="Read the physical SO101 follower and publish mapped joint_states for RViz."
    )
    parser.add_argument("--demo-root", default=str(DEFAULT_DEMO_ROOT))
    parser.add_argument("--serial-config", default="")
    parser.add_argument("--calibration", default="")
    parser.add_argument("--joint-map", default=str(DEFAULT_JOINT_MAP))
    parser.add_argument(
        "--input-space",
        choices=["official-normalized", "official-degrees", "manual", "motor"],
        default="official-normalized",
    )
    parser.add_argument("--rate", type=float, default=10.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--no-scan", action="store_true")
    parser.add_argument("--no-clamp", action="store_true")
    parser.add_argument("--print-every", type=float, default=1.0)
    args = parser.parse_args()

    demo_root = Path(args.demo_root).resolve()
    serial_config_path = Path(args.serial_config) if args.serial_config else demo_root / "config" / "serial_config.json"
    serial_config = load_json(serial_config_path)
    calibration_path = Path(args.calibration) if args.calibration else demo_root / serial_config.get(
        "calibration_file", "config/follower_calibration.json"
    )
    calibration = load_json(calibration_path)
    with open(args.joint_map, encoding="utf-8") as fh:
        joint_map = yaml.safe_load(fh)

    NativeFeetechSTSBus, raw_present_to_manual_positions = load_demo_runtime(demo_root)

    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import JointState

    ids = [int(calibration[name]["id"]) for name in JOINT_NAMES]
    serial_mapping = serial_config.get("mapping", {})
    bus = NativeFeetechSTSBus(serial_config)
    bus.connect()
    try:
        if not args.no_scan:
            found = bus.scan_expected(ids)
            missing = [motor_id for motor_id in ids if motor_id not in found]
            if missing:
                raise RuntimeError("missing follower motor IDs: %s; found=%s" % (missing, found))

        rclpy.init()
        node = Node("so101_live_follower_joint_state_bridge")
        pub = node.create_publisher(JointState, "/joint_states", 10)
        period = 1.0 / max(0.1, float(args.rate))
        next_print = 0.0
        node.get_logger().info(
            "publishing /joint_states from %s, input_space=%s, joint_map=%s"
            % (serial_config.get("port"), args.input_space, args.joint_map)
        )
        while rclpy.ok():
            raw_by_id = bus.read_present_positions(ids)
            source = source_positions(
                raw_by_id,
                calibration,
                serial_mapping,
                args.input_space,
                raw_present_to_manual_positions,
            )
            names, positions, clamped = apply_urdf_map(source, joint_map, clamp_enabled=not args.no_clamp)

            msg = JointState()
            msg.header.stamp = node.get_clock().now().to_msg()
            msg.name = names
            msg.position = positions
            pub.publish(msg)

            now = time.time()
            if args.print_every > 0 and now >= next_print:
                raw_list = [raw_by_id[int(calibration[name]["id"])] for name in JOINT_NAMES]
                suffix = " clamped=%s" % ",".join(clamped) if clamped else ""
                node.get_logger().info(
                    "raw=%s source=%s urdf=%s%s"
                    % (raw_list, format_values(source), format_values(positions), suffix)
                )
                next_print = now + float(args.print_every)

            if args.once:
                break
            rclpy.spin_once(node, timeout_sec=0.0)
            time.sleep(period)
    finally:
        try:
            bus.disconnect()
        finally:
            if "rclpy" in sys.modules and rclpy.ok():
                rclpy.shutdown()


if __name__ == "__main__":
    main()
