#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


STREAMS = ("image", "detections", "vision_targets", "joint_states", "task_status", "benchmark_result")


@dataclass(frozen=True)
class TimedEvent:
    stream: str
    event: dict[str, Any]
    stamp_ns: int
    wall_ms: int
    index: int


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stamp_ns_from_payload(payload: dict[str, Any]) -> int:
    stamp = payload.get("stamp")
    if isinstance(stamp, dict):
        return int(stamp.get("sec") or 0) * 1_000_000_000 + int(stamp.get("nanosec") or 0)
    return 0


def event_time_key(event: dict[str, Any]) -> tuple[int, int]:
    stream = str(event.get("stream") or "")
    wall_ms = int(event.get("received_wall_ms") or 0)
    stamp_ns = int(event.get("stamp_ns") or 0)
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    if not stamp_ns and stream in {"detections", "vision_targets"}:
        stamp_ns = stamp_ns_from_payload(payload)
    if not stamp_ns and payload and isinstance(payload.get("ts"), (int, float)):
        stamp_ns = int(payload["ts"]) * 1_000_000
    return stamp_ns, wall_ms


def load_events(events_path: Path) -> dict[str, list[TimedEvent]]:
    streams = {stream: [] for stream in STREAMS}
    with Path(events_path).open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            text = line.strip()
            if not text:
                continue
            event = json.loads(text)
            stream = str(event.get("stream") or "")
            if stream not in streams:
                continue
            stamp_ns, wall_ms = event_time_key(event)
            streams[stream].append(TimedEvent(stream=stream, event=event, stamp_ns=stamp_ns, wall_ms=wall_ms, index=index))
    for values in streams.values():
        values.sort(key=lambda item: (item.stamp_ns or item.wall_ms, item.wall_ms, item.index))
    return streams


def nearest_event(anchor: TimedEvent, candidates: list[TimedEvent], *, prefer_stamp: bool = True) -> tuple[TimedEvent | None, float | None]:
    if not candidates:
        return None, None
    anchor_value = anchor.stamp_ns if prefer_stamp and anchor.stamp_ns else anchor.wall_ms * 1_000_000
    best = min(
        candidates,
        key=lambda item: abs((item.stamp_ns if prefer_stamp and item.stamp_ns else item.wall_ms * 1_000_000) - anchor_value),
    )
    best_value = best.stamp_ns if prefer_stamp and best.stamp_ns else best.wall_ms * 1_000_000
    return best, round(abs(best_value - anchor_value) / 1_000_000_000.0, 6)


def image_anchor_events(images: list[TimedEvent], *, require_snapshot: bool) -> list[TimedEvent]:
    if not require_snapshot:
        return images
    return [item for item in images if item.event.get("snapshot_path")]


def compact_detection(event: TimedEvent | None) -> dict[str, Any] | None:
    if event is None:
        return None
    payload = event.event.get("payload") or {}
    detections = payload.get("detections") or []
    return {
        "source": payload.get("source"),
        "count": payload.get("count", len(detections)),
        "detections": detections,
    }


def compact_vision_target(event: TimedEvent | None) -> dict[str, Any] | None:
    if event is None:
        return None
    payload = event.event.get("payload") or {}
    targets = payload.get("targets") or []
    return {
        "source": payload.get("source"),
        "target_frame": payload.get("target_frame"),
        "table_z": payload.get("table_z"),
        "count": payload.get("count", len(targets)),
        "targets": targets,
    }


def compact_joint_state(event: TimedEvent | None) -> dict[str, Any] | None:
    if event is None:
        return None
    return {
        "joint_names": event.event.get("joint_names") or [],
        "positions": event.event.get("positions") or [],
        "velocities": event.event.get("velocities") or [],
    }


def compact_task_status(event: TimedEvent | None) -> dict[str, Any] | None:
    if event is None:
        return None
    payload = event.event.get("payload") or {}
    return {
        "requestId": payload.get("requestId"),
        "state": payload.get("state"),
        "code": payload.get("code"),
        "message": payload.get("message"),
        "ts": payload.get("ts"),
    }


