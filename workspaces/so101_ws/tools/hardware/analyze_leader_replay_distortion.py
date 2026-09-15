#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


def load_recording(path: Path) -> dict[str, Any]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError(f"no rows in {path}")
    start_ns = int(rows[0]["stamp_ns"])
    joint_names = [str(value) for value in rows[0]["joint_names"]]
    samples = []
    for row in rows:
        samples.append(
            {
                "stamp_ns": int(row["stamp_ns"]),
                "t_sec": round((int(row["stamp_ns"]) - start_ns) / 1_000_000_000.0, 6),
                "positions": [float(value) for value in row["positions"]],
            }
        )
    return {
        "path": str(path.resolve()),
        "joint_names": joint_names,
        "samples": samples,
        "first_stamp_ns": start_ns,
        "last_stamp_ns": int(rows[-1]["stamp_ns"]),
        "duration_sec": samples[-1]["t_sec"],
    }


def load_command_dump(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "path": str(path.resolve()),
        "joint_names": [str(value) for value in payload["joint_names"]],
        "samples": [
            {
                "t_sec": float(point["time_from_start_sec"]),
                "positions": [float(value) for value in point["positions"]],
            }
            for point in payload.get("points", [])
        ],
    }


def load_controller_state(path: Path) -> dict[str, Any]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError(f"no rows in {path}")
    start_ns = int(rows[0]["stamp_ns"])
    joint_names = [str(value) for value in rows[0]["joint_names"]]
    reference_samples = []
    feedback_samples = []
    output_samples = []
    for row in rows:
        stamp_ns = int(row["stamp_ns"])
        t_sec = round((stamp_ns - start_ns) / 1_000_000_000.0, 6)
        reference_samples.append({"t_sec": t_sec, "positions": [float(value) for value in row["reference"]["positions"]]})
        feedback_samples.append({"t_sec": t_sec, "positions": [float(value) for value in row["feedback"]["positions"]]})
        output_samples.append({"t_sec": t_sec, "positions": [float(value) for value in row["output"]["positions"]]})
        reference_samples[-1]["stamp_ns"] = stamp_ns
        feedback_samples[-1]["stamp_ns"] = stamp_ns
        output_samples[-1]["stamp_ns"] = stamp_ns
    return {
        "path": str(path.resolve()),
        "joint_names": joint_names,
        "reference": reference_samples,
        "feedback": feedback_samples,
        "output": output_samples,
    }


def load_replay_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def interpolate_positions(samples: list[dict[str, Any]], t_sec: float) -> list[float]:
    if not samples:
        raise ValueError("samples is empty")
    if len(samples) == 1:
        return list(samples[0]["positions"])
    if t_sec <= samples[0]["t_sec"]:
        return list(samples[0]["positions"])
    if t_sec >= samples[-1]["t_sec"]:
        return list(samples[-1]["positions"])
    for left, right in zip(samples, samples[1:]):
        if t_sec > right["t_sec"]:
            continue
        dt = right["t_sec"] - left["t_sec"]
        if dt <= 0.0:
            return list(right["positions"])
        alpha = (t_sec - left["t_sec"]) / dt
        return [
            float(left_value + (right_value - left_value) * alpha)
            for left_value, right_value in zip(left["positions"], right["positions"])
        ]
    return list(samples[-1]["positions"])


def interpolate_positions_by_stamp(samples: list[dict[str, Any]], stamp_ns: int) -> list[float]:
    if not samples:
        raise ValueError("samples is empty")
    if len(samples) == 1:
        return list(samples[0]["positions"])
    if stamp_ns <= int(samples[0]["stamp_ns"]):
        return list(samples[0]["positions"])
    if stamp_ns >= int(samples[-1]["stamp_ns"]):
        return list(samples[-1]["positions"])
    for left, right in zip(samples, samples[1:]):
        right_stamp_ns = int(right["stamp_ns"])
        if stamp_ns > right_stamp_ns:
            continue
        left_stamp_ns = int(left["stamp_ns"])
        dt = right_stamp_ns - left_stamp_ns
        if dt <= 0:
            return list(right["positions"])
        alpha = (stamp_ns - left_stamp_ns) / dt
        return [
            float(left_value + (right_value - left_value) * alpha)
            for left_value, right_value in zip(left["positions"], right["positions"])
        ]
    return list(samples[-1]["positions"])


