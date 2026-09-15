#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def source_rows(source: Path, *, splits: list[str]) -> dict[str, list[dict[str, Any]]]:
    source = Path(source).resolve()
    if source.is_file() and source.name == "dataset-index.json":
        index = load_json(source)
        return {"train": load_jsonl(Path(index["samples_path"]))}

    candidate_dir = source.parent if source.is_file() and source.name == "manifest.json" else source
    manifest_path = candidate_dir / "manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}
    manifest_paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    result: dict[str, list[dict[str, Any]]] = {}
    for split in splits:
        key = f"{split}_samples"
        path = Path(manifest_paths[key]) if manifest_paths.get(key) else candidate_dir / f"{split}_samples.jsonl"
        result[split] = load_jsonl(path) if path.exists() else []
    return result


def image_info(row: dict[str, Any]) -> dict[str, Any]:
    observation = row.get("observation") if isinstance(row.get("observation"), dict) else {}
    images = observation.get("images") if isinstance(observation.get("images"), dict) else {}
    overhead = images.get("overhead") if isinstance(images.get("overhead"), dict) else {}
    if overhead:
        return {
            "path": overhead.get("path"),
            "width": overhead.get("width"),
            "height": overhead.get("height"),
        }
    anchor = row.get("anchor") if isinstance(row.get("anchor"), dict) else {}
    return {
        "path": anchor.get("image_path"),
        "width": anchor.get("width"),
        "height": anchor.get("height"),
    }


def detections_from_row(row: dict[str, Any]) -> list[dict[str, Any]]:
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    detection_payload = source.get("detection") if isinstance(source.get("detection"), dict) else row.get("detection")
    if not isinstance(detection_payload, dict):
        return []
    detections = detection_payload.get("detections")
    return detections if isinstance(detections, list) else []


def normalize_bbox_xyxy(bbox: list[Any], *, width: float, height: float) -> tuple[float, float, float, float]:
    if len(bbox) != 4:
        raise ValueError(f"bbox_xyxy must contain 4 values: {bbox}")
    x1, y1, x2, y2 = [float(value) for value in bbox]
    x1 = max(0.0, min(width, x1))
    x2 = max(0.0, min(width, x2))
    y1 = max(0.0, min(height, y1))
    y2 = max(0.0, min(height, y2))
    box_w = max(0.0, x2 - x1)
    box_h = max(0.0, y2 - y1)
    x_center = x1 + box_w / 2.0
    y_center = y1 + box_h / 2.0
    return x_center / width, y_center / height, box_w / width, box_h / height


def class_map_from_rows(rows_by_split: dict[str, list[dict[str, Any]]], requested_classes: list[str]) -> dict[str, int]:
    classes = list(dict.fromkeys(item for item in requested_classes if item))
    if not classes:
        for rows in rows_by_split.values():
            for row in rows:
                for detection in detections_from_row(row):
                    category = str(detection.get("category") or detection.get("name") or "").strip()
                    if category and category not in classes:
                        classes.append(category)
    return {name: index for index, name in enumerate(classes)}


def write_yolo_dataset(
    rows_by_split: dict[str, list[dict[str, Any]]],
    *,
    output_dir: Path,
    classes: list[str],
    copy_images: bool,
    allow_missing_images: bool,
) -> dict[str, Any]:
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    class_to_id = class_map_from_rows(rows_by_split, classes)
    if not class_to_id:
        raise ValueError("no classes found; pass --classes or provide detections with category")

    split_counts: dict[str, dict[str, int]] = {}
    skipped: list[dict[str, Any]] = []
    for split, rows in rows_by_split.items():
        image_dir = output_dir / "images" / split
        label_dir = output_dir / "labels" / split
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        written_images = 0
        written_labels = 0
        written_boxes = 0

        for row_index, row in enumerate(rows):
            info = image_info(row)
            image_path = Path(str(info.get("path") or ""))
            width = float(info.get("width") or 0)
            height = float(info.get("height") or 0)
            if not image_path.exists():
                if allow_missing_images:
                    skipped.append({"split": split, "row_index": row_index, "reason": "missing_image", "path": str(image_path)})
                    continue
                raise FileNotFoundError(f"missing image for {split} row {row_index}: {image_path}")
            if width <= 0 or height <= 0:
                skipped.append({"split": split, "row_index": row_index, "reason": "missing_image_size"})
                continue

            target_image = image_dir / image_path.name
            if copy_images:
                shutil.copy2(image_path, target_image)
            elif not target_image.exists():
                target_image.symlink_to(image_path)
            written_images += 1

            label_lines: list[str] = []
            for detection in detections_from_row(row):
                category = str(detection.get("category") or detection.get("name") or "").strip()
                if category not in class_to_id:
                    continue
                bbox = detection.get("bbox_xyxy")
                if not isinstance(bbox, list):
                    continue
                x_center, y_center, box_w, box_h = normalize_bbox_xyxy(bbox, width=width, height=height)
                if box_w <= 0 or box_h <= 0:
                    continue
                label_lines.append(
                    f"{class_to_id[category]} {x_center:.6f} {y_center:.6f} {box_w:.6f} {box_h:.6f}"
                )
            label_path = label_dir / f"{image_path.stem}.txt"
            label_path.write_text("\n".join(label_lines) + ("\n" if label_lines else ""), encoding="utf-8")
            written_labels += 1
            written_boxes += len(label_lines)

        split_counts[split] = {
            "input_rows": len(rows),
            "written_images": written_images,
            "written_label_files": written_labels,
            "written_boxes": written_boxes,
        }

    names = [name for name, _index in sorted(class_to_id.items(), key=lambda item: item[1])]
    data_yaml = output_dir / "data.yaml"
    data_yaml.write_text(
        "\n".join(
            [
                f"path: {output_dir}",
                "train: images/train",
                "val: images/debug",
                "test: images/rejected",
                f"names: {json.dumps(names)}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    manifest = {
        "schema": "so101_yolo_dataset_export_v1",
        "output_dir": str(output_dir),
        "data_yaml": str(data_yaml),
        "classes": names,
        "class_to_id": class_to_id,
        "split_counts": split_counts,
        "skipped": skipped,
        "promotion_note": "Gazebo color-detector labels are useful for dataset plumbing smoke; real YOLO promotion requires human-reviewed or real-camera labels.",
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="dataset-index.json, lerobot-candidate directory, or candidate manifest.json")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--splits", default="train,debug,rejected")
    parser.add_argument("--classes", default="", help="Comma-separated class names. Default: infer from detections.")
    parser.add_argument("--copy-images", action="store_true", help="Copy images instead of creating symlinks")
    parser.add_argument("--allow-missing-images", action="store_true")
    args = parser.parse_args()

    splits = [item.strip() for item in args.splits.split(",") if item.strip()]
    classes = [item.strip() for item in args.classes.split(",") if item.strip()]
    rows = source_rows(Path(args.source), splits=splits)
    manifest = write_yolo_dataset(
        rows,
        output_dir=Path(args.output_dir),
        classes=classes,
        copy_images=args.copy_images,
        allow_missing_images=args.allow_missing_images,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
