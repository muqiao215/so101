#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


DEFAULT_RECORDINGS_DIR = Path("docs/generated/leader-recordings")
DEFAULT_OUTPUT_DIR = Path("docs/generated/leader-waypoints")
PROFILE_DEFAULTS = {
    "stable": {
        "motion_epsilon_rad": 0.02,
        "min_stable_sec": 0.4,
        "dedupe_epsilon_rad": 0.08,
    },
    "dense": {
        "motion_epsilon_rad": 0.03,
        "min_stable_sec": 0.3,
        "dedupe_epsilon_rad": 0.05,
    },
}


@dataclass
class RecordingFrame:
    stamp_ns: int
    joint_names: list[str]
    positions: list[float]


@dataclass
class StableSegment:
    start_index: int
    end_index: int
    start_stamp_ns: int
    end_stamp_ns: int
    representative_positions: list[float]
    duration_sec: float


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


def resolve_recordings_dir(workspace_root: Path) -> Path:
    return workspace_root / DEFAULT_RECORDINGS_DIR


def resolve_output_dir(workspace_root: Path) -> Path:
    return workspace_root / DEFAULT_OUTPUT_DIR


def find_latest_recording(recordings_dir: Path) -> Path:
    candidates = sorted(
        [
            path
            for path in recordings_dir.glob("leader-recording-*.jsonl")
            if not path.name.endswith(".meta.json")
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"no leader recording jsonl found in {recordings_dir}")
    return candidates[0]


def load_recording(recording_path: Path) -> list[RecordingFrame]:
    frames: list[RecordingFrame] = []
    expected_joint_names: list[str] | None = None

    for line_no, raw_line in enumerate(recording_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"line {line_no}: payload is not a JSON object")

        joint_names = [str(value) for value in payload.get("joint_names", [])]
        positions = [float(value) for value in payload.get("positions", [])]
        stamp_ns = int(payload.get("stamp_ns", 0))

        if not joint_names:
            raise ValueError(f"line {line_no}: joint_names is empty")
        if len(positions) != len(joint_names):
            raise ValueError(
                f"line {line_no}: positions length mismatch, expected {len(joint_names)}, got {len(positions)}"
            )

        if expected_joint_names is None:
            expected_joint_names = joint_names
        elif joint_names != expected_joint_names:
            raise ValueError(f"line {line_no}: joint_names changed inside one recording")

        frames.append(
            RecordingFrame(
                stamp_ns=stamp_ns,
                joint_names=joint_names,
                positions=positions,
            )
        )

    if not frames:
        raise ValueError(f"recording is empty: {recording_path}")

    frames.sort(key=lambda frame: frame.stamp_ns)
    return frames


def max_abs_delta(a: Sequence[float], b: Sequence[float]) -> float:
    return max(abs(float(x) - float(y)) for x, y in zip(a, b))


def median_pose(frames: Sequence[RecordingFrame]) -> list[float]:
    columns = list(zip(*[frame.positions for frame in frames]))
    return [round(float(statistics.median(column)), 6) for column in columns]


def detect_stable_segments(
    frames: Sequence[RecordingFrame],
    *,
    motion_epsilon_rad: float,
    min_stable_sec: float,
    dedupe_epsilon_rad: float,
) -> list[StableSegment]:
    if len(frames) == 1:
        return [
            StableSegment(
                start_index=0,
                end_index=0,
                start_stamp_ns=frames[0].stamp_ns,
                end_stamp_ns=frames[0].stamp_ns,
                representative_positions=list(frames[0].positions),
                duration_sec=0.0,
            )
        ]

    segments: list[StableSegment] = []
    stable_start = 0

    for index in range(1, len(frames)):
        delta = max_abs_delta(frames[index - 1].positions, frames[index].positions)
        if delta > motion_epsilon_rad:
            stable_end = index - 1
            segment = build_stable_segment(frames, stable_start, stable_end)
            if segment.duration_sec >= min_stable_sec:
                if not segments or max_abs_delta(
                    segments[-1].representative_positions,
                    segment.representative_positions,
                ) > dedupe_epsilon_rad:
                    segments.append(segment)
            stable_start = index

    segment = build_stable_segment(frames, stable_start, len(frames) - 1)
    if segment.duration_sec >= min_stable_sec or not segments:
        if not segments or max_abs_delta(segments[-1].representative_positions, segment.representative_positions) > dedupe_epsilon_rad:
            segments.append(segment)

    return segments


def build_stable_segment(frames: Sequence[RecordingFrame], start_index: int, end_index: int) -> StableSegment:
    selected = frames[start_index : end_index + 1]
    start_stamp_ns = selected[0].stamp_ns
    end_stamp_ns = selected[-1].stamp_ns
    return StableSegment(
        start_index=start_index,
        end_index=end_index,
        start_stamp_ns=start_stamp_ns,
        end_stamp_ns=end_stamp_ns,
        representative_positions=median_pose(selected),
        duration_sec=max((end_stamp_ns - start_stamp_ns) / 1_000_000_000.0, 0.0),
    )


def fallback_segments(frames: Sequence[RecordingFrame], *, max_waypoints: int) -> list[StableSegment]:
    if max_waypoints <= 1 or len(frames) == 1:
        mid = len(frames) // 2
        return [build_stable_segment(frames, mid, mid)]

    if max_waypoints == 2:
        indexes = [0, len(frames) - 1]
    else:
        indexes = sorted(
            {
                round((len(frames) - 1) * step / (max_waypoints - 1))
                for step in range(max_waypoints)
            }
        )

    return [build_stable_segment(frames, index, index) for index in indexes]


def build_waypoint_names(prefix: str, count: int) -> list[str]:
    safe_prefix = sanitize_name(prefix)
    safe_prefix = safe_prefix or "leader_demo"
    return [f"{safe_prefix}_{index:02d}" for index in range(1, count + 1)]


def sanitize_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value.strip().lower()).strip("_")


