#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


SAMPLE_FILES = ("train_samples.jsonl", "debug_samples.jsonl", "rejected_samples.jsonl")
EXECUTION_ACTION_TYPES = {"follower_joint_action", "gazebo_joint_trajectory", "joint_positions", "joint_deltas"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def resolve_candidate_dir(path: Path) -> Path:
    path = Path(path).resolve()
    if path.is_file() and path.name == "manifest.json":
        return path.parent
    if path.is_dir():
        return path
    raise FileNotFoundError(f"candidate path does not exist: {path}")


def sample_paths(candidate_dir: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    manifest_paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    for split, filename in (
        ("train", "train_samples.jsonl"),
        ("debug", "debug_samples.jsonl"),
        ("rejected", "rejected_samples.jsonl"),
    ):
        key = f"{split}_samples"
        if manifest_paths.get(key):
            paths[split] = Path(manifest_paths[key])
        else:
            paths[split] = candidate_dir / filename
    return paths


def infer_action_fields(action: dict[str, Any]) -> set[str]:
    return {key for key, value in action.items() if value is not None}


def inspect_candidate(candidate_path: Path) -> dict[str, Any]:
    candidate_dir = resolve_candidate_dir(candidate_path)
    manifest_path = candidate_dir / "manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}
    paths = sample_paths(candidate_dir, manifest)

    action_type_counts: Counter[str] = Counter()
    split_counts: dict[str, int] = {}
    missing_action_count = 0
    action_fields: set[str] = set()
    examples: list[dict[str, Any]] = []

    for split, path in paths.items():
        rows = load_jsonl(path)
        split_counts[split] = len(rows)
        for row in rows:
            action = row.get("action") if isinstance(row.get("action"), dict) else {}
            action_type = str(action.get("type") or "missing")
            action_type_counts[action_type] += 1
            if action_type == "missing":
                missing_action_count += 1
            action_fields.update(infer_action_fields(action))
            if len(examples) < 5:
                examples.append(
                    {
                        "split": split,
                        "sample_index": row.get("sample_index"),
                        "action": action,
                    }
                )

    execution_action_types_present = sorted(set(action_type_counts) & EXECUTION_ACTION_TYPES)
    only_vision_target_xyz = bool(action_type_counts) and set(action_type_counts) == {"vision_target_xyz"}
    has_execution_action_labels = bool(execution_action_types_present)
    gap_status = "gap_confirmed" if only_vision_target_xyz or not has_execution_action_labels else "execution_action_present"
    if has_execution_action_labels:
        impact = (
            "Execution action labels are present. This candidate may be promoted beyond vision-only smoke, but the "
            "action source still determines training meaning: Gazebo executed-state labels are not real follower hardware commands."
        )
        next_steps = [
            "Keep vision_target_xyz as target metadata, not as policy action.",
            "Validate action timestamp alignment and source trace before training promotion.",
            "Replace or augment Gazebo executed-state labels with real follower command labels when hardware is available.",
        ]
    else:
        impact = (
            "Current candidate can train or validate vision target extraction, but must not be used as a complete "
            "imitation-learning action dataset until follower/Gazebo execution action labels are attached."
        )
        next_steps = [
            "Keep vision_target_xyz as target metadata, not as policy action.",
            "Attach follower joint action from real hardware logs or Gazebo controller commands.",
            "Re-run this report and require has_execution_action_labels=true before native LeRobot training promotion.",
        ]

    required_for_imitation = {
        "accepted_action_types": sorted(EXECUTION_ACTION_TYPES),
        "required_fields": [
            "action.type in accepted_action_types",
            "action.joint_names or trajectory joint_names",
            "action.positions or trajectory points",
            "action timestamp alignment to observation",
            "source execution trace: follower hardware or Gazebo controller command",
        ],
    }

    return {
        "schema": "so101_action_label_gap_report_v1",
        "candidate_dir": str(candidate_dir),
        "manifest_path": str(manifest_path) if manifest_path.exists() else None,
        "source_dataset_index": manifest.get("source_dataset_index"),
        "source_episode_id": manifest.get("source_episode_id"),
        "sample_counts": {
            "total": sum(split_counts.values()),
            **split_counts,
        },
        "action_type_counts": dict(sorted(action_type_counts.items())),
        "action_fields": sorted(action_fields),
        "missing_action_count": missing_action_count,
        "only_vision_target_xyz": only_vision_target_xyz,
        "has_execution_action_labels": has_execution_action_labels,
        "execution_action_types_present": execution_action_types_present,
        "gap_status": gap_status,
        "impact": impact,
        "required_for_imitation": required_for_imitation,
        "next_steps": next_steps,
        "examples": examples,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Action Label Gap Report",
        "",
        f"- Candidate: `{report['candidate_dir']}`",
        f"- Status: `{report['gap_status']}`",
        f"- Total samples: `{report['sample_counts']['total']}`",
        f"- Action types: `{json.dumps(report['action_type_counts'], sort_keys=True)}`",
        f"- Only `vision_target_xyz`: `{str(report['only_vision_target_xyz']).lower()}`",
        f"- Execution action labels present: `{str(report['has_execution_action_labels']).lower()}`",
        "",
        "## Impact",
        "",
        report["impact"],
        "",
        "## Required For Imitation",
        "",
    ]
    for item in report["required_for_imitation"]["required_fields"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Next Steps", ""])
    for item in report["next_steps"]:
        lines.append(f"- {item}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", help="Path to lerobot-candidate directory or manifest.json")
    parser.add_argument("--report-json", default="", help="Optional output JSON report path")
    parser.add_argument("--report-md", default="", help="Optional output Markdown report path")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when execution action labels are missing")
    args = parser.parse_args()

    report = inspect_candidate(Path(args.candidate))
    if args.report_json:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.report_md:
        report_md = Path(args.report_md)
        report_md.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(report, report_md)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if args.strict and not report["has_execution_action_labels"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
