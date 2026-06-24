# SO101 Lightweight Follower Demo

This is a lightweight runtime for graduation-project demos on Linux Mint or other low-spec Linux machines.
It does not require ROS2, Gazebo, RViz, MoveIt2, Node.js, or Java.

## What It Demonstrates

```text
Browser UI -> local Python HTTP server -> follower action template/manual six-axis target -> status/log feedback
```

It is a small follower-side loop, not the full ROS2 system.

## Requirements

- Linux Mint 21/22 or another Ubuntu-like Linux
- Python 3.8.x recommended. Linux Mint 22.3 can use system `python3`.
- A modern enough browser for local HTML/JS

No ROS2, Gazebo, Node.js, Java, pip package, Flask, pyserial, or LeRobot install is required for the default package.

The packaged Linux entry point is intended for the real SO101 follower on `/dev/ttyACM0`.
The UI exposes only two operator modes: monitor mode and action mode.

## Quick Start

Optional environment check:

```bash
python3 check_environment.py
```

Linux Mint:

```bash
cd ..
chmod +x start.sh
./start.sh
```

The startup window prints the frontend address:

```text
Frontend: http://127.0.0.1:8765
```

Each start first closes the old local service on ports 8765/8766, then starts a fresh server.
Closing the startup window stops the service.
Clicking Connect scans the six servos and can take about 20 seconds; wait for the web UI result instead of retrying in the terminal.

## Independent Camera Check

The camera is not part of the SO101 control loop. Use it as a separate UVC device for preview, screenshots, or OpenCV tests.

Verified device:

```text
UVCCamera: Lihappe8_A168
Stable path: /dev/v4l/by-id/usb-Clxet_UVCCamera_12345678-video-index0
Main node:   /dev/video2
Side node:   /dev/video3
```

Prefer the stable `/dev/v4l/by-id/...` path in scripts. Do not hard-code `/dev/video2`, because `/dev/video*` numbers can change after reboot or USB reconnect.

Install tools:

```bash
sudo apt update
sudo apt install -y v4l-utils ffmpeg python3-opencv
```

Set the device variable:

```bash
DEV=/dev/v4l/by-id/usb-Clxet_UVCCamera_12345678-video-index0
```

List devices and supported formats:

```bash
v4l2-ctl --list-devices
v4l2-ctl -d "$DEV" --all
v4l2-ctl -d "$DEV" --list-formats-ext
v4l2-ctl -d "$DEV" --list-ctrls
```

Observed support:

```text
YUYV: 640x480 30fps
MJPG: 640x360, 640x480, 1280x720, 1920x1080 30fps
H264: 640x480, 1280x720, 1920x1080 30fps
```

Measured behavior on this machine: 1080p MJPG and 720p MJPG stream without read errors, but practical frame rate is about 25fps, not a steady 30fps.

## Optional Visual Action Selection

The product console includes a lightweight Visual Inspect button. It is intentionally not a live video stream.
When clicked, the server opens the USB camera, warms up for a few frames, captures one 1280x720 MJPG frame, rotates it 180 degrees, detects the colored sandbags inside the table ROI, saves a static annotated JPEG, and releases the camera.

Default station semantics:

```text
Right blue bag:   raw material zone
Center yellow bag: processing zone
Left purple bag: finished goods zone
```

The visual result only selects a released product action in the existing dropdown. It does not run the robot automatically.
OpenCV is optional; without `python3-opencv`, the main console still starts, but Visual Inspect returns a dependency error.

Preview 1080p MJPG:

```bash
ffplay -f v4l2 \
  -input_format mjpeg \
  -video_size 1920x1080 \
  -framerate 30 \
  "$DEV"
```

Preview 720p MJPG, recommended for OpenCV and lower latency:

```bash
ffplay -f v4l2 \
  -input_format mjpeg \
  -video_size 1280x720 \
  -framerate 30 \
  "$DEV"
```

Capture one 1080p test image:

```bash
ffmpeg -f v4l2 \
  -input_format mjpeg \
  -video_size 1920x1080 \
  -framerate 30 \
  -i "$DEV" \
  -frames:v 1 /tmp/uvc_test_1080p.jpg

xdg-open /tmp/uvc_test_1080p.jpg
```

OpenCV smoke test:

```python
import cv2
import time

dev = "/dev/v4l/by-id/usb-Clxet_UVCCamera_12345678-video-index0"
cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)

cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)

start = time.time()
frames = 0

while True:
    ok, frame = cap.read()
    if not ok:
        print("read failed")
        break

    frames += 1
    elapsed = time.time() - start
    if elapsed >= 1:
        print("FPS:", frames / elapsed)
        start = time.time()
        frames = 0

    cv2.imshow("camera", frame)
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
```

Practical recommendation:

