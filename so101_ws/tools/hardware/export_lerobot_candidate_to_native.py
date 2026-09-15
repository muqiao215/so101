#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.metadata
import json
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any


SCHEMA = "so101_native_lerobot_export_v1"
DEFAULT_REPO_ID = "so101/gazebo-vision-smoke"
DEFAULT_OUTPUT_DIR_NAME = "lerobot-native"


class NativeExportBlocked(RuntimeError):
    def __init__(self, reason: str, *, details: dict[str, Any] | None = None):
        super().__init__(reason)
        self.reason = reason
        self.details = details or {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def package_version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def environment_snapshot() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "packages": {
            "lerobot": package_version("lerobot"),
            "numpy": package_version("numpy"),
            "pandas": package_version("pandas"),
            "torch": package_version("torch"),
            "datasets": package_version("datasets"),
            "pyarrow": package_version("pyarrow"),
            "pillow": package_version("pillow"),
        },
    }


def bootstrap_advice() -> dict[str, Any]:
    requirements = [
        "# Keep this isolated from the ROS2/user Python environment.",
        "# Confirm the exact LeRobot release against the project before training.",
        "lerobot==0.4.4",
        "# Newer evdev releases currently build wheels with metadata uv rejects on this WSL host.",
        "evdev==1.6.1",
        "# LeRobot 0.4.4 pulls rerun-sdk>=0.24,<0.27, which requires numpy>=2.",
        "numpy>=2,<3",
        "pandas>=2.2,<2.4",
        "pyarrow>=15,<24",
        "pillow>=10,<12",
    ]
    uv_run_prefix = (
        "UV_HTTP_TIMEOUT=300 env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 "
        "uv run --isolated --python 3.10 "
        "--with 'lerobot==0.4.4' "
        "--with 'evdev==1.6.1' "
        "--with 'numpy>=2,<3' "
        "--with 'pandas>=2.2,<2.4' "
        "--with 'pyarrow>=15,<24' "
        "--with 'pillow>=10,<12' "
    )
    return {
        "environment_mode": "uv_run_isolated",
        "commands": [
            "cat > /tmp/so101-lerobot-v3-requirements.txt <<'REQ'\n"
            + "\n".join(requirements)
            + "\nREQ",
            uv_run_prefix
            + "python tools/hardware/export_lerobot_candidate_to_native.py "
            "docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset/lerobot-candidate/manifest.json "
            "--output-dir docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset/lerobot-native "
            "--overwrite",
            uv_run_prefix
            + "python - <<'PY' > docs/generated/vision-episodes/lerobot-v3-uvrun-packages.json\n"
            "import importlib.metadata, json\n"
            "packages = ['lerobot', 'evdev', 'numpy', 'pandas', 'pyarrow', 'pillow', 'torch', 'datasets']\n"
            "print(json.dumps({name: importlib.metadata.version(name) for name in packages}, indent=2))\n"
            "PY",
        ],
        "requirements_lock_suggestion": requirements,
    }


def resolve_candidate_input(input_path: Path) -> dict[str, Any]:
    input_path = input_path.resolve()
    if input_path.name == "manifest.json":
        manifest = load_json(input_path)
        train_samples = Path(manifest["paths"]["train_samples"]).resolve()
        return {
            "input_kind": "manifest",
            "manifest_path": input_path,
            "manifest": manifest,
            "train_samples_path": train_samples,
        }

    if input_path.name == "train_samples.jsonl":
        manifest_path = input_path.parent / "manifest.json"
        manifest = load_json(manifest_path) if manifest_path.exists() else None
        return {
            "input_kind": "train_samples",
            "manifest_path": manifest_path if manifest_path.exists() else None,
            "manifest": manifest,
            "train_samples_path": input_path,
        }

    raise ValueError("input must be a lerobot-candidate manifest.json or train_samples.jsonl")


def image_shape_from_rows(rows: list[dict[str, Any]]) -> list[int]:
    for row in rows:
        overhead = (((row.get("observation") or {}).get("images") or {}).get("overhead") or {})
        width = overhead.get("width")
        height = overhead.get("height")
        if width and height:
            return [int(height), int(width), 3]
    return [480, 640, 3]


def joint_names_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    for row in rows:
        names = (((row.get("observation") or {}).get("state") or {}).get("joint_names") or [])
        if names:
            return [str(name) for name in names]
    return []


