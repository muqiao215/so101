#!/usr/bin/env python3
import argparse
from pathlib import Path

from action_template_mapping import load_yaml, merge_export_into_waypoints_doc, save_yaml


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge exported MoveIt trajectory mapping into action_templates."
    )
    parser.add_argument(
        "--export-yaml",
        required=True,
        help="Path to pick_place_runner --export-mapping-yaml output.",
    )
    parser.add_argument(
        "--waypoints-yaml",
        required=True,
        help="Path to so101_bringup/config/waypoints.yaml.",
    )
    parser.add_argument(
        "--target-template",
        default="pick_place_default",
        help="Template that should own the exported mapped_steps.",
    )
    parser.add_argument(
        "--alias-template",
        action="append",
        default=[],
        help="Templates that should reuse target template mapped_steps.",
    )
    args = parser.parse_args()

    export_path = Path(args.export_yaml)
    waypoints_path = Path(args.waypoints_yaml)

    export_doc = load_yaml(export_path)
    waypoints_doc = load_yaml(waypoints_path)
    updated = merge_export_into_waypoints_doc(
        waypoints_doc,
        export_doc,
        target_template=args.target_template,
        alias_templates=args.alias_template,
    )
    save_yaml(waypoints_path, updated)
    print(f"synced mapped trajectory into {waypoints_path}")
    print(f"source export: {export_path}")
    print(f"target template: {args.target_template}")
    if args.alias_template:
        print(f"alias templates: {', '.join(args.alias_template)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
