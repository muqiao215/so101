#!/usr/bin/env python3
import copy
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml


def load_yaml(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML at {path} must be an object.")
    return data


def save_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


def merge_export_into_waypoints_doc(
    waypoints_doc: Dict[str, Any],
    export_doc: Dict[str, Any],
    target_template: str,
    alias_templates: Iterable[str],
) -> Dict[str, Any]:
    updated = copy.deepcopy(waypoints_doc)
    templates = updated.setdefault("action_templates", {})
    if target_template not in templates:
        raise ValueError(f"target template '{target_template}' not found in waypoints yaml")

    export_steps = export_doc.get("steps", {})
    if not isinstance(export_steps, dict) or not export_steps:
        raise ValueError("export yaml missing non-empty 'steps'")

    sequence = list(templates[target_template].get("sequence", []))
    if not sequence:
        raise ValueError(f"target template '{target_template}' has empty sequence")

    normalized_sequence = []
    for step_name in sequence:
        if step_name not in normalized_sequence:
            normalized_sequence.append(step_name)

    export_step_names = list(export_steps.keys())
    if export_step_names != normalized_sequence:
        raise ValueError(
            f"export steps {export_step_names} do not match template sequence {normalized_sequence}"
        )

    templates[target_template]["mapped_steps"] = copy.deepcopy(export_steps)
    templates[target_template]["trajectory_mapping_source"] = {
        "source_action_template": export_doc.get("source_action_template", ""),
        "joint_names": copy.deepcopy(export_doc.get("joint_names", [])),
        "group": export_doc.get("group", ""),
        "summary": copy.deepcopy(export_doc.get("summary", {})),
    }

    for alias in alias_templates:
        if alias not in templates:
            raise ValueError(f"alias template '{alias}' not found in waypoints yaml")
        alias_sequence = list(templates[alias].get("sequence", []))
        if alias_sequence != sequence:
            raise ValueError(
                f"alias template '{alias}' sequence {alias_sequence} does not match {sequence}"
            )
        templates[alias]["trajectory_source_template"] = target_template

    return updated


def resolve_template_mapping(
    templates: Dict[str, Any],
    template_id: str,
) -> Optional[Dict[str, Any]]:
    template = templates.get(template_id, {})
    mapped_steps = template.get("mapped_steps")
    if isinstance(mapped_steps, dict) and mapped_steps:
        return mapped_steps

    source_template_id = str(template.get("trajectory_source_template", "")).strip()
    if source_template_id:
        source_template = templates.get(source_template_id, {})
        source_steps = source_template.get("mapped_steps")
        if isinstance(source_steps, dict) and source_steps:
            return source_steps

    return None


def resolve_step_mapping(
    templates: Dict[str, Any],
    template_id: str,
    step_name: str,
) -> Optional[Dict[str, Any]]:
    mapped_steps = resolve_template_mapping(templates, template_id)
    if not mapped_steps:
        return None
    step_mapping = mapped_steps.get(step_name)
    return step_mapping if isinstance(step_mapping, dict) else None
