#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_recording(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError(f"no rows in {path}")
    return rows


def find_window(rows: list[dict[str, Any]], *, start_t_sec: float, end_t_sec: float) -> list[dict[str, Any]]:
    first_stamp_ns = int(rows[0]["stamp_ns"])
    selected = []
    for row in rows:
        t_sec = (int(row["stamp_ns"]) - first_stamp_ns) / 1_000_000_000.0
        if t_sec < start_t_sec or t_sec > end_t_sec:
            continue
        selected.append(dict(row))
    if not selected:
        raise ValueError(f"no rows in window [{start_t_sec}, {end_t_sec}]")
    return selected


def build_probe_rows(rows: list[dict[str, Any]], *, joint_name: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    joint_names = [str(value) for value in rows[0]["joint_names"]]
    if joint_name not in joint_names:
        raise ValueError(f"joint {joint_name!r} not in joint_names {joint_names}")
    joint_index = joint_names.index(joint_name)
    frozen_positions = [float(value) for value in rows[0]["positions"]]
    probe_rows = []
    target_min = None
    target_max = None
    for row in rows:
        positions = [float(value) for value in row["positions"]]
        target_value = positions[joint_index]
        probe_positions = list(frozen_positions)
        probe_positions[joint_index] = target_value
        payload = dict(row)
        payload["positions"] = probe_positions
        velocities = payload.get("velocities") or []
        if velocities:
            frozen_velocities = [0.0 for _ in probe_positions]
            if len(velocities) == len(probe_positions):
                frozen_velocities[joint_index] = float(velocities[joint_index])
            payload["velocities"] = frozen_velocities
        probe_rows.append(payload)
        target_min = target_value if target_min is None else min(target_min, target_value)
        target_max = target_value if target_max is None else max(target_max, target_value)
    summary = {
        "joint_name": joint_name,
        "joint_index": joint_index,
        "frame_count": len(probe_rows),
        "target_min_rad": round(float(target_min), 6),
        "target_max_rad": round(float(target_max), 6),
        "frozen_positions": [round(value, 6) for value in frozen_positions],
    }
    return probe_rows, summary


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a single-joint probe recording by freezing all other joints in a time window.")
    parser.add_argument("--input", required=True, help="Input recording JSONL")
    parser.add_argument("--joint-name", required=True, help="Joint to keep dynamic")
    parser.add_argument("--start-t-sec", type=float, required=True, help="Window start time relative to first stamp")
    parser.add_argument("--end-t-sec", type=float, required=True, help="Window end time relative to first stamp")
    parser.add_argument("--output", required=True, help="Output probe JSONL")
    parser.add_argument("--summary-output", required=True, help="Output summary JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.input).resolve()
    rows = load_recording(input_path)
    window_rows = find_window(rows, start_t_sec=float(args.start_t_sec), end_t_sec=float(args.end_t_sec))
    probe_rows, summary = build_probe_rows(window_rows, joint_name=str(args.joint_name))
    output_path = Path(args.output).resolve()
    write_jsonl(output_path, probe_rows)
    payload = {
        "schema_version": "single_joint_probe_recording.v1",
        "input_path": str(input_path),
        "output_path": str(output_path),
        "start_t_sec": float(args.start_t_sec),
        "end_t_sec": float(args.end_t_sec),
        **summary,
    }
    write_json(Path(args.summary_output).resolve(), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
