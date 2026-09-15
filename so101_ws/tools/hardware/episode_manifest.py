#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import socket
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_EPISODES_DIR = Path("docs/generated/leader-episodes")
MANIFEST_SCHEMA_VERSION = "v1"


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


def timestamp_now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sanitize_episode_id(value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError("episode_id must not be empty")
    safe = "".join(ch if (ch.isalnum() or ch in {"_", "-"}) else "_" for ch in text)
    safe = safe.strip("_")
    if not safe:
        raise ValueError(f"episode_id '{value}' becomes empty after sanitize")
    return safe


def resolve_optional_path(value: str, workspace_root: Path) -> str | None:
    text = value.strip()
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        path = workspace_root / path
    return str(path.resolve())


def resolve_required_path(value: str, workspace_root: Path, *, field_name: str) -> str:
    resolved = resolve_optional_path(value, workspace_root)
    if resolved is None:
        raise ValueError(f"{field_name} is required")
    return resolved


def load_recording_meta(meta_path: str | None) -> dict[str, Any]:
    summary = {
        "status": "not_provided",
        "meta_path": meta_path,
        "duration_sec": None,
        "frame_count": None,
        "sample_rate_hz": None,
        "invalid_frame_count": None,
        "joint_name_mismatch_count": None,
        "non_monotonic_stamp_count": None,
        "large_interval_count": None,
        "avg_frame_gap_sec": None,
        "max_frame_gap_sec": None,
        "warnings": [],
        "anomaly_counts": {},
        "invalid_reason_counts": {},
        "frame_interval_stats": {},
        "quality_metrics": {},
        "quality_score": None,
        "load_error": None,
    }
    if not meta_path:
        return summary

    path = Path(meta_path)
    if not path.exists():
        summary["status"] = "meta_not_found"
        summary["load_error"] = f"recording meta not found: {meta_path}"
        return summary

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        summary["status"] = "meta_load_error"
        summary["load_error"] = str(exc)
        return summary

    for key in (
        "duration_sec",
        "frame_count",
        "sample_rate_hz",
        "invalid_frame_count",
        "joint_name_mismatch_count",
        "non_monotonic_stamp_count",
        "large_interval_count",
    ):
        summary[key] = payload.get(key)
    frame_interval_stats = payload.get("frame_interval_stats") or {}
    anomaly_counts = payload.get("anomaly_counts") or {}
    invalid_reason_counts = payload.get("invalid_reason_counts") or {}
    quality_metrics = payload.get("quality_metrics") or {}
    if not isinstance(frame_interval_stats, dict):
        frame_interval_stats = {}
    if not isinstance(anomaly_counts, dict):
        anomaly_counts = {}
    if not isinstance(invalid_reason_counts, dict):
        invalid_reason_counts = {}
    if not isinstance(quality_metrics, dict):
        quality_metrics = {}
    summary["frame_interval_stats"] = frame_interval_stats
    summary["anomaly_counts"] = anomaly_counts
    summary["invalid_reason_counts"] = invalid_reason_counts
    summary["quality_metrics"] = quality_metrics
    summary["avg_frame_gap_sec"] = frame_interval_stats.get("avg_sec")
    summary["max_frame_gap_sec"] = frame_interval_stats.get("max_sec")
    warnings = payload.get("warnings") or []
    if not isinstance(warnings, list):
        warnings = [str(warnings)]
    summary["warnings"] = [str(item) for item in warnings]

    error_counts = [
        int(summary["invalid_frame_count"] or 0),
        int(summary["joint_name_mismatch_count"] or 0),
        int(summary["non_monotonic_stamp_count"] or 0),
        int(summary["large_interval_count"] or 0),
    ]
    has_errors = any(value > 0 for value in error_counts)
    has_warnings = bool(summary["warnings"])
    summary["status"] = "warn" if (has_errors or has_warnings) else "ok"

    # Minimal quality score skeleton: start from 1.0, penalize errors and warnings.
    quality_score = 1.0
    quality_score -= min(error_counts[0] * 0.05, 0.3)
    quality_score -= min(error_counts[1] * 0.1, 0.3)
    quality_score -= min(error_counts[2] * 0.02, 0.2)
    quality_score -= min(error_counts[3] * 0.02, 0.15)
    if has_warnings:
        quality_score -= min(len(summary["warnings"]) * 0.02, 0.1)
    summary["quality_score"] = round(max(quality_score, 0.0), 3)
    return summary


def load_replay_result(result_path: str | None) -> dict[str, Any]:
    summary = {
        "status": "not_run",
        "profile": None,
        "result_path": result_path,
        "summary": {},
        "duration_delta_sec": None,
        "duration_delta_abs_sec": None,
        "load_error": None,
    }
    if not result_path:
        return summary

    path = Path(result_path)
    if not path.exists():
        summary["status"] = "result_not_found"
        summary["load_error"] = f"replay result not found: {result_path}"
        return summary

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        summary["status"] = "result_load_error"
        summary["load_error"] = str(exc)
        return summary

    judgment = payload.get("judgment") or {}
    metrics = payload.get("metrics") or {}
    overall = metrics.get("overall") or payload.get("overall") or {}
    diagnostics = payload.get("diagnostics") or {}
    worst_point = diagnostics.get("worst_point") or {}
    if not isinstance(judgment, dict):
        judgment = {}
    if not isinstance(overall, dict):
        overall = {}
    if not isinstance(worst_point, dict):
        worst_point = {}

    status = str(judgment.get("status") or payload.get("status") or "unknown")
    summary["status"] = status
    summary["profile"] = judgment.get("profile")
    summary["summary"] = {
        "mae_rad": overall.get("mae_rad"),
        "rmse_rad": overall.get("rmse_rad"),
        "max_error_rad": overall.get("max_error_rad"),
        "p95_error_rad": overall.get("p95_error_rad"),
        "duration_delta_sec": overall.get("duration_delta_sec", payload.get("duration_delta_sec")),
        "duration_delta_abs_sec": overall.get("duration_delta_abs_sec", payload.get("duration_delta_abs_sec")),
        "duration_ratio": overall.get("duration_ratio"),
        "worst_joint": worst_point.get("joint"),
        "worst_t_sec": worst_point.get("t_sec"),
    }
    summary["duration_delta_sec"] = summary["summary"]["duration_delta_sec"]
    summary["duration_delta_abs_sec"] = summary["summary"]["duration_delta_abs_sec"]
    return summary


def load_cleaning_report(report_path: str | None) -> dict[str, Any]:
    summary = {
        "status": "not_run",
        "report_path": report_path,
        "source_sha256": None,
        "changed": None,
        "summary": {},
        "load_error": None,
    }
    if not report_path:
        return summary

    path = Path(report_path)
    if not path.exists():
        summary["status"] = "report_not_found"
        summary["load_error"] = f"cleaning report not found: {report_path}"
        return summary

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        summary["status"] = "report_load_error"
        summary["load_error"] = str(exc)
        return summary

    report_summary = payload.get("summary") or {}
    input_payload = payload.get("input") or {}
    output_payload = payload.get("output") or {}
    if not isinstance(report_summary, dict):
        report_summary = {}
    if not isinstance(input_payload, dict):
        input_payload = {}
    if not isinstance(output_payload, dict):
        output_payload = {}

    changed = bool(report_summary.get("changed"))
    summary["status"] = "cleaned_from_invalid" if changed else "passed"
    summary["source_sha256"] = input_payload.get("sha256")
    summary["changed"] = changed
    summary["summary"] = {
        "removed_frame_count": report_summary.get("removed_frame_count"),
        "duplicate_timestamp_count": report_summary.get("duplicate_timestamp_count"),
        "non_monotonic_timestamp_count": report_summary.get("non_monotonic_timestamp_count"),
        "labels": report_summary.get("labels") or [],
        "cleaned_frame_count": output_payload.get("frame_count"),
        "cleaned_duration_sec": output_payload.get("duration_sec"),
        "cleaned_sample_rate_hz": output_payload.get("sample_rate_hz"),
        "cleaned_avg_frame_gap_sec": output_payload.get("avg_frame_gap_sec"),
        "cleaned_max_frame_gap_sec": output_payload.get("max_frame_gap_sec"),
    }
    return summary


def load_annotation(annotation_path: str | None) -> dict[str, Any]:
    summary = {
        "status": "not_provided",
        "annotation_path": annotation_path,
        "source_status": None,
        "cleaned_status": None,
        "usable_for_regression": None,
        "reasons": [],
        "source_sha256": None,
        "load_error": None,
    }
    if not annotation_path:
        return summary

    path = Path(annotation_path)
    if not path.exists():
        summary["status"] = "annotation_not_found"
        summary["load_error"] = f"annotation not found: {annotation_path}"
        return summary

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        summary["status"] = "annotation_load_error"
        summary["load_error"] = str(exc)
        return summary

    reasons = payload.get("reasons") or []
    if not isinstance(reasons, list):
        reasons = [str(reasons)]
    summary["status"] = "ok"
    summary["source_status"] = payload.get("source_status")
    summary["cleaned_status"] = payload.get("cleaned_status")
    summary["usable_for_regression"] = payload.get("usable_for_regression")
    summary["reasons"] = [str(reason) for reason in reasons]
    summary["source_sha256"] = payload.get("source_sha256")
    return summary


def load_source_quality_report(report_path: str | None) -> dict[str, Any]:
    summary = {
        "status": "not_run",
        "report_path": report_path,
        "reasons": [],
        "frame_count": None,
        "duration_sec": None,
        "joint_count": None,
        "load_error": None,
    }
    if not report_path:
        return summary

    path = Path(report_path)
    if not path.exists():
        summary["status"] = "report_not_found"
        summary["load_error"] = f"source quality report not found: {report_path}"
        return summary

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        summary["status"] = "report_load_error"
        summary["load_error"] = str(exc)
        return summary

    quality = payload.get("quality") or {}
    if not isinstance(quality, dict):
        quality = {}
    reasons = quality.get("reasons") or []
    if not isinstance(reasons, list):
        reasons = [str(reasons)]
    joints = quality.get("joints") or {}
    if not isinstance(joints, dict):
        joints = {}
    summary["status"] = str(quality.get("status") or "unknown")
    summary["reasons"] = [str(reason) for reason in reasons]
    summary["frame_count"] = quality.get("frame_count")
    summary["duration_sec"] = quality.get("duration_sec")
    summary["joint_count"] = len(joints)
    return summary


def detect_git_context(workspace_root: Path) -> dict[str, Any]:
    context = {"commit": "unknown", "dirty": None}
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(workspace_root),
            text=True,
        ).strip()
        context["commit"] = commit or "unknown"
    except Exception:
        return context

    try:
        status_output = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=str(workspace_root),
            text=True,
        )
        context["dirty"] = bool(status_output.strip())
    except Exception:
        context["dirty"] = None
    return context


