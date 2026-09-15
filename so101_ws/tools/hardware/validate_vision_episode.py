#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REQUIRED_STREAMS = ("image", "detections", "vision_targets", "task_status", "joint_states")


@dataclass
class ValidationResult:
    status: str = "passed"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def fail(self, message: str) -> None:
        self.errors.append(message)
        self.status = "failed"

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        if self.status == "passed":
            self.status = "warn"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_events(events_path: Path):
    with events_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                yield line_no, {"_decode_error": str(exc)}
                continue
            yield line_no, payload


def validate_episode(episode_dir: Path, *, min_counts: dict[str, int] | None = None) -> ValidationResult:
    episode_dir = Path(episode_dir).resolve()
    result = ValidationResult()
    min_counts = min_counts or {
        "image": 1,
        "detections": 1,
        "vision_targets": 1,
        "task_status": 1,
        "joint_states": 1,
    }

    manifest_path = episode_dir / "manifest.json"
    events_path = episode_dir / "events.jsonl"
    if not manifest_path.exists():
        result.fail(f"missing manifest: {manifest_path}")
        return result
    if not events_path.exists():
        result.fail(f"missing events file: {events_path}")
        return result

    manifest = load_json(manifest_path)
    if manifest.get("schema") != "so101_vision_episode_v1":
        result.fail(f"unexpected schema: {manifest.get('schema')}")

    event_counts: dict[str, int] = {}
    first_wall_ms = 0
    last_wall_ms = 0
    non_monotonic_wall_count = 0
    decode_error_count = 0
    snapshot_paths: list[str] = []
    first_detection: dict[str, Any] | None = None
    first_target: dict[str, Any] | None = None

    for line_no, event in iter_events(events_path):
        if "_decode_error" in event:
            decode_error_count += 1
            result.fail(f"events.jsonl line {line_no} decode error: {event['_decode_error']}")
            continue
        stream = str(event.get("stream") or "unknown")
        event_counts[stream] = event_counts.get(stream, 0) + 1
        wall_ms = int(event.get("received_wall_ms") or 0)
        if wall_ms:
            if not first_wall_ms:
                first_wall_ms = wall_ms
            if last_wall_ms and wall_ms < last_wall_ms:
                non_monotonic_wall_count += 1
            last_wall_ms = wall_ms
        if stream == "image" and event.get("snapshot_path"):
            snapshot_paths.append(str(event["snapshot_path"]))
        if stream == "detections" and first_detection is None:
            payload = event.get("payload") or {}
            if isinstance(payload, dict):
                detections = payload.get("detections") or []
                first_detection = detections[0] if detections else None
        if stream == "vision_targets" and first_target is None:
            payload = event.get("payload") or {}
            if isinstance(payload, dict):
                targets = payload.get("targets") or []
                first_target = targets[0] if targets else None

    for stream, minimum in min_counts.items():
        actual = event_counts.get(stream, 0)
        if actual < minimum:
            result.fail(f"stream '{stream}' count {actual} < required {minimum}")

    manifest_counts = manifest.get("event_counts") or {}
    if isinstance(manifest_counts, dict):
        for stream in REQUIRED_STREAMS:
            if int(manifest_counts.get(stream, 0)) != int(event_counts.get(stream, 0)):
                result.warn(
                    f"manifest count mismatch for {stream}: manifest={manifest_counts.get(stream)} events={event_counts.get(stream, 0)}"
                )

    for relative_path in snapshot_paths:
        if not (episode_dir / relative_path).exists():
            result.fail(f"missing snapshot file: {relative_path}")

    if non_monotonic_wall_count:
        result.warn(f"non-monotonic received_wall_ms count: {non_monotonic_wall_count}")

    duration_sec = 0.0
    if first_wall_ms and last_wall_ms >= first_wall_ms:
        duration_sec = round((last_wall_ms - first_wall_ms) / 1000.0, 3)

    result.summary = {
        "episode_dir": str(episode_dir),
        "manifest_path": str(manifest_path),
        "events_path": str(events_path),
        "schema": manifest.get("schema"),
        "duration_sec": duration_sec,
        "manifest_duration_sec": manifest.get("duration_sec"),
        "event_counts": event_counts,
        "snapshot_count": len(snapshot_paths),
        "manifest_snapshot_count": manifest.get("image_snapshot_count"),
        "decode_error_count": decode_error_count,
        "non_monotonic_wall_count": non_monotonic_wall_count,
        "first_detection": first_detection,
        "first_target": first_target,
    }
    return result


def build_markdown_report(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    counts = summary.get("event_counts") or {}
    lines = [
        "# Vision Episode Report",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Episode: `{summary.get('episode_dir')}`",
        f"- Duration: `{summary.get('duration_sec')}` sec",
        f"- Snapshots: `{summary.get('snapshot_count')}`",
        "",
        "## Stream Counts",
        "",
    ]
    for stream in REQUIRED_STREAMS:
        lines.append(f"- `{stream}`: `{counts.get(stream, 0)}`")
    if report.get("errors"):
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {item}" for item in report["errors"])
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
    first_detection = summary.get("first_detection")
    first_target = summary.get("first_target")
    if first_detection:
        lines.extend(["", "## First Detection", "", f"```json\n{json.dumps(first_detection, ensure_ascii=False, indent=2)}\n```"])
    if first_target:
        lines.extend(["", "## First Target", "", f"```json\n{json.dumps(first_target, ensure_ascii=False, indent=2)}\n```"])
    return "\n".join(lines) + "\n"


def parse_min_counts(values: list[str]) -> dict[str, int]:
    counts = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"min count must be stream=count: {item}")
        stream, value = item.split("=", 1)
        counts[stream.strip()] = int(value)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode_dir")
    parser.add_argument("--report-json", default="")
    parser.add_argument("--report-md", default="")
    parser.add_argument("--min-count", action="append", default=[])
    args = parser.parse_args()

    min_counts = parse_min_counts(args.min_count) if args.min_count else None
    result = validate_episode(Path(args.episode_dir), min_counts=min_counts)
    report = {
        "status": result.status,
        "errors": result.errors,
        "warnings": result.warnings,
        "summary": result.summary,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    print(output, end="")
    if args.report_json:
        Path(args.report_json).write_text(output, encoding="utf-8")
    if args.report_md:
        Path(args.report_md).write_text(build_markdown_report(report), encoding="utf-8")
    return 0 if result.status in {"passed", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
