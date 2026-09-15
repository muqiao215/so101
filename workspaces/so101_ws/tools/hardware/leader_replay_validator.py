#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_TOP_K = 10
DEFAULT_EDGE_WINDOW_SEC = 0.1
DEFAULT_POSITION_ABS_LIMIT_RAD = 6.4
DEFAULT_THRESHOLDS_PATH = Path(__file__).with_name("replay_validator_thresholds.json")


@dataclass(frozen=True)
class RecordingFrame:
    stamp_ns: int
    joint_names: list[str]
    positions: list[float]


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    rank = max(0.0, min(q, 1.0)) * (len(values) - 1)
    left = int(math.floor(rank))
    right = int(math.ceil(rank))
    if left == right:
        return float(values[left])
    alpha = rank - left
    return float(values[left] + (values[right] - values[left]) * alpha)


def load_recording(path: Path) -> list[RecordingFrame]:
    frames: list[RecordingFrame] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        joint_names = [str(value) for value in payload["joint_names"]]
        positions = [float(value) for value in payload["positions"]]
        if not joint_names:
            raise ValueError(f"{path}:{line_no}: joint_names is empty")
        if len(joint_names) != len(positions):
            raise ValueError(
                f"{path}:{line_no}: positions length mismatch: expected {len(joint_names)}, got {len(positions)}"
            )
        frames.append(
            RecordingFrame(
                stamp_ns=int(payload["stamp_ns"]),
                joint_names=joint_names,
                positions=positions,
            )
        )
    if not frames:
        raise ValueError(f"no frames found in {path}")
    return frames


def recording_duration_sec(frames: list[RecordingFrame]) -> float:
    if len(frames) < 2:
        return 0.0
    return max((frames[-1].stamp_ns - frames[0].stamp_ns) / 1_000_000_000.0, 0.0)


def relative_time_ns(frames: list[RecordingFrame], stamp_ns: int) -> int:
    return max(stamp_ns - frames[0].stamp_ns, 0)


def analyze_timestamp_sequence(frames: list[RecordingFrame]) -> tuple[list[RecordingFrame], dict[str, int]]:
    cleaned: list[RecordingFrame] = []
    duplicate_count = 0
    non_monotonic_count = 0
    last_stamp_ns: int | None = None
    for frame in frames:
        if last_stamp_ns is None or frame.stamp_ns > last_stamp_ns:
            cleaned.append(frame)
            last_stamp_ns = frame.stamp_ns
            continue
        if frame.stamp_ns == last_stamp_ns:
            duplicate_count += 1
        else:
            non_monotonic_count += 1
    return cleaned, {
        "duplicate_timestamp_count": duplicate_count,
        "non_monotonic_timestamp_count": non_monotonic_count,
    }


def analyze_data_quality(frames: list[RecordingFrame], *, position_abs_limit_rad: float) -> dict[str, int]:
    nan_count = 0
    inf_count = 0
    out_of_range_count = 0
    missing_value_count = 0
    for frame in frames:
        if len(frame.joint_names) != len(frame.positions):
            missing_value_count += 1
        for value in frame.positions:
            if math.isnan(value):
                nan_count += 1
            elif math.isinf(value):
                inf_count += 1
            elif abs(value) > position_abs_limit_rad:
                out_of_range_count += 1
    return {
        "nan_count": nan_count,
        "inf_count": inf_count,
        "out_of_range_count": out_of_range_count,
        "missing_value_count": missing_value_count,
    }


def joint_coverage_summary(reference_frames: list[RecordingFrame], candidate_frames: list[RecordingFrame]) -> dict[str, Any]:
    reference_names = list(reference_frames[0].joint_names)
    candidate_names = list(candidate_frames[0].joint_names)
    reference_set = set(reference_names)
    candidate_set = set(candidate_names)
    return {
        "missing_joints_in_reference": sorted(candidate_set - reference_set),
        "missing_joints_in_candidate": sorted(reference_set - candidate_set),
        "extra_joints_in_reference": sorted(reference_set - candidate_set),
        "extra_joints_in_candidate": sorted(candidate_set - reference_set),
        "joint_name_mismatch": reference_names != candidate_names,
    }