def format_scalar(value: float) -> str:
    if abs(value) < 0.0000005:
        value = 0.0
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    if "." not in text:
        text += ".0"
    return text


def build_yaml_snippet(
    *,
    joint_names: Sequence[str],
    template_name: str,
    waypoint_names: Sequence[str],
    waypoint_positions: Sequence[Sequence[float]],
    source_recording: Path,
) -> str:
    lines = [
        f"# generated from {source_recording}",
        "joint_names:",
    ]
    for joint_name in joint_names:
        lines.append(f"- {joint_name}")

    lines.append("waypoints:")
    for name, positions in zip(waypoint_names, waypoint_positions):
        lines.append(f"  {name}:")
        for value in positions:
            lines.append(f"  - {format_scalar(float(value))}")

    lines.extend(
        [
            "action_templates:",
            f"  {template_name}:",
            "    detection_required: false",
            "    sequence:",
        ]
    )
    for name in waypoint_names:
        lines.append(f"    - {name}")
    return "\n".join(lines) + "\n"


def build_summary_payload(
    *,
    source_recording: Path,
    output_yaml_path: Path,
    frames: Sequence[RecordingFrame],
    segments: Sequence[StableSegment],
    waypoint_names: Sequence[str],
    extraction_method: str,
    motion_epsilon_rad: float,
    min_stable_sec: float,
    dedupe_epsilon_rad: float,
) -> dict[str, Any]:
    first_stamp_ns = frames[0].stamp_ns
    return {
        "source_recording": str(source_recording),
        "output_yaml_path": str(output_yaml_path),
        "frame_count": len(frames),
        "waypoint_count": len(segments),
        "extraction_method": extraction_method,
        "motion_epsilon_rad": motion_epsilon_rad,
        "min_stable_sec": min_stable_sec,
        "dedupe_epsilon_rad": dedupe_epsilon_rad,
        "waypoints": [
            {
                "name": name,
                "start_index": segment.start_index,
                "end_index": segment.end_index,
                "relative_start_sec": round((segment.start_stamp_ns - first_stamp_ns) / 1_000_000_000.0, 3),
                "relative_end_sec": round((segment.end_stamp_ns - first_stamp_ns) / 1_000_000_000.0, 3),
                "duration_sec": round(segment.duration_sec, 3),
                "positions": [round(value, 6) for value in segment.representative_positions],
            }
            for name, segment in zip(waypoint_names, segments)
        ],
    }