def action_vector_from_row(row: dict[str, Any]) -> list[float]:
    action = row.get("action") if isinstance(row.get("action"), dict) else {}
    if isinstance(action.get("positions"), list):
        return [float(item) for item in action["positions"]]
    if isinstance(action.get("target_xyz"), list):
        return [float(item) for item in action["target_xyz"]]
    return []


def action_names_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    for row in rows:
        action = row.get("action") if isinstance(row.get("action"), dict) else {}
        if isinstance(action.get("joint_names"), list) and action["joint_names"]:
            return [str(name) for name in action["joint_names"]]
        if isinstance(action.get("positions"), list):
            names = joint_names_from_rows([row])
            if names and len(names) == len(action["positions"]):
                return names
        if isinstance(action.get("target_xyz"), list):
            return ["target_x", "target_y", "target_z"]
    return []


def build_lerobot_features(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    joint_names = joint_names_from_rows(rows)
    state_size = len(joint_names)
    if state_size == 0:
        state_size = len((((rows[0].get("observation") or {}).get("state") or {}).get("positions") or []))
        joint_names = [f"joint_{index}" for index in range(state_size)]
    if state_size == 0:
        raise NativeExportBlocked("candidate train samples do not contain observation.state.positions")

    action_names = action_names_from_rows(rows)
    action_size = len(action_names)
    if action_size == 0:
        for row in rows:
            action_size = len(action_vector_from_row(row))
            if action_size:
                action_names = [f"action_{index}" for index in range(action_size)]
                break
    if action_size == 0:
        raise NativeExportBlocked("candidate train samples do not contain action.positions or action.target_xyz")

    return {
        "observation.images.overhead": {
            "dtype": "image",
            "shape": tuple(image_shape_from_rows(rows)),
            "names": ["height", "width", "channels"],
        },
        "observation.state": {
            "dtype": "float32",
            "shape": (state_size,),
            "names": joint_names,
        },
        "action": {
            "dtype": "float32",
            "shape": (action_size,),
            "names": action_names,
        },
    }


def import_native_dependencies() -> dict[str, Any]:
    try:
        import numpy as np
        from PIL import Image
        from lerobot.datasets.lerobot_dataset import LeRobotDataset
    except Exception as exc:
        raise NativeExportBlocked(
            f"{type(exc).__name__}: {exc}",
            details={"traceback": traceback.format_exc(limit=12)},
        ) from exc
    return {"np": np, "Image": Image, "LeRobotDataset": LeRobotDataset}


def require_vector(row: dict[str, Any], path: str, *, size: int) -> list[float]:
    value: Any = row
    for part in path.split("."):
        if not isinstance(value, dict):
            value = None
            break
        value = value.get(part)
    if not isinstance(value, list) or len(value) != size:
        raise NativeExportBlocked(f"sample {row.get('sample_index')} is missing {path} with size {size}")
    return [float(item) for item in value]


def require_image_path(row: dict[str, Any]) -> Path:
    overhead = (((row.get("observation") or {}).get("images") or {}).get("overhead") or {})
    image_path = overhead.get("path")
    if not image_path:
        raise NativeExportBlocked(f"sample {row.get('sample_index')} is missing observation.images.overhead.path")
    path = Path(image_path)
    if not path.exists():
        raise NativeExportBlocked(f"sample {row.get('sample_index')} image does not exist: {path}")
    return path


def add_rows_to_native_dataset(dataset: Any, rows: list[dict[str, Any]], features: dict[str, Any], deps: dict[str, Any]) -> None:
    np = deps["np"]
    Image = deps["Image"]
    state_size = int(features["observation.state"]["shape"][0])
    action_size = int(features["action"]["shape"][0])
    for row in rows:
        image = Image.open(require_image_path(row)).convert("RGB")
        action_vector = action_vector_from_row(row)
        if len(action_vector) != action_size:
            raise NativeExportBlocked(
                f"sample {row.get('sample_index')} action vector size mismatch: expected {action_size}, got {len(action_vector)}"
            )
        frame = {
            "task": row.get("task") or "so101 gazebo vision target",
            "observation.images.overhead": np.asarray(image),
            "observation.state": np.asarray(
                require_vector(row, "observation.state.positions", size=state_size), dtype=np.float32
            ),
            "action": np.asarray(action_vector, dtype=np.float32),
        }
        dataset.add_frame(frame)


def copy_sidecars(candidate: dict[str, Any], output_dir: Path) -> list[str]:
    copied: list[str] = []
    sidecar_dir = output_dir / "sidecars"
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = candidate.get("manifest_path")
    if manifest_path:
        dst = sidecar_dir / "candidate-manifest.json"
        shutil.copy2(manifest_path, dst)
        copied.append(str(dst.resolve()))

    manifest = candidate.get("manifest") or {}
    for key, dst_name in (
        ("source_dataset_index", "source-dataset-index.json"),
        ("source_validation_report", "source-validation-report.json"),
    ):
        value = manifest.get(key)
        if value and Path(value).exists():
            dst = sidecar_dir / dst_name
            shutil.copy2(value, dst)
            copied.append(str(dst.resolve()))
    return copied


def export_native(
    input_path: Path,
    *,
    output_dir: Path | None = None,
    repo_id: str = DEFAULT_REPO_ID,
    fps: int | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    candidate = resolve_candidate_input(input_path)
    rows = load_jsonl(candidate["train_samples_path"])
    if not rows:
        raise NativeExportBlocked(f"no train samples found in {candidate['train_samples_path']}")

    manifest = candidate.get("manifest") or {}
    output_dir = output_dir.resolve() if output_dir else candidate["train_samples_path"].parent.parent / DEFAULT_OUTPUT_DIR_NAME
    report_path = output_dir / "native-export-report.json"
    selected_fps = int(fps or manifest.get("fps") or 5)
    features = build_lerobot_features(rows)

    base_report = {
        "schema": SCHEMA,
        "status": "dry_run" if dry_run else "in_progress",
        "input_kind": candidate["input_kind"],
        "input_path": str(Path(input_path).resolve()),
        "candidate_manifest_path": str(candidate["manifest_path"]) if candidate.get("manifest_path") else None,
        "train_samples_path": str(candidate["train_samples_path"]),
        "output_dir": str(output_dir),
        "repo_id": repo_id,
        "fps": selected_fps,
        "sample_count": len(rows),
        "features": features,
        "environment": environment_snapshot(),
    }
    if dry_run:
        return base_report

    if output_dir.exists():
        if not overwrite:
            raise NativeExportBlocked(f"output directory already exists, pass --overwrite to replace: {output_dir}")
        shutil.rmtree(output_dir)

    deps = import_native_dependencies()
    try:
        dataset = deps["LeRobotDataset"].create(
            repo_id=repo_id,
            fps=selected_fps,
            root=output_dir,
            robot_type="so101_gazebo_vision",
            features=features,
            use_videos=False,
        )
        add_rows_to_native_dataset(dataset, rows, features, deps)
        dataset.save_episode(parallel_encoding=False)
        dataset.finalize()
    except NativeExportBlocked:
        raise
    except Exception as exc:
        raise NativeExportBlocked(
            f"{type(exc).__name__}: {exc}",
            details={"traceback": traceback.format_exc(limit=16)},
        ) from exc

    sidecars = copy_sidecars(candidate, output_dir)
    report = {
        **base_report,
        "status": "done",
        "native_dataset_root": str(output_dir.resolve()),
        "sidecars": sidecars,
        "bootstrap_advice": None,
    }
    write_json(report_path, report)
    return report


def blocked_report(
    input_path: Path,
    *,
    output_dir: Path,
    reason: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = {
        "schema": SCHEMA,
        "status": "blocked",
        "input_path": str(Path(input_path).resolve()),
        "output_dir": str(output_dir.resolve()),
        "reason": reason,
        "details": details or {},
        "environment": environment_snapshot(),
        "bootstrap_advice": bootstrap_advice(),
    }
    write_json(output_dir / "native-export-blocked-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Export SO101 LeRobot candidate rows to a native LeRobot v3 dataset.")
    parser.add_argument("input", help="Path to lerobot-candidate/manifest.json or train_samples.jsonl")
    parser.add_argument("--output-dir", default="", help="Output directory for the native LeRobot dataset")
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--fps", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fail-on-blocked", action="store_true", help="Return non-zero when native export is blocked")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir).resolve() if args.output_dir else input_path.resolve().parent.parent / DEFAULT_OUTPUT_DIR_NAME
    try:
        report = export_native(
            input_path,
            output_dir=output_dir,
            repo_id=args.repo_id,
            fps=args.fps,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
    except NativeExportBlocked as exc:
        report = blocked_report(input_path, output_dir=output_dir, reason=exc.reason, details=exc.details)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2 if args.fail_on_blocked else 0

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
