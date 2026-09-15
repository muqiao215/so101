#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


SPLIT_FILES = {
    "train": "train_samples.jsonl",
    "debug": "debug_samples.jsonl",
    "rejected": "rejected_samples.jsonl",
}
EXECUTION_ACTION_TYPES = {"joint_positions", "joint_deltas", "gazebo_joint_trajectory", "follower_joint_action"}
REAL_ACTION_TYPES = {"follower_joint_action"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def resolve_candidate_dir(path: Path) -> Path:
    path = Path(path).resolve()
    if path.is_file() and path.name == "manifest.json":
        return path.parent
    if path.is_dir():
        return path
    raise FileNotFoundError(f"candidate path does not exist: {path}")


def sample_paths(candidate_dir: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    manifest_paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    resolved: dict[str, Path] = {}
    for split, filename in SPLIT_FILES.items():
        key = f"{split}_samples"
        resolved[split] = Path(manifest_paths[key]).resolve() if manifest_paths.get(key) else candidate_dir / filename
    return resolved


def observation_issues(row: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    observation = row.get("observation") if isinstance(row.get("observation"), dict) else {}
    overhead = ((observation.get("images") or {}).get("overhead") or {}) if isinstance(observation.get("images"), dict) else {}
    state = observation.get("state") if isinstance(observation.get("state"), dict) else {}
    if not (overhead.get("path") or overhead.get("relative_path")):
        issues.append("missing_image")
    if not state.get("joint_names") or not state.get("positions"):
        issues.append("missing_joint_state")
    elif len(state.get("joint_names") or []) != len(state.get("positions") or []):
        issues.append("joint_state_size_mismatch")
    return issues


def action_issues(row: dict[str, Any], *, require_real_action: bool) -> list[str]:
    action = row.get("action") if isinstance(row.get("action"), dict) else {}
    action_type = str(action.get("type") or "")
    issues: list[str] = []
    accepted_types = REAL_ACTION_TYPES if require_real_action else EXECUTION_ACTION_TYPES
    if action_type not in accepted_types:
        issues.append(f"unsupported_action_type:{action_type or 'missing'}")
        return issues
    joint_names = action.get("joint_names") or []
    positions = action.get("positions") or []
    if action_type in {"joint_positions", "follower_joint_action"}:
        if not joint_names:
            issues.append("missing_action_joint_names")
        if not positions:
            issues.append("missing_action_positions")
        if joint_names and positions and len(joint_names) != len(positions):
            issues.append("action_size_mismatch")
    if action_type == "joint_deltas" and not action.get("deltas"):
        issues.append("missing_action_deltas")
    return issues


def quality_issues(row: dict[str, Any]) -> list[str]:
    quality = row.get("quality") if isinstance(row.get("quality"), dict) else {}
    status = str(quality.get("status") or "")
    if status not in {"passed", "warn"}:
        return [f"quality_status:{status or 'missing'}"]
    return []


def classify_row(row: dict[str, Any], *, split: str, require_real_action: bool, allow_warn: bool) -> dict[str, Any]:
    issues = []
    issues.extend(observation_issues(row))
    issues.extend(action_issues(row, require_real_action=require_real_action))
    issues.extend(quality_issues(row))
    quality = row.get("quality") if isinstance(row.get("quality"), dict) else {}
    quality_status = str(quality.get("status") or "")
    if quality_status == "warn" and not allow_warn:
        issues.append("warn_sample_not_allowed")

    action = row.get("action") if isinstance(row.get("action"), dict) else {}
    if not issues and split == "train":
        route = "trainable"
    elif issues and split != "rejected":
        route = "debug_only"
    else:
        route = "rejected"
    return {
        "sample_index": row.get("sample_index"),
        "timestamp": row.get("timestamp"),
        "source_split": split,
        "route": route,
        "issues": issues,
        "quality_status": quality_status,
        "action_type": action.get("type"),
        "action_source": action.get("source"),
    }


def evaluate_candidate(
    candidate_path: Path,
    *,
    output_dir: Path | None = None,
    require_real_action: bool = False,
    allow_warn: bool = False,
) -> dict[str, Any]:
    candidate_dir = resolve_candidate_dir(candidate_path)
    manifest_path = candidate_dir / "manifest.json"
    manifest = load_json(manifest_path)
    paths = sample_paths(candidate_dir, manifest)
    rows_by_split = {split: load_jsonl(path) for split, path in paths.items()}

    decisions: list[dict[str, Any]] = []
    for split, rows in rows_by_split.items():
        for row in rows:
            decisions.append(
                classify_row(row, split=split, require_real_action=require_real_action, allow_warn=allow_warn)
            )

    route_counts = Counter(decision["route"] for decision in decisions)
    issue_counts = Counter(issue for decision in decisions for issue in decision["issues"])
    action_type_counts = Counter(str(decision.get("action_type") or "missing") for decision in decisions)
    trainable_count = route_counts.get("trainable", 0)
    blocked = trainable_count == 0
    status = "blocked" if blocked else "trainable_smoke"
    if require_real_action and trainable_count > 0:
        status = "trainable_real"

    output_dir = output_dir.resolve() if output_dir else candidate_dir / "trainability"
    report_path = output_dir / "trainability-report.json"
    decisions_path = output_dir / "sample-decisions.jsonl"
    report = {
        "schema": "so101_trainable_candidate_gate_v1",
        "candidate_dir": str(candidate_dir),
        "candidate_manifest": str(manifest_path),
        "status": status,
        "require_real_action": require_real_action,
        "allow_warn": allow_warn,
        "sample_count": len(decisions),
        "trainable_sample_count": trainable_count,
        "debug_only_sample_count": route_counts.get("debug_only", 0),
        "rejected_sample_count": route_counts.get("rejected", 0),
        "route_counts": dict(sorted(route_counts.items())),
        "issue_counts": dict(sorted(issue_counts.items())),
        "action_type_counts": dict(sorted(action_type_counts.items())),
        "policy": {
            "smoke_training": "Gazebo execution labels are acceptable for local smoke training only.",
            "real_training": "require_real_action=true requires follower_joint_action labels.",
            "warn_samples": "warn samples are excluded unless allow_warn=true.",
        },
        "paths": {
            "report": str(report_path.resolve()),
            "sample_decisions": str(decisions_path.resolve()),
        },
    }
    write_json(report_path, report)
    write_jsonl(decisions_path, decisions)
    return {"report": report, "report_path": report_path, "decisions_path": decisions_path}


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate whether a LeRobot candidate package is trainable.")
    parser.add_argument("candidate", help="Path to candidate directory or manifest.json")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--require-real-action", action="store_true")
    parser.add_argument("--allow-warn", action="store_true")
    parser.add_argument("--fail-on-blocked", action="store_true")
    args = parser.parse_args()

    result = evaluate_candidate(
        Path(args.candidate),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        require_real_action=args.require_real_action,
        allow_warn=args.allow_warn,
    )
    print(json.dumps({"report_path": str(result["report_path"]), **result["report"]}, ensure_ascii=False, indent=2))
    if args.fail_on_blocked and result["report"]["status"] == "blocked":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
