#!/usr/bin/env python3
"""Build a detector/projection quality smoke report from recorded vision artifacts."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_no}: {exc}") from exc
            if isinstance(row, dict):
                rows.append(row)
    return rows


def write_yaml(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(dict(payload), sort_keys=False, allow_unicode=True), encoding="utf-8")


def distance(left: Sequence[float] | None, right: Sequence[float] | None) -> float | None:
    if not left or not right or len(left) != 3 or len(right) != 3:
        return None
    try:
        return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(left, right)))
    except (TypeError, ValueError):
        return None


def pixel_distance(left: Sequence[float] | None, right: Sequence[float] | None) -> float | None:
    if not left or not right or len(left) != 2 or len(right) != 2:
        return None
    try:
        return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(left, right)))
    except (TypeError, ValueError):
        return None


def same_xyz(left: Any, right: Any, tolerance: float = 1e-6) -> bool:
    if not isinstance(left, list) or not isinstance(right, list) or len(left) != len(right):
        return False
    try:
        return all(abs(float(a) - float(b)) <= tolerance for a, b in zip(left, right))
    except (TypeError, ValueError):
        return False


def event_stamp_key(event: Mapping[str, Any]) -> tuple[int, int]:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    stamp = payload.get("stamp") if isinstance(payload.get("stamp"), dict) else {}
    stamp_ns = int(event.get("stamp_ns") or 0)
    if not stamp_ns and stamp:
        stamp_ns = int(stamp.get("sec") or 0) * 1_000_000_000 + int(stamp.get("nanosec") or 0)
    return stamp_ns, int(event.get("received_wall_ms") or 0)


def nearest_by_time(anchor: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    if not candidates:
        return None
    anchor_stamp, anchor_wall = event_stamp_key(anchor)
    anchor_value = anchor_stamp or anchor_wall * 1_000_000
    return min(candidates, key=lambda item: abs((event_stamp_key(item)[0] or event_stamp_key(item)[1] * 1_000_000) - anchor_value))


def target_by_category(targets: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for target in targets:
        category = str(target.get("category") or "")
        if category and category not in result:
            result[category] = target
    return result


def detection_by_category(detections: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for detection in detections:
        category = str(detection.get("category") or "")
        if category and category not in result:
            result[category] = detection
    return result


def summarize(values: Sequence[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "p50": None, "p90": None, "max": None}
    ordered = sorted(values)

    def percentile(q: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        rank = (len(ordered) - 1) * q
        lower = int(rank)
        upper = min(lower + 1, len(ordered) - 1)
        weight = rank - lower
        return ordered[lower] * (1.0 - weight) + ordered[upper] * weight

    return {
        "mean": statistics.fmean(ordered),
        "p50": percentile(0.5),
        "p90": percentile(0.9),
        "max": max(ordered),
    }


def parse_expected_target(value: str) -> tuple[str, list[float]]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected CATEGORY=x,y,z")
    category, xyz_text = value.split("=", 1)
    xyz = [float(part.strip()) for part in xyz_text.replace("[", "").replace("]", "").split(",") if part.strip()]
    if not category or len(xyz) != 3:
        raise argparse.ArgumentTypeError("expected CATEGORY=x,y,z")
    return category, xyz


def build_quality_report(
    events_path: Path,
    *,
    expected_targets: Mapping[str, Sequence[float]] | None = None,
    max_world_error_m: float = 0.05,
    max_pixel_error_px: float = 5.0,
) -> dict[str, Any]:
    events = load_jsonl(events_path)
    detection_events = [event for event in events if event.get("stream") == "detections"]
    target_events = [event for event in events if event.get("stream") == "vision_targets"]
    benchmark_events = [event for event in events if event.get("stream") == "benchmark_result"]
    expected_targets = expected_targets or {}

    samples: list[dict[str, Any]] = []
    miss_counts: Counter[str] = Counter()
    false_positive_counts: Counter[str] = Counter()
    clamp_counts: Counter[str] = Counter()
    raw_world_errors: list[float] = []
    canonical_world_errors: list[float] = []
    pixel_errors: list[float] = []

    anchors: Sequence[Mapping[str, Any]] = benchmark_events or target_events
    for index, anchor in enumerate(anchors):
        benchmark_payload = anchor.get("payload") if anchor.get("stream") == "benchmark_result" else {}
        target_event = (
            nearest_by_time(anchor, target_events)
            if anchor.get("stream") == "benchmark_result"
            else anchor
        )
        detection_event = nearest_by_time(anchor, detection_events)
        target_payload = target_event.get("payload") if isinstance(target_event, Mapping) else {}
        detection_payload = detection_event.get("payload") if isinstance(detection_event, Mapping) else {}
        projected_targets = target_by_category(target_payload.get("targets") or [])
        detections = detection_by_category(detection_payload.get("detections") or [])

        benchmark_target = benchmark_payload.get("target_object") if isinstance(benchmark_payload, dict) else None
        categories = set(projected_targets) | set(detections) | set(expected_targets)
        if isinstance(benchmark_target, dict) and benchmark_target.get("category"):
            categories.add(str(benchmark_target["category"]))

        for category in sorted(categories):
            projected = projected_targets.get(category)
            detection = detections.get(category)
            expected_xyz = list(expected_targets[category]) if category in expected_targets else None
            raw_world_xyz = projected.get("world_xyz") if projected else None
            canonical_world_xyz = raw_world_xyz
            source = "vision_target"
            expected_pixel = None
            if isinstance(benchmark_target, dict) and str(benchmark_target.get("category") or "") == category:
                raw_world_xyz = benchmark_target.get("raw_world_xyz") or raw_world_xyz
                canonical_world_xyz = benchmark_target.get("world_xyz") or canonical_world_xyz
                expected_xyz = expected_xyz or canonical_world_xyz
                expected_pixel = benchmark_target.get("pixel_center")
                source = "benchmark_result"

            raw_error = distance(raw_world_xyz, expected_xyz)
            canonical_error = distance(canonical_world_xyz, expected_xyz)
            pixel_error = pixel_distance(
                projected.get("pixel_center") if projected else None,
                expected_pixel,
            )
            if raw_error is not None:
                raw_world_errors.append(raw_error)
            if canonical_error is not None:
                canonical_world_errors.append(canonical_error)
            if pixel_error is not None:
                pixel_errors.append(pixel_error)

            clamp_reason = ""
            if raw_world_xyz and canonical_world_xyz and not same_xyz(raw_world_xyz, canonical_world_xyz):
                clamp_reason = "raw_world_xyz_adjusted_to_canonical_workspace"
                clamp_counts[clamp_reason] += 1
            if category in expected_targets and not projected:
                miss_counts[category] += 1
            if projected and category not in expected_targets and not benchmark_target:
                false_positive_counts[category] += 1

            samples.append(
                {
                    "sample_index": index,
                    "category": category,
                    "source": source,
                    "detection_present": detection is not None,
                    "target_present": projected is not None,
                    "raw_world_xyz": raw_world_xyz,
                    "canonical_world_xyz": canonical_world_xyz,
                    "expected_world_xyz": expected_xyz,
                    "raw_world_error_m": raw_error,
                    "canonical_world_error_m": canonical_error,
                    "pixel_error_px": pixel_error,
                    "clamp_reason": clamp_reason,
                }
            )

    status = "passed"
    if miss_counts:
        status = "failed"
    elif canonical_world_errors and max(canonical_world_errors) > max_world_error_m:
        status = "warn"
    elif pixel_errors and max(pixel_errors) > max_pixel_error_px:
        status = "warn"

    return {
        "schema": "so101_vision_projection_quality_smoke_v1",
        "status": status,
        "events_path": str(events_path.resolve()),
        "sample_count": len(samples),
        "event_counts": {
            "detections": len(detection_events),
            "vision_targets": len(target_events),
            "benchmark_results": len(benchmark_events),
        },
        "thresholds": {
            "max_world_error_m": max_world_error_m,
            "max_pixel_error_px": max_pixel_error_px,
        },
        "summary": {
            "raw_world_error_m": summarize(raw_world_errors),
            "canonical_world_error_m": summarize(canonical_world_errors),
            "pixel_error_px": summarize(pixel_errors),
            "miss_counts": dict(sorted(miss_counts.items())),
            "false_positive_counts": dict(sorted(false_positive_counts.items())),
            "clamp_reason_counts": dict(sorted(clamp_counts.items())),
        },
        "samples": samples[:50],
        "boundary": (
            "This is a detector/projection data-quality smoke over Gazebo or recorded artifacts. "
            "It does not validate real YOLO quality, real grasp success, or trainable_real labels."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-path", required=True)
    parser.add_argument("--report-path", default="docs/generated/acceptance/vision-projection-quality.yaml")
    parser.add_argument("--expected-target", action="append", type=parse_expected_target, default=[])
    parser.add_argument("--max-world-error-m", type=float, default=0.05)
    parser.add_argument("--max-pixel-error-px", type=float, default=5.0)
    args = parser.parse_args()

    report = build_quality_report(
        Path(args.events_path),
        expected_targets=dict(args.expected_target),
        max_world_error_m=args.max_world_error_m,
        max_pixel_error_px=args.max_pixel_error_px,
    )
    write_yaml(Path(args.report_path), report)
    print(yaml.safe_dump({"status": report["status"], "report_path": args.report_path}, sort_keys=False))
    return 0 if report["status"] in {"passed", "warn"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