def build_default_manifest_path(workspace_root: Path, episode_id: str) -> Path:
    return (workspace_root / DEFAULT_EPISODES_DIR / episode_id / "manifest.json").resolve()


def build_manifest(args: argparse.Namespace, workspace_root: Path) -> tuple[dict[str, Any], Path]:
    episode_id = sanitize_episode_id(args.episode_id)
    task_name = args.task_name.strip()
    if not task_name:
        raise ValueError("task_name must not be empty")

    created_at = args.created_at.strip() or timestamp_now_iso()
    raw_record_path = resolve_required_path(args.raw_record_path, workspace_root, field_name="raw_record_path")
    if not Path(raw_record_path).exists():
        raise FileNotFoundError(f"raw_record_path not found: {raw_record_path}")
    recording_meta_path = resolve_optional_path(args.recording_meta_path, workspace_root)
    draft_waypoint_path = resolve_optional_path(args.draft_waypoint_path, workspace_root)
    replay_raw_result_path = resolve_optional_path(args.replay_raw_result_path, workspace_root)
    replay_waypoint_result_path = resolve_optional_path(args.replay_waypoint_result_path, workspace_root)
    cleaned_record_path = resolve_optional_path(args.cleaned_record_path, workspace_root)
    cleaning_report_path = resolve_optional_path(args.cleaning_report_path, workspace_root)
    annotation_path = resolve_optional_path(args.annotation_path, workspace_root)
    source_quality_report_path = resolve_optional_path(args.source_quality_report_path, workspace_root)

    output_path = (
        Path(resolve_required_path(args.output_path, workspace_root, field_name="output_path"))
        if args.output_path.strip()
        else build_default_manifest_path(workspace_root, episode_id)
    )

    git_context = detect_git_context(workspace_root)
    quality_summary = load_recording_meta(recording_meta_path)
    replay_raw_summary = load_replay_result(replay_raw_result_path)
    replay_waypoint_summary = load_replay_result(replay_waypoint_result_path)
    cleaning_summary = load_cleaning_report(cleaning_report_path)
    annotation_summary = load_annotation(annotation_path)
    source_quality_summary = load_source_quality_report(source_quality_report_path)
    source_sha256 = args.source_sha256.strip() or cleaning_summary["source_sha256"] or annotation_summary["source_sha256"]
    asset_status = (
        args.asset_status.strip()
        or annotation_summary["cleaned_status"]
        or annotation_summary["source_status"]
        or cleaning_summary["status"]
        or "unknown"
    )

    primary_quality_source = "raw_meta"
    primary_quality_payload = {
        "frame_count": quality_summary["frame_count"],
        "duration_sec": quality_summary["duration_sec"],
        "sample_rate_hz": quality_summary["sample_rate_hz"],
        "invalid_frame_count": quality_summary["invalid_frame_count"],
        "joint_name_mismatch_count": quality_summary["joint_name_mismatch_count"],
        "non_monotonic_stamp_count": quality_summary["non_monotonic_stamp_count"],
        "large_interval_count": quality_summary["large_interval_count"],
        "avg_frame_gap_sec": quality_summary["avg_frame_gap_sec"],
        "max_frame_gap_sec": quality_summary["max_frame_gap_sec"],
        "quality_score": quality_summary["quality_score"],
    }
    cleaning_compact = cleaning_summary["summary"] if isinstance(cleaning_summary["summary"], dict) else {}
    if cleaned_record_path and cleaning_compact:
        primary_quality_source = "cleaned_report"
        primary_quality_payload = {
            "frame_count": cleaning_compact.get("cleaned_frame_count"),
            "duration_sec": cleaning_compact.get("cleaned_duration_sec"),
            "sample_rate_hz": cleaning_compact.get("cleaned_sample_rate_hz"),
            "invalid_frame_count": 0,
            "joint_name_mismatch_count": 0,
            "non_monotonic_stamp_count": 0,
            "large_interval_count": None,
            "avg_frame_gap_sec": cleaning_compact.get("cleaned_avg_frame_gap_sec"),
            "max_frame_gap_sec": cleaning_compact.get("cleaned_max_frame_gap_sec"),
            "quality_score": None,
        }

    manifest = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "episode_id": episode_id,
        "task_name": task_name,
        "created_at": created_at,
        "operator": args.operator.strip() or "unknown",
        "source_mode": args.source_mode.strip() or "leader_only",
        "robot_profile": args.robot_profile.strip() or "so101_leader",
        "calibration_version": args.calibration_version.strip() or "unknown",
        "asset_status": asset_status,
        "source_sha256": source_sha256 or None,
        "raw_record_path": raw_record_path,
        "recording_meta_path": recording_meta_path,
        "cleaned_record_path": cleaned_record_path,
        "cleaning_report_path": cleaning_report_path,
        "annotation_path": annotation_path,
        "source_quality_report_path": source_quality_report_path,
        "draft_waypoint_path": draft_waypoint_path,
        "merged_waypoint_version": args.merged_waypoint_version.strip() or "unknown",
        "replay_raw_result_path": replay_raw_result_path,
        "replay_waypoint_result_path": replay_waypoint_result_path,
        "notes": args.notes,
        "recording_layers": {
            "raw": {
                "path": raw_record_path,
                "meta_path": recording_meta_path,
                "status": annotation_summary["source_status"] or quality_summary["status"],
            },
            "cleaned": {
                "path": cleaned_record_path,
                "report_path": cleaning_report_path,
                "annotation_path": annotation_path,
                "status": annotation_summary["cleaned_status"] or cleaning_summary["status"],
                "source_sha256": source_sha256 or None,
            },
        },
        "task_metadata": {
            "start_condition": args.start_condition,
            "end_condition": args.end_condition,
            "outcome": args.outcome,
            "interrupted": bool(args.interrupted),
        },
        "system_metadata": {
            "workspace_root": str(workspace_root),
            "git_commit": git_context["commit"],
            "git_dirty": git_context["dirty"],
            "host": socket.gethostname(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "manifest_tool": "tools/hardware/episode_manifest.py",
            "generated_at": timestamp_now_iso(),
        },
        "quality_metadata": {
            "input_recording": quality_summary,
            "cleaning": cleaning_summary,
            "annotation": annotation_summary,
            "source_quality": source_quality_summary,
            "replay_validation": {
                "raw": replay_raw_summary,
                "waypoint": replay_waypoint_summary,
            },
        },
        "quality_summary": {
            "source": primary_quality_source,
            **primary_quality_payload,
        },
    }
    return manifest, output_path


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate episode manifest.json for leader episode assets.")
    parser.add_argument("--episode-id", required=True, help="Episode identifier, e.g. pick_demo_001")
    parser.add_argument("--task-name", required=True, help="Task name, e.g. pick_place")
    parser.add_argument("--raw-record-path", required=True, help="Path to raw episode recording JSONL")
    parser.add_argument("--recording-meta-path", default="", help="Path to recording metadata JSON")
    parser.add_argument("--cleaned-record-path", default="", help="Path to cleaned recording JSONL")
    parser.add_argument("--cleaning-report-path", default="", help="Path to cleaning report JSON")
    parser.add_argument("--annotation-path", default="", help="Path to annotation JSON")
    parser.add_argument("--source-quality-report-path", default="", help="Path to source quality gate report JSON")
    parser.add_argument("--output-path", default="", help="Output manifest path; default under docs/generated/leader-episodes/<episode_id>/manifest.json")
    parser.add_argument("--operator", default="unknown", help="Operator name")
    parser.add_argument("--source-mode", default="leader_only", help="Source mode label")
    parser.add_argument("--robot-profile", default="so101_leader", help="Robot profile label")
    parser.add_argument("--calibration-version", default="unknown", help="Calibration version or hash")
    parser.add_argument(
        "--asset-status",
        default="",
        help="Optional explicit asset status, e.g. invalid_result or cleaned_from_invalid",
    )
    parser.add_argument("--source-sha256", default="", help="Optional source recording sha256")
    parser.add_argument("--draft-waypoint-path", default="", help="Path to derived waypoint draft yaml")
    parser.add_argument("--merged-waypoint-version", default="unknown", help="Merged waypoint version id")
    parser.add_argument("--replay-raw-result-path", default="", help="Path to replay raw validator result")
    parser.add_argument("--replay-waypoint-result-path", default="", help="Path to replay waypoint validator result")
    parser.add_argument("--start-condition", default="", help="Task start condition note")
    parser.add_argument("--end-condition", default="", help="Task end condition note")
    parser.add_argument("--outcome", default="unknown", choices=["unknown", "success", "failed", "aborted"], help="Task outcome")
    parser.add_argument("--interrupted", action="store_true", help="Mark episode interrupted by operator")
    parser.add_argument("--notes", default="", help="Free text note")
    parser.add_argument("--created-at", default="", help="Created timestamp override, default now")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace_root = discover_workspace_root(Path(__file__))
    manifest, output_path = build_manifest(args, workspace_root)
    write_manifest(output_path, manifest)
    result = {
        "episode_id": manifest["episode_id"],
        "task_name": manifest["task_name"],
        "output_path": str(output_path),
        "raw_record_path": manifest["raw_record_path"],
        "recording_meta_path": manifest["recording_meta_path"],
        "quality_status": manifest["quality_metadata"]["input_recording"]["status"],
        "quality_score": manifest["quality_metadata"]["input_recording"]["quality_score"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
