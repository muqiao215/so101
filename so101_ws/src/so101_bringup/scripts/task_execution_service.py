#!/usr/bin/env python3
"""Pure task execution flow separated from ROS node boilerplate."""

from typing import Callable, Dict, List, Optional, Sequence, Tuple


DetectionCandidate = Tuple[str, float]


def _default_build_mapped_trajectory_message(
    _step_mapping: Dict,
    _default_joint_names: Optional[Sequence[str]] = None,
) -> Optional[Tuple[object, float]]:
    return None


def _default_build_single_point_trajectory_message(
    joint_names: Sequence[str],
    positions: Sequence[float],
    duration_sec: float,
) -> object:
    return {
        "joint_names": list(joint_names),
        "positions": [float(value) for value in positions],
        "duration_sec": float(duration_sec),
    }


def _default_select_detection_category(
    candidates: Sequence[DetectionCandidate],
    expected_category: str,
) -> Optional[str]:
    normalized_expected = str(expected_category).strip().lower()
    for category, _confidence in candidates:
        normalized_category = str(category).strip().lower()
        if not normalized_expected or normalized_category == normalized_expected:
            return normalized_category
    return None


class TaskExecutionService:
    def __init__(
        self,
        *,
        templates: Dict,
        waypoints: Dict,
        joint_names: Sequence[str],
        default_step_duration: float,
        resolve_step_mapping: Callable[[Dict, str, str], Optional[Dict]],
        parse_preview_pose: Callable[[Optional[Dict]], Optional[Dict]],
        publish_status: Callable[..., None],
        publish_trajectory: Callable[[object], None],
        sleep_fn: Callable[[float], None],
        build_mapped_trajectory_message: Callable[[Dict, Optional[Sequence[str]]], Optional[Tuple[object, float]]] = _default_build_mapped_trajectory_message,
        build_single_point_trajectory_message: Callable[[Sequence[str], Sequence[float], float], object] = _default_build_single_point_trajectory_message,
        select_detection_category: Callable[[Sequence[DetectionCandidate], str], Optional[str]] = _default_select_detection_category,
    ) -> None:
        self.templates = templates
        self.waypoints = waypoints
        self.joint_names = list(joint_names)
        self.default_step_duration = float(default_step_duration)
        self.resolve_step_mapping = resolve_step_mapping
        self.parse_preview_pose = parse_preview_pose
        self.publish_status = publish_status
        self.publish_trajectory = publish_trajectory
        self.sleep_fn = sleep_fn
        self.build_mapped_trajectory_message = build_mapped_trajectory_message
        self.build_single_point_trajectory_message = build_single_point_trajectory_message
        self.select_detection_category = select_detection_category

    def _publish_status(self, request_id: str, state: str, code: str, message: str) -> None:
        self.publish_status(
            request_id=request_id,
            state=state,
            code=code,
            message=message,
        )

    def _publish_single_point(self, positions: Sequence[float], duration_sec: float) -> None:
        self.publish_trajectory(
            self.build_single_point_trajectory_message(
                self.joint_names,
                positions,
                duration_sec,
            )
        )

    def _publish_step_trajectory(self, template_id: str, step_name: str, fallback_positions: Sequence[float]) -> float:
        self._publish_single_point(fallback_positions, self.default_step_duration)
        return self.default_step_duration

    def _execute_preview_pose(self, request_id: str, preview_pose: Dict) -> None:
        duration = float(preview_pose["duration_sec"])
        self._publish_status(request_id, "执行中", "STARTED", f"preview={preview_pose['name']}")
        self._publish_single_point(preview_pose["positions"], duration)
        self._publish_status(request_id, "执行中", "STEP", f"1/1 -> {preview_pose['name']}")
        self._publish_status(request_id, "完成", "OK", "Preview pose completed")

    def execute(
        self,
        request_id: str,
        template_id: str,
        params: Optional[Dict] = None,
        *,
        detection_candidates: Optional[Sequence[DetectionCandidate]] = None,
        detection_snapshot: Optional[Dict] = None,
    ) -> None:
        preview_pose = self.parse_preview_pose(params)
        if template_id == "preview_pose" and preview_pose is not None:
            self._execute_preview_pose(request_id, preview_pose)
            return

        template = self.templates.get(template_id, self.templates["pick_place_default"])
        expected_category = str(template.get("expected_category", "")).strip().lower()
        detection_required = bool(template.get("detection_required", False))
        sequence = template.get("sequence", [])
        if not sequence:
            raise RuntimeError(f"Template '{template_id}' has empty sequence.")

        candidates = list(detection_candidates or [])
        if detection_required:
            got = self.select_detection_category(candidates, expected_category)
            if got != expected_category:
                observed = ""
                if isinstance(detection_snapshot, dict):
                    observed = str(detection_snapshot.get("category", "")).strip().lower()
                if not observed and candidates:
                    observed = str(candidates[0][0]).strip().lower()
                self._publish_status(
                    request_id,
                    "异常",
                    "DETECTION_MISMATCH",
                    f"Expected category={expected_category}, got={observed}",
                )
                return

        self._publish_status(request_id, "执行中", "STARTED", f"template={template_id}")
        for idx, wp_name in enumerate(sequence):
            positions = self.waypoints["waypoints"].get(wp_name)
            if positions is None:
                raise RuntimeError(f"Waypoint '{wp_name}' not found.")
            step_duration = self._publish_step_trajectory(template_id, wp_name, positions)
            self._publish_status(
                request_id,
                "执行中",
                "STEP",
                f"{idx + 1}/{len(sequence)} -> {wp_name}",
            )
            self.sleep_fn(step_duration + 0.15)

        self._publish_status(request_id, "完成", "OK", "Task completed")
