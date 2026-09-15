#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            rows.append(json.loads(text))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def resolve_candidate_dir(path: Path) -> Path:
    path = Path(path).resolve()
    if path.is_file() and path.name == "manifest.json":
        return path.parent
    if path.is_dir():
        return path
    raise FileNotFoundError(f"candidate path does not exist: {path}")


def train_samples_path(candidate_dir: Path, manifest: dict[str, Any]) -> Path:
    paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    return Path(paths["train_samples"]).resolve() if paths.get("train_samples") else candidate_dir / "train_samples.jsonl"


def current_positions(row: dict[str, Any]) -> tuple[list[str], list[float]]:
    state = (((row.get("observation") or {}).get("state") or {}) if isinstance(row.get("observation"), dict) else {})
    names = [str(name) for name in (state.get("joint_names") or [])]
    positions = [float(value) for value in (state.get("positions") or [])]
    return names, positions


def target_positions(row: dict[str, Any], *, mode: str, step_scale: float) -> tuple[str, list[str], list[float]]:
    action = row.get("action") if isinstance(row.get("action"), dict) else {}
    action_type = str(action.get("type") or "")
    names, positions = current_positions(row)
    if mode == "replay_action" and action_type in {"joint_positions", "follower_joint_action"}:
        return action_type, [str(name) for name in action.get("joint_names") or []], [float(value) for value in action.get("positions") or []]
    if mode == "damped_delta" and action_type == "joint_positions":
        target = [float(value) for value in action.get("positions") or []]
        if len(target) == len(positions):
            return (
                "damped_delta",
                names,
                [round(current + (next_value - current) * step_scale, 9) for current, next_value in zip(positions, target)],
            )
    return "hold_position", names, positions


def build_policy_command(row: dict[str, Any], *, index: int, mode: str, step_scale: float) -> dict[str, Any]:
    action_source, joint_names, positions = target_positions(row, mode=mode, step_scale=step_scale)
    return {
        "schema": "so101_policy_inference_smoke_command_v1",
        "sample_index": row.get("sample_index", index),
        "timestamp": row.get("timestamp"),
        "policy": {
            "type": "heuristic_smoke",
            "mode": mode,
            "action_source": action_source,
            "step_scale": step_scale,
        },
        "command": {
            "type": "joint_positions",
            "joint_names": joint_names,
            "positions": positions,
        },
        "trace": {
            "observation_quality": (row.get("quality") or {}).get("status") if isinstance(row.get("quality"), dict) else None,
            "source_action_type": (row.get("action") or {}).get("type") if isinstance(row.get("action"), dict) else None,
        },
    }


def run_smoke(
    candidate_path: Path,
    *,
    output_dir: Path | None = None,
    mode: str = "replay_action",
    limit: int = 16,
    step_scale: float = 1.0,
) -> dict[str, Any]:
    candidate_dir = resolve_candidate_dir(candidate_path)
    manifest = load_json(candidate_dir / "manifest.json")
    rows = load_jsonl(train_samples_path(candidate_dir, manifest), limit=max(limit, 1))
    commands = [build_policy_command(row, index=index, mode=mode, step_scale=step_scale) for index, row in enumerate(rows)]
    invalid = [
        command
        for command in commands
        if not command["command"]["joint_names"]
        or len(command["command"]["joint_names"]) != len(command["command"]["positions"])
    ]
    output_dir = output_dir.resolve() if output_dir else candidate_dir / "policy-smoke"
    report_path = output_dir / "policy-inference-smoke-report.json"
    commands_path = output_dir / "policy-commands.jsonl"
    status = "done" if commands and not invalid else "blocked"
    report = {
        "schema": "so101_policy_inference_smoke_report_v1",
        "status": status,
        "candidate_dir": str(candidate_dir),
        "mode": mode,
        "command_count": len(commands),
        "invalid_command_count": len(invalid),
        "note": "This is a policy interface smoke. It does not claim model quality or real robot safety.",
        "paths": {
            "report": str(report_path.resolve()),
            "commands": str(commands_path.resolve()),
        },
    }
    write_json(report_path, report)
    write_jsonl(commands_path, commands)
    return {"report": report, "report_path": report_path, "commands_path": commands_path}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local policy inference interface smoke over candidate train samples.")
    parser.add_argument("candidate", help="Path to candidate directory or manifest.json")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--mode", choices=["replay_action", "damped_delta", "hold_position"], default="replay_action")
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("--step-scale", type=float, default=1.0)
    parser.add_argument("--fail-on-blocked", action="store_true")
    args = parser.parse_args()

    result = run_smoke(
        Path(args.candidate),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        mode=args.mode,
        limit=args.limit,
        step_scale=max(min(float(args.step_scale), 1.0), 0.0),
    )
    print(json.dumps({"report_path": str(result["report_path"]), **result["report"]}, ensure_ascii=False, indent=2))
    if args.fail_on_blocked and result["report"]["status"] != "done":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
