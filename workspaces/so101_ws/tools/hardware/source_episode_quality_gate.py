#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


@dataclass(frozen=True)
class Frame:
    stamp_ns: int
    joint_names: list[str]
    positions: list[float]


def load_recording(path: Path) -> list[Frame]:
    frames: list[Frame] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        joint_names = [str(value) for value in payload["joint_names"]]
        positions = [float(value) for value in payload["positions"]]
        if len(joint_names) != len(positions):
            raise ValueError(f"{path}:{line_no}: joint_names/positions length mismatch")
        frames.append(Frame(stamp_ns=int(payload["stamp_ns"]), joint_names=joint_names, positions=positions))
    if not frames:
        raise ValueError(f"no frames in {path}")
    return frames


def parse_urdf_joint_limits(path: Path) -> dict[str, dict[str, float]]:
    root = ElementTree.fromstring(path.read_text(encoding="utf-8"))
    limits: dict[str, dict[str, float]] = {}
    for joint in root.findall("joint"):
        name = joint.attrib.get("name")
        limit = joint.find("limit")
        if not name or limit is None:
            continue
        limits[name] = {
            key: float(value)
            for key, value in limit.attrib.items()
            if key in {"lower", "upper", "velocity", "effort"}
        }
    return limits


def _empty_joint_report(limit: dict[str, float] | None) -> dict[str, Any]:
    return {
        "limit": limit or {},
        "position": {
            "min_rad": None,
            "max_rad": None,
            "below_lower_count": 0,
            "above_upper_count": 0,
            "max_lower_violation_rad": 0.0,
            "max_upper_violation_rad": 0.0,
        },
        "velocity": {
            "max_abs_velocity_rad_s": 0.0,
            "velocity_limit_rad_s": (round(float(limit["velocity"]), 6) if limit and "velocity" in limit else None),
            "violation_count": 0,
            "max_violation_rad_s": 0.0,
        },
    }


def evaluate_source_quality(
    frames: list[Frame],
    joint_limits: dict[str, dict[str, float]],
    *,
    position_tolerance_rad: float,
    velocity_scale: float,
) -> dict[str, Any]:
    joint_names = list(frames[0].joint_names)
    if any(frame.joint_names != joint_names for frame in frames):
        return {
            "status": "source_quality_failed",
            "reasons": ["joint_order_changed"],
            "joint_names": joint_names,
            "joints": {},
        }

    reports = {name: _empty_joint_report(joint_limits.get(name)) for name in joint_names}
    reasons: list[str] = []

    for joint_index, joint_name in enumerate(joint_names):
        limit = joint_limits.get(joint_name)
        values = [float(frame.positions[joint_index]) for frame in frames]
        report = reports[joint_name]
        position = report["position"]
        position["min_rad"] = round(min(values), 6)
        position["max_rad"] = round(max(values), 6)
        if limit:
            lower = limit.get("lower")
            upper = limit.get("upper")
            lower_violations = [lower - value for value in values if lower is not None and value < lower - position_tolerance_rad]
            upper_violations = [value - upper for value in values if upper is not None and value > upper + position_tolerance_rad]
            position["below_lower_count"] = len(lower_violations)
            position["above_upper_count"] = len(upper_violations)
            position["max_lower_violation_rad"] = round(max(lower_violations), 6) if lower_violations else 0.0
            position["max_upper_violation_rad"] = round(max(upper_violations), 6) if upper_violations else 0.0
            if lower_violations or upper_violations:
                reasons.append(f"{joint_name}:position_limit_violation")

        velocity = report["velocity"]
        velocity_limit = float(limit["velocity"]) * velocity_scale if limit and "velocity" in limit else None
        max_abs_velocity = 0.0
        velocity_violations: list[float] = []
        for left, right in zip(frames, frames[1:]):
            dt = (right.stamp_ns - left.stamp_ns) / 1_000_000_000.0
            if dt <= 0.0:
                continue
            observed = abs((float(right.positions[joint_index]) - float(left.positions[joint_index])) / dt)
            max_abs_velocity = max(max_abs_velocity, observed)
            if velocity_limit is not None and observed > velocity_limit:
                velocity_violations.append(observed - velocity_limit)
        velocity["max_abs_velocity_rad_s"] = round(max_abs_velocity, 6)
        if velocity_limit is not None:
            velocity["velocity_limit_rad_s"] = round(velocity_limit, 6)
        velocity["violation_count"] = len(velocity_violations)
        velocity["max_violation_rad_s"] = round(max(velocity_violations), 6) if velocity_violations else 0.0
        if velocity_violations:
            reasons.append(f"{joint_name}:velocity_limit_violation")

    unique_reasons = sorted(set(reasons))
    return {
        "status": "source_quality_failed" if unique_reasons else "passed",
        "reasons": unique_reasons,
        "joint_names": joint_names,
        "frame_count": len(frames),
        "duration_sec": round(max((frames[-1].stamp_ns - frames[0].stamp_ns) / 1_000_000_000.0, 0.0), 6),
        "position_tolerance_rad": position_tolerance_rad,
        "velocity_scale": velocity_scale,
        "joints": reports,
    }


def build_report(
    *,
    recording_path: Path,
    urdf_path: Path,
    position_tolerance_rad: float,
    velocity_scale: float,
) -> dict[str, Any]:
    frames = load_recording(recording_path)
    limits = parse_urdf_joint_limits(urdf_path)
    quality = evaluate_source_quality(
        frames,
        limits,
        position_tolerance_rad=position_tolerance_rad,
        velocity_scale=velocity_scale,
    )
    return {
        "schema_version": "source_episode_quality_gate.v1",
        "recording_path": str(recording_path.resolve()),
        "urdf_path": str(urdf_path.resolve()),
        "quality": quality,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate source episode joint limits and velocity limits before replay.")
    parser.add_argument("--recording", required=True, help="Source recording JSONL")
    parser.add_argument("--urdf", required=True, help="URDF containing joint limits")
    parser.add_argument("--output", required=True, help="Output source-quality JSON")
    parser.add_argument("--position-tolerance-rad", type=float, default=1e-6)
    parser.add_argument("--velocity-scale", type=float, default=1.0, help="Multiplier applied to URDF velocity limits")
    parser.add_argument("--fail-on-violation", action="store_true", help="Exit non-zero when source quality fails")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(
        recording_path=Path(args.recording).resolve(),
        urdf_path=Path(args.urdf).resolve(),
        position_tolerance_rad=max(float(args.position_tolerance_rad), 0.0),
        velocity_scale=max(float(args.velocity_scale), 1e-9),
    )
    write_json(Path(args.output).resolve(), report)
    status = report["quality"]["status"]
    print(json.dumps({"status": status, "reasons": report["quality"]["reasons"], "output": str(Path(args.output).resolve())}, ensure_ascii=False, indent=2))
    if args.fail_on_violation and status != "passed":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
