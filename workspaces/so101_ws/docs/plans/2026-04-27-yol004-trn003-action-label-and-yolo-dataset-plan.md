# YOL-004 / TRN-003 Minimal Landing Plan

Date: 2026-04-27

## Scope

This checkpoint does not run large training. It only makes the current data gaps inspectable and defines the smallest conversion path from vision episode/candidate assets to a YOLO dataset.

## TRN-003 Action Label Gap

Current `lerobot-candidate` rows carry:

- `observation.images.overhead`
- `observation.state`
- `action.type=vision_target_xyz`
- `action.target_xyz`

This is target metadata, not an imitation-learning action label. It can support vision target extraction and dataset plumbing checks, but it must not be promoted as a complete LeRobot policy dataset until one of these labels is attached:

- `follower_joint_action`
- `gazebo_joint_trajectory`
- `joint_positions`
- `joint_deltas`

Inspection command:

```bash
python3 tools/hardware/check_lerobot_candidate_action_gap.py docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset/lerobot-candidate --report-json docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset/lerobot-candidate/action-label-gap-report.json --report-md docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset/lerobot-candidate/action-label-gap-report.md
```

Promotion gate:

- `has_execution_action_labels` must be `true`.
- `action.type` must be one of the accepted execution action types.
- The action label source must be traceable to follower hardware logs or Gazebo controller commands.

## YOL-004 YOLO Dataset Conversion

The minimal converter reads either:

- `dataset-index.json` from `build_vision_dataset_adapter.py`
- a `lerobot-candidate` directory or its `manifest.json`

It writes YOLO layout:

```text
yolo-dataset/
  data.yaml
  manifest.json
  images/train/*.jpg
  labels/train/*.txt
  images/debug/*.jpg
  labels/debug/*.txt
  images/rejected/*.jpg
  labels/rejected/*.txt
```

Conversion command:

```bash
python3 tools/hardware/build_yolo_dataset_from_vision_candidate.py docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset/lerobot-candidate --output-dir docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset/yolo-dataset --classes red,blue --copy-images
```

Current labels are generated from `bbox_xyxy` in the detection payload. Gazebo color-detector labels are acceptable for plumbing smoke only. Real YOLO promotion still requires real-camera images or human-reviewed labels, then training/inference validation with `/detections`.

## Next Landing Steps

1. Run the action gap report on every new candidate package.
2. Export a YOLO-format smoke dataset from the latest vision candidate.
3. Add a human-review stage before any real YOLO fine-tuning.
4. Only after reviewed labels exist, run small YOLO train/infer smoke and verify output returns to `/detections`.
