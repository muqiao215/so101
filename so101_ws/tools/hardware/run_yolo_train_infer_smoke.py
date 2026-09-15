#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


DEFAULT_DATASET = (
    "docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset/yolo-dataset"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def image_count(dataset_dir: Path, split: str) -> int:
    image_dir = dataset_dir / "images" / split
    if not image_dir.exists():
        return 0
    return sum(1 for path in image_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"})


def first_image(dataset_dir: Path, split: str = "train") -> Path | None:
    image_dir = dataset_dir / "images" / split
    if not image_dir.exists():
        return None
    for path in sorted(image_dir.iterdir()):
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
            return path
    return None


def yaml_list(values: list[str]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"


def build_smoke_data_yaml(dataset_dir: Path, output_path: Path) -> dict[str, Any]:
    source_yaml = dataset_dir / "data.yaml"
    manifest_path = dataset_dir / "manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}
    classes = manifest.get("classes") or ["red", "blue"]
    split_counts = {
        "train": image_count(dataset_dir, "train"),
        "debug": image_count(dataset_dir, "debug"),
        "rejected": image_count(dataset_dir, "rejected"),
    }
    val_split = "debug" if split_counts["debug"] > 0 else "train"
    test_split = "rejected" if split_counts["rejected"] > 0 else val_split
    content = "\n".join(
        [
            f"path: {dataset_dir.resolve()}",
            "train: images/train",
            f"val: images/{val_split}",
            f"test: images/{test_split}",
            f"names: {yaml_list([str(item) for item in classes])}",
            "",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return {
        "source_data_yaml": str(source_yaml.resolve()) if source_yaml.exists() else None,
        "smoke_data_yaml": str(output_path.resolve()),
        "classes": classes,
        "split_counts": split_counts,
        "val_split": val_split,
        "test_split": test_split,
    }


def summarize_train_result(result: Any) -> dict[str, Any]:
    save_dir = getattr(result, "save_dir", None)
    return {
        "type": type(result).__name__,
        "save_dir": str(save_dir) if save_dir is not None else None,
        "results_dict": getattr(result, "results_dict", None),
    }


def summarize_predict_results(results: Any) -> dict[str, Any]:
    items = list(results or [])
    first = items[0] if items else None
    boxes = getattr(first, "boxes", None) if first is not None else None
    box_count = 0
    if boxes is not None:
        try:
            box_count = len(boxes)
        except TypeError:
            box_count = int(getattr(boxes, "shape", [0])[0])
    return {"result_count": len(items), "first_box_count": box_count}


def run_smoke(
    dataset_dir: Path,
    *,
    output_dir: Path,
    model: str = "yolo11n.yaml",
    epochs: int = 1,
    imgsz: int = 320,
    batch: int = 2,
    device: str = "cpu",
    dry_run: bool = False,
) -> dict[str, Any]:
    dataset_dir = dataset_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    smoke_yaml_info = build_smoke_data_yaml(dataset_dir, output_dir / "data.smoke.yaml")
    predict_image = first_image(dataset_dir, "train")
    if predict_image is None:
        raise FileNotFoundError(f"no train image found in {dataset_dir / 'images' / 'train'}")

    report: dict[str, Any] = {
        "schema": "so101_yolo_train_infer_smoke_v1",
        "status": "dry_run" if dry_run else "in_progress",
        "dataset_dir": str(dataset_dir),
        "output_dir": str(output_dir),
        "model": model,
        "epochs": epochs,
        "imgsz": imgsz,
        "batch": batch,
        "device": device,
        "data_yaml": smoke_yaml_info,
        "predict_image": str(predict_image.resolve()),
        "promotion_note": (
            "This smoke uses Gazebo color-detector labels to validate the YOLO train/val/predict plumbing. "
            "It is not a real YOLO quality claim until labels come from real camera data or human review."
        ),
    }
    if dry_run:
        write_json(output_dir / "yolo-smoke-report.json", report)
        return report

    try:
        from ultralytics import YOLO
    except Exception as exc:
        report.update({"status": "blocked", "reason": f"{type(exc).__name__}: {exc}"})
        write_json(output_dir / "yolo-smoke-report.json", report)
        return report

    project_dir = output_dir / "ultralytics-runs"
    if project_dir.exists():
        shutil.rmtree(project_dir)
    yolo = YOLO(model)
    train_result = yolo.train(
        data=smoke_yaml_info["smoke_data_yaml"],
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project=str(project_dir),
        name="train",
        exist_ok=True,
        verbose=False,
        plots=False,
        workers=0,
    )
    best_weight = project_dir / "train" / "weights" / "best.pt"
    last_weight = project_dir / "train" / "weights" / "last.pt"
    predict_model_path = best_weight if best_weight.exists() else last_weight
    predict_source = output_dir / "predict-source"
    predict_source.mkdir(parents=True, exist_ok=True)
    predict_image_copy = predict_source / predict_image.name
    shutil.copy2(predict_image, predict_image_copy)
    yolo_for_predict = YOLO(str(predict_model_path)) if predict_model_path.exists() else yolo
    predict_results = yolo_for_predict.predict(
        source=str(predict_image_copy),
        imgsz=imgsz,
        device=device,
        project=str(project_dir),
        name="predict",
        exist_ok=True,
        save=True,
        verbose=False,
    )
    report.update(
        {
            "status": "done",
            "train": summarize_train_result(train_result),
            "weights": {
                "best": str(best_weight.resolve()) if best_weight.exists() else None,
                "last": str(last_weight.resolve()) if last_weight.exists() else None,
            },
            "predict": summarize_predict_results(predict_results),
        }
    )
    write_json(output_dir / "yolo-smoke-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a tiny YOLO train/predict smoke on an exported SO101 YOLO dataset.")
    parser.add_argument("--dataset-dir", default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", default="docs/generated/yolo-smoke/gzv011")
    parser.add_argument("--model", default="yolo11n.yaml")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--batch", type=int, default=2)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = run_smoke(
        Path(args.dataset_dir),
        output_dir=Path(args.output_dir),
        model=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"done", "dry_run"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
