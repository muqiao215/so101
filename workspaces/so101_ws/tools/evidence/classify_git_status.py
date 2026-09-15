#!/usr/bin/env python3
"""Classify current git status for GZV/RLG closeout review.

This script is intentionally read-only: it only runs `git status --porcelain`
and prints a grouped Markdown summary for commit planning.
"""

from __future__ import annotations

import argparse
import subprocess
from collections import defaultdict
from pathlib import Path


BUCKET_RULES = (
    ("tracking_docs", ("docs/任务清单.md", "docs/进度日志.md", "progress.md", "task_plan.md", "findings.md")),
    ("strategy_docs", ("docs/plans/", "docs/OPS-")),
    ("evidence_keep_candidates", ("docs/evidence/",)),
    ("generated_episode_candidates", ("docs/generated/vision-episodes/", "docs/generated/leader-episodes/")),
    ("ros_bringup_runtime", ("src/so101_bringup/",)),
    ("gazebo_scene", ("src/so101_gazebo/",)),
    ("mes_backend", ("mes_backend/",)),
    ("mes_frontend", ("mes_frontend/",)),
    ("e2e_scripts", ("tools/e2e/",)),
    ("hardware_dataset_tools", ("tools/hardware/",)),
    ("evidence_tools", ("tools/evidence/",)),
)


def run_git_status(repo: Path) -> list[tuple[str, str]]:
    proc = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z"],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )
    entries: list[tuple[str, str]] = []
    parts = proc.stdout.split(b"\0")
    i = 0
    while i < len(parts):
        raw = parts[i]
        i += 1
        if not raw:
            continue
        text = raw.decode("utf-8", errors="replace")
        status = text[:2]
        path = text[3:]
        if status.startswith("R") or status.startswith("C"):
            if i < len(parts) and parts[i]:
                new_path = parts[i].decode("utf-8", errors="replace")
                i += 1
                path = f"{path} -> {new_path}"
        entries.append((status, path))
    return entries


def bucket_for(path: str) -> str:
    comparable = path.split(" -> ")[-1]
    for bucket, prefixes in BUCKET_RULES:
        if any(comparable == prefix or comparable.startswith(prefix) for prefix in prefixes):
            return bucket
    return "other"


def print_markdown(entries: list[tuple[str, str]]) -> None:
    buckets: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for status, path in entries:
        buckets[bucket_for(path)].append((status, path))

    print("# Git Status Classification")
    print()
    print(f"Total changed paths: {len(entries)}")
    print()
    for bucket in sorted(buckets):
        items = sorted(buckets[bucket], key=lambda item: item[1])
        print(f"## {bucket} ({len(items)})")
        for status, path in items:
            print(f"- `{status}` `{path}`")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=".",
        type=Path,
        help="Repository root or any path inside it. Defaults to current directory.",
    )
    args = parser.parse_args()
    print_markdown(run_git_status(args.repo.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