def extract_joint_values(samples: list[dict[str, Any]], joint_index: int) -> list[tuple[float, float]]:
    return [(float(sample["t_sec"]), float(sample["positions"][joint_index])) for sample in samples]


def parse_urdf_joint_limits(path: Path | None) -> dict[str, dict[str, float]]:
    if path is None:
        return {}
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


def series_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"min": None, "max": None, "range": None}
    minimum = min(values)
    maximum = max(values)
    return {"min": round(minimum, 6), "max": round(maximum, 6), "range": round(maximum - minimum, 6)}


def max_abs_velocity(samples: list[dict[str, Any]], joint_index: int) -> float:
    peak = 0.0
    for left, right in zip(samples, samples[1:]):
        dt = float(right["t_sec"]) - float(left["t_sec"])
        if dt <= 0.0:
            continue
        velocity = abs((float(right["positions"][joint_index]) - float(left["positions"][joint_index])) / dt)
        peak = max(peak, velocity)
    return round(peak, 6)


def limit_profile(values: list[float], limit: dict[str, float] | None) -> dict[str, Any]:
    profile: dict[str, Any] = {"limit": limit or {}, "stats": series_stats(values)}
    if not limit:
        profile.update({"below_lower_count": 0, "above_upper_count": 0, "max_lower_violation_rad": 0.0, "max_upper_violation_rad": 0.0})
        return profile
    lower = limit.get("lower")
    upper = limit.get("upper")
    below = [lower - value for value in values if lower is not None and value < lower]
    above = [value - upper for value in values if upper is not None and value > upper]
    profile.update(
        {
            "below_lower_count": len(below),
            "above_upper_count": len(above),
            "max_lower_violation_rad": round(max(below), 6) if below else 0.0,
            "max_upper_violation_rad": round(max(above), 6) if above else 0.0,
        }
    )
    return profile


def estimate_best_lag(
    reference_samples: list[dict[str, Any]],
    candidate_samples: list[dict[str, Any]],
    joint_index: int,
    *,
    lag_range_sec: float,
    lag_step_sec: float,
) -> dict[str, Any]:
    best_lag_sec = 0.0
    best_mae = math.inf
    shifts_considered = 0
    lag = -lag_range_sec
    while lag <= lag_range_sec + 1e-9:
        errors = []
        for sample in reference_samples:
            candidate_positions = interpolate_positions(candidate_samples, float(sample["t_sec"]) + lag)
            errors.append(abs(float(sample["positions"][joint_index]) - float(candidate_positions[joint_index])))
        mae = sum(errors) / len(errors) if errors else math.inf
        if mae < best_mae:
            best_mae = mae
            best_lag_sec = round(lag, 6)
        lag += lag_step_sec
        shifts_considered += 1
    return {
        "best_lag_sec": best_lag_sec,
        "mae_at_best_lag_rad": round(best_mae, 6),
        "search_range_sec": lag_range_sec,
        "search_step_sec": lag_step_sec,
        "shifts_considered": shifts_considered,
    }


def linear_fit(reference_values: list[float], candidate_values: list[float]) -> dict[str, Any]:
    count = min(len(reference_values), len(candidate_values))
    if count == 0:
        return {"slope": None, "offset": None}
    x_values = reference_values[:count]
    y_values = candidate_values[:count]
    mean_x = sum(x_values) / count
    mean_y = sum(y_values) / count
    variance_x = sum((value - mean_x) ** 2 for value in x_values)
    if variance_x <= 1e-12:
        slope = 0.0
    else:
        covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values))
        slope = covariance / variance_x
    offset = mean_y - slope * mean_x
    return {"slope": round(slope, 6), "offset": round(offset, 6)}


