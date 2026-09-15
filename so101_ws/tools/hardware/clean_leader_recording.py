#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


CLEANING_SCHEMA_VERSION = "leader_recording_cleaning.v1"
ANNOTATION_SCHEMA_VERSION = "leader_recording_annotation.v1"


@dataclass(frozen=True)
class RecordingLine:
    line_no: int
    stamp_ns: int
    payload: dict[str, Any]


def timestamp_now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_recording_lines(path: Path) -> list[RecordingLine]:
    records: list[RecordingLine] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_no}: payload is not a JSON object")
        stamp_ns = int(payload.get("stamp_ns", 0))
        records.append(RecordingLine(line_no=line_no, stamp_ns=stamp_ns, payload=payload))
    if not records:
        raise ValueError(f"no frames found in {path}")
    return records


def compute_timing_summary(records: list[RecordingLine]) -> dict[str, Any]:
    if not records:
        return {
            "frame_count": 0,
            "first_stamp_ns": None,
            "last_stamp_ns": None,
            "duration_sec": 0.0,
            "sample_rate_hz": None,
            "avg_frame_gap_sec": None,
            "max_frame_gap_sec": None,
        }

    first_stamp_ns = records[0].stamp_ns
    last_stamp_ns = records[-1].stamp_ns
    duration_sec = max((last_stamp_ns - first_stamp_ns) / 1_000_000_000.0, 0.0)
    gaps_sec = [
        max((right.stamp_ns - left.stamp_ns) / 1_000_000_000.0, 0.0)
        for left, right in zip(records, records[1:])
    ]
    sample_rate_hz = None
    if duration_sec > 0.0:
        sample_rate_hz = round(len(records) / duration_sec, 3)

    return {
        "frame_count": len(records),
        "first_stamp_ns": first_stamp_ns,
        "last_stamp_ns": last_stamp_ns,
        "duration_sec": round(duration_sec, 6),
        "sample_rate_hz": sample_rate_hz,
        "avg_frame_gap_sec": round(sum(gaps_sec) / len(gaps_sec), 6) if gaps_sec else None,
        "max_frame_gap_sec": round(max(gaps_sec), 6) if gaps_sec else None,
    }


def clean_timestamp_sequence(records: list[RecordingLine]) -> tuple[list[RecordingLine], list[dict[str, Any]], dict[str, int]]:
    kept: list[RecordingLine] = []
    removed: list[dict[str, Any]] = []
    duplicate_count = 0
    non_monotonic_count = 0

    last_kept: RecordingLine | None = None
    for record in records:
        if last_kept is None or record.stamp_ns > last_kept.stamp_ns:
            kept.append(record)
            last_kept = record
            continue

        reason = "duplicate_timestamp" if record.stamp_ns == last_kept.stamp_ns else "non_monotonic_timestamp"
        if reason == "duplicate_timestamp":
            duplicate_count += 1
        else:
            non_monotonic_count += 1
        removed.append(
            {
                "line_no": record.line_no,
                "stamp_ns": record.stamp_ns,
                "reason": reason,
                "previous_kept_line_no": last_kept.line_no,
                "previous_kept_stamp_ns": last_kept.stamp_ns,
                "delta_ns": record.stamp_ns - last_kept.stamp_ns,
            }
        )

    return kept, removed, {
        "duplicate_timestamp_count": duplicate_count,
        "non_monotonic_timestamp_count": non_monotonic_count,
        "removed_frame_count": len(removed),
    }


