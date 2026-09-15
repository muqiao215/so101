# TRN-002 Native LeRobot Export Notes

Date: 2026-04-27

## Scope

This note records the native LeRobot export environment decisions for `TRN-002`. It is documentation-only and does not change exporter logic.

## Final Invocation Pattern

Do not create or activate an explicit project venv for this export path. Use `uv run --isolated` and scrub ROS/user Python leakage at the process boundary:

```bash
UV_HTTP_TIMEOUT=300 env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 \
  uv run --isolated --python 3.10 \
  --with 'lerobot==0.4.4' \
  --with 'evdev==1.6.1' \
  --with 'numpy>=2,<3' \
  --with 'pandas>=2.2,<2.4' \
  --with 'pyarrow>=15,<24' \
  --with 'pillow>=10,<12' \
  python tools/hardware/export_lerobot_candidate_to_native.py \
  docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset/lerobot-candidate/manifest.json \
  --output-dir docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset/lerobot-native-uvrun \
  --overwrite --fail-on-blocked
```

`UV_HTTP_TIMEOUT=300` is intentional because `av` and other large packages can time out on this WSL host.

## Environment Pitfalls

- `PYTHONPATH` from ROS Humble can include `/opt/ros/humble/...` and `/usr/lib/python3/dist-packages`.
- If `PYTHONPATH` is not removed, the temporary `uv run` interpreter can still import system packages, observed as `numpy 1.21.5` and `pillow 9.0.1`.
- `PYTHONHOME` should also be removed, and `PYTHONNOUSERSITE=1` should be set so user-site packages do not leak into the isolated run.
- LeRobot `0.4.4` pulls `rerun-sdk`; that dependency path requires `numpy>=2`, so pinning `numpy<2` is invalid for the current native export route.
- `pynput` pulls `evdev`. On this WSL host, uv rejected wheel metadata for newer `evdev` releases observed in the `1.9.x`, `1.8.x`, and `1.7.x` ranges with `Metadata field Name not found`.
- `evdev==1.6.1` installs successfully here and is therefore pinned in the known-good command.

## Evidence

- Native export output directory: `docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset/lerobot-native-uvrun/`
- Export report: `docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset/lerobot-native-uvrun/native-export-report.json`
- Recorded package versions: `docs/generated/vision-episodes/lerobot-v3-uvrun-packages.json`
- Successful environment versions recorded in the progress log: `lerobot=0.4.4`, `numpy=2.2.6`, `pandas=2.3.3`, `pillow=11.3.0`

## Status

`TRN-002` is complete for native dataset environment and export plumbing. The exported rows still use `action.type=vision_target_xyz`; executable imitation-learning action labels remain owned by `TRN-003`.
