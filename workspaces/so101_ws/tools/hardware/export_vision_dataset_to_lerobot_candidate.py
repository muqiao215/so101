#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


SCHEMA = "so101_lerobot_candidate_v1"
DEFAULT_TASK = "pick visible target from Gazebo overhead camera"
WARN_POLICIES = {"debug_only", "reject", "include_candidate"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def sample_quality(sample: dict[str, Any], *, thresholds: dict[str, float]) -> dict[str, Any]:
    missing = []
    for key in ("detection", "vision_target", "joint_state", "task_status"):
        if sample.get(key) is None:
            missing.append(key)

    large_delta = []
    alignment = sample.get("alignment") or {}
    for key, delta_key in (
        ("detection", "detection_delta_sec"),
        ("vision_target", "vision_target_delta_sec"),
        ("joint_state", "joint_state_delta_sec"),
        ("task_status", "task_status_delta_sec"),
    ):
        value = alignment.get(delta_key)
        if value is not None and float(value) > thresholds[key]:
            large_delta.append(key)

    status = "passed"
    reasons = []
    if missing:
        status = "failed"
        reasons.extend(f"missing:{key}" for key in missing)
    elif large_delta:
        status = "warn"
        reasons.extend(f"large_delta:{key}" for key in large_delta)

    return {
        "status": status,
        "reasons": reasons,
        "missing": missing,
        "large_delta": large_delta,
        "alignment": alignment,
        "thresholds": thresholds,
    }


def choose_target(sample: dict[str, Any], *, target_category: str | None) -> dict[str, Any] | None:
    target_payload = sample.get("vision_target") or {}
    targets = target_payload.get("targets") or []
    if target_category:
        for target in targets:
            if target.get("category") == target_category:
                return target
    return targets[0] if targets else None


def same_xyz(left: Any, right: Any, *, tolerance: float = 1e-6) -> bool:
    if not isinstance(left, list) or not isinstance(right, list) or len(left) != len(right):
        return False
    return all(abs(float(left_value) - float(right_value)) <= tolerance for left_value, right_value in zip(left, right))


def benchmark_matches_target(benchmark_target: dict[str, Any], target: dict[str, Any] | None) -> bool:
    if not benchmark_target or target is None:
        return False
    benchmark_category = benchmark_target.get("category")
    if benchmark_category is not None and benchmark_category != target.get("category"):
        return False
    target_xyz = target.get("world_xyz")
    raw_benchmark_xyz = benchmark_target.get("raw_world_xyz")
    if raw_benchmark_xyz is not None:
        return same_xyz(raw_benchmark_xyz, target_xyz)
    return same_xyz(benchmark_target.get("world_xyz"), target_xyz)


def timestamp_sec(sample: dict[str, Any], *, first_stamp_ns: int | None, sample_index: int, fps: float) -> float:
    anchor = sample.get("anchor") or {}
    stamp_ns = int(anchor.get("stamp_ns") or 0)
    if first_stamp_ns is not None and stamp_ns:
        return round((stamp_ns - first_stamp_ns) / 1_000_000_000.0, 6)
    return round(sample_index / fps, 6)


def copy_image_if_requested(
    *,
    sample: dict[str, Any],
    output_dir: Path,
    copy_images: bool,
) -> tuple[str | None, str | None]:
    anchor = sample.get("anchor") or {}
    image_path = anchor.get("image_path")
    if not image_path:
        return None, None
    src = Path(image_path)
    if not copy_images:
        return str(src), anchor.get("image_relative_path")
    dst = output_dir / "images" / src.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return str(dst.resolve()), str(dst.relative_to(output_dir))


def build_candidate_sample(
    sample: dict[str, Any],
    *,
    output_dir: Path,
    sample_index: int,
    first_stamp_ns: int | None,
    fps: float,
    task: str,
    target_category: str | None,
    thresholds: dict[str, float],
    copy_images: bool,
) -> dict[str, Any]:
    quality = sample_quality(sample, thresholds=thresholds)
    target = choose_target(sample, target_category=target_category)
    image_path, image_relative_path = copy_image_if_requested(sample=sample, output_dir=output_dir, copy_images=copy_images)
    anchor = sample.get("anchor") or {}
    joint_state = sample.get("joint_state") or {}
    benchmark_result = sample.get("benchmark_result") or {}
    benchmark_target = benchmark_result.get("target_object") or {}
    evaluation_result = benchmark_result.get("evaluation_result") or {}
    metrics = evaluation_result.get("metrics") or {}
    grasp_candidate = benchmark_result.get("grasp_candidate") or {}
    plan_result = benchmark_result.get("plan_result") or {}
    matched_benchmark = benchmark_matches_target(benchmark_target, target)
    canonical_target_xyz = benchmark_target.get("world_xyz") if matched_benchmark else None
    raw_target_xyz = benchmark_target.get("raw_world_xyz") if matched_benchmark else None
    target_xyz = canonical_target_xyz or (target.get("world_xyz") if target else None)
    if raw_target_xyz is None and target is not None:
        raw_target_xyz = target.get("world_xyz")

    return {
        "schema": SCHEMA,
        "sample_index": sample.get("sample_index", sample_index),
        "timestamp": timestamp_sec(sample, first_stamp_ns=first_stamp_ns, sample_index=sample_index, fps=fps),
        "task": task,
        "observation": {
            "images": {
                "overhead": {
                    "path": image_path,
                    "relative_path": image_relative_path,
                    "width": anchor.get("width"),
                    "height": anchor.get("height"),
                    "encoding": anchor.get("encoding"),
                    "frame_id": anchor.get("frame_id"),
                }
            },
            "state": {
                "joint_names": joint_state.get("joint_names") or [],
                "positions": joint_state.get("positions") or [],
                "velocities": joint_state.get("velocities") or [],
            },
        },
        "action": {
            "type": "vision_target_xyz",
            "target_category": target.get("category") if target else None,
            "target_xyz": target_xyz,
            "raw_target_xyz": raw_target_xyz,
            "confidence": target.get("confidence") if target else None,
            "note": "Primary target_xyz uses benchmark canonical target only when it matches the selected object; raw_target_xyz preserves projector output.",
            "selected_candidate_id": grasp_candidate.get("candidate_id") if matched_benchmark else None,
            "result_label": evaluation_result.get("result_label") if matched_benchmark else None,
            "reach_success": metrics.get("reach_success") if matched_benchmark else None,
            "min_distance_m": metrics.get("min_distance_m") if matched_benchmark else None,
            "planner_backend": plan_result.get("planner_backend") if matched_benchmark else None,
        },
        "source": {
            "detection": sample.get("detection"),
            "vision_target": sample.get("vision_target"),
            "task_status": sample.get("task_status"),
            "benchmark_result": benchmark_result,
        },
        "quality": quality,
    }


def route_sample(row: dict[str, Any], *, warn_policy: str) -> str:
    status = (row.get("quality") or {}).get("status")
    if status == "passed":
        return "train"
    if status == "warn":
        if warn_policy == "reject":
            return "rejected"
        if warn_policy == "include_candidate":
            return "train"
        return "debug"
    return "rejected"


def native_lerobot_probe() -> dict[str, Any]:
    try:
        from lerobot.datasets.lerobot_dataset import LeRobotDataset  # noqa: F401
    except Exception as exc:  # pragma: no cover - records host environment state.
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}"}
    return {"available": True, "reason": ""}