def build_cleaning_report(
    *,
    input_path: Path,
    cleaned_output_path: Path,
    source_sha256: str,
    source_records: list[RecordingLine],
    cleaned_records: list[RecordingLine],
    removed_frames: list[dict[str, Any]],
    counters: dict[str, int],
) -> dict[str, Any]:
    input_summary = compute_timing_summary(source_records)
    cleaned_summary = compute_timing_summary(cleaned_records)
    labels: list[str] = []
    if counters["duplicate_timestamp_count"] > 0:
        labels.append("duplicate_timestamp")
    if counters["non_monotonic_timestamp_count"] > 0:
        labels.append("non_monotonic_timestamp")

    return {
        "schema_version": CLEANING_SCHEMA_VERSION,
        "generated_at": timestamp_now_iso(),
        "tool": {
            "name": "clean_leader_recording",
            "version": "1.0.0",
            "mode": "timestamp_axis_only",
        },
        "input": {
            "path": str(input_path.resolve()),
            "sha256": source_sha256,
            **input_summary,
        },
        "output": {
            "path": str(cleaned_output_path.resolve()),
            **cleaned_summary,
        },
        "summary": {
            **counters,
            "changed": bool(removed_frames),
            "labels": labels,
        },
        "removed_frames": removed_frames,
    }


def build_annotation(
    *,
    input_path: Path,
    cleaned_output_path: Path,
    cleaning_report_path: Path,
    source_sha256: str,
    counters: dict[str, int],
) -> dict[str, Any]:
    source_status = "invalid_result" if counters["removed_frame_count"] > 0 else "passed"
    cleaned_status = "cleaned_from_invalid" if counters["removed_frame_count"] > 0 else "passed"
    reasons: list[str] = []
    if counters["duplicate_timestamp_count"] > 0:
        reasons.append("duplicate_timestamp")
    if counters["non_monotonic_timestamp_count"] > 0:
        reasons.append("non_monotonic_timestamp")

    return {
        "schema_version": ANNOTATION_SCHEMA_VERSION,
        "generated_at": timestamp_now_iso(),
        "source_path": str(input_path.resolve()),
        "cleaned_path": str(cleaned_output_path.resolve()),
        "cleaning_report_path": str(cleaning_report_path.resolve()),
        "source_sha256": source_sha256,
        "source_status": source_status,
        "cleaned_status": cleaned_status,
        "reasons": reasons,
        "usable_for_regression": True,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_cleaned_recording(path: Path, records: list[RecordingLine]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(record.payload, ensure_ascii=False) for record in records)
    path.write_text(content + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clean leader recording JSONL by removing duplicate/non-monotonic timestamps without changing joint values."
    )
    parser.add_argument("--input", required=True, help="Input leader recording JSONL")
    parser.add_argument("--cleaned-output", required=True, help="Output cleaned JSONL path")
    parser.add_argument("--report-output", required=True, help="Output cleaning report JSON path")
    parser.add_argument("--annotation-output", required=True, help="Output annotation JSON path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.input).resolve()
    cleaned_output_path = Path(args.cleaned_output).resolve()
    report_output_path = Path(args.report_output).resolve()
    annotation_output_path = Path(args.annotation_output).resolve()

    source_records = load_recording_lines(input_path)
    cleaned_records, removed_frames, counters = clean_timestamp_sequence(source_records)
    source_sha256 = sha256_file(input_path)

    write_cleaned_recording(cleaned_output_path, cleaned_records)
    report = build_cleaning_report(
        input_path=input_path,
        cleaned_output_path=cleaned_output_path,
        source_sha256=source_sha256,
        source_records=source_records,
        cleaned_records=cleaned_records,
        removed_frames=removed_frames,
        counters=counters,
    )
    annotation = build_annotation(
        input_path=input_path,
        cleaned_output_path=cleaned_output_path,
        cleaning_report_path=report_output_path,
        source_sha256=source_sha256,
        counters=counters,
    )
    write_json(report_output_path, report)
    write_json(annotation_output_path, annotation)

    result = {
        "input_path": str(input_path),
        "cleaned_output_path": str(cleaned_output_path),
        "report_output_path": str(report_output_path),
        "annotation_output_path": str(annotation_output_path),
        "source_sha256": source_sha256,
        "removed_frame_count": counters["removed_frame_count"],
        "duplicate_timestamp_count": counters["duplicate_timestamp_count"],
        "non_monotonic_timestamp_count": counters["non_monotonic_timestamp_count"],
        "source_status": annotation["source_status"],
        "cleaned_status": annotation["cleaned_status"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
