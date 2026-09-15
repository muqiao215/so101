#!/usr/bin/env python3
"""Run or assemble the pre-real non-hardware acceptance suite."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from run_mtc_reach_benchmark_suite import build_arg_parser as build_mtc_suite_parser
from run_mtc_reach_benchmark_suite import run_suite as run_mtc_suite
from run_vision_projection_quality_smoke import build_quality_report, write_yaml


ACCEPTANCE_DIR = Path("docs/generated/acceptance")
DEFAULT_TRAINABILITY_REPORT = Path(
    "docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/"
    "dataset/trainability-smoke/trainability-report.json"
)
DEFAULT_REAL_TRAINABILITY_REPORT = Path(
    "docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/"
    "dataset/trainability-real-required/trainability-report.json"
)


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def latest_file(patterns: Sequence[str]) -> Path | None:
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(Path(".").glob(pattern))
    files = [path for path in candidates if path.is_file()]
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_mtime)


def shell_join(command: Sequence[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in command)


def run_command(command: Sequence[str], *, cwd: Path, stdout_path: Path, stderr_path: Path) -> int:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        process = subprocess.run(command, cwd=cwd, stdout=stdout, stderr=stderr, text=True, check=False)
    return int(process.returncode)


def classify_step(status: str, *, required: bool = True) -> str:
    if status in {"passed", "trainable_smoke"}:
        return "passed_smoke"
    if status in {"blocked", "deferred"} or not required:
        return "blocked_deferred"
    if status == "warn":
        return "passed_smoke_with_warnings"
    return "failed"


def step_passed(classification: str) -> bool:
    return classification in {"passed_smoke", "passed_smoke_with_warnings", "blocked_deferred"}


def reach_value(summary_or_report: Mapping[str, Any]) -> Any:
    if summary_or_report.get("reach_success_rate") is not None:
        return summary_or_report.get("reach_success_rate")
    if summary_or_report.get("reach_success") is not None:
        return summary_or_report.get("reach_success")
    metrics = ((summary_or_report.get("evaluation_result") or {}).get("metrics") or {})
    if metrics.get("reach_success") is not None:
        return metrics.get("reach_success")
    return None


def reach_gate_passed(summary_or_report: Mapping[str, Any], threshold: float) -> bool:
    if summary_or_report.get("reach_success_rate") is not None:
        return float(summary_or_report.get("reach_success_rate") or 0.0) >= threshold
    if summary_or_report.get("reach_success") is not None:
        return bool(summary_or_report.get("reach_success"))
    metrics = ((summary_or_report.get("evaluation_result") or {}).get("metrics") or {})
    if metrics.get("reach_success") is not None:
        return bool(metrics.get("reach_success"))
    return False


def build_dashboard(report: Mapping[str, Any]) -> str:
    reach = ((report.get("mtc_reach_smoke") or {}).get("summary") or {})
    jitter = ((report.get("jitter_suite") or {}).get("summary") or {})
    trainability = ((report.get("dataset_trainability") or {}).get("report") or {})
    quality = ((report.get("vision_projection_quality") or {}).get("report") or {})
    contact = report.get("contact_lift_diagnostic") or {}
    artifacts = report.get("artifacts") or {}

    def value(data: Mapping[str, Any], key: str) -> Any:
        item = data.get(key)
        return "n/a" if item is None else item

    lines = [
        "# SO101 Pre-Real Acceptance Dashboard",
        "",
        f"- Status: **{report.get('status')}**",
        f"- Timestamp: `{report.get('timestamp')}`",
        f"- Scope: `{report.get('scope')}`",
        "",
        "## Summary",
        "",
        "| Area | Status | Key metric |",
        "| --- | --- | --- |",
        f"| Vision smoke | {((report.get('vision_smoke') or {}).get('classification'))} | {((report.get('vision_smoke') or {}).get('status'))} |",
        f"| Vision projection quality | {((report.get('vision_projection_quality') or {}).get('classification'))} | raw/canonical quality smoke |",
        f"| MTC reach smoke | {((report.get('mtc_reach_smoke') or {}).get('classification'))} | reach_success={reach_value(reach)} |",
        f"| Jitter suite | {((report.get('jitter_suite') or {}).get('classification'))} | reach_success_rate={value(jitter, 'reach_success_rate')} |",
        f"| Dataset trainability | {((report.get('dataset_trainability') or {}).get('classification'))} | status={trainability.get('status', 'n/a')} |",
        f"| Contact/lift diagnostic | {contact.get('classification')} | contact={contact.get('contact_success')} lift={contact.get('lift_success')} |",
        "",
        "## Reach Metrics",
        "",
        f"- Reach success rate: `{value(jitter, 'reach_success_rate')}`",
        f"- Min distance mean: `{value(jitter, 'mean_min_distance_m')}`",
        f"- Min distance p50: `{value(jitter, 'p50_min_distance_m')}`",
        f"- Min distance p90: `{value(jitter, 'p90_min_distance_m')}`",
        f"- Min distance max: `{value(jitter, 'max_min_distance_m')}`",
        f"- Failure reason counts: `{value(jitter, 'failure_reason_counts')}`",
        "",
        "## Dataset And Vision",
        "",
        f"- Trainability status: `{trainability.get('status', 'n/a')}`",
        f"- Trainable samples: `{trainability.get('trainable_sample_count', 'n/a')}`",
        f"- Real trainability: `not trainable_real`",
        f"- Vision miss counts: `{((quality.get('summary') or {}).get('miss_counts', {}))}`",
        f"- Vision false positive counts: `{((quality.get('summary') or {}).get('false_positive_counts', {}))}`",
        f"- Vision clamp reasons: `{((quality.get('summary') or {}).get('clamp_reason_counts', {}))}`",
        "",
        "## Artifact Links",
        "",
    ]
    for key, path in sorted(artifacts.items()):
        lines.append(f"- `{key}`: `{path}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This is a Gazebo simulation smoke / execution-grounded simulated reach benchmark acceptance gate.",
            "- Contact and lift remain blocked/deferred optional diagnostics; `contact_success=false` or `lift_success=false` does not fail pre-real acceptance.",
            "- This is `trainable_smoke`, not `trainable_real`.",
            "- It does not claim real grasp success, real follower closed loop, real YOLO quality closure, or successful simulated grasp/lift.",
        ]
    )
    return "\n".join(lines) + "\n"


def update_latest_index(index_path: Path, run_record: Mapping[str, Any]) -> None:
    if index_path.exists():
        index = load_yaml(index_path)
    else:
        index = {"schema": "so101_pre_real_acceptance_run_index_v1", "runs": []}
    runs = list(index.get("runs") or [])
    runs.insert(0, dict(run_record))
    index["latest"] = dict(run_record)
    index["runs"] = runs[:50]
    write_yaml(index_path, index)


def build_mtc_args(base: argparse.Namespace, output_dir: Path, *, suite_name: str, episode_count: int, jitter_xyz: str) -> argparse.Namespace:
    parser = build_mtc_suite_parser()
    args = parser.parse_args(
        [
            "--workspace",
            str(Path.cwd()),
            "--output-dir",
            str(output_dir),
            "--suite-name",
            suite_name,
            "--episode-count",
            str(episode_count),
            "--target-xyz",
            base.target_xyz,
            "--jitter-xyz",
            jitter_xyz,
            "--seed",
            str(base.seed),
            "--timeout-sec",
            str(base.mtc_timeout_sec),
            "--execute-duration-sec",
            str(base.execute_duration_sec),
            "--settle-duration-sec",
            str(base.settle_duration_sec),
            "--trace-sample-period-sec",
            str(base.trace_sample_period_sec),
        ]
    )
    args.dry_run = bool(base.dry_run)
    return args


def evaluate_or_load_trainability(args: argparse.Namespace, run_dir: Path) -> tuple[dict[str, Any], Path | None]:
    if args.candidate_dir:
        output_dir = run_dir / "trainability-smoke"
        command = [
            sys.executable,
            "tools/hardware/evaluate_trainable_candidate.py",
            args.candidate_dir,
            "--output-dir",
            str(output_dir),
        ]
        rc = run_command(command, cwd=Path.cwd(), stdout_path=run_dir / "trainability.stdout.log", stderr_path=run_dir / "trainability.stderr.log")
        report_path = output_dir / "trainability-report.json"
        if report_path.exists():
            return load_json(report_path), report_path
        return {"status": "failed", "returncode": rc}, None
    report_path = Path(args.trainability_report)
    if report_path.exists():
        return load_json(report_path), report_path
    return {"status": "blocked", "reason": "trainability_report_missing", "path": str(report_path)}, None


def load_vision_smoke(args: argparse.Namespace, run_dir: Path) -> tuple[dict[str, Any], Path | None]:
    if args.run_vision_smoke:
        report_path = run_dir / "vision-smoke.json"
        command = [
            sys.executable,
            "tools/e2e/assert_sim_vision_closed_loop.py",
            "--timeout-sec",
            str(args.vision_timeout_sec),
            "--require-overlay-image",
            "--report-path",
            str(report_path),
        ]
        rc = run_command(command, cwd=Path.cwd(), stdout_path=run_dir / "vision-smoke.stdout.log", stderr_path=run_dir / "vision-smoke.stderr.log")
        if report_path.exists():
            return load_json(report_path), report_path
        return {"status": "failed", "returncode": rc}, None
    report_path = Path(args.vision_smoke_report) if args.vision_smoke_report else latest_file(
        ["docs/generated/vision-episodes/sim-vision-*gazebo-color*.json", "docs/generated/vision-episodes/*assertion*.json"]
    )
    if report_path and report_path.exists():
        return load_json(report_path), report_path
    return {"status": "blocked", "reason": "vision_smoke_artifact_missing"}, None


def contact_lift_diagnostic_from(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "classification": "blocked_deferred",
        "status": "blocked/deferred optional diagnostic",
        "contact_success": summary.get("contact_success_rate"),
        "lift_success": summary.get("lift_success_rate"),
        "failure_reason": "Gazebo Classic contact/lift physics ROI; not a pre-real acceptance blocker",
    }


def run_acceptance(args: argparse.Namespace) -> dict[str, Any]:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = (ACCEPTANCE_DIR / f"pre-real-acceptance-{timestamp}").resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    vision_report, vision_path = load_vision_smoke(args, run_dir)
    events_path = Path(args.vision_events_path) if args.vision_events_path else latest_file(["docs/generated/vision-episodes/*/events.jsonl"])
    if not events_path:
        quality_report = {"status": "blocked", "reason": "vision_events_artifact_missing"}
        quality_path = None
    else:
        quality_report = build_quality_report(events_path)
        quality_path = run_dir / "vision_projection_quality_report.yaml"
        write_yaml(quality_path, quality_report)

    if args.reuse_latest_artifacts:
        smoke_path = Path(args.mtc_smoke_report) if args.mtc_smoke_report else latest_file(["docs/generated/vision-episodes/mtc-*reach*.yaml"])
        smoke_summary = load_yaml(smoke_path) if smoke_path else {"status": "blocked", "reason": "mtc_smoke_report_missing"}
        jitter_path = Path(args.jitter_summary_report) if args.jitter_summary_report else latest_file(
            ["docs/generated/vision-episodes/mtc-reach-suite-*/summary_report.yaml"]
        )
        jitter_summary = load_yaml(jitter_path) if jitter_path else {"status": "blocked", "reason": "jitter_summary_missing"}
    else:
        smoke_output = run_dir / "mtc-reach-smoke"
        smoke_summary = run_mtc_suite(
            build_mtc_args(args, smoke_output, suite_name="pre-real-mtc-reach-smoke", episode_count=1, jitter_xyz="0,0,0")
        )
        smoke_path = smoke_output / "summary_report.yaml"
        jitter_output = run_dir / "mtc-reach-jitter-small"
        jitter_summary = run_mtc_suite(
            build_mtc_args(
                args,
                jitter_output,
                suite_name="pre-real-mtc-reach-jitter-small",
                episode_count=args.jitter_episodes,
                jitter_xyz=args.jitter_xyz,
            )
        )
        jitter_path = jitter_output / "summary_report.yaml"

    trainability_report, trainability_path = evaluate_or_load_trainability(args, run_dir)
    real_trainability_path = Path(args.real_trainability_report)
    real_trainability = load_json(real_trainability_path) if real_trainability_path.exists() else {"status": "blocked"}

    vision_class = classify_step(str(vision_report.get("status") or "blocked"))
    quality_class = classify_step(str(quality_report.get("status") or "blocked"))
    smoke_class = classify_step("passed" if reach_gate_passed(smoke_summary, args.min_reach_success_rate) else "failed")
    jitter_class = classify_step("passed" if reach_gate_passed(jitter_summary, args.min_reach_success_rate) else "failed")
    train_class = classify_step(str(trainability_report.get("status") or "blocked"))
    contact_diag = contact_lift_diagnostic_from(jitter_summary)

    artifacts = {
        "run_dir": str(run_dir),
        "acceptance_report": str(run_dir / "acceptance_report.yaml"),
        "dashboard": str(run_dir / "dashboard.md"),
        "latest_index": str((ACCEPTANCE_DIR / "latest_runs.yaml").resolve()),
        "vision_smoke_report": str(vision_path.resolve()) if vision_path else "",
        "vision_projection_quality_report": str(quality_path.resolve()) if quality_path else "",
        "mtc_reach_smoke_summary": str(smoke_path.resolve()) if smoke_path else "",
        "jitter_summary": str(jitter_path.resolve()) if jitter_path else "",
        "trainability_report": str(trainability_path.resolve()) if trainability_path else "",
        "real_trainability_report": str(real_trainability_path.resolve()) if real_trainability_path.exists() else "",
    }
    report = {
        "schema": "so101_pre_real_acceptance_report_v1",
        "timestamp": timestamp,
        "command": shell_join([sys.executable, *sys.argv]),
        "status": "passed" if all(step_passed(item) for item in [vision_class, quality_class, smoke_class, jitter_class, train_class]) else "failed",
        "scope": "pre-real non-hardware acceptance: Gazebo simulation smoke, execution-grounded simulated reach benchmark, trainable_smoke",
        "boundaries": {
            "real_grasp_success": False,
            "real_follower_closed_loop": False,
            "real_yolo_quality_closed_loop": False,
            "trainable_real": False,
            "sim_grasp_lift_success": False,
        },
        "vision_smoke": {"classification": vision_class, "status": vision_report.get("status"), "report": vision_report},
        "vision_projection_quality": {"classification": quality_class, "status": quality_report.get("status"), "report": quality_report},
        "mtc_reach_smoke": {"classification": smoke_class, "summary": smoke_summary},
        "jitter_suite": {"classification": jitter_class, "summary": jitter_summary},
        "dataset_trainability": {
            "classification": train_class,
            "status": trainability_report.get("status"),
            "report": trainability_report,
            "real_gate_status": real_trainability.get("status"),
            "real_gate_note": "not trainable_real until follower_joint_action labels are available",
        },
        "contact_lift_diagnostic": contact_diag,
        "artifacts": artifacts,
        "promotion_note": (
            "Passed smoke and trainable_smoke are acceptable pre-real evidence. "
            "Contact/lift are blocked/deferred optional diagnostics and do not fail this gate."
        ),
    }
    report_path = run_dir / "acceptance_report.yaml"
    dashboard_path = run_dir / "dashboard.md"
    write_yaml(report_path, report)
    dashboard_path.write_text(build_dashboard(report), encoding="utf-8")
    update_latest_index(
        ACCEPTANCE_DIR / "latest_runs.yaml",
        {
            "timestamp": timestamp,
            "command": report["command"],
            "success": report["status"] == "passed",
            "status": report["status"],
            "report_path": str(report_path),
            "dashboard_path": str(dashboard_path),
            "reach_success_rate": jitter_summary.get("reach_success_rate"),
            "min_distance_summary": {
                "mean": jitter_summary.get("mean_min_distance_m"),
                "p50": jitter_summary.get("p50_min_distance_m"),
                "p90": jitter_summary.get("p90_min_distance_m"),
                "max": jitter_summary.get("max_min_distance_m"),
            },
            "failure_reason_counts": jitter_summary.get("failure_reason_counts") or {},
            "dataset_trainability_status": trainability_report.get("status"),
        },
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-latest-artifacts", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Use the MTC suite dry-run path for fast tool validation.")
    parser.add_argument("--run-vision-smoke", action="store_true")
    parser.add_argument("--vision-timeout-sec", type=float, default=45.0)
    parser.add_argument("--vision-smoke-report", default="")
    parser.add_argument("--vision-events-path", default="")
    parser.add_argument("--mtc-smoke-report", default="")
    parser.add_argument("--jitter-summary-report", default="")
    parser.add_argument("--trainability-report", default=str(DEFAULT_TRAINABILITY_REPORT))
    parser.add_argument("--real-trainability-report", default=str(DEFAULT_REAL_TRAINABILITY_REPORT))
    parser.add_argument("--candidate-dir", default="")
    parser.add_argument("--jitter-episodes", type=int, default=3)
    parser.add_argument("--jitter-xyz", default="0.01,0.01,0")
    parser.add_argument("--target-xyz", default="0.292,0.131,0.758")
    parser.add_argument("--seed", type=int, default=21)
    parser.add_argument("--mtc-timeout-sec", type=float, default=180.0)
    parser.add_argument("--execute-duration-sec", type=float, default=3.0)
    parser.add_argument("--settle-duration-sec", type=float, default=1.0)
    parser.add_argument("--trace-sample-period-sec", type=float, default=0.05)
    parser.add_argument("--min-reach-success-rate", type=float, default=1.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_acceptance(args)
    print(yaml.safe_dump({"status": report["status"], "artifacts": report["artifacts"]}, sort_keys=False, allow_unicode=True))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