```text
AI / OpenCV: 1280x720 MJPG, about 25fps practical
Screenshot: 1920x1080 MJPG
Most compatible: 640x480 YUYV
Long recording experiments: H264 1920x1080
```

## Leader-Follower Teleoperation Calibration

Teleoperation uses two serial buses:

```text
Follower arm: /dev/serial/by-id/usb-1a86_USB_Single_Serial_5B3E089429-if00
Leader arm:   /dev/serial/by-id/usb-1a86_USB_Single_Serial_5B3D042873-if00
```

Both arms can use servo IDs `1..6` because they are on separate serial ports.

### A/B Route

Use two routes and keep them separate:

```text
A. Official LeRobot route:
   Use it on the capable development machine for official calibration checks and validation.
   Do not make the deployed product depend on the full LeRobot install.

B. Lightweight product route:
   Run this web console with the stdlib Feetech serial driver.
   Keep ports, follower calibration, and teleoperation alignment in this repository.
```

The migration target is route B. The runtime does not need PyTorch, Torchvision, OpenCV, Gym, or the full LeRobot package.

If you only need the low-level Feetech serial dependency for separate tools, install the small packages directly:

```bash
pip install feetech-servo-sdk pyserial deepdiff
```

No domestic mirror is required when the machine already has a proxy.

The calibration file is:

```text
config/teleop_calibration.json
```

This file is meant to be committed to git and migrated with the project. It stores the leader raw positions and follower raw positions for one matched physical pose.

This file is not the same as the official LeRobot motor calibration cache. LeRobot's cache stores each arm's motor `id`, `homing_offset`, `range_min`, and `range_max`. This product file stores a matched leader/follower physical pose, which is what fixes "same motion, different position" during master-follower control.

Calibration flow:

```text
1. Switch to action mode.
2. Connect follower hardware.
3. Put the leader and follower into the same physical pose.
4. Click "扫描主臂".
5. Click "同步当前位置为校准".
6. Commit config/teleop_calibration.json.
```

After calibration, "开始跟随" uses the saved leader/follower raw baseline. The follower starts from its current pose and moves toward the calibrated mapping through the configured speed limit, instead of jumping directly to the saved pose.

If one axis moves in the wrong direction, edit `teleop_invert` in `config/serial_config.json` and change only that axis from `1.0` to `-1.0`, then test with small leader movements.

To inspect official LeRobot calibration files without importing or installing the full LeRobot runtime:

```bash
python3 tools/inspect_lerobot_calibration.py
```

By default it reads:

```text
~/.cache/huggingface/lerobot/calibration/
```

The official SO101 calibration commands can still be used on the capable development machine:

```bash
lerobot-calibrate \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM0 \
  --robot.id=my_awesome_follower_arm

lerobot-calibrate \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM1 \
  --teleop.id=my_awesome_leader_arm
```

After that, return to the web console and click "同步当前位置为校准" with both arms in the same physical pose. Commit `config/teleop_calibration.json` for migration.

## Real Follower Mode

Edit:

```text
config\serial_config.json
```

Linux Mint set:

```json
{
  "monitor_mode": false,
  "port": "/dev/ttyACM0",
  "backend": "native_posix"
}
```

`native_posix` uses Python stdlib `termios` and `select`, not `pyserial`.

The `native_win32` backend remains in the code only for compatibility with older packages; the maintained project target is Linux Mint.

If Linux reports permission denied for `/dev/ttyACM0`, run:

```bash
sudo usermod -aG dialout "$USER"
```

Then log out and log back in. For a one-time local test only:

```bash
sudo chmod 666 /dev/ttyACM0
```

Keep `max_relative_target_deg` small for the first tests, for example `2.0`. In this fallback package, the value is documented for safety alignment; the native packet sender executes the fixed template goal positions directly.

## Safety Notes

- Start in monitor mode when you only want to observe joint readings.
- Switch to action mode only when the arm is clear to move.
- After connecting in action mode, sync the current joint readings before running playback or manual targets.
- Keep the arm unloaded and away from table edges.
- Use `home` before longer templates.
- This package does not claim real grasp success.
- This package is a Mint fallback execution demo, not `trainable_real` and not the ROS2 acceptance suite.

## API

```text
GET  /api/status
GET  /api/templates
POST /api/connect
POST /api/disconnect
POST /api/control/initialize
POST /api/action
POST /api/stop
```

Example:

```json
{"template": "inspection_sweep"}
```

Manual six-axis target:

```json
{"label": "manual_six_axis", "positions": [0.0, -0.2, 0.4, -0.2, 0.0, 0.2]}
```

The first five values are radians. The gripper value is normalized from `0.0` to `1.0`.
In live mode, initialize control from the current hardware observation before sending manual targets or templates.
`/api/stop` requests execution to stop and releases torque; it is not a physical emergency-stop button.
After stopping, wait until the status returns to idle before starting the next action.