def rank_player_joint_matches(
    *,
    target_values: list[float],
    player_joint_names: list[str],
    player_series_by_joint: dict[str, list[float]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    rows = []
    for joint_name in player_joint_names:
        candidate_values = player_series_by_joint[joint_name]
        count = min(len(target_values), len(candidate_values))
        if count == 0:
            continue
        mae = sum(abs(left - right) for left, right in zip(target_values[:count], candidate_values[:count])) / count
        fit = linear_fit(candidate_values[:count], target_values[:count])
        rows.append(
            {
                "player_joint": joint_name,
                "mae_rad": round(mae, 6),
                "slope_to_target": fit["slope"],
                "offset_to_target": fit["offset"],
            }
        )
    rows.sort(key=lambda item: float(item["mae_rad"]))
    return rows[:limit]


def classify_joint_issue(*, slope: float | None, offset: float | None, best_lag_sec: float, moving_mae_rad: float, steady_mae_rad: float) -> str:
    if slope is None or offset is None:
        return "insufficient_data"
    if slope < -0.5:
        return "sign_flip_like"
    if abs(slope - 1.0) <= 0.2 and abs(offset) >= 0.2:
        return "offset_like"
    if 0.0 < slope < 0.8:
        return "amplitude_decay_like"
    if abs(best_lag_sec) >= 0.05 and moving_mae_rad > steady_mae_rad:
        return "lag_like"
    if moving_mae_rad > max(steady_mae_rad * 2.0, steady_mae_rad + 0.15):
        return "dynamic_transition_like"
    return "mixed_or_unclassified"


def pick_focus_joints(replay_result: dict[str, Any], count: int) -> list[str]:
    per_joint = replay_result.get("metrics", {}).get("per_joint") or {}
    ordered = sorted(
        per_joint.items(),
        key=lambda item: float((item[1] or {}).get("max_error_rad") or 0.0),
        reverse=True,
    )
    return [joint_name for joint_name, _ in ordered[:count]]


def build_segments(
    replay_result: dict[str, Any],
    focus_joints: list[str],
    *,
    window_sec: float,
) -> list[dict[str, Any]]:
    half_window = window_sec / 2.0
    top_samples = replay_result.get("diagnostics", {}).get("top_k_worst_samples") or []
    segments = []
    seen = set()
    for sample in top_samples:
        joint_name = str(sample.get("joint"))
        if joint_name not in focus_joints or joint_name in seen:
            continue
        center_t_sec = float(sample.get("t_sec") or 0.0)
        segments.append(
            {
                "joint": joint_name,
                "center_t_sec": round(center_t_sec, 6),
                "start_t_sec": round(max(center_t_sec - half_window, 0.0), 6),
                "end_t_sec": round(center_t_sec + half_window, 6),
                "reason": "worst_error_window",
            }
        )
        seen.add(joint_name)
    return segments


def build_compare_bundle(
    *,
    reference: dict[str, Any],
    command: dict[str, Any],
    controller: dict[str, Any],
    candidate: dict[str, Any],
    replay_result: dict[str, Any],
    focus_joints: list[str],
    window_sec: float,
) -> dict[str, Any]:
    joint_index_map = {name: index for index, name in enumerate(reference["joint_names"])}
    segments = build_segments(replay_result, focus_joints, window_sec=window_sec)
    bundle_segments = []
    for segment in segments:
        start_t_sec = float(segment["start_t_sec"])
        end_t_sec = float(segment["end_t_sec"])
        rows = []
        for sample in reference["samples"]:
            t_sec = float(sample["t_sec"])
            if t_sec < start_t_sec or t_sec > end_t_sec:
                continue
            row = {"t_sec": round(t_sec, 6), "joints": {}}
            for joint_name in focus_joints:
                joint_index = joint_index_map[joint_name]
                command_positions = interpolate_positions(command["samples"], t_sec)
                candidate_positions = interpolate_positions(candidate["samples"], t_sec)
                candidate_stamp_ns = int(candidate["first_stamp_ns"] + round(t_sec * 1_000_000_000))
                controller_reference = interpolate_positions_by_stamp(controller["reference"], candidate_stamp_ns)
                controller_feedback = interpolate_positions_by_stamp(controller["feedback"], candidate_stamp_ns)
                row["joints"][joint_name] = {
                    "reference": round(float(sample["positions"][joint_index]), 6),
                    "player_command": round(float(command_positions[joint_index]), 6),
                    "controller_reference": round(float(controller_reference[joint_index]), 6),
                    "controller_feedback": round(float(controller_feedback[joint_index]), 6),
                    "recorded_replay": round(float(candidate_positions[joint_index]), 6),
                }
            rows.append(row)
        bundle_segments.append({**segment, "rows": rows})
    return {
        "schema_version": "leader_replay_compare_bundle.v1",
        "focus_joints": focus_joints,
        "segments": bundle_segments,
    }


def build_joint_diagnostics(
    *,
    joint_name: str,
    joint_index: int,
    reference: dict[str, Any],
    command: dict[str, Any],
    controller: dict[str, Any],
    candidate: dict[str, Any],
    joint_limit: dict[str, float] | None,
    lag_range_sec: float,
    lag_step_sec: float,
    motion_epsilon_rad: float,
) -> dict[str, Any]:
    reference_values = [float(sample["positions"][joint_index]) for sample in reference["samples"]]
    candidate_values = [float(interpolate_positions(candidate["samples"], float(sample["t_sec"]))[joint_index]) for sample in reference["samples"]]
    command_values = [float(interpolate_positions(command["samples"], float(sample["t_sec"]))[joint_index]) for sample in reference["samples"]]
    controller_reference_values = [
        float(
            interpolate_positions_by_stamp(
                controller["reference"],
                int(candidate["first_stamp_ns"] + round(float(sample["t_sec"]) * 1_000_000_000)),
            )[joint_index]
        )
        for sample in reference["samples"]
    ]
    controller_feedback_values = [
        float(
            interpolate_positions_by_stamp(
                controller["feedback"],
                int(candidate["first_stamp_ns"] + round(float(sample["t_sec"]) * 1_000_000_000)),
            )[joint_index]
        )
        for sample in reference["samples"]
    ]
    player_series_by_joint = {
        other_joint_name: [
            float(interpolate_positions(command["samples"], float(sample["t_sec"]))[other_joint_index])
            for sample in reference["samples"]
        ]
        for other_joint_index, other_joint_name in enumerate(command["joint_names"])
    }
    moving_errors = []
    steady_errors = []
    for left, right, candidate_value in zip(reference["samples"], reference["samples"][1:], candidate_values[1:]):
        ref_prev = float(left["positions"][joint_index])
        ref_curr = float(right["positions"][joint_index])
        error = abs(ref_curr - candidate_value)
        if abs(ref_curr - ref_prev) > motion_epsilon_rad:
            moving_errors.append(error)
        else:
            steady_errors.append(error)
    moving_mae_rad = round(sum(moving_errors) / len(moving_errors), 6) if moving_errors else 0.0
    steady_mae_rad = round(sum(steady_errors) / len(steady_errors), 6) if steady_errors else 0.0
    lag = estimate_best_lag(
        reference["samples"],
        candidate["samples"],
        joint_index,
        lag_range_sec=lag_range_sec,
        lag_step_sec=lag_step_sec,
    )
    fit = linear_fit(reference_values, candidate_values)
    command_to_controller_mae = round(
        sum(abs(command_value - controller_value) for command_value, controller_value in zip(command_values, controller_reference_values))
        / len(command_values),
        6,
    )
    controller_to_recorded_mae = round(
        sum(abs(controller_value - recorded_value) for controller_value, recorded_value in zip(controller_feedback_values, candidate_values))
        / len(candidate_values),
        6,
    )
    issue = classify_joint_issue(
        slope=fit["slope"],
        offset=fit["offset"],
        best_lag_sec=float(lag["best_lag_sec"]),
        moving_mae_rad=moving_mae_rad,
        steady_mae_rad=steady_mae_rad,
    )
    return {
        "joint_name": joint_name,
        "best_lag": lag,
        "linear_fit_replay_vs_reference": fit,
        "layer_mae_rad": {
            "command_to_controller_reference": command_to_controller_mae,
            "controller_reference_to_recorded": controller_to_recorded_mae,
        },
        "limit_profile": {
            "reference": limit_profile(reference_values, joint_limit),
            "player_command": limit_profile(command_values, joint_limit),
            "recorded_replay": limit_profile(candidate_values, joint_limit),
        },
        "velocity_profile": {
            "reference_max_abs_velocity_rad_s": max_abs_velocity(reference["samples"], joint_index),
            "player_command_max_abs_velocity_rad_s": max_abs_velocity(command["samples"], joint_index),
            "recorded_replay_max_abs_velocity_rad_s": max_abs_velocity(candidate["samples"], joint_index),
            "urdf_velocity_limit_rad_s": round(float(joint_limit["velocity"]), 6)
            if joint_limit and "velocity" in joint_limit
            else None,
        },
        "controller_reference_player_match_rank": rank_player_joint_matches(
            target_values=controller_reference_values,
            player_joint_names=command["joint_names"],
            player_series_by_joint=player_series_by_joint,
        ),
        "controller_feedback_player_match_rank": rank_player_joint_matches(
            target_values=controller_feedback_values,
            player_joint_names=command["joint_names"],
            player_series_by_joint=player_series_by_joint,
        ),
        "moving_mae_rad": moving_mae_rad,
        "steady_mae_rad": steady_mae_rad,
        "issue_hypothesis": issue,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze replay distortion across reference, player command, controller state, and recorded replay.")
    parser.add_argument("--reference", required=True, help="Reference recording JSONL")
    parser.add_argument("--candidate", required=True, help="Replay-recorded candidate JSONL")
    parser.add_argument("--command-dump", required=True, help="Player command dump JSON")
    parser.add_argument("--controller-state", required=True, help="Controller state JSONL")
    parser.add_argument("--replay-result", required=True, help="Replay validator result JSON")
    parser.add_argument("--output", required=True, help="Output diagnostics JSON")
    parser.add_argument("--compare-bundle-output", required=True, help="Output compare bundle JSON")
    parser.add_argument("--focus-joints", default="", help="Comma separated joint names; default top-2 by max error")
    parser.add_argument("--window-sec", type=float, default=4.0, help="Window size for compare bundle segments")
    parser.add_argument("--lag-range-sec", type=float, default=0.5, help="Lag search range for per-joint estimation")
    parser.add_argument("--lag-step-sec", type=float, default=0.01, help="Lag search step")
    parser.add_argument("--motion-epsilon-rad", type=float, default=0.03, help="Threshold to split moving vs steady samples")
    parser.add_argument("--urdf", default="", help="Optional URDF path for joint limit diagnostics")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reference = load_recording(Path(args.reference).resolve())
    candidate = load_recording(Path(args.candidate).resolve())
    command = load_command_dump(Path(args.command_dump).resolve())
    controller = load_controller_state(Path(args.controller_state).resolve())
    replay_result = load_replay_result(Path(args.replay_result).resolve())
    joint_limits = parse_urdf_joint_limits(Path(args.urdf).resolve()) if str(args.urdf).strip() else {}

    if reference["joint_names"] != candidate["joint_names"]:
        raise ValueError("reference and candidate joint order mismatch")
    if reference["joint_names"] != command["joint_names"]:
        raise ValueError("reference and command joint order mismatch")
    if reference["joint_names"] != controller["joint_names"]:
        raise ValueError("reference and controller joint order mismatch")

    focus_joints = [joint.strip() for joint in args.focus_joints.split(",") if joint.strip()]
    if not focus_joints:
        focus_joints = pick_focus_joints(replay_result, count=2)
    joint_index_map = {name: index for index, name in enumerate(reference["joint_names"])}
    diagnostics = []
    for joint_name in focus_joints:
        if joint_name not in joint_index_map:
            continue
        diagnostics.append(
            build_joint_diagnostics(
                joint_name=joint_name,
                joint_index=joint_index_map[joint_name],
                reference=reference,
                command=command,
                controller=controller,
                candidate=candidate,
                joint_limit=joint_limits.get(joint_name),
                lag_range_sec=args.lag_range_sec,
                lag_step_sec=args.lag_step_sec,
                motion_epsilon_rad=args.motion_epsilon_rad,
            )
        )

    compare_bundle = build_compare_bundle(
        reference=reference,
        command=command,
        controller=controller,
        candidate=candidate,
        replay_result=replay_result,
        focus_joints=focus_joints,
        window_sec=args.window_sec,
    )
    write_json(Path(args.compare_bundle_output).resolve(), compare_bundle)

    result = {
        "schema_version": "leader_replay_distortion_diagnostics.v1",
        "reference_path": reference["path"],
        "candidate_path": candidate["path"],
        "command_dump_path": command["path"],
        "controller_state_path": controller["path"],
        "replay_result_path": str(Path(args.replay_result).resolve()),
        "alignment": {
            "method": "controller_state_absolute_stamp_to_candidate_recording_window",
            "candidate_first_stamp_ns": candidate["first_stamp_ns"],
            "candidate_last_stamp_ns": candidate["last_stamp_ns"],
            "controller_first_stamp_ns": controller["reference"][0]["stamp_ns"],
            "controller_last_stamp_ns": controller["reference"][-1]["stamp_ns"],
        },
        "urdf_path": str(Path(args.urdf).resolve()) if str(args.urdf).strip() else None,
        "focus_joints": focus_joints,
        "joint_diagnostics": diagnostics,
        "compare_bundle_path": str(Path(args.compare_bundle_output).resolve()),
    }
    write_json(Path(args.output).resolve(), result)
    print(json.dumps({"output_path": str(Path(args.output).resolve()), "focus_joints": focus_joints}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
