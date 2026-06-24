# Package Notes

## Included

- `app.py`: local HTTP server and follower runtime.
- `static/`: browser UI.
- `config/action_templates.json`: fixed industrial demo templates.
- `config/serial_config.json`: serial/runtime settings.
- `config/follower_calibration.json`: copied follower calibration values from the ROS2 project.
- `logs/`: runtime JSONL logs.
- `native_win32` backend: compatibility backend for older Windows packages; no `pyserial` package required.
- `native_posix` backend: direct Linux serial access via Python `termios`/`select`; no `pyserial` package required.

## Not Included

- ROS2
- Gazebo
- RViz
- MoveIt2
- Java backend
- Vue/Node toolchain
- YOLO training/inference stack

## Recommended Demo Script

1. Start with `dry_run=true`.
2. Open `http://127.0.0.1:8765`.
3. Run `home`, `inspection_sweep`, and `wave_demo`.
4. If the real follower serial port is ready on Linux Mint, set `dry_run=false`, `backend=native_posix`, and `port=/dev/ttyACM0` or `/dev/ttyUSB0`.
5. Run `home` first, then small templates only.

## Thesis Wording

Use this wording:

```text
Lightweight fallback follower execution terminal for Linux Mint or low-spec Linux.
```

Avoid this wording:

```text
Full ROS2 system on Linux Mint.
Real grasp success.
trainable_real.
```
