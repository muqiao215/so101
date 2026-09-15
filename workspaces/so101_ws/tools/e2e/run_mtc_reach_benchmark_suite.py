#!/usr/bin/env python3
"""Run a multi-episode Gazebo/MTC execution-grounded reach benchmark suite."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import signal
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import yaml


DEFAULT_TARGET = (0.32, 0.18, 0.8)


def parse_xyz(value: str) -> List[float]:
    parts = [part.strip() for part in value.replace("[", "").replace("]", "").split(",")]
    xyz = [float(part) for part in parts if part]
    if len(xyz) != 3:
        raise argparse.ArgumentTypeError("expected x,y,z")
    return xyz


def jitter_target(base_target: Sequence[float], jitter_xyz: Sequence[float], rng: random.Random) -> List[float]:
    return [
        float(base_target[index]) + rng.uniform(-float(jitter_xyz[index]), float(jitter_xyz[index]))
        for index in range(3)
    ]


def percentile(values: Sequence[float], q: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * q
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def as_bool(value: Any) -> bool:
    return bool(value) if value is not None else False


def classify_failure(report: Mapping[str, Any]) -> str:
    if not as_bool(report.get("planning_success")):
        failure_phase = str(report.get("failure_phase") or "")
        failure_type = str(report.get("failure_type") or "")
        if failure_phase == "ik_preflight" or "IK" in failure_type or "setFromIK" in failure_type:
            return "no_ik"
        return "mtc_plan_failed"
    if report.get("execution_trace", {}).get("attempted") and not report.get("execution_trace", {}).get("sample_count"):
        return "execution_trace_missing"
    if not as_bool(report.get("trajectory_execution_success")):
        return "trajectory_publish_failed"
    if not as_bool(report.get("controller_converged")):
        return "controller_not_converged"
    if not as_bool(report.get("reach_success")):
        return "reach_failed"
    return "success"


def rate(reports: Sequence[Mapping[str, Any]], key: str) -> float:
    if not reports:
        return 0.0
    return sum(1 for report in reports if as_bool(report.get(key))) / len(reports)


def summarize_reports(reports: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    distances = [float(report["min_distance_m"]) for report in reports if report.get("min_distance_m") is not None]
    failure_counts = Counter(classify_failure(report) for report in reports if classify_failure(report) != "success")
    contact_success_rate = 0.0
    lift_success_rate = 0.0
    if reports:
      contact_success_rate = sum(
          1
          for report in reports
          if bool(((report.get("evaluation_result") or {}).get("metrics") or {}).get("contact_success"))
      ) / len(reports)
      lift_success_rate = sum(
          1
          for report in reports
          if bool(((report.get("evaluation_result") or {}).get("metrics") or {}).get("lift_success"))
      ) / len(reports)
    return {
        "schema": "so101_mtc_reach_benchmark_suite_v1",
        "total_episodes": len(reports),
        "planning_success_rate": rate(reports, "planning_success"),
        "trajectory_execution_success_rate": rate(reports, "trajectory_execution_success"),
        "controller_converged_rate": rate(reports, "controller_converged"),
        "execution_success_rate": rate(reports, "execution_success"),
        "reach_success_rate": rate(reports, "reach_success"),
        "contact_success_rate": contact_success_rate,
        "lift_success_rate": lift_success_rate,
        "mean_min_distance_m": statistics.fmean(distances) if distances else None,
        "p50_min_distance_m": percentile(distances, 0.50),
        "p90_min_distance_m": percentile(distances, 0.90),
        "min_min_distance_m": min(distances) if distances else None,
        "max_min_distance_m": max(distances) if distances else None,
        "failure_reason_counts": dict(sorted(failure_counts.items())),
    }


def write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def flatten_trace_rows(trace: Sequence[Mapping[str, Any]], include_joints: bool) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for sample in trace:
        xyz = sample.get("tcp_world_xyz") or [None, None, None]
        row: Dict[str, Any] = {"t": sample.get("t")}
        if not include_joints:
            row.update({
                "tcp_x": xyz[0] if len(xyz) > 0 else None,
                "tcp_y": xyz[1] if len(xyz) > 1 else None,
                "tcp_z": xyz[2] if len(xyz) > 2 else None,
            })
        if include_joints:
            for joint_name, joint_value in (sample.get("joints") or {}).items():
                row[joint_name] = joint_value
        rows.append(row)
    return rows


def write_episode_artifacts(episode_dir: Path, report: Mapping[str, Any], target_xyz: Sequence[float]) -> None:
    write_yaml(episode_dir / "selected_candidate.yaml", {
        "selected_candidate_id": report.get("selected_candidate_id"),
        "joint_goal": report.get("joint_goal"),
        "selected_cartesian_candidate_world_xyz": report.get("selected_cartesian_candidate_world_xyz"),
        "ik_preflight": report.get("ik_preflight"),
    })
    write_yaml(episode_dir / "planned_goal_proxy.yaml", report.get("planned_goal_proxy") or {})
    write_yaml(episode_dir / "execution_grounded_metrics.yaml", report.get("evaluation_result", {}).get("metrics") or {})
    with (episode_dir / "target.json").open("w", encoding="utf-8") as handle:
        json.dump({"target_xyz": list(target_xyz), "canonical_target_xyz": report.get("canonical_target_xyz")}, handle, indent=2)

    trace = report.get("execution_trace", {}).get("tcp_trace") or []
    tcp_rows = flatten_trace_rows(trace, include_joints=False)
    write_csv(episode_dir / "tcp_trace.csv", tcp_rows, ["t", "tcp_x", "tcp_y", "tcp_z"])
    joint_rows = flatten_trace_rows(trace, include_joints=True)
    joint_names = sorted({key for row in joint_rows for key in row.keys()} - {"t", "tcp_x", "tcp_y", "tcp_z"})
    write_csv(episode_dir / "joint_trace.csv", joint_rows, ["t", *joint_names])


def build_launch_command(args: argparse.Namespace, report_path: Path, target_xyz: Sequence[float]) -> List[str]:
    return [
        "ros2",
        "launch",
        "so101_moveit_config",
        "mtc_reach_benchmark.launch.py",
        f"report_path:={report_path}",
        f"target_xyz:=[{target_xyz[0]},{target_xyz[1]},{target_xyz[2]}]",
        "target_mode:=vision_canonical",
        "backend_mode:=cartesian_ik_move_to",
        "execute_in_gazebo:=true",
        f"execute_duration_sec:={args.execute_duration_sec}",
        f"settle_duration_sec:={args.settle_duration_sec}",
        f"trace_sample_period_sec:={args.trace_sample_period_sec}",
        f"controller_convergence_tolerance_rad:={args.controller_convergence_tolerance_rad}",
        "use_rviz:=false",
        f"use_gzclient:={'true' if args.use_gzclient else 'false'}",
    ]


def run_episode(args: argparse.Namespace, episode_dir: Path, target_xyz: Sequence[float]) -> Dict[str, Any]:
    report_path = episode_dir / "report.yaml"
    command = build_launch_command(args, report_path.resolve(), target_xyz)
    episode_dir.mkdir(parents=True, exist_ok=True)
    (episode_dir / "command.txt").write_text(" ".join(command) + "\n", encoding="utf-8")
    if args.dry_run:
        report = {
            "planning_success": False,
            "trajectory_execution_success": False,
            "controller_converged": False,
            "execution_success": False,
            "reach_success": False,
            "failure_phase": "dry_run",
            "min_distance_m": None,
        }
        write_yaml(report_path, report)
        write_episode_artifacts(episode_dir, report, target_xyz)
        return report

    stdout_path = episode_dir / "launch.stdout.log"
    stderr_path = episode_dir / "launch.stderr.log"
    with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
        process = subprocess.Popen(
            command,
            cwd=args.workspace,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            start_new_session=True,
        )
        deadline = time.monotonic() + float(args.timeout_sec)
        report_written = False
        while time.monotonic() < deadline:
            if report_path.exists():
                try:
                    with report_path.open("r", encoding="utf-8") as handle:
                        current_report = yaml.safe_load(handle) or {}
                    if current_report.get("evaluation_result") or current_report.get("failure_phase"):
                        report_written = True
                        break
                except Exception:
                    pass
            if process.poll() is not None:
                break
            time.sleep(1.0)
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGINT)
                process.wait(timeout=10)
            except Exception:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=10)
                except Exception:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)
        if not report_written and not report_path.exists():
            stderr_handle.write(f"\n[runner] episode timed out after {args.timeout_sec}s before report was written\n")

    if not report_path.exists():
        report = {
            "planning_success": False,
            "trajectory_execution_success": False,
            "controller_converged": False,
            "execution_success": False,
            "reach_success": False,
            "failure_phase": "report_missing",
            "failure_type": "benchmark_report_not_written",
            "min_distance_m": None,
        }
        write_yaml(report_path, report)
    else:
        with report_path.open("r", encoding="utf-8") as handle:
            report = yaml.safe_load(handle) or {}
    write_episode_artifacts(episode_dir, report, target_xyz)
    return report


def run_suite(args: argparse.Namespace) -> Dict[str, Any]:
    rng = random.Random(args.seed)
    output_dir = args.output_dir.resolve()
    reports: List[Dict[str, Any]] = []
    episode_index: List[Dict[str, Any]] = []
    for episode_id in range(args.episode_count):
        target_xyz = jitter_target(args.target_xyz, args.jitter_xyz, rng)
        episode_dir = output_dir / f"episode_{episode_id:04d}"
        report = run_episode(args, episode_dir, target_xyz)
        reports.append(report)
        episode_index.append({
            "episode_id": episode_id,
            "episode_dir": str(episode_dir),
            "target_xyz": target_xyz,
            "planning_success": report.get("planning_success"),
            "trajectory_execution_success": report.get("trajectory_execution_success"),
            "controller_converged": report.get("controller_converged"),
            "reach_success": report.get("reach_success"),
            "contact_success": ((report.get("evaluation_result") or {}).get("metrics") or {}).get("contact_success"),
            "lift_success": ((report.get("evaluation_result") or {}).get("metrics") or {}).get("lift_success"),
            "min_distance_m": report.get("min_distance_m"),
            "failure_reason": classify_failure(report),
        })
    summary = summarize_reports(reports)
    summary.update({
        "suite_name": args.suite_name,
        "seed": args.seed,
        "base_target_xyz": list(args.target_xyz),
        "jitter_xyz": list(args.jitter_xyz),
        "episode_index": episode_index,
        "scope": "Gazebo execution-grounded simulated benchmark; contact/lift fields are simulated evaluator outputs only, not real hardware, not trainable_real",
    })
    write_yaml(output_dir / "summary_report.yaml", summary)
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=Path("docs/generated/vision-episodes/mtc-reach-suite"))
    parser.add_argument("--suite-name", default=f"mtc-reach-suite-{int(time.time())}")
    parser.add_argument("--episode-count", type=int, default=1)
    parser.add_argument("--target-xyz", type=parse_xyz, default=list(DEFAULT_TARGET))
    parser.add_argument("--jitter-xyz", type=parse_xyz, default=[0.0, 0.0, 0.0])
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--timeout-sec", type=float, default=180.0)
    parser.add_argument("--execute-duration-sec", type=float, default=3.0)
    parser.add_argument("--settle-duration-sec", type=float, default=1.0)
    parser.add_argument("--trace-sample-period-sec", type=float, default=0.05)
    parser.add_argument("--controller-convergence-tolerance-rad", type=float, default=0.08)
    parser.add_argument("--use-gzclient", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    summary = run_suite(args)
    print(yaml.safe_dump(summary, sort_keys=False, allow_unicode=True))
    return 0 if summary.get("total_episodes", 0) == 0 or summary.get("reach_success_rate", 0.0) >= 0.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