def interpolate_positions(frames: list[RecordingFrame], target_rel_ns: int) -> tuple[list[float], bool]:
    if len(frames) == 1:
        return list(frames[0].positions), False

    first_rel_ns = 0
    last_rel_ns = relative_time_ns(frames, frames[-1].stamp_ns)
    if target_rel_ns <= first_rel_ns:
        return list(frames[0].positions), target_rel_ns < first_rel_ns
    if target_rel_ns >= last_rel_ns:
        return list(frames[-1].positions), target_rel_ns > last_rel_ns

    for left, right in zip(frames, frames[1:]):
        left_rel_ns = relative_time_ns(frames, left.stamp_ns)
        right_rel_ns = relative_time_ns(frames, right.stamp_ns)
        if target_rel_ns > right_rel_ns:
            continue
        if right_rel_ns <= left_rel_ns:
            return list(right.positions), False
        alpha = (target_rel_ns - left_rel_ns) / float(right_rel_ns - left_rel_ns)
        return (
            [
                float(left_value + (right_value - left_value) * alpha)
                for left_value, right_value in zip(left.positions, right.positions)
            ],
            False,
        )

    return list(frames[-1].positions), False


def load_threshold_profiles(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError(f"threshold file {path} has no profiles")
    return profiles


def build_check(*, actual: Any, threshold: Any, op: str, passed: bool) -> dict[str, Any]:
    return {
        "actual": actual,
        "threshold": threshold,
        "op": op,
        "result": "pass" if passed else "fail",
    }


def empty_worst_point() -> dict[str, Any]:
    return {
        "joint": None,
        "t_sec": None,
        "reference_value_rad": None,
        "candidate_value_rad": None,
        "abs_error_rad": 0.0,
        "is_edge_region": False,
    }


def build_validation_report(
    reference_frames: list[RecordingFrame],
    candidate_frames: list[RecordingFrame],
    *,
    profile_name: str,
    thresholds: dict[str, Any],
    top_k: int,
    edge_window_sec: float,
) -> dict[str, Any]:
    if top_k <= 0:
        raise ValueError(f"top_k must be positive, got {top_k}")

    coverage = joint_coverage_summary(reference_frames, candidate_frames)
    reference_clean, reference_alignment = analyze_timestamp_sequence(reference_frames)
    candidate_clean, candidate_alignment = analyze_timestamp_sequence(candidate_frames)
    if not reference_clean or not candidate_clean:
        raise ValueError("cleaned recordings are empty after timestamp sanitization")

    reference_joint_order = list(reference_clean[0].joint_names)
    candidate_joint_order = list(candidate_clean[0].joint_names)
    can_compare_positions = not coverage["joint_name_mismatch"]

    reference_duration_sec = recording_duration_sec(reference_clean)
    candidate_duration_sec = recording_duration_sec(candidate_clean)
    effective_duration_sec = min(reference_duration_sec, candidate_duration_sec)
    reference_duration_ns = max(reference_clean[-1].stamp_ns - reference_clean[0].stamp_ns, 0)
    candidate_duration_ns = max(candidate_clean[-1].stamp_ns - candidate_clean[0].stamp_ns, 0)

    data_quality = {
        "reference": analyze_data_quality(reference_frames, position_abs_limit_rad=DEFAULT_POSITION_ABS_LIMIT_RAD),
        "candidate": analyze_data_quality(candidate_frames, position_abs_limit_rad=DEFAULT_POSITION_ABS_LIMIT_RAD),
    }
    aggregate_quality = {
        "nan_count": data_quality["reference"]["nan_count"] + data_quality["candidate"]["nan_count"],
        "inf_count": data_quality["reference"]["inf_count"] + data_quality["candidate"]["inf_count"],
        "out_of_range_count": data_quality["reference"]["out_of_range_count"] + data_quality["candidate"]["out_of_range_count"],
        "missing_value_count": data_quality["reference"]["missing_value_count"] + data_quality["candidate"]["missing_value_count"],
    }

    evaluated_sample_count = len(reference_clean) if can_compare_positions else 0
    used_extrapolation = False
    all_errors: list[float] = []
    per_joint_errors: dict[str, list[float]] = {joint_name: [] for joint_name in reference_joint_order}
    top_samples: list[dict[str, Any]] = []

    if can_compare_positions:
        for frame in reference_clean:
            reference_rel_ns = relative_time_ns(reference_clean, frame.stamp_ns)
            if reference_duration_ns > 0 and candidate_duration_ns > 0:
                target_rel_ns = int(round((reference_rel_ns / reference_duration_ns) * candidate_duration_ns))
            else:
                target_rel_ns = reference_rel_ns

            candidate_positions, extrapolated = interpolate_positions(candidate_clean, target_rel_ns)
            used_extrapolation = used_extrapolation or extrapolated
            t_sec = reference_rel_ns / 1_000_000_000.0
            is_edge_region = (
                t_sec <= edge_window_sec
                or (reference_duration_sec > 0.0 and t_sec >= max(reference_duration_sec - edge_window_sec, 0.0))
            )
            for joint_name, reference_value, candidate_value in zip(reference_joint_order, frame.positions, candidate_positions):
                error = abs(reference_value - candidate_value)
                all_errors.append(error)
                per_joint_errors[joint_name].append(error)
                top_samples.append(
                    {
                        "joint": joint_name,
                        "t_sec": round(t_sec, 6),
                        "reference_value_rad": round(reference_value, 6),
                        "candidate_value_rad": round(candidate_value, 6),
                        "abs_error_rad": round(error, 6),
                        "is_edge_region": is_edge_region,
                    }
                )

    sorted_errors = sorted(all_errors)
    overall_mae = 0.0 if not all_errors else sum(all_errors) / len(all_errors)
    overall_rmse = 0.0 if not all_errors else math.sqrt(sum(error * error for error in all_errors) / len(all_errors))
    overall_max = 0.0 if not all_errors else max(all_errors)
    overall_p95 = 0.0 if not all_errors else percentile(sorted_errors, 0.95)
    rounded_overall_mae = round(overall_mae, 6)
    rounded_overall_rmse = round(overall_rmse, 6)
    rounded_overall_p95 = round(overall_p95, 6)
    duration_delta_sec = candidate_duration_sec - reference_duration_sec
    duration_delta_abs_sec = abs(duration_delta_sec)
    duration_ratio = None if reference_duration_sec <= 0.0 else candidate_duration_sec / reference_duration_sec

    per_joint_metrics: dict[str, dict[str, float]] = {}
    for joint_name in reference_joint_order:
        joint_errors = sorted(per_joint_errors.get(joint_name, []))
        if not joint_errors:
            per_joint_metrics[joint_name] = {
                "mae_rad": 0.0,
                "rmse_rad": 0.0,
                "max_error_rad": 0.0,
                "p95_error_rad": 0.0,
            }
            continue
        joint_mae = sum(joint_errors) / len(joint_errors)
        joint_rmse = math.sqrt(sum(error * error for error in joint_errors) / len(joint_errors))
        per_joint_metrics[joint_name] = {
            "mae_rad": round(joint_mae, 6),
            "rmse_rad": round(joint_rmse, 6),
            "max_error_rad": round(max(joint_errors), 6),
            "p95_error_rad": round(percentile(joint_errors, 0.95), 6),
        }

    rounded_overall_max = round(overall_max, 6)
    top_samples_sorted = sorted(top_samples, key=lambda item: item["abs_error_rad"], reverse=True)
    top_samples_output: list[dict[str, Any]] = []
    meaningful_top_samples = top_samples_sorted if rounded_overall_max > 0.0 else []
    for index, sample in enumerate(meaningful_top_samples[:top_k], start=1):
        top_samples_output.append(
            {
                "rank": index,
                **sample,
            }
        )

    worst_point = top_samples_output[0] if top_samples_output else empty_worst_point()
    edge_errors = [sample["abs_error_rad"] for sample in top_samples if sample["is_edge_region"]]
    non_edge_errors = [sample["abs_error_rad"] for sample in top_samples if not sample["is_edge_region"]]
    edge_max_error = max(edge_errors) if edge_errors else 0.0
    non_edge_max_error = max(non_edge_errors) if non_edge_errors else 0.0

    hard_reasons: list[str] = []
    soft_reasons: list[str] = []
    invalid_reasons: list[str] = []
    checks: dict[str, dict[str, Any]] = {}

    profile = thresholds[profile_name]
    hard = profile.get("hard", {})
    soft = profile.get("soft", {})
    invalid = profile.get("invalid", {})
    per_joint_hard = profile.get("per_joint_hard", {})
    per_joint_soft = profile.get("per_joint_soft", {})

    checks["metrics.overall.mae_rad"] = build_check(
        actual=rounded_overall_mae,
        threshold=hard.get("overall.mae_rad"),
        op="<=",
        passed=overall_mae <= float(hard.get("overall.mae_rad", float("inf"))),
    )
    if checks["metrics.overall.mae_rad"]["result"] == "fail":
        hard_reasons.append("overall.mae_rad exceeds hard threshold")

    checks["metrics.overall.max_error_rad"] = build_check(
        actual=round(overall_max, 6),
        threshold=hard.get("overall.max_error_rad"),
        op="<=",
        passed=overall_max <= float(hard.get("overall.max_error_rad", float("inf"))),
    )
    if checks["metrics.overall.max_error_rad"]["result"] == "fail":
        hard_reasons.append("overall.max_error_rad exceeds hard threshold")

    checks["metrics.overall.duration_delta_abs_sec"] = build_check(
        actual=round(duration_delta_abs_sec, 6),
        threshold=hard.get("overall.duration_delta_abs_sec"),
        op="<=",
        passed=duration_delta_abs_sec <= float(hard.get("overall.duration_delta_abs_sec", float("inf"))),
    )
    if checks["metrics.overall.duration_delta_abs_sec"]["result"] == "fail":
        hard_reasons.append("overall.duration_delta_abs_sec exceeds hard threshold")

    checks["alignment.used_extrapolation"] = build_check(
        actual=used_extrapolation,
        threshold=hard.get("alignment.used_extrapolation"),
        op="==",
        passed=used_extrapolation == bool(hard.get("alignment.used_extrapolation", False)),
    )
    if checks["alignment.used_extrapolation"]["result"] == "fail":
        invalid_reasons.append("alignment used extrapolation but profile forbids it")

    checks["diagnostics.joint_coverage.joint_name_mismatch"] = build_check(
        actual=coverage["joint_name_mismatch"],
        threshold=hard.get("diagnostics.joint_coverage.joint_name_mismatch"),
        op="==",
        passed=coverage["joint_name_mismatch"] == bool(hard.get("diagnostics.joint_coverage.joint_name_mismatch", False)),
    )
    if checks["diagnostics.joint_coverage.joint_name_mismatch"]["result"] == "fail":
        invalid_reasons.append("joint order or names mismatch between reference and candidate")

    for key in ("nan_count", "inf_count", "out_of_range_count", "missing_value_count"):
        check_key = f"diagnostics.data_quality.{key}"
        threshold_value = int(hard.get(check_key, 0))
        actual_value = int(aggregate_quality[key])
        checks[check_key] = build_check(actual=actual_value, threshold=threshold_value, op="==", passed=actual_value == threshold_value)
        if checks[check_key]["result"] == "fail":
            invalid_reasons.append(f"data quality check failed: {key}={actual_value}")

    checks["metrics.overall.p95_error_rad"] = build_check(
        actual=rounded_overall_p95,
        threshold=soft.get("metrics.overall.p95_error_rad"),
        op="<=",
        passed=overall_p95 <= float(soft.get("metrics.overall.p95_error_rad", float("inf"))),
    )
    if checks["metrics.overall.p95_error_rad"]["result"] == "fail":
        soft_reasons.append("overall.p95_error_rad exceeds soft threshold")

    checks["diagnostics.edge_region.edge_max_error_rad"] = build_check(
        actual=round(edge_max_error, 6),
        threshold=soft.get("diagnostics.edge_region.edge_max_error_rad"),
        op="<=",
        passed=edge_max_error <= float(soft.get("diagnostics.edge_region.edge_max_error_rad", float("inf"))),
    )
    if checks["diagnostics.edge_region.edge_max_error_rad"]["result"] == "fail":
        soft_reasons.append("edge region max error exceeds soft threshold")

    if duration_ratio is not None and "overall.duration_ratio_min" in soft:
        checks["metrics.overall.duration_ratio_min"] = build_check(
            actual=round(duration_ratio, 6),
            threshold=soft.get("overall.duration_ratio_min"),
            op=">=",
            passed=duration_ratio >= float(soft["overall.duration_ratio_min"]),
        )
        if checks["metrics.overall.duration_ratio_min"]["result"] == "fail":
            soft_reasons.append("duration ratio below soft minimum")
    if duration_ratio is not None and "overall.duration_ratio_max" in soft:
        checks["metrics.overall.duration_ratio_max"] = build_check(
            actual=round(duration_ratio, 6),
            threshold=soft.get("overall.duration_ratio_max"),
            op="<=",
            passed=duration_ratio <= float(soft["overall.duration_ratio_max"]),
        )
        if checks["metrics.overall.duration_ratio_max"]["result"] == "fail":
            soft_reasons.append("duration ratio above soft maximum")

    if per_joint_hard:
        for joint_name, metrics in per_joint_metrics.items():
            mae_threshold = float(per_joint_hard.get("mae_rad", float("inf")))
            max_threshold = float(per_joint_hard.get("max_error_rad", float("inf")))
            mae_key = f"metrics.per_joint.{joint_name}.mae_rad"
            max_key = f"metrics.per_joint.{joint_name}.max_error_rad"
            checks[mae_key] = build_check(actual=metrics["mae_rad"], threshold=mae_threshold, op="<=", passed=metrics["mae_rad"] <= mae_threshold)
            checks[max_key] = build_check(actual=metrics["max_error_rad"], threshold=max_threshold, op="<=", passed=metrics["max_error_rad"] <= max_threshold)
            if checks[mae_key]["result"] == "fail":
                hard_reasons.append(f"{joint_name} mae exceeds hard threshold")
            if checks[max_key]["result"] == "fail":
                hard_reasons.append(f"{joint_name} max error exceeds hard threshold")

    if per_joint_soft:
        for joint_name, metrics in per_joint_metrics.items():
            mae_threshold = float(per_joint_soft.get("mae_rad", float("inf")))
            max_threshold = float(per_joint_soft.get("max_error_rad", float("inf")))
            mae_key = f"soft.per_joint.{joint_name}.mae_rad"
            max_key = f"soft.per_joint.{joint_name}.max_error_rad"
            checks[mae_key] = build_check(actual=metrics["mae_rad"], threshold=mae_threshold, op="<=", passed=metrics["mae_rad"] <= mae_threshold)
            checks[max_key] = build_check(actual=metrics["max_error_rad"], threshold=max_threshold, op="<=", passed=metrics["max_error_rad"] <= max_threshold)
            if checks[mae_key]["result"] == "fail":
                soft_reasons.append(f"{joint_name} mae exceeds soft threshold")
            if checks[max_key]["result"] == "fail":
                soft_reasons.append(f"{joint_name} max error exceeds soft threshold")

    if reference_alignment["duplicate_timestamp_count"] or reference_alignment["non_monotonic_timestamp_count"]:
        invalid_reasons.append("reference timestamps are not strictly monotonic")
    if candidate_alignment["duplicate_timestamp_count"] or candidate_alignment["non_monotonic_timestamp_count"]:
        invalid_reasons.append("candidate timestamps are not strictly monotonic")
    if evaluated_sample_count <= 0 or effective_duration_sec <= 0.0:
        invalid_reasons.append("effective comparison window is empty")

    edge_ratio = None
    if non_edge_max_error > 0.0:
        edge_ratio = edge_max_error / non_edge_max_error
    elif edge_max_error > 0.0:
        edge_ratio = float("inf")
    invalid_edge_ratio_min = invalid.get("identity_edge_spike_ratio_min")
    invalid_non_edge_cap = invalid.get("identity_non_edge_max_error_rad_max")
    if (
        profile_name == "identity_strict"
        and invalid_edge_ratio_min is not None
        and invalid_non_edge_cap is not None
        and overall_max > float(hard.get("overall.max_error_rad", float("inf")))
        and non_edge_max_error <= float(invalid_non_edge_cap)
        and edge_ratio is not None
        and edge_ratio >= float(invalid_edge_ratio_min)
    ):
        invalid_reasons.append("identity comparison has edge-dominated spike inconsistent with steady-state error profile")

    if profile_name == "identity_strict" and invalid_non_edge_cap is not None:
        checks["diagnostics.edge_region.non_edge_max_error_rad"] = build_check(
            actual=round(non_edge_max_error, 6),
            threshold=float(invalid_non_edge_cap),
            op="<=",
            passed=non_edge_max_error <= float(invalid_non_edge_cap),
        )

    status = "passed"
    if invalid_reasons:
        status = "invalid_result"
    elif hard_reasons:
        status = "hard_failed"
    elif soft_reasons:
        status = "soft_failed"

    if status == "passed":
        summary = "all hard and soft checks passed"
    elif status == "soft_failed":
        summary = "hard checks passed, but one or more soft checks failed"
    elif status == "hard_failed":
        summary = "one or more hard checks failed"
    else:
        summary = "validation result is not trustworthy because input structure or alignment assumptions were violated"

    return {
        "schema_version": "replay_validator.v2",
        "validator": {
            "name": "leader_replay_validator",
            "version": "2.0.0",
        },
        "run": {
            "reference_path": None,
            "candidate_path": None,
            "reference_frame_count": len(reference_frames),
            "candidate_frame_count": len(candidate_frames),
            "reference_clean_frame_count": len(reference_clean),
            "candidate_clean_frame_count": len(candidate_clean),
            "reference_duration_sec": round(reference_duration_sec, 6),
            "candidate_duration_sec": round(candidate_duration_sec, 6),
            "comparison_window": {
                "reference_start_sec": 0.0,
                "reference_end_sec": round(reference_duration_sec, 6),
                "candidate_start_sec": 0.0,
                "candidate_end_sec": round(candidate_duration_sec, 6),
                "effective_start_sec": 0.0,
                "effective_end_sec": round(effective_duration_sec, 6),
                "effective_duration_sec": round(effective_duration_sec, 6),
            },
            "alignment": {
                "method": "timestamp_linear_interp",
                "evaluated_sample_count": evaluated_sample_count,
                "can_compare_positions": can_compare_positions,
                "used_extrapolation": used_extrapolation,
                "trimmed_head_sec": 0.0,
                "trimmed_tail_sec": 0.0,
                "reference_removed_frame_count": len(reference_frames) - len(reference_clean),
                "candidate_removed_frame_count": len(candidate_frames) - len(candidate_clean),
                "reference_duplicate_timestamp_count": reference_alignment["duplicate_timestamp_count"],
                "candidate_duplicate_timestamp_count": candidate_alignment["duplicate_timestamp_count"],
                "reference_non_monotonic_timestamp_count": reference_alignment["non_monotonic_timestamp_count"],
                "candidate_non_monotonic_timestamp_count": candidate_alignment["non_monotonic_timestamp_count"],
                "duplicate_timestamp_count": reference_alignment["duplicate_timestamp_count"] + candidate_alignment["duplicate_timestamp_count"],
                "non_monotonic_timestamp_count": reference_alignment["non_monotonic_timestamp_count"] + candidate_alignment["non_monotonic_timestamp_count"],
            },
            "joint_order": list(reference_joint_order),
        },
        "metrics": {
            "overall": {
                "mae_rad": rounded_overall_mae,
                "rmse_rad": rounded_overall_rmse,
                "max_error_rad": rounded_overall_max,
                "p95_error_rad": rounded_overall_p95,
                "duration_delta_sec": round(duration_delta_sec, 6),
                "duration_delta_abs_sec": round(duration_delta_abs_sec, 6),
                "duration_ratio": None if duration_ratio is None else round(duration_ratio, 6),
            },
            "per_joint": per_joint_metrics,
        },
        "diagnostics": {
            "worst_point": worst_point,
            "top_k_worst_samples": top_samples_output,
            "edge_region": {
                "edge_window_sec": round(edge_window_sec, 6),
                "edge_sample_count": len(edge_errors),
                "non_edge_sample_count": len(non_edge_errors),
                "edge_max_error_rad": round(edge_max_error, 6),
                "non_edge_max_error_rad": round(non_edge_max_error, 6),
                "edge_spike_ratio": None if edge_ratio is None or math.isinf(edge_ratio) else round(edge_ratio, 6),
            },
            "joint_coverage": coverage,
            "data_quality": {
                **aggregate_quality,
                "aggregate": aggregate_quality,
                "reference": data_quality["reference"],
                "candidate": data_quality["candidate"],
            },
        },
        "judgment": {
            "profile": profile_name,
            "status": status,
            "summary": summary,
            "hard_fail_reasons": sorted(set(hard_reasons)),
            "soft_fail_reasons": sorted(set(soft_reasons)),
            "invalid_reasons": sorted(set(invalid_reasons)),
            "checks": checks,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate leader replay fidelity between two recording jsonl files.")
    parser.add_argument("--reference", "--source", dest="reference", required=True, help="Path to reference/original leader recording jsonl")
    parser.add_argument("--candidate", "--replay", dest="candidate", required=True, help="Path to candidate/replay leader recording jsonl")
    parser.add_argument("--output", default="", help="Optional JSON output path")
    parser.add_argument("--profile", default="identity_strict", help="Threshold profile name")
    parser.add_argument("--thresholds", default=str(DEFAULT_THRESHOLDS_PATH), help="Path to thresholds json")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Number of worst samples to include")
    parser.add_argument("--edge-window-sec", type=float, default=DEFAULT_EDGE_WINDOW_SEC, help="Edge region size in seconds")
    parser.add_argument("--fail-on", choices=["none", "hard", "soft"], default="none", help="Exit non-zero on failure level")
    parser.add_argument("--print-summary", action="store_true", help="Print a one-line summary after JSON output")
    return parser.parse_args(argv)


def should_fail(status: str, fail_on: str) -> bool:
    if fail_on == "none":
        return False
    if fail_on == "hard":
        return status in {"hard_failed", "invalid_result"}
    return status in {"soft_failed", "hard_failed", "invalid_result"}


def build_summary_line(report: dict[str, Any]) -> str:
    overall = report["metrics"]["overall"]
    worst = report["diagnostics"]["worst_point"]
    return (
        f"status={report['judgment']['status']} "
        f"profile={report['judgment']['profile']} "
        f"mae={overall['mae_rad']:.6f} "
        f"max={overall['max_error_rad']:.6f} "
        f"p95={overall['p95_error_rad']:.6f} "
        f"duration_delta={overall['duration_delta_sec']:.6f} "
        f"worst_joint={worst['joint']} "
        f"worst_t={worst['t_sec']}"
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    reference_path = Path(args.reference).resolve()
    candidate_path = Path(args.candidate).resolve()
    thresholds_path = Path(args.thresholds).resolve()
    profiles = load_threshold_profiles(thresholds_path)
    if args.profile not in profiles:
        raise ValueError(f"profile '{args.profile}' not found in {thresholds_path}")

    reference_frames = load_recording(reference_path)
    candidate_frames = load_recording(candidate_path)
    report = build_validation_report(
        reference_frames,
        candidate_frames,
        profile_name=args.profile,
        thresholds=profiles,
        top_k=max(args.top_k, 1),
        edge_window_sec=max(args.edge_window_sec, 0.0),
    )
    report["run"]["reference_path"] = str(reference_path)
    report["run"]["candidate_path"] = str(candidate_path)

    if args.output.strip():
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": report["judgment"]["status"], "output_path": str(output_path)}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.print_summary:
        print(build_summary_line(report))
    return 1 if should_fail(report["judgment"]["status"], args.fail_on) else 0


if __name__ == "__main__":
    raise SystemExit(main())
