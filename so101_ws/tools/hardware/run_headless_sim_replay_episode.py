#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


def discover_workspace_root(start_path: Path | None = None) -> Path:
    search_roots: list[Path] = []
    for candidate in (start_path, Path.cwd()):
        if candidate is None:
            continue
        resolved = Path(candidate).resolve()
        search_roots.append(resolved)
        search_roots.extend(resolved.parents)

    for candidate in search_roots:
        if (candidate / "AGENTS.md").is_file() and (candidate / "docs").is_dir() and (candidate / "src").is_dir():
            return candidate

    resolved = Path(start_path or __file__).resolve()
    return resolved.parents[2]


def timestamp_slug() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def sanitize_episode_id(value: str) -> str:
    text = value.strip()
    safe = "".join(ch if (ch.isalnum() or ch in {"_", "-"}) else "_" for ch in text)
    safe = safe.strip("_")
    if not safe:
        raise ValueError(f"invalid episode id: {value!r}")
    return safe


def default_episode_id(input_path: Path) -> str:
    return sanitize_episode_id(f"sim_replay_{input_path.stem}_{timestamp_slug()}")


def latest_recording(output_dir: Path) -> tuple[Path, Path]:
    candidates = sorted(output_dir.glob("leader-recording-*.jsonl"))
    if not candidates:
        raise FileNotFoundError(f"no simulated replay recording found in {output_dir}")
    recording_path = candidates[-1]
    meta_path = recording_path.with_suffix(".meta.json")
    if not meta_path.is_file():
        raise FileNotFoundError(f"expected replay recording metadata next to {recording_path}")
    return recording_path, meta_path


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_shell(cmd: str, *, cwd: Path, log_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["bash", "-lc", cmd],
        cwd=str(cwd),
        text=True,
        capture_output=True,
    )
    if log_path is not None:
        combined = []
        if result.stdout:
            combined.append(result.stdout)
        if result.stderr:
            combined.append(result.stderr)
        log_path.write_text("".join(combined), encoding="utf-8")
    return result