def export_candidate(
    dataset_index_path: Path,
    *,
    output_dir: Path | None = None,
    warn_policy: str = "debug_only",
    target_category: str | None = "red",
    fps: float = 5.0,
    task: str = DEFAULT_TASK,
    copy_images: bool = True,
) -> dict[str, Any]:
    if warn_policy not in WARN_POLICIES:
        raise ValueError(f"warn_policy must be one of {sorted(WARN_POLICIES)}")

    dataset_index_path = Path(dataset_index_path).resolve()
    index = load_json(dataset_index_path)
    samples = load_jsonl(Path(index["samples_path"]))
    output_dir = Path(output_dir).resolve() if output_dir else dataset_index_path.parent / "lerobot-candidate"
    output_dir.mkdir(parents=True, exist_ok=True)

    first_stamp_ns = None
    for sample in samples:
        stamp_ns = int((sample.get("anchor") or {}).get("stamp_ns") or 0)
        if stamp_ns:
            first_stamp_ns = stamp_ns
            break

    base_max_delta_sec = float(index.get("max_delta_sec") or 0.25)
    thresholds = {
        "detection": base_max_delta_sec,
        "vision_target": base_max_delta_sec,
        "joint_state": base_max_delta_sec,
        "task_status": base_max_delta_sec,
    }
    thresholds.update({key: float(value) for key, value in (index.get("delta_thresholds") or {}).items()})
    rows = [
        build_candidate_sample(
            sample,
            output_dir=output_dir,
            sample_index=sample_index,
            first_stamp_ns=first_stamp_ns,
            fps=fps,
            task=task,
            target_category=target_category,
            thresholds=thresholds,
            copy_images=copy_images,
        )
        for sample_index, sample in enumerate(samples)
    ]

    train_rows: list[dict[str, Any]] = []
    debug_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    for row in rows:
        route = route_sample(row, warn_policy=warn_policy)
        if route == "train":
            train_rows.append(row)
        elif route == "debug":
            debug_rows.append(row)
        else:
            rejected_rows.append(row)

    train_path = output_dir / "train_samples.jsonl"
    debug_path = output_dir / "debug_samples.jsonl"
    rejected_path = output_dir / "rejected_samples.jsonl"
    write_jsonl(train_path, train_rows)
    write_jsonl(debug_path, debug_rows)
    write_jsonl(rejected_path, rejected_rows)

    quality_counts = {"passed": 0, "warn": 0, "failed": 0}
    for row in rows:
        status = (row.get("quality") or {}).get("status")
        quality_counts[status] = quality_counts.get(status, 0) + 1

    manifest = {
        "schema": SCHEMA,
        "source_dataset_index": str(dataset_index_path),
        "source_episode_id": index.get("source_episode_id"),
        "source_schema": index.get("schema"),
        "sample_count": len(rows),
        "train_sample_count": len(train_rows),
        "debug_sample_count": len(debug_rows),
        "rejected_sample_count": len(rejected_rows),
        "quality_counts": quality_counts,
        "warn_policy": warn_policy,
        "delta_thresholds": thresholds,
        "promotion_policy": {
            "candidate": "passed samples may be used as LeRobot candidate rows",
            "debug_only": "warn samples are retained for diagnosis and excluded from train_samples.jsonl by default",
            "golden": "only passed samples with traceable source and repeated validation may be promoted",
        },
        "target_category": target_category,
        "fps": fps,
        "task": task,
        "paths": {
            "train_samples": str(train_path.resolve()),
            "debug_samples": str(debug_path.resolve()),
            "rejected_samples": str(rejected_path.resolve()),
        },
        "native_lerobot": native_lerobot_probe(),
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"manifest": manifest, "manifest_path": manifest_path}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_index")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--warn-policy", choices=sorted(WARN_POLICIES), default="debug_only")
    parser.add_argument("--target-category", default="red")
    parser.add_argument("--fps", type=float, default=5.0)
    parser.add_argument("--task", default=DEFAULT_TASK)
    parser.add_argument("--no-copy-images", action="store_true")
    args = parser.parse_args()

    result = export_candidate(
        Path(args.dataset_index),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        warn_policy=args.warn_policy,
        target_category=args.target_category or None,
        fps=args.fps,
        task=args.task,
        copy_images=not args.no_copy_images,
    )
    print(json.dumps({"manifest_path": str(result["manifest_path"]), **result["manifest"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