def compact_benchmark_result(event: TimedEvent | None) -> dict[str, Any] | None:
    if event is None:
        return None
    payload = event.event.get("payload") or {}
    return {
        "schema": payload.get("schema"),
        "target_object": payload.get("target_object"),
        "grasp_candidate": payload.get("grasp_candidate"),
        "plan_result": payload.get("plan_result"),
        "execution_trace": payload.get("execution_trace"),
        "evaluation_result": payload.get("evaluation_result"),
        "promotion_note": payload.get("promotion_note"),
    }


def build_sample(
    *,
    episode_dir: Path,
    sample_index: int,
    image_event: TimedEvent,
    detection_event: TimedEvent | None,
    detection_delta_sec: float | None,
    target_event: TimedEvent | None,
    target_delta_sec: float | None,
    joint_event: TimedEvent | None,
    joint_delta_sec: float | None,
    status_event: TimedEvent | None,
    status_delta_sec: float | None,
    benchmark_event: TimedEvent | None,
    benchmark_delta_sec: float | None,
) -> dict[str, Any]:
    image = image_event.event
    snapshot_path = image.get("snapshot_path")
    image_path = str((episode_dir / snapshot_path).resolve()) if snapshot_path else None
    return {
        "sample_index": sample_index,
        "anchor": {
            "stream": "image",
            "stamp_ns": image_event.stamp_ns,
            "received_wall_ms": image_event.wall_ms,
            "frame_id": image.get("frame_id"),
            "image_path": image_path,
            "image_relative_path": snapshot_path,
            "width": image.get("width"),
            "height": image.get("height"),
            "encoding": image.get("encoding"),
        },
        "alignment": {
            "detection_delta_sec": detection_delta_sec,
            "vision_target_delta_sec": target_delta_sec,
            "joint_state_delta_sec": joint_delta_sec,
            "task_status_delta_sec": status_delta_sec,
            "benchmark_result_delta_sec": benchmark_delta_sec,
        },
        "detection": compact_detection(detection_event),
        "vision_target": compact_vision_target(target_event),
        "joint_state": compact_joint_state(joint_event),
        "task_status": compact_task_status(status_event),
        "benchmark_result": compact_benchmark_result(benchmark_event),
    }


def validate_samples(
    samples: list[dict[str, Any]],
    *,
    max_delta_sec: float,
    max_detection_delta_sec: float | None = None,
    max_vision_target_delta_sec: float | None = None,
    max_joint_state_delta_sec: float | None = None,
    max_task_status_delta_sec: float | None = None,
) -> dict[str, Any]:
    missing = {"detection": 0, "vision_target": 0, "joint_state": 0, "task_status": 0}
    large_delta = {"detection": 0, "vision_target": 0, "joint_state": 0, "task_status": 0}
    thresholds = {
        "detection": max_delta_sec if max_detection_delta_sec is None else max_detection_delta_sec,
        "vision_target": max_delta_sec if max_vision_target_delta_sec is None else max_vision_target_delta_sec,
        "joint_state": max_delta_sec if max_joint_state_delta_sec is None else max_joint_state_delta_sec,
        "task_status": max_delta_sec if max_task_status_delta_sec is None else max_task_status_delta_sec,
    }
    for sample in samples:
        for key in missing:
            if sample.get(key) is None:
                missing[key] += 1
        alignment = sample.get("alignment") or {}
        for key, delta_key in (
            ("detection", "detection_delta_sec"),
            ("vision_target", "vision_target_delta_sec"),
            ("joint_state", "joint_state_delta_sec"),
            ("task_status", "task_status_delta_sec"),
        ):
            value = alignment.get(delta_key)
            if value is not None and float(value) > thresholds[key]:
                large_delta[key] += 1
    status = "passed"
    if any(missing.values()):
        status = "failed"
    elif any(large_delta.values()):
        status = "warn"
    return {"status": status, "missing": missing, "large_delta": large_delta, "max_delta_sec": max_delta_sec, "thresholds": thresholds}


