#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


SCHEMA = "so101_lerobot_candidate_exec_actions_v1"
SOURCE_SCHEMA = "so101_lerobot_candidate_v1"
SPLIT_FILES = {
    "train": "train_samples.jsonl",
    "debug": "debug_samples.jsonl",
    "rejected": "rejected_samples.jsonl",
}


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


def split_paths(candidate_dir: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    resolved: dict[str, Path] = {}
    for split, filename in SPLIT_FILES.items():
        key = f"{split}_samples"
        resolved[split] = Path(paths[key]).resolve() if paths.get(key) else candidate_dir / filename
    return resolved


def row_timestamp(row: dict[str, Any]) -> float:
    value = row.get("timestamp")
    return float(value) if value is not None else float(row.get("sample_index") or 0)


def joint_state(row: dict[str, Any]) -> dict[str, Any]:
    return ((row.get("observation") or {}).get("state") or {}) if isinstance(row.get("observation"), dict) else {}


def joint_names(row: dict[str, Any]) -> list[str]:
    names = joint_state(row).get("joint_names") or []
    return [str(name) for name in names]


def joint_positions(row: dict[str, Any]) -> list[float]:
    positions = joint_state(row).get("positions") or []
    return [float(value) for value in positions]


def validate_next_action_pair(row: dict[str, Any], next_row: dict[str, Any]) -> str | None:
    names = joint_names(row)
    next_names = joint_names(next_row)
    positions = joint_positions(next_row)
    if not names:
        return "missing_current_joint_names"
    if not next_names:
        return "missing_next_joint_names"
    if names != next_names:
        return "joint_names_mismatch"
    if len(positions) != len(names):
        return "next_positions_size_mismatch"
    return None


def attach_next_joint_action(row: dict[str, Any], next_row: dict[str, Any], *, source_split: str) -> dict[str, Any]:
    updated = dict(row)
    original_action = row.get("action") if isinstance(row.get("action"), dict) else {}
    current_positions = joint_positions(row)
    next_positions = joint_positions(next_row)
    names = joint_names(row)
    timestamp = row_timestamp(row)
    next_timestamp = row_timestamp(next_row)
    updated["schema"] = SCHEMA
    updated["target_metadata"] = {
        "type": "vision_target_xyz",
        "target_category": original_action.get("target_category"),
        "target_xyz": original_action.get("target_xyz"),
        "confidence": original_action.get("confidence"),
        "source_action_note": original_action.get("note"),
    }
    updated["action"] = {
        "type": "joint_positions",
        "source": "gazebo_next_observation_joint_state",
        "source_split": source_split,
        "joint_names": names,
        "positions": next_positions,
        "deltas": [round(next_value - current_value, 9) for current_value, next_value in zip(current_positions, next_positions)],
        "timestamp": next_timestamp,
        "delta_sec": round(next_timestamp - timestamp, 6),
        "note": (
            "Gazebo executed-state action label derived from the next synchronized joint_state sample. "
            "This is stronger than vision_target_xyz, but still not a real follower hardware command."
        ),
    }
    source = dict(updated.get("source") or {})
    source["previous_action"] = original_action
    updated["source"] = source
    quality = dict(updated.get("quality") or {})
    reasons = list(quality.get("reasons") or [])
    reasons.append("execution_action:gazebo_next_observation_joint_state")
    quality["reasons"] = reasons
    quality["execution_action"] = {
        "status": "attached",
        "source": "gazebo_next_observation_joint_state",
        "delta_sec": round(next_timestamp - timestamp, 6),
    }
    updated["quality"] = quality
    return updated


def copy_or_link_image_paths(rows: list[dict[str, Any]], *, output_dir: Path) -> None:
    for row in rows:
        overhead = (((row.get("observation") or {}).get("images") or {}).get("overhead") or {})
        image_path = overhead.get("path")
        relative_path = overhead.get("relative_path")
        if not image_path or not relative_path:
            continue
        src = Path(image_path)
        if not src.exists():
            continue
        dst = output_dir / relative_path
        if dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        overhead["path"] = str(dst.resolve())


def attach_actions(
    candidate_path: Path,
    *,
    output_dir: Path | None = None,
    drop_terminal_train_sample: bool = True,
) -> dict[str, Any]:
    candidate_dir = resolve_candidate_dir(candidate_path)
    manifest_path = candidate_dir / "manifest.json"
    manifest = load_json(manifest_path)
    paths = split_paths(candidate_dir, manifest)
    output_dir = output_dir.resolve() if output_dir else candidate_dir.parent / "lerobot-candidate-exec-actions"
    output_dir.mkdir(parents=True, exist_ok=True)

    source_rows = {split: load_jsonl(path) for split, path in paths.items()}
    transformed: dict[str, list[dict[str, Any]]] = {split: [] for split in SPLIT_FILES}
    rejected_rows = list(source_rows.get("rejected") or [])
    missing_next_count = 0
    rejected_for_action_count = 0

    for split in ("train", "debug"):
        rows = source_rows[split]
        for index, row in enumerate(rows):
            next_row = rows[index + 1] if index + 1 < len(rows) else None
            if next_row is None:
                missing_next_count += 1
                if split == "train" and drop_terminal_train_sample:
                    rejected = dict(row)
                    rejected["schema"] = SCHEMA
                    quality = dict(rejected.get("quality") or {})
                    reasons = list(quality.get("reasons") or [])
                    reasons.append("missing_next_joint_state_for_execution_action")
                    quality["status"] = "failed"
                    quality["reasons"] = reasons
                    quality["execution_action"] = {"status": "missing_next_sample"}
                    rejected["quality"] = quality
                    rejected_rows.append(rejected)
                    rejected_for_action_count += 1
                    continue
                transformed[split].append(row)
                continue

            error = validate_next_action_pair(row, next_row)
            if error:
                rejected = dict(row)
                rejected["schema"] = SCHEMA
                quality = dict(rejected.get("quality") or {})
                reasons = list(quality.get("reasons") or [])
                reasons.append(f"execution_action:{error}")
                quality["status"] = "failed"
                quality["reasons"] = reasons
                quality["execution_action"] = {"status": "failed", "reason": error}
                rejected["quality"] = quality
                rejected_rows.append(rejected)
                rejected_for_action_count += 1
                continue
            transformed[split].append(attach_next_joint_action(row, next_row, source_split=split))

    transformed["rejected"] = rejected_rows
    for rows in transformed.values():
        copy_or_link_image_paths(rows, output_dir=output_dir)

    output_paths: dict[str, str] = {}
    for split, filename in SPLIT_FILES.items():
        path = output_dir / filename
        write_jsonl(path, transformed[split])
        output_paths[f"{split}_samples"] = str(path.resolve())

    manifest_out = {
        **manifest,
        "schema": SCHEMA,
        "source_schema": manifest.get("schema") or SOURCE_SCHEMA,
        "source_candidate_manifest": str(manifest_path.resolve()),
        "sample_count": sum(len(rows) for rows in transformed.values()),
        "train_sample_count": len(transformed["train"]),
        "debug_sample_count": len(transformed["debug"]),
        "rejected_sample_count": len(transformed["rejected"]),
        "action_labeling": {
            "status": "attached",
            "action_type": "joint_positions",
            "source": "gazebo_next_observation_joint_state",
            "drop_terminal_train_sample": drop_terminal_train_sample,
            "missing_next_count": missing_next_count,
            "rejected_for_action_count": rejected_for_action_count,
            "limitation": "Gazebo executed-state label, not a real follower hardware command.",
        },
        "paths": output_paths,
    }
    output_manifest_path = output_dir / "manifest.json"
    write_json(output_manifest_path, manifest_out)
    return {"manifest_path": output_manifest_path, "manifest": manifest_out}


def main() -> int:
    parser = argparse.ArgumentParser(description="Attach Gazebo execution action labels to LeRobot candidate rows.")
    parser.add_argument("candidate", help="Path to lerobot-candidate directory or manifest.json")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--keep-terminal-train-sample", action="store_true")
    args = parser.parse_args()

    result = attach_actions(
        Path(args.candidate),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        drop_terminal_train_sample=not args.keep_terminal_train_sample,
    )
    print(json.dumps({"manifest_path": str(result["manifest_path"]), **result["manifest"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