def build_source_prefix(workspace_root: Path) -> str:
    preferred = [
        workspace_root / "install" / "setup.bash",
        workspace_root / "install" / "local_setup.bash",
        Path("/opt/ros/humble/setup.bash"),
    ]
    for path in preferred:
        if path.is_file():
            return f"source '{path}'"
    raise FileNotFoundError("no ROS setup.bash found; expected workspace install setup or /opt/ros/humble/setup.bash")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run L1 headless simulated-arm replay episode and generate replay validation + manifest."
    )
    parser.add_argument("--input", required=True, help="Source leader recording jsonl")
    parser.add_argument("--episode-id", default="", help="Episode id; default sim_replay_<recording>_<timestamp>")
    parser.add_argument("--task-name", default="sim_headless_replay", help="Task name for manifest")
    parser.add_argument("--operator", default=getpass.getuser(), help="Operator name for manifest")
    parser.add_argument("--rate-scale", type=float, default=1.0, help="Replay speed multiplier")
    parser.add_argument(
        "--command-mode",
        choices=("topic", "action"),
        default="topic",
        help="How to send JointTrajectory to the controller",
    )
    parser.add_argument(
        "--follow-joint-trajectory-action",
        default="/joint_trajectory_controller/follow_joint_trajectory",
        help="FollowJointTrajectory action name when --command-mode=action",
    )
    parser.add_argument(
        "--action-server-wait-sec",
        type=float,
        default=10.0,
        help="How long to wait for the FollowJointTrajectory server",
    )
    parser.add_argument(
        "--action-result-timeout-sec",
        type=float,
        default=0.0,
        help="How long to wait for the action result; 0 means auto",
    )
    parser.add_argument(
        "--goal-time-tolerance-sec",
        type=float,
        default=0.0,
        help="goal_time_tolerance used when sending FollowJointTrajectory goals",
    )
    parser.add_argument("--controller-load-delay-sec", type=float, default=20.0, help="Controller load delay for sim launch")
    parser.add_argument("--replay-start-delay-sec", type=float, default=1.0, help="Delay before trajectory publish after controller is ready")
    parser.add_argument("--post-replay-wait-sec", type=float, default=1.0, help="Wait before auto shutdown after replay finishes")
    parser.add_argument("--trajectory-settle-sec", type=float, default=2.0, help="Extra settle time after last point before player exits")
    parser.add_argument("--wait-for-subscribers-sec", type=float, default=5.0, help="How long player waits for controller subscriber")
    parser.add_argument("--profile", default="replay_default", help="Replay validator profile")
    parser.add_argument(
        "--controllers-yaml",
        default="",
        help="Optional controller YAML passed to Gazebo via SO101_CONTROLLERS_YAML",
    )
    parser.add_argument("--initial-hold-sec", type=float, default=0.0, help="Shift all trajectory time_from_start by this amount")
    parser.add_argument(
        "--prepend-first-point-copy",
        action="store_true",
        help="Insert a hold point at t=0 using the first point positions before replay starts",
    )
    parser.add_argument(
        "--header-start-delay-sec",
        type=float,
        default=0.0,
        help="Set JointTrajectory.header.stamp to now + delay before publish",
    )
    parser.add_argument(
        "--preposition-first-point-sec",
        type=float,
        default=0.0,
        help="Move the simulated arm to the first trajectory point before recording the replay",
    )
    parser.add_argument(
        "--source-quality-policy",
        choices=("warn", "fail", "skip"),
        default="warn",
        help="How to handle source joint limit / velocity limit violations before replay",
    )
    parser.add_argument("--source-quality-velocity-scale", type=float, default=1.0, help="Multiplier for URDF velocity limits")
    parser.add_argument("--notes", default="L1 headless simulated-arm replay", help="Manifest note")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace_root = discover_workspace_root(Path(__file__))
    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"input recording not found: {input_path}")

    episode_id = sanitize_episode_id(args.episode_id) if args.episode_id.strip() else default_episode_id(input_path)
    episode_dir = (workspace_root / "docs" / "generated" / "leader-episodes" / episode_id).resolve()
    episode_dir.mkdir(parents=True, exist_ok=True)

    launch_log_path = episode_dir / "launch.log"
    replay_result_path = episode_dir / "replay-raw.json"
    compare_bundle_path = episode_dir / "replay-compare-bundle.json"
    replay_diagnostics_path = episode_dir / "replay-diagnostics.json"
    manifest_path = episode_dir / "manifest.json"
    summary_path = episode_dir / "l1-sim-replay-summary.json"
    command_dump_path = episode_dir / "player-command.json"
    controller_state_path = episode_dir / "controller-state.jsonl"
    action_feedback_path = episode_dir / "action-feedback.jsonl"
    action_result_path = episode_dir / "action-result.json"
    source_quality_path = episode_dir / "source-quality.json"

    source_quality_payload: dict[str, Any] | None = None
    if args.source_quality_policy != "skip":
        source_quality_cmd = [
            "python3",
            str((workspace_root / "tools" / "hardware" / "source_episode_quality_gate.py").resolve()),
            "--recording",
            str(input_path),
            "--urdf",
            str((workspace_root / "src" / "so101_description" / "urdf" / "so101.urdf").resolve()),
            "--output",
            str(source_quality_path),
            "--velocity-scale",
            str(max(float(args.source_quality_velocity_scale), 1e-9)),
        ]
        if args.source_quality_policy == "fail":
            source_quality_cmd.append("--fail-on-violation")
        source_quality_result = subprocess.run(
            source_quality_cmd,
            cwd=str(workspace_root),
            text=True,
            capture_output=True,
            check=False,
        )
        if source_quality_path.exists():
            source_quality_payload = json.loads(source_quality_path.read_text(encoding="utf-8"))
        if source_quality_result.returncode != 0:
            write_json(
                summary_path,
                {
                    "status": "source_quality_failed",
                    "episode_id": episode_id,
                    "input_path": str(input_path),
                    "source_quality_policy": args.source_quality_policy,
                    "source_quality_report_path": str(source_quality_path),
                    "source_quality": (source_quality_payload or {}).get("quality", {}),
                    "stderr": source_quality_result.stderr,
                    "stdout": source_quality_result.stdout,
                },
            )
            print(summary_path.read_text(encoding="utf-8"))
            return source_quality_result.returncode

    source_prefix = build_source_prefix(workspace_root)
    controllers_env = ""
    if str(args.controllers_yaml).strip():
        controllers_path = Path(args.controllers_yaml).resolve()
        if not controllers_path.is_file():
            raise FileNotFoundError(f"controllers yaml not found: {controllers_path}")
        controllers_env = f"SO101_CONTROLLERS_YAML='{controllers_path}' "
    launch_cmd = (
        f"{source_prefix} && {controllers_env}"
        f"ros2 launch so101_bringup leader_sim_replay_headless.launch.py "
        f"input_path:='{input_path}' "
        f"output_dir:='{episode_dir}' "
        f"use_gzclient:=false "
        f"command_mode:={args.command_mode} "
        f"follow_joint_trajectory_action:='{args.follow_joint_trajectory_action}' "
        f"action_server_wait_sec:={args.action_server_wait_sec} "
        f"action_result_timeout_sec:={args.action_result_timeout_sec} "
        f"goal_time_tolerance_sec:={args.goal_time_tolerance_sec} "
        f"controller_load_delay_sec:={args.controller_load_delay_sec} "
        f"replay_start_delay_sec:={args.replay_start_delay_sec} "
        f"post_replay_wait_sec:={args.post_replay_wait_sec} "
        f"trajectory_settle_sec:={args.trajectory_settle_sec} "
        f"wait_for_subscribers_sec:={args.wait_for_subscribers_sec} "
        f"rate_scale:={args.rate_scale} "
        f"initial_hold_sec:={args.initial_hold_sec} "
        f"prepend_first_point_copy:={'true' if args.prepend_first_point_copy else 'false'} "
        f"header_start_delay_sec:={args.header_start_delay_sec} "
        f"preposition_first_point_sec:={args.preposition_first_point_sec}"
    )

    launch_result = run_shell(launch_cmd, cwd=workspace_root, log_path=launch_log_path)
    if launch_result.returncode != 0:
        write_json(
            summary_path,
            {
                "status": "launch_failed",
                "episode_id": episode_id,
                "input_path": str(input_path),
                "launch_log_path": str(launch_log_path),
                "launch_returncode": launch_result.returncode,
            },
        )
        raise RuntimeError(f"headless sim replay launch failed; see {launch_log_path}")

    candidate_record_path, candidate_meta_path = latest_recording(episode_dir)
    if candidate_record_path.stat().st_size <= 0:
        write_json(
            summary_path,
            {
                "status": "recording_empty",
                "episode_id": episode_id,
                "input_path": str(input_path),
                "candidate_record_path": str(candidate_record_path),
                "candidate_meta_path": str(candidate_meta_path),
                "launch_log_path": str(launch_log_path),
            },
        )
        raise RuntimeError(f"sim replay candidate recording is empty; see {launch_log_path}")

    validator_cmd = [
        "python3",
        str((workspace_root / "tools" / "hardware" / "leader_replay_validator.py").resolve()),
        "--reference",
        str(input_path),
        "--candidate",
        str(candidate_record_path),
        "--profile",
        args.profile,
        "--thresholds",
        str((workspace_root / "tools" / "hardware" / "replay_validator_thresholds.json").resolve()),
        "--top-k",
        "10",
        "--edge-window-sec",
        "0.10",
        "--output",
        str(replay_result_path),
        "--print-summary",
    ]
    validator_result = subprocess.run(validator_cmd, cwd=str(workspace_root), text=True, capture_output=True, check=False)
    if validator_result.returncode != 0:
        raise RuntimeError(f"validator failed unexpectedly: {validator_result.stderr or validator_result.stdout}")

    if command_dump_path.is_file() and controller_state_path.is_file():
        diagnostics_cmd = [
            "python3",
            str((workspace_root / "tools" / "hardware" / "analyze_leader_replay_distortion.py").resolve()),
            "--reference",
            str(input_path),
            "--candidate",
            str(candidate_record_path),
            "--command-dump",
            str(command_dump_path),
            "--controller-state",
            str(controller_state_path),
            "--replay-result",
            str(replay_result_path),
            "--compare-bundle-output",
            str(compare_bundle_path),
            "--output",
            str(replay_diagnostics_path),
            "--urdf",
            str((workspace_root / "src" / "so101_description" / "urdf" / "so101.urdf").resolve()),
        ]
        diagnostics_result = subprocess.run(
            diagnostics_cmd,
            cwd=str(workspace_root),
            text=True,
            capture_output=True,
            check=False,
        )
        if diagnostics_result.returncode != 0:
            raise RuntimeError(f"replay distortion diagnostics failed unexpectedly: {diagnostics_result.stderr or diagnostics_result.stdout}")

    manifest_cmd = [
        "python3",
        str((workspace_root / "tools" / "hardware" / "episode_manifest.py").resolve()),
        "--episode-id",
        episode_id,
        "--task-name",
        args.task_name,
        "--raw-record-path",
        str(candidate_record_path),
        "--recording-meta-path",
        str(candidate_meta_path),
        "--replay-raw-result-path",
        str(replay_result_path),
        "--source-quality-report-path",
        str(source_quality_path) if source_quality_path.exists() else "",
        "--output-path",
        str(manifest_path),
        "--operator",
        args.operator,
        "--source-mode",
        "offline_replay",
        "--robot-profile",
        "so101_sim_headless",
        "--notes",
        f"{args.notes}; source_record_path={input_path}",
    ]
    manifest_result = subprocess.run(manifest_cmd, cwd=str(workspace_root), text=True, capture_output=True, check=False)
    if manifest_result.returncode != 0:
        raise RuntimeError(f"manifest generation failed unexpectedly: {manifest_result.stderr or manifest_result.stdout}")

    replay_payload = json.loads(replay_result_path.read_text(encoding="utf-8"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    action_result_payload = (
        json.loads(action_result_path.read_text(encoding="utf-8"))
        if args.command_mode == "action" and action_result_path.exists()
        else None
    )
    summary_payload = {
        "status": "completed",
        "episode_id": episode_id,
        "task_name": args.task_name,
        "input_path": str(input_path),
        "candidate_record_path": str(candidate_record_path),
        "candidate_meta_path": str(candidate_meta_path),
        "replay_result_path": str(replay_result_path),
        "command_dump_path": str(command_dump_path) if command_dump_path.exists() else None,
        "controller_state_path": str(controller_state_path) if controller_state_path.exists() else None,
        "action_feedback_path": str(action_feedback_path) if action_feedback_path.exists() else None,
        "action_result_path": str(action_result_path) if action_result_path.exists() else None,
        "compare_bundle_path": str(compare_bundle_path) if compare_bundle_path.exists() else None,
        "replay_diagnostics_path": str(replay_diagnostics_path) if replay_diagnostics_path.exists() else None,
        "manifest_path": str(manifest_path),
        "launch_log_path": str(launch_log_path),
        "command_mode": args.command_mode,
        "controllers_yaml": str(Path(args.controllers_yaml).resolve()) if str(args.controllers_yaml).strip() else None,
        "source_quality_policy": args.source_quality_policy,
        "source_quality_report_path": str(source_quality_path) if source_quality_path.exists() else None,
        "source_quality_status": (
            (source_quality_payload or {}).get("quality", {}).get("status")
            if source_quality_payload is not None
            else None
        ),
        "source_quality_reasons": (
            (source_quality_payload or {}).get("quality", {}).get("reasons", [])
            if source_quality_payload is not None
            else []
        ),
        "validator_status": replay_payload.get("judgment", {}).get("status"),
        "validator_profile": replay_payload.get("judgment", {}).get("profile"),
        "initial_hold_sec": args.initial_hold_sec,
        "prepend_first_point_copy": bool(args.prepend_first_point_copy),
        "header_start_delay_sec": args.header_start_delay_sec,
        "preposition_first_point_sec": args.preposition_first_point_sec,
        "action_goal_status_label": (
            action_result_payload.get("goal_status_label") if action_result_payload is not None else None
        ),
        "action_runtime_error": (
            action_result_payload.get("runtime_error") if action_result_payload is not None else None
        ),
        "manifest_quality_status": manifest_payload.get("quality_metadata", {}).get("input_recording", {}).get("status"),
        "summary": manifest_payload.get("quality_metadata", {}).get("replay_validation", {}).get("raw", {}).get("summary", {}),
    }
    write_json(summary_path, summary_payload)
    print(json.dumps(summary_payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
