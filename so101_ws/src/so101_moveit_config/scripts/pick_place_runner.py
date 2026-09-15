#!/usr/bin/env python3
import argparse
import time
from pathlib import Path

import rclpy
import yaml
from rclpy.action import ActionClient
from rclpy.node import Node

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint


SUCCESS = 1


class PickPlaceRunner(Node):
    def __init__(self, action_name: str):
        super().__init__("pick_place_runner")
        self._client = ActionClient(self, MoveGroup, action_name)

    def wait_for_server(self, timeout_sec: float) -> bool:
        return self._client.wait_for_server(timeout_sec=timeout_sec)

    def execute_joint_goal(
        self,
        group_name: str,
        joint_names: list[str],
        positions: list[float],
        allowed_planning_time: float,
        vel_scale: float,
        acc_scale: float,
        planning_attempts: int,
        planner_id: str,
    ) -> tuple[bool, int, float, object]:
        goal_msg = MoveGroup.Goal()
        req = goal_msg.request
        req.group_name = group_name
        req.num_planning_attempts = planning_attempts
        req.allowed_planning_time = allowed_planning_time
        req.max_velocity_scaling_factor = vel_scale
        req.max_acceleration_scaling_factor = acc_scale
        req.pipeline_id = "ompl"
        req.planner_id = planner_id

        constraints = Constraints()
        constraints.name = "joint_target"
        for jn, pos in zip(joint_names, positions):
            jc = JointConstraint()
            jc.joint_name = jn
            jc.position = float(pos)
            jc.tolerance_above = 0.02
            jc.tolerance_below = 0.02
            jc.weight = 1.0
            constraints.joint_constraints.append(jc)
        req.goal_constraints = [constraints]

        goal_msg.planning_options.plan_only = False
        goal_msg.planning_options.look_around = False
        goal_msg.planning_options.replan = True
        goal_msg.planning_options.replan_attempts = 1
        goal_msg.planning_options.replan_delay = 0.2

        send_future = self._client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_future)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            return False, -999, 0.0, None

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result()
        if result is None:
            return False, -998, 0.0, None

        err = int(result.result.error_code.val)
        planning_time = float(result.result.planning_time)
        return err == SUCCESS, err, planning_time, result.result


def extract_planned_points(move_group_result, max_points: int) -> dict:
    traj = move_group_result.planned_trajectory.joint_trajectory
    points = []
    for idx, p in enumerate(traj.points):
        if idx >= max_points:
            break
        t = float(p.time_from_start.sec) + float(p.time_from_start.nanosec) * 1e-9
        points.append(
            {
                "t": round(t, 6),
                "positions": [round(float(x), 6) for x in p.positions],
            }
        )
    return {
        "joint_names": list(traj.joint_names),
        "points": points,
    }


def load_pick_place_sequence(waypoints_yaml: Path, action_template: str) -> tuple[list[str], dict[str, list[float]]]:
    data = yaml.safe_load(waypoints_yaml.read_text(encoding="utf-8"))
    joint_names = list(data["joint_names"])
    waypoint_map = dict(data["waypoints"])
    templates = data.get("action_templates", {})
    if action_template not in templates:
        raise ValueError(f"action_template '{action_template}' not found in {waypoints_yaml}")
    sequence = list(templates[action_template]["sequence"])

    for step in sequence:
        if step not in waypoint_map:
            raise ValueError(f"sequence step '{step}' not found in waypoints")
        if len(waypoint_map[step]) != len(joint_names):
            raise ValueError(f"waypoint '{step}' joint count mismatch")

    return joint_names, {name: waypoint_map[name] for name in sequence}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MoveIt2 pick-place sequence and collect success metrics.")
    parser.add_argument("--group", default="arm")
    parser.add_argument("--action-name", default="/move_action")
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--retry-per-waypoint", type=int, default=2)
    parser.add_argument("--planning-time", type=float, default=2.0)
    parser.add_argument("--velocity-scale", type=float, default=0.3)
    parser.add_argument("--acceleration-scale", type=float, default=0.3)
    parser.add_argument("--planning-attempts", type=int, default=5)
    parser.add_argument("--planner-id", default="RRTConnectkConfigDefault")
    parser.add_argument(
        "--waypoints-yaml",
        default="/home/muqiao/dev/ros2/workspaces/so101_ws/src/so101_bringup/config/waypoints.yaml",
    )
    parser.add_argument("--action-template", default="pick_place_default")
    parser.add_argument(
        "--export-mapping-yaml",
        default="",
        help="Optional output file path. If set, export per-step planned trajectories.",
    )
    parser.add_argument(
        "--export-max-points",
        type=int,
        default=20,
        help="Max number of planned trajectory points exported per step.",
    )
    args = parser.parse_args()

    waypoints_path = Path(args.waypoints_yaml)
    joint_names, ordered_waypoints = load_pick_place_sequence(waypoints_path, args.action_template)
    step_names = list(ordered_waypoints.keys())

    rclpy.init()
    node = PickPlaceRunner(args.action_name)

    if not node.wait_for_server(timeout_sec=20.0):
        node.get_logger().error(f"MoveGroup action server '{args.action_name}' not available.")
        node.destroy_node()
        rclpy.shutdown()
        return 2

    total = 0
    passed = 0
    export_data = {
        "source_action_template": args.action_template,
        "joint_names": joint_names,
        "group": args.group,
        "iterations": args.iterations,
        "steps": {},
    }

    for i in range(1, args.iterations + 1):
        node.get_logger().info(f"=== Iteration {i}/{args.iterations} ===")
        iteration_ok = True
        for step in step_names:
            target = ordered_waypoints[step]
            step_ok = False
            for trial in range(1, args.retry_per_waypoint + 1):
                ok, err, plan_t, move_group_result = node.execute_joint_goal(
                    group_name=args.group,
                    joint_names=joint_names,
                    positions=target,
                    allowed_planning_time=args.planning_time,
                    vel_scale=args.velocity_scale,
                    acc_scale=args.acceleration_scale,
                    planning_attempts=args.planning_attempts,
                    planner_id=args.planner_id,
                )
                if ok:
                    node.get_logger().info(
                        f"[{step}] pass on trial {trial}, planning_time={plan_t:.3f}s"
                    )
                    export_data["steps"][step] = {
                        "target_positions": [round(float(x), 6) for x in target],
                        "planning_time": round(plan_t, 6),
                        "planned_trajectory": extract_planned_points(
                            move_group_result, args.export_max_points
                        ),
                    }
                    step_ok = True
                    break
                node.get_logger().warn(f"[{step}] fail on trial {trial}, error_code={err}")
                time.sleep(0.2)

            total += 1
            if step_ok:
                passed += 1
            else:
                iteration_ok = False
                node.get_logger().error(f"[{step}] failed after {args.retry_per_waypoint} trials")
                break

        if iteration_ok:
            node.get_logger().info(f"Iteration {i} finished successfully")
        else:
            node.get_logger().warn(f"Iteration {i} ended early due to step failure")

    rate = (100.0 * passed / total) if total else 0.0
    node.get_logger().info(f"Summary: step_success={passed}/{total} ({rate:.1f}%)")

    if args.export_mapping_yaml:
        export_path = Path(args.export_mapping_yaml)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_data["summary"] = {
            "step_success": int(passed),
            "step_total": int(total),
            "success_rate": round(rate, 2),
        }
        export_path.write_text(
            yaml.safe_dump(export_data, sort_keys=False, allow_unicode=False),
            encoding="utf-8",
        )
        node.get_logger().info(f"Exported mapping yaml: {export_path}")

    node.destroy_node()
    rclpy.shutdown()
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
