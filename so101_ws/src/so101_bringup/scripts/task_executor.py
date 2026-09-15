#!/usr/bin/env python3
"""MES task executor for SO-101 demo.

Subscribes `/mes_task_cmd` (JSON string), publishes trajectory commands to
`/joint_trajectory_controller/joint_trajectory`, and publishes task status
events to `/mes_task_status`.
"""

import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import rclpy
import yaml
from action_template_mapping import resolve_step_mapping
from detection_trigger_policy import DetectionTriggerPolicy
from rclpy.node import Node
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory
from task_execution_service import TaskExecutionService
from task_executor_contract import evaluate_command_request
from task_preview_utils import parse_preview_pose
from task_status_publisher import TaskStatusPublisher
from trajectory_builder import (
    build_mapped_trajectory_message,
    create_single_point_trajectory_message,
)


DEFAULT_JOINTS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]


class TaskExecutor(Node):
    def __init__(self) -> None:
        super().__init__("so101_task_executor")
        self.declare_parameter("waypoints_file", "")
        self.declare_parameter("trajectory_topic", "/joint_trajectory_controller/joint_trajectory")
        self.declare_parameter("step_duration_sec", 1.8)
        self.declare_parameter("command_execution_enabled", True)
        self.declare_parameter("detection_trigger_enabled", True)
        self.declare_parameter("detection_confidence_threshold", 0.5)
        self.declare_parameter("detection_trigger_cooldown_sec", 8.0)
        self.declare_parameter(
            "detection_template_map_json",
            '{"red":"pick_place_red","blue":"pick_place_blue"}',
        )

        waypoints_file = self.get_parameter("waypoints_file").get_parameter_value().string_value
        if not waypoints_file:
            raise RuntimeError("Parameter 'waypoints_file' must be set.")

        self.waypoints, self.templates = self._load_plan(waypoints_file)
        self.joint_names = self._load_joint_names()
        self.step_duration = float(
            self.get_parameter("step_duration_sec").get_parameter_value().double_value
        )
        self.command_execution_enabled = bool(
            self.get_parameter("command_execution_enabled").get_parameter_value().bool_value
        )
        self.detection_trigger_enabled = bool(
            self.get_parameter("detection_trigger_enabled").get_parameter_value().bool_value
        )
        self.detection_confidence_threshold = float(
            self.get_parameter("detection_confidence_threshold")
            .get_parameter_value()
            .double_value
        )
        self.detection_trigger_cooldown = float(
            self.get_parameter("detection_trigger_cooldown_sec")
            .get_parameter_value()
            .double_value
        )
        self.detection_template_map = self._load_detection_template_map(
            self.get_parameter("detection_template_map_json")
            .get_parameter_value()
            .string_value
        )

        traj_topic = self.get_parameter("trajectory_topic").get_parameter_value().string_value
        self.traj_pub = self.create_publisher(JointTrajectory, traj_topic, 10)
        self.status_pub = self.create_publisher(String, "/mes_task_status", 20)
        self.cmd_sub = self.create_subscription(String, "/mes_task_cmd", self._on_command, 20)
        self.det_sub = self.create_subscription(String, "/detections", self._on_detection, 20)

        self._status_writer = TaskStatusPublisher(
            publish_text=lambda text: self.status_pub.publish(String(data=text)),
            log_info=self.get_logger().info,
        )
        self._detection_policy = DetectionTriggerPolicy(
            enabled=self.detection_trigger_enabled,
            threshold=self.detection_confidence_threshold,
            cooldown_sec=self.detection_trigger_cooldown,
            template_map=self.detection_template_map,
        )
        self._execution_service = TaskExecutionService(
            templates=self.templates,
            waypoints=self.waypoints,
            joint_names=self.joint_names,
            default_step_duration=self.step_duration,
            resolve_step_mapping=resolve_step_mapping,
            parse_preview_pose=parse_preview_pose,
            publish_status=self._publish_status,
            publish_trajectory=self.traj_pub.publish,
            sleep_fn=time.sleep,
            build_mapped_trajectory_message=build_mapped_trajectory_message,
            build_single_point_trajectory_message=create_single_point_trajectory_message,
            select_detection_category=lambda candidates, expected_category="": self._detection_policy.select_category(
                candidates,
                expected_category=expected_category,
            ),
        )

        self._lock = threading.Lock()
        self._busy = False
        self._last_detection = {}
        self.get_logger().info(f"Task executor ready. Loaded templates: {list(self.templates.keys())}")
        self.get_logger().info(
            "Command gate: enabled=%s; detection trigger: enabled=%s, conf>=%.2f, cooldown=%.1fs, map=%s"
            % (
                self.command_execution_enabled,
                self.detection_trigger_enabled,
                self.detection_confidence_threshold,
                self.detection_trigger_cooldown,
                self.detection_template_map,
            )
        )

    def _load_detection_template_map(self, map_json: str) -> Dict[str, str]:
        try:
            payload = json.loads(map_json)
            if not isinstance(payload, dict):
                raise ValueError("detection_template_map_json must be JSON object.")
            cleaned = {}
            for k, v in payload.items():
                key = str(k).strip().lower()
                template_id = str(v).strip()
                if key and template_id:
                    cleaned[key] = template_id
            return cleaned
        except Exception as exc:
            self.get_logger().warn(
                f"Invalid detection_template_map_json, fallback to default mapping. detail={exc}"
            )
            return {"red": "pick_place_red", "blue": "pick_place_blue"}

    def _load_joint_names(self):
        if "joint_names" in self.waypoints:
            return self.waypoints["joint_names"]
        return DEFAULT_JOINTS

    def _load_plan(self, file_path: str):
        content = yaml.safe_load(Path(file_path).read_text(encoding="utf-8"))
        if not isinstance(content, dict) or "waypoints" not in content:
            raise RuntimeError("Invalid waypoints yaml: missing 'waypoints'")
        waypoints = content["waypoints"]
        templates = content.get("action_templates", {})
        if "pick_place_default" not in templates:
            templates["pick_place_default"] = {
                "detection_required": False,
                "sequence": ["home"],
            }
        return content, templates

    def _on_detection(self, msg: String):
        try:
            self._last_detection = json.loads(msg.data)
        except json.JSONDecodeError:
            self._last_detection = {"raw": msg.data}
            return

        self._try_trigger_from_detection()

    def _extract_detection_candidates(self) -> List[Tuple[str, float]]:
        data = self._last_detection
        if not isinstance(data, dict):
            return []

        # Backward compatible with mock payload: {"category":"red","confidence":0.95}
        if "category" in data:
            category = str(data.get("category", "")).strip().lower()
            try:
                confidence = float(data.get("confidence", 1.0))
            except Exception:
                confidence = 1.0
            return [(category, confidence)] if category else []

        detections = data.get("detections", [])
        if not isinstance(detections, list):
            return []

        results = []
        for item in detections:
            if not isinstance(item, dict):
                continue
            category = str(item.get("category", "")).strip().lower()
            if not category:
                continue
            try:
                confidence = float(item.get("confidence", 0.0))
            except Exception:
                confidence = 0.0
            results.append((category, confidence))
        return results

    def _select_detection_category(self, expected_category: str = "") -> Optional[str]:
        candidates = self._extract_detection_candidates()
        if not candidates:
            return None

        threshold = self.detection_confidence_threshold
        matched = []
        for category, confidence in candidates:
            if confidence < threshold:
                continue
            if expected_category and category != expected_category:
                continue
            matched.append((category, confidence))

        if not matched:
            return None
        matched.sort(key=lambda item: item[1], reverse=True)
        return matched[0][0]

    def _try_trigger_from_detection(self) -> None:
        with self._lock:
            if not self.command_execution_enabled:
                return
            decision = self._detection_policy.try_trigger(
                self._extract_detection_candidates(),
                busy=self._busy,
                now=time.time(),
            )
            if decision is None:
                return
            self._busy = True

        self._publish_status(
            decision.request_id,
            "执行中",
            "DETECTION_TRIGGER",
            f"category={decision.category} -> template={decision.template_id}",
        )
        th = threading.Thread(
            target=self._execute_service_request,
            args=(decision.request_id, decision.template_id, None),
            daemon=True,
        )
        th.start()

    def _publish_status(self, request_id: str, state: str, code: str, message: str):
        self._status_writer.emit(request_id, state, code, message)

    def _execute_service_request(self, request_id: str, template_id: str, params: Optional[Dict] = None):
        try:
            self._execution_service.execute(
                request_id,
                template_id,
                params=params,
                detection_candidates=self._extract_detection_candidates(),
                detection_snapshot=self._last_detection,
            )
        except Exception as exc:
            self._publish_status(request_id, "异常", "EXECUTION_ERROR", str(exc))
            self.get_logger().error(f"Task failed: {exc}")
        finally:
            with self._lock:
                self._busy = False

    def _on_command(self, msg: String):
        try:
            payload = json.loads(msg.data)
            request_id = payload.get("requestId") or f"req-{int(time.time() * 1000)}"
            template_id = payload.get("actionTemplateId", "pick_place_default")
            params = payload.get("params", {})
        except Exception:
            self._publish_status("unknown", "异常", "BAD_REQUEST", "Invalid JSON command")
            return

        if not self.command_execution_enabled:
            decision = evaluate_command_request(
                request_id=request_id,
                template_id=template_id,
                params=params,
                command_execution_enabled=self.command_execution_enabled,
                busy=False,
            )
            status = decision["status"]
            self._publish_status(
                status["requestId"],
                status["state"],
                status["code"],
                status["message"],
            )
            return

        with self._lock:
            decision = evaluate_command_request(
                request_id=request_id,
                template_id=template_id,
                params=params,
                command_execution_enabled=True,
                busy=self._busy,
            )
            if not decision["accepted"]:
                status = decision["status"]
                self._publish_status(
                    status["requestId"],
                    status["state"],
                    status["code"],
                    status["message"],
                )
                return
            self._busy = True

        th = threading.Thread(
            target=self._execute_service_request,
            args=(request_id, template_id, params),
            daemon=True,
        )
        th.start()


def main():
    rclpy.init()
    node = TaskExecutor()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
