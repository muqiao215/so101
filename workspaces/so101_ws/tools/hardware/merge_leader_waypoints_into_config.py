#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from shutil import copy2
from typing import Any

import yaml


DEFAULT_TARGET_WAYPOINTS = Path("src/so101_bringup/config/waypoints.yaml")
DEFAULT_BACKUP_DIR = Path("docs/generated/leader-waypoints/backups")


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


def load_yaml_doc(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError(f"yaml at {path} must be an object")
    return payload


def save_yaml_doc(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


def validate_draft_doc(draft_doc: dict[str, Any]) -> tuple[list[str], dict[str, list[float]], dict[str, Any]]:
    joint_names = draft_doc.get("joint_names")
    waypoints = draft_doc.get("waypoints")
    templates = draft_doc.get("action_templates")

    if not isinstance(joint_names, list) or not joint_names:
        raise ValueError("draft yaml missing non-empty joint_names")
    if not isinstance(waypoints, dict) or not waypoints:
        raise ValueError("draft yaml missing non-empty waypoints")
    if not isinstance(templates, dict) or not templates:
        raise ValueError("draft yaml missing non-empty action_templates")

    normalized_joint_names = [str(name) for name in joint_names]
    for name, positions in waypoints.items():
        if not isinstance(positions, list) or len(positions) != len(normalized_joint_names):
            raise ValueError(f"draft waypoint '{name}' does not match joint_names length")
    return normalized_joint_names, waypoints, templates


def merge_draft_into_waypoints_doc(
    target_doc: dict[str, Any],
    draft_doc: dict[str, Any],
    *,
    template_name: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    updated = dict(target_doc)
    target_joint_names = updated.get("joint_names")
    draft_joint_names, draft_waypoints, draft_templates = validate_draft_doc(draft_doc)

    if target_joint_names is None:
        updated["joint_names"] = draft_joint_names
    elif list(target_joint_names) != draft_joint_names:
        raise ValueError(
            f"joint_names mismatch: target={list(target_joint_names)} draft={draft_joint_names}"
        )

    updated_waypoints = dict(updated.get("waypoints", {}))
    updated_templates = dict(updated.get("action_templates", {}))

    merged_waypoint_names: list[str] = []
    for name, positions in draft_waypoints.items():
        updated_waypoints[str(name)] = [float(value) for value in positions]
        merged_waypoint_names.append(str(name))

    if template_name:
        if template_name not in draft_templates:
            raise ValueError(f"template '{template_name}' not found in draft yaml")
        selected_templates = {template_name: draft_templates[template_name]}
    else:
        selected_templates = draft_templates

    merged_template_names: list[str] = []
    for name, template in selected_templates.items():
        if not isinstance(template, dict):
            raise ValueError(f"template '{name}' must be an object")
        updated_templates[str(name)] = template
        merged_template_names.append(str(name))

    updated["waypoints"] = updated_waypoints
    updated["action_templates"] = updated_templates
    return updated, {
        "merged_waypoint_names": merged_waypoint_names,
        "merged_template_names": merged_template_names,
    }


def build_backup_path(backup_dir: Path, target_waypoints_path: Path) -> Path:
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    return backup_dir / f"{timestamp}-{target_waypoints_path.name}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge generated leader waypoint draft yaml into src/so101_bringup/config/waypoints.yaml."
    )
    parser.add_argument(
        "--draft-yaml",
        required=True,
        help="Path to generated leader waypoint draft yaml.",
    )
    parser.add_argument(
        "--waypoints-yaml",
        default="",
        help="Target waypoints.yaml path. Default: src/so101_bringup/config/waypoints.yaml",
    )
    parser.add_argument(
        "--template-name",
        default="",
        help="Only merge one template from the draft. Default: merge all templates in draft.",
    )
    parser.add_argument(
        "--backup-dir",
        default="",
        help="Backup directory. Default: docs/generated/leader-waypoints/backups",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print summary without modifying target waypoints.yaml.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    workspace_root = discover_workspace_root(Path(__file__))

    draft_yaml_path = Path(args.draft_yaml).resolve()
    target_waypoints_path = (
        Path(args.waypoints_yaml).resolve()
        if args.waypoints_yaml
        else (workspace_root / DEFAULT_TARGET_WAYPOINTS).resolve()
    )
    backup_dir = (
        Path(args.backup_dir).resolve()
        if args.backup_dir
        else (workspace_root / DEFAULT_BACKUP_DIR).resolve()
    )

    if not draft_yaml_path.exists():
        raise FileNotFoundError(f"draft yaml not found: {draft_yaml_path}")
    if not target_waypoints_path.exists():
        raise FileNotFoundError(f"target waypoints yaml not found: {target_waypoints_path}")

    draft_doc = load_yaml_doc(draft_yaml_path)
    target_doc = load_yaml_doc(target_waypoints_path)
    updated_doc, summary = merge_draft_into_waypoints_doc(
        target_doc,
        draft_doc,
        template_name=(args.template_name.strip() or None),
    )

    result = {
        "draft_yaml": str(draft_yaml_path),
        "target_waypoints_yaml": str(target_waypoints_path),
        "dry_run": bool(args.dry_run),
        "merged_waypoint_count": len(summary["merged_waypoint_names"]),
        "merged_template_count": len(summary["merged_template_names"]),
        "merged_waypoint_names": summary["merged_waypoint_names"],
        "merged_template_names": summary["merged_template_names"],
        "backup_path": None,
    }

    if not args.dry_run:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = build_backup_path(backup_dir, target_waypoints_path)
        copy2(target_waypoints_path, backup_path)
        save_yaml_doc(target_waypoints_path, updated_doc)
        result["backup_path"] = str(backup_path)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
