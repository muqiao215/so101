# SO101 Windows 7 Follower Demo

This is a lightweight fallback runtime for graduation-project demos on old Windows 7 machines.
It does not require ROS2, Gazebo, RViz, MoveIt2, Node.js, or Java.

## What It Demonstrates

```text
Browser UI -> local Python HTTP server -> follower action template -> status/log feedback
```

It is a small follower-side loop, not the full ROS2 system.

## Requirements

- Windows 7 SP1 or newer
- Python 3.8.x recommended
- A modern enough browser for local HTML/JS

No ROS2, Gazebo, Node.js, Java, pip package, Flask, pyserial, or LeRobot install is required for the default package.

The default mode is `dry_run=true`, so the UI and logs work without touching hardware.

## Quick Start

```bat
cd win7_follower_demo
run_demo.bat
```

Then open:

```text
http://127.0.0.1:8765
```

## Real Follower Mode

Edit:

```text
config\serial_config.json
```

Set:

```json
{
  "dry_run": false,
  "port": "COM6",
  "backend": "native_win32"
}
```

`native_win32` uses Python `ctypes` and the Windows serial API directly. It sends minimal Feetech STS packets to IDs 1..6.

Keep `max_relative_target_deg` small for the first tests, for example `2.0`. In this fallback package, the value is documented for safety alignment; the native packet sender executes the fixed template goal positions directly.

## Safety Notes

- First run in `dry_run=true`.
- Confirm the arm responds to `home` before running longer templates.
- Keep the arm unloaded and away from table edges.
- Use `home` before longer templates.
- This package does not claim real grasp success.
- This package is a Win7 fallback execution demo, not `trainable_real` and not the ROS2 acceptance suite.

## API

```text
GET  /api/status
GET  /api/templates
POST /api/connect
POST /api/disconnect
POST /api/action
POST /api/stop
```

Example:

```json
{"template": "inspection_sweep"}
```