def build_dataset(
    episode_dir: Path,
    *,
    output_dir: Path | None = None,
    require_snapshot: bool = True,
    max_delta_sec: float = 0.25,
    max_detection_delta_sec: float | None = None,
    max_vision_target_delta_sec: float | None = None,
    max_joint_state_delta_sec: float | None = None,
    max_task_status_delta_sec: float | None = 2.0,
) -> dict[str, Any]:
    episode_dir = Path(episode_dir).resolve()
    manifest = load_json(episode_dir / "manifest.json")
    streams = load_events(episode_dir / "events.jsonl")
    anchors = image_anchor_events(streams["image"], require_snapshot=require_snapshot)
    output_dir = Path(output_dir).resolve() if output_dir else episode_dir / "dataset"
    output_dir.mkdir(parents=True, exist_ok=True)

    samples: list[dict[str, Any]] = []
    for sample_index, image_event in enumerate(anchors):
        detection, detection_delta = nearest_event(image_event, streams["detections"], prefer_stamp=True)
        target, target_delta = nearest_event(image_event, streams["vision_targets"], prefer_stamp=True)
        joint, joint_delta = nearest_event(image_event, streams["joint_states"], prefer_stamp=True)
        status, status_delta = nearest_event(image_event, streams["task_status"], prefer_stamp=False)
        benchmark, benchmark_delta = nearest_event(image_event, streams["benchmark_result"], prefer_stamp=False)
        samples.append(
            build_sample(
                episode_dir=episode_dir,
                sample_index=sample_index,
                image_event=image_event,
                detection_event=detection,
                detection_delta_sec=detection_delta,
                target_event=target,
                target_delta_sec=target_delta,
                joint_event=joint,
                joint_delta_sec=joint_delta,
                status_event=status,
                status_delta_sec=status_delta,
                benchmark_event=benchmark,
                benchmark_delta_sec=benchmark_delta,
            )
        )

    validation = validate_samples(
        samples,
        max_delta_sec=max_delta_sec,
        max_detection_delta_sec=max_detection_delta_sec,
        max_vision_target_delta_sec=max_vision_target_delta_sec,
        max_joint_state_delta_sec=max_joint_state_delta_sec,
        max_task_status_delta_sec=max_task_status_delta_sec,
    )
    samples_path = output_dir / "samples.jsonl"
    with samples_path.open("w", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")

    index = {
        "schema": "so101_vision_dataset_adapter_v1",
        "source_episode": str(episode_dir),
        "source_manifest": str((episode_dir / "manifest.json").resolve()),
        "source_episode_id": manifest.get("episode_id"),
        "sample_count": len(samples),
        "require_snapshot": require_snapshot,
        "max_delta_sec": max_delta_sec,
        "delta_thresholds": validation["thresholds"],
        "samples_path": str(samples_path.resolve()),
        "validation": validation,
        "source_event_counts": manifest.get("event_counts") or {},
    }
    index_path = output_dir / "dataset-index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"index": index, "index_path": index_path, "samples_path": samples_path}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode_dir")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--include-all-images", action="store_true")
    parser.add_argument("--max-delta-sec", type=float, default=0.25)
    parser.add_argument("--max-detection-delta-sec", type=float, default=None)
    parser.add_argument("--max-vision-target-delta-sec", type=float, default=None)
    parser.add_argument("--max-joint-state-delta-sec", type=float, default=None)
    parser.add_argument("--max-task-status-delta-sec", type=float, default=2.0)
    args = parser.parse_args()

    result = build_dataset(
        Path(args.episode_dir),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        require_snapshot=not args.include_all_images,
        max_delta_sec=args.max_delta_sec,
        max_detection_delta_sec=args.max_detection_delta_sec,
        max_vision_target_delta_sec=args.max_vision_target_delta_sec,
        max_joint_state_delta_sec=args.max_joint_state_delta_sec,
        max_task_status_delta_sec=args.max_task_status_delta_sec,
    )
    print(json.dumps({"index_path": str(result["index_path"]), "samples_path": str(result["samples_path"]), **result["index"]}, ensure_ascii=False, indent=2))
    return 0 if result["index"]["validation"]["status"] in {"passed", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