def choose_segments(
    frames: Sequence[RecordingFrame],
    *,
    motion_epsilon_rad: float,
    min_stable_sec: float,
    dedupe_epsilon_rad: float,
    max_waypoints: int,
) -> tuple[list[StableSegment], str]:
    stable_segments = detect_stable_segments(
        frames,
        motion_epsilon_rad=motion_epsilon_rad,
        min_stable_sec=min_stable_sec,
        dedupe_epsilon_rad=dedupe_epsilon_rad,
    )
    if len(stable_segments) >= 2:
        return stable_segments[:max_waypoints], "stable_segments"
    fallback = fallback_segments(frames, max_waypoints=min(max_waypoints, 6))
    return fallback, "fallback_sampling"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a leader recording JSONL into waypoints.yaml-compatible draft snippets."
    )
    parser.add_argument("--input", help="Path to a leader recording JSONL. Default: latest recording.")
    parser.add_argument("--template-name", default="leader_demo", help="Output action template name.")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_DEFAULTS.keys()),
        default="stable",
        help="Extraction preset. 'stable' is conservative, 'dense' keeps shorter pauses.",
    )
    parser.add_argument(
        "--waypoint-prefix",
        default="",
        help="Waypoint name prefix. Default: reuse template name.",
    )
    parser.add_argument(
        "--motion-epsilon-rad",
        type=float,
        default=None,
        help="Two consecutive frames within this max joint delta are treated as stable.",
    )
    parser.add_argument(
        "--min-stable-sec",
        type=float,
        default=None,
        help="Minimum dwell time for a stable segment to become a waypoint.",
    )
    parser.add_argument(
        "--dedupe-epsilon-rad",
        type=float,
        default=None,
        help="If two extracted poses are closer than this, collapse them.",
    )
    parser.add_argument(
        "--max-waypoints",
        type=int,
        default=12,
        help="Upper bound for extracted waypoint count.",
    )
    parser.add_argument(
        "--output-yaml",
        default="",
        help="Output YAML path. Default: docs/generated/leader-waypoints/<recording>.waypoints.yaml",
    )
    parser.add_argument(
        "--summary-json",
        default="",
        help="Optional summary JSON path. Default: alongside output YAML.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    workspace_root = discover_workspace_root(Path(__file__))
    profile = PROFILE_DEFAULTS[args.profile]
    motion_epsilon_rad = max(
        float(args.motion_epsilon_rad if args.motion_epsilon_rad is not None else profile["motion_epsilon_rad"]),
        0.0001,
    )
    min_stable_sec = max(
        float(args.min_stable_sec if args.min_stable_sec is not None else profile["min_stable_sec"]),
        0.0,
    )
    dedupe_epsilon_rad = max(
        float(args.dedupe_epsilon_rad if args.dedupe_epsilon_rad is not None else profile["dedupe_epsilon_rad"]),
        0.0001,
    )

    recording_path = Path(args.input).resolve() if args.input else find_latest_recording(resolve_recordings_dir(workspace_root))
    frames = load_recording(recording_path)
    joint_names = frames[0].joint_names

    segments, extraction_method = choose_segments(
        frames,
        motion_epsilon_rad=motion_epsilon_rad,
        min_stable_sec=min_stable_sec,
        dedupe_epsilon_rad=dedupe_epsilon_rad,
        max_waypoints=max(args.max_waypoints, 2),
    )

    waypoint_prefix = args.waypoint_prefix or args.template_name
    waypoint_names = build_waypoint_names(waypoint_prefix, len(segments))
    waypoint_positions = [segment.representative_positions for segment in segments]

    safe_template_name = sanitize_name(args.template_name) or "leader_demo"
    default_output_path = resolve_output_dir(workspace_root) / f"{recording_path.stem}.{safe_template_name}.waypoints.yaml"
    output_yaml_path = Path(args.output_yaml).resolve() if args.output_yaml else default_output_path
    output_yaml_path.parent.mkdir(parents=True, exist_ok=True)

    summary_json_path = (
        Path(args.summary_json).resolve()
        if args.summary_json
        else output_yaml_path.with_suffix(".summary.json")
    )
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)

    yaml_text = build_yaml_snippet(
        joint_names=joint_names,
        template_name=args.template_name,
        waypoint_names=waypoint_names,
        waypoint_positions=waypoint_positions,
        source_recording=recording_path,
    )
    output_yaml_path.write_text(yaml_text, encoding="utf-8")

    summary_payload = build_summary_payload(
        source_recording=recording_path,
        output_yaml_path=output_yaml_path,
        frames=frames,
        segments=segments,
        waypoint_names=waypoint_names,
        extraction_method=extraction_method,
        motion_epsilon_rad=motion_epsilon_rad,
        min_stable_sec=min_stable_sec,
        dedupe_epsilon_rad=dedupe_epsilon_rad,
    )
    summary_json_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"source_recording={recording_path}")
    print(f"frames={len(frames)}")
    print(f"profile={args.profile}")
    print(f"extraction_method={extraction_method}")
    print(f"waypoint_count={len(segments)}")
    print(f"output_yaml={output_yaml_path}")
    print(f"summary_json={summary_json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
