#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
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


def resolve_dataset_index(path: Path) -> Path:
    path = Path(path).resolve()
    if path.is_file():
        return path
    candidate = path / "dataset-index.json"
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(f"dataset-index.json not found: {path}")


def compact_sample(sample: dict[str, Any]) -> dict[str, Any]:
    anchor = sample.get("anchor") if isinstance(sample.get("anchor"), dict) else {}
    detection = sample.get("detection") if isinstance(sample.get("detection"), dict) else {}
    target = sample.get("vision_target") if isinstance(sample.get("vision_target"), dict) else {}
    benchmark_result = sample.get("benchmark_result") if isinstance(sample.get("benchmark_result"), dict) else {}
    benchmark_target = benchmark_result.get("target_object") if isinstance(benchmark_result.get("target_object"), dict) else {}
    benchmark_candidate = benchmark_result.get("grasp_candidate") if isinstance(benchmark_result.get("grasp_candidate"), dict) else {}
    benchmark_eval = benchmark_result.get("evaluation_result") if isinstance(benchmark_result.get("evaluation_result"), dict) else {}
    benchmark_metrics = benchmark_eval.get("metrics") if isinstance(benchmark_eval.get("metrics"), dict) else {}
    joint_state = sample.get("joint_state") if isinstance(sample.get("joint_state"), dict) else {}
    task_status = sample.get("task_status") if isinstance(sample.get("task_status"), dict) else {}
    return {
        "sample_index": sample.get("sample_index"),
        "image_path": anchor.get("image_path"),
        "image_relative_path": anchor.get("image_relative_path"),
        "image_size": [anchor.get("width"), anchor.get("height")],
        "alignment": sample.get("alignment") or {},
        "detections": detection.get("detections") or [],
        "targets": target.get("targets") or [],
        "benchmark_summary": {
            "selected_candidate_id": benchmark_candidate.get("candidate_id"),
            "reach_success": benchmark_metrics.get("reach_success"),
            "min_distance_m": benchmark_metrics.get("min_distance_m"),
            "canonical_target_xyz": benchmark_target.get("world_xyz"),
            "raw_target_xyz": benchmark_target.get("raw_world_xyz"),
        },
        "joint_names": joint_state.get("joint_names") or [],
        "positions": joint_state.get("positions") or [],
        "task_status": task_status,
    }


def build_viewer_data(dataset_index_path: Path, *, limit: int) -> dict[str, Any]:
    dataset_index_path = resolve_dataset_index(dataset_index_path)
    index = load_json(dataset_index_path)
    samples_path = Path(index["samples_path"]).resolve()
    samples = [compact_sample(sample) for sample in load_jsonl(samples_path, limit=limit)]
    return {
        "schema": "so101_episode_viewer_data_v1",
        "dataset_index": str(dataset_index_path),
        "source_episode_id": index.get("source_episode_id"),
        "sample_count": index.get("sample_count"),
        "shown_sample_count": len(samples),
        "validation": index.get("validation") or {},
        "delta_thresholds": index.get("delta_thresholds") or {},
        "samples": samples,
    }


def render_html(data_path: Path, data: dict[str, Any]) -> str:
    title = f"SO101 Episode Viewer - {data.get('source_episode_id') or 'dataset'}"
    first = data.get("samples", [{}])[0] if data.get("samples") else {}
    first_image = first.get("image_path") or ""
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, sans-serif; background: #101410; color: #eef4e8; }}
    main {{ max-width: 1160px; margin: 0 auto; padding: 28px; }}
    .hero {{ display: grid; gap: 8px; margin-bottom: 22px; }}
    .grid {{ display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr); gap: 18px; }}
    .card {{ background: #182018; border: 1px solid #31402e; border-radius: 18px; padding: 16px; box-shadow: 0 20px 60px rgba(0,0,0,.24); }}
    img {{ width: 100%; border-radius: 12px; background: #050705; }}
    select {{ width: 100%; padding: 10px; border-radius: 10px; border: 1px solid #42543d; background: #0d120d; color: #eef4e8; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #0b100b; padding: 12px; border-radius: 12px; max-height: 520px; overflow: auto; }}
    .pill {{ display: inline-block; padding: 4px 8px; margin-right: 6px; border-radius: 999px; background: #263526; color: #bfe8af; font-size: 12px; }}
    @media (max-width: 820px) {{ .grid {{ grid-template-columns: 1fr; }} main {{ padding: 16px; }} }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <span class="pill">dataset viewer</span>
    <h1>{html.escape(title)}</h1>
    <p>Source samples: {html.escape(str(data.get('sample_count')))} · shown: {html.escape(str(data.get('shown_sample_count')))} · validation: {html.escape(str((data.get('validation') or {}).get('status')))}</p>
    <p style="opacity:.82">Viewer now surfaces benchmark summary directly: <code>reach_success</code>, <code>min_distance_m</code>, <code>selected_candidate_id</code>, and canonical/raw target delta.</p>
  </section>
  <section class="grid">
    <article class="card">
      <select id="sampleSelect"></select>
      <div style="height:12px"></div>
      <img id="sampleImage" src="{html.escape(first_image)}" alt="sample image">
    </article>
    <article class="card">
      <h2>Sample Payload</h2>
      <pre id="samplePayload"></pre>
    </article>
  </section>
</main>
<script>
const DATA_PATH = {json.dumps(data_path.name)};
fetch(DATA_PATH).then(r => r.json()).then(data => {{
  const select = document.getElementById('sampleSelect');
  const image = document.getElementById('sampleImage');
  const payload = document.getElementById('samplePayload');
  data.samples.forEach((sample, index) => {{
    const option = document.createElement('option');
    option.value = String(index);
    option.textContent = `#${{sample.sample_index}} · detections=${{sample.detections.length}} · targets=${{sample.targets.length}}`;
    select.appendChild(option);
  }});
  function render() {{
    const sample = data.samples[Number(select.value || 0)] || {{}};
    image.src = sample.image_path || '';
    payload.textContent = JSON.stringify(sample, null, 2);
  }}
  select.addEventListener('change', render);
  render();
}});
</script>
</body>
</html>
"""


def build_viewer(dataset_index: Path, *, output_dir: Path | None = None, limit: int = 80) -> dict[str, Any]:
    dataset_index_path = resolve_dataset_index(dataset_index)
    output_dir = output_dir.resolve() if output_dir else dataset_index_path.parent / "viewer"
    output_dir.mkdir(parents=True, exist_ok=True)
    data = build_viewer_data(dataset_index_path, limit=limit)
    data_path = output_dir / "viewer-data.json"
    html_path = output_dir / "index.html"
    write_json(data_path, data)
    html_path.write_text(render_html(data_path, data), encoding="utf-8")
    return {
        "schema": "so101_episode_viewer_manifest_v1",
        "dataset_index": str(dataset_index_path),
        "viewer_html": str(html_path.resolve()),
        "viewer_data": str(data_path.resolve()),
        "shown_sample_count": data["shown_sample_count"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a local HTML viewer for a vision dataset index.")
    parser.add_argument("dataset_index", help="Path to dataset-index.json or dataset directory")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args()

    manifest = build_viewer(
        Path(args.dataset_index),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        limit=max(int(args.limit), 1),
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
