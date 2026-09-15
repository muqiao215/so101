#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import yaml

from so101_units import JOINT_NAMES, apply_urdf_map


SCENE_DIR = Path(__file__).resolve().parent
DEFAULT_DEMO_ROOT = Path(__file__).resolve().parents[1] / "mint_follower_demo"
DEFAULT_JOINT_MAP = SCENE_DIR / "so101_official_to_urdf.yaml"
DEFAULT_RVIZ_LAUNCH = SCENE_DIR / "launch_rviz_joint_states_only.launch.py"


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SO101 Sync Player</title>
  <style>
    :root { color-scheme: dark; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #101214; color: #eef1f3; }
    main { max-width: 1280px; margin: 0 auto; padding: 24px; }
    h1 { margin: 0 0 18px; font-size: 24px; font-weight: 650; }
    .grid { display: grid; grid-template-columns: 390px 1fr; gap: 16px; align-items: start; }
    section { background: #191c20; border: 1px solid #2a3036; border-radius: 8px; padding: 16px; }
    label { display: block; color: #aab3bd; font-size: 13px; margin: 12px 0 6px; }
    select, input { width: 100%; box-sizing: border-box; border: 1px solid #3a424b; border-radius: 6px; padding: 10px; background: #101214; color: #eef1f3; font-size: 14px; }
    .row { display: flex; gap: 8px; align-items: center; }
    .row > * { flex: 1; }
    button { border: 0; border-radius: 6px; padding: 10px 12px; color: #fff; background: #2f6df6; font-size: 14px; cursor: pointer; }
    button.secondary { background: #39424d; }
    button.danger { background: #b33a3a; }
    button:disabled { opacity: .45; cursor: not-allowed; }
    .status { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 12px; }
    .metric { background: #101214; border: 1px solid #2a3036; border-radius: 6px; padding: 10px; }
    .metric strong { display: block; font-size: 18px; margin-top: 4px; }
    .muted { color: #aab3bd; }
    pre { height: 440px; overflow: auto; white-space: pre-wrap; margin: 0; padding: 12px; background: #0b0d0f; border: 1px solid #2a3036; border-radius: 6px; color: #d7dde3; }
    .check { display: flex; gap: 8px; align-items: center; margin-top: 12px; color: #d7dde3; }
    .check input { width: auto; }
    .debug-grid { display: grid; grid-template-columns: 120px 34px 1fr 72px 34px; gap: 8px; align-items: center; margin: 8px 0; }
    .debug-grid button { padding: 8px; }
    .joint-name { color: #d7dde3; font-size: 13px; }
    input[type=range] { padding: 0; }
    @media (max-width: 860px) { .grid { grid-template-columns: 1fr; } .status { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>SO101 Sync Player</h1>
    <div class="grid">
      <section>
        <button class="secondary" onclick="openRviz()">Open RViz</button>
        <label>Published action / recording</label>
        <select id="motion"></select>
        <div class="row">
          <div>
            <label>Delay seconds</label>
            <input id="delay" type="number" min="0.03" max="3" step="0.01" value="0.25">
          </div>
          <div>
            <label>Repeat</label>
            <input id="repeat" type="number" min="1" max="999" step="1" value="1">
          </div>
        </div>
        <label class="check"><input id="loop" type="checkbox"> Loop until stopped</label>
        <label class="check"><input id="real" type="checkbox" checked> Send to real follower</label>
        <label class="check"><input id="rviz" type="checkbox" checked> Publish to RViz</label>
        <div class="row" style="margin-top:16px">
          <button onclick="startPlay()">Start</button>
          <button class="danger" onclick="stopPlay()">Stop</button>
        </div>
        <hr style="border:0;border-top:1px solid #2a3036;margin:18px 0">
        <label>Manual sync debug</label>
        <div id="manual"></div>
        <div class="row">
          <div>
            <label>Step</label>
            <input id="step" type="number" min="0.1" max="20" step="0.1" value="2">
          </div>
          <div>
            <label>Debug targets</label>
            <button class="secondary" onclick="readCurrent()">Read current</button>
          </div>
        </div>
        <div class="row" style="margin-top:12px">
          <button onclick="applyManual()">Apply</button>
          <button class="secondary" onclick="zeroManual()">Zero preview</button>
        </div>
      </section>
      <section>
        <div class="status">
          <div class="metric"><span class="muted">State</span><strong id="state">-</strong></div>
          <div class="metric"><span class="muted">Frame</span><strong id="frame">-</strong></div>
          <div class="metric"><span class="muted">Recording</span><strong id="current">-</strong></div>
        </div>
        <pre id="log"></pre>
      </section>
    </div>
  </main>
  <script>
    async function api(path, body) {
      const options = body ? {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)} : {};
      const res = await fetch(path, options);
      const data = await res.json();
      if (!data.ok && data.error) throw new Error(data.error);
      return data;
    }
    function appendLog(line) {
      const log = document.getElementById('log');
      log.textContent = `${new Date().toLocaleTimeString()}  ${line}\n` + log.textContent;
    }
    const jointNames = ['shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_roll', 'gripper'];
    const manualValues = [0, 0, 0, 0, 0, 0];
    function renderManual() {
      const root = document.getElementById('manual');
      root.innerHTML = '';
      jointNames.forEach((name, index) => {
        const row = document.createElement('div');
        row.className = 'debug-grid';
        const label = document.createElement('div');
        label.className = 'joint-name';
        label.textContent = name;
        const minus = document.createElement('button');
        minus.className = 'secondary';
        minus.textContent = '-';
        const slider = document.createElement('input');
        slider.type = 'range';
        slider.min = name === 'gripper' ? '0' : '-100';
        slider.max = '100';
        slider.step = '0.1';
        slider.value = manualValues[index];
        const input = document.createElement('input');
        input.type = 'number';
        input.min = slider.min;
        input.max = slider.max;
        input.step = '0.1';
        input.value = Number(manualValues[index]).toFixed(1);
        const sync = (value) => {
          const low = Number(slider.min);
          const high = Number(slider.max);
          manualValues[index] = Math.max(low, Math.min(high, Number(value)));
          slider.value = manualValues[index];
          input.value = Number(manualValues[index]).toFixed(1);
        };
        slider.oninput = () => sync(slider.value);
        input.onchange = () => sync(input.value);
        minus.onclick = () => { sync(manualValues[index] - Number(document.getElementById('step').value || 1)); applyManual(); };
        const plus = document.createElement('button');
        plus.className = 'secondary';
        plus.textContent = '+';
        plus.onclick = () => { sync(manualValues[index] + Number(document.getElementById('step').value || 1)); applyManual(); };
        row.append(label, minus, slider, input, plus);
        root.appendChild(row);
      });
    }
    async function refreshMotions() {
      const data = await api('/api/motions');
      const select = document.getElementById('motion');
      select.innerHTML = '';
      for (const row of data.motions) {
        const opt = document.createElement('option');
        opt.value = row.id;
        opt.textContent = `${row.kind}: ${row.display_name || row.id}  (${row.samples} frames, ${row.delay}s)`;
        opt.dataset.delay = row.delay || 0.25;
        select.appendChild(opt);
      }
      select.onchange = () => {
        const opt = select.selectedOptions[0];
        if (opt && opt.dataset.delay) document.getElementById('delay').value = opt.dataset.delay;
      };
      select.onchange();
    }
    async function refreshStatus() {
      try {
        const s = await api('/api/status');
        document.getElementById('state').textContent = s.running ? 'running' : 'idle';
        document.getElementById('frame').textContent = `${s.frame || 0}/${s.total || 0}`;
        document.getElementById('current').textContent = s.recording || '-';
        if (s.message) appendLog(s.message);
        if (s.error) appendLog(`ERROR: ${s.error}`);
      } catch (err) {
        appendLog(`status failed: ${err.message}`);
      }
    }
    async function startPlay() {
      try {
        const body = {
          motion: document.getElementById('motion').value,
          delay: Number(document.getElementById('delay').value),
          repeat: Number(document.getElementById('repeat').value),
          loop: document.getElementById('loop').checked,
          real: document.getElementById('real').checked,
          rviz: document.getElementById('rviz').checked
        };
        const data = await api('/api/start', body);
        appendLog(data.message || 'started');
      } catch (err) {
        appendLog(`start failed: ${err.message}`);
      }
    }
    async function stopPlay() {
      try {
        const data = await api('/api/stop', {});
        appendLog(data.message || 'stopped');
      } catch (err) {
        appendLog(`stop failed: ${err.message}`);
      }
    }
    async function openRviz() {
      try {
        const data = await api('/api/open-rviz', {});
        appendLog(data.message || 'rviz requested');
      } catch (err) {
        appendLog(`rviz failed: ${err.message}`);
      }
    }
    async function readCurrent() {
      try {
        const data = await api('/api/manual/read-current', {});
        data.positions.forEach((v, i) => manualValues[i] = Number(v));
        renderManual();
        appendLog('current real positions loaded');
      } catch (err) {
        appendLog(`read current failed: ${err.message}`);
      }
    }
    async function applyManual() {
      try {
        const data = await api('/api/manual/apply', {
          positions: manualValues,
          real: document.getElementById('real').checked,
          rviz: document.getElementById('rviz').checked
        });
        appendLog(data.message || 'manual applied');
      } catch (err) {
        appendLog(`manual apply failed: ${err.message}`);
      }
    }
    function zeroManual() {
      jointNames.forEach((name, index) => manualValues[index] = name === 'gripper' ? 0 : 0);
      renderManual();
      applyManual();
    }
    renderManual();
    refreshMotions().then(refreshStatus);
    setInterval(refreshStatus, 1000);
  </script>
</body>
</html>
"""


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json_response(handler, status, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


class SyncPlayer:
    def __init__(self, args):
        self.args = args
        self.demo_root = Path(args.demo_root).resolve()
        self.config_dir = self.demo_root / "config"
        self.recordings_dir = self.config_dir / "recordings"
        self.product_actions_path = self.config_dir / "product_actions.json"
        self.action_templates_path = self.config_dir / "action_templates.json"
        self.serial_config = load_json(self.config_dir / "serial_config.json")
        calibration_path = self.demo_root / self.serial_config.get("calibration_file", "config/follower_calibration.json")
        self.calibration = load_json(calibration_path)
        with open(args.joint_map, encoding="utf-8") as fh:
            self.joint_map = yaml.safe_load(fh)

        sys.path.insert(0, str(self.demo_root))
        from app import NativeSTSFollowerDriver, normalize_manual_positions, observation_to_manual_positions

        self.NativeSTSFollowerDriver = NativeSTSFollowerDriver
        self.normalize_manual_positions = normalize_manual_positions
        self.observation_to_manual_positions = observation_to_manual_positions
        self.driver = None
        self.node = None
        self.publisher = None
        self.rclpy = None
        self.rviz_proc = None

        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.worker = None
        self.status = {
            "running": False,
            "recording": "",
            "frame": 0,
            "total": 0,
            "message": "",
            "error": "",
        }

    def _set_status(self, **kwargs):
        with self.lock:
            self.status.update(kwargs)

    def get_status(self):
        with self.lock:
            data = dict(self.status)
            self.status["message"] = ""
            return data

    def _load_templates(self):
        if not self.action_templates_path.is_file():
            return {"templates": {}, "waypoints": {}, "template_delays": {}, "template_display_names": {}}
        payload = load_json(self.action_templates_path)
        payload.setdefault("templates", {})
        payload.setdefault("waypoints", {})
        payload.setdefault("template_delays", {})
        payload.setdefault("template_display_names", {})
        return payload

    def _template_points(self, template_name):
        templates = self._load_templates()
        sequence = templates.get("templates", {}).get(template_name)
        if not sequence:
            raise ValueError("unknown template: %s" % template_name)
        waypoints = templates.get("waypoints", {})
        points = []
        for waypoint_name in sequence:
            point = waypoints.get(waypoint_name)
            if point is None:
                raise ValueError("missing waypoint %s in template %s" % (waypoint_name, template_name))
            points.append(self.normalize_manual_positions(point))
        if len(points) < 2:
            raise ValueError("template has fewer than 2 points: %s" % template_name)
        delay = float(templates.get("template_delays", {}).get(template_name, self.serial_config.get("command_step_delay_sec", 0.25)))
        display_name = templates.get("template_display_names", {}).get(template_name, template_name)
        return points, delay, display_name

    def list_motions(self):
        rows = []
        templates = self._load_templates()
        template_map = templates.get("templates", {})
        template_delays = templates.get("template_delays", {})
        actions = []
        if self.product_actions_path.is_file():
            try:
                actions = load_json(self.product_actions_path).get("actions", [])
            except Exception:
                actions = []
        for action in sorted(actions, key=lambda row: str(row.get("name", ""))):
            if action.get("status") != "released":
                continue
            template_name = str(action.get("execution_template") or action.get("source_template") or "").strip()
            if not template_name or template_name not in template_map:
                continue
            rows.append({
                "kind": "released",
                "id": "action:%s" % action.get("id", ""),
                "display_name": action.get("name") or action.get("id") or template_name,
                "samples": len(template_map.get(template_name, [])),
                "delay": float(template_delays.get(template_name, action.get("optimization", {}).get("frame_delay_sec", 0.08))),
                "template": template_name,
            })
        if self.recordings_dir.is_dir():
            for path in sorted(self.recordings_dir.glob("*.json")):
                try:
                    payload = load_json(path)
                    points = payload.get("points", [])
                    rows.append({
                        "kind": "recording",
                        "id": "recording:%s" % path.name,
                        "display_name": payload.get("name") or payload.get("template") or path.stem,
                        "samples": len(points),
                        "delay": float(payload.get("delay", 0.25)),
                    })
                except Exception as exc:
                    rows.append({
                        "kind": "recording",
                        "id": "recording:%s" % path.name,
                        "display_name": path.name + " (load error: %s)" % exc,
                        "samples": 0,
                        "delay": 0.25,
                    })
        return rows

    def load_motion_points(self, motion_id):
        motion_id = str(motion_id or "").strip()
        if motion_id.startswith("action:"):
            action_id = motion_id.split(":", 1)[1]
            actions = load_json(self.product_actions_path).get("actions", []) if self.product_actions_path.is_file() else []
            for action in actions:
                if str(action.get("id", "")) == action_id:
                    if action.get("status") != "released":
                        raise ValueError("action is not released: %s" % action_id)
                    template_name = str(action.get("execution_template") or action.get("source_template") or "").strip()
                    points, delay, _display_name = self._template_points(template_name)
                    return action.get("name") or action_id, points, delay
            raise ValueError("released action not found: %s" % action_id)
        if motion_id.startswith("template:"):
            template_name = motion_id.split(":", 1)[1]
            points, delay, display_name = self._template_points(template_name)
            return display_name, points, delay
        if motion_id.startswith("recording:"):
            motion_id = motion_id.split(":", 1)[1]
        return self.load_recording_points(motion_id)

    def load_recording_points(self, recording_id):
        safe_name = os.path.basename(str(recording_id or "").strip())
        if not safe_name:
            raise ValueError("recording is required")
        path = self.recordings_dir / safe_name
        if not path.is_file():
            raise ValueError("recording not found: %s" % safe_name)
        payload = load_json(path)
        points = [self.normalize_manual_positions(point) for point in payload.get("points", [])]
        if len(points) < 2:
            raise ValueError("recording has fewer than 2 points")
        return safe_name, points, float(payload.get("delay", 0.25))

    def ensure_ros(self):
        if self.publisher is not None:
            return
        import rclpy
        from rclpy.node import Node
        from sensor_msgs.msg import JointState

        if not rclpy.ok():
            rclpy.init(args=None)
        self.rclpy = rclpy
        self.JointState = JointState
        self.node = Node("so101_simple_sync_player")
        self.publisher = self.node.create_publisher(JointState, "/joint_states", 10)

    def publish_rviz(self, point):
        self.ensure_ros()
        names, positions, _clamped = apply_urdf_map(point, self.joint_map, clamp_enabled=True)
        msg = self.JointState()
        msg.header.stamp = self.node.get_clock().now().to_msg()
        msg.name = names
        msg.position = positions
        self.publisher.publish(msg)
        self.rclpy.spin_once(self.node, timeout_sec=0.0)

    def ensure_driver(self):
        if self.driver is None:
            self.driver = self.NativeSTSFollowerDriver(
                self.serial_config,
                self.calibration,
                self.serial_config.get("mapping", {}),
            )
        return self.driver

    def send_real(self, point):
        self.ensure_driver().send_positions(point)

    def start(self, options):
        with self.lock:
            if self.status.get("running"):
                raise RuntimeError("player is already running")
        recording, points, file_delay = self.load_motion_points(options.get("motion") or options.get("recording"))
        delay = max(0.03, min(3.0, float(options.get("delay") or file_delay)))
        repeat = max(1, min(999, int(options.get("repeat") or 1)))
        loop = bool(options.get("loop"))
        real = bool(options.get("real", True))
        rviz = bool(options.get("rviz", True))
        if not real and not rviz:
            raise ValueError("enable at least one target: real or rviz")

        self.stop_event.clear()
        self._set_status(
            running=True,
            recording=recording,
            frame=0,
            total=len(points),
            message="started %s" % recording,
            error="",
        )
        self.worker = threading.Thread(
            target=self._run,
            args=(recording, points, delay, repeat, loop, real, rviz),
            daemon=True,
        )
        self.worker.start()

    def manual_apply(self, positions, real=True, rviz=True):
        if self.status.get("running"):
            raise RuntimeError("stop playback before manual debug")
        point = self.normalize_manual_positions(positions)
        if rviz:
            self.publish_rviz(point)
        if real:
            self.send_real(point)
        self._set_status(recording="manual", frame=1, total=1, message="manual point applied", error="")
        return point

    def read_current_positions(self):
        if self.status.get("running"):
            raise RuntimeError("stop playback before reading current position")
        driver = self.ensure_driver()
        if not driver.connected:
            driver.connect()
        observation = driver.get_observation()
        positions = self.observation_to_manual_positions(observation, self.calibration, self.serial_config.get("mapping", {}))
        if positions is None:
            raise RuntimeError("failed to convert current follower observation")
        point = self.normalize_manual_positions(positions)
        self.publish_rviz(point)
        self._set_status(recording="manual-current", frame=1, total=1, message="current real position published to RViz", error="")
        return point

    def _run(self, recording, points, delay, repeat, loop, real, rviz):
        try:
            cycle = 0
            while not self.stop_event.is_set() and (loop or cycle < repeat):
                cycle += 1
                for idx, point in enumerate(points, start=1):
                    if self.stop_event.is_set():
                        break
                    if rviz:
                        self.publish_rviz(point)
                    if real:
                        self.send_real(point)
                    self._set_status(frame=idx, total=len(points), message="")
                    time.sleep(delay)
            self._set_status(running=False, message="playback stopped" if self.stop_event.is_set() else "playback complete")
        except Exception as exc:
            self._set_status(running=False, error="%s: %s" % (type(exc).__name__, exc))
            traceback.print_exc()
        finally:
            if self.stop_event.is_set() and self.driver is not None:
                try:
                    self.driver.release_torque()
                except Exception:
                    pass

    def stop(self):
        self.stop_event.set()
        if self.worker is not None:
            self.worker.join(timeout=2.0)
        if self.driver is not None:
            try:
                self.driver.release_torque()
            except Exception:
                pass
        self._set_status(running=False, message="stop requested")

    def open_rviz(self):
        if self.rviz_proc is not None and self.rviz_proc.poll() is None:
            return "RViz already running from simple player"
        cmd = (
            "source /opt/ros/humble/setup.bash && "
            "source '%s' && "
            "ros2 launch '%s' use_rviz:=true"
        ) % (str(Path(__file__).resolve().parents[1] / "workspaces/so101_ws/install/setup.bash"), str(DEFAULT_RVIZ_LAUNCH))
        self.rviz_proc = subprocess.Popen(
            ["bash", "-lc", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return "RViz launch requested"


class Handler(BaseHTTPRequestHandler):
    player = None

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == "/":
                data = HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if path == "/api/status":
                write_json_response(self, 200, {"ok": True, **self.player.get_status()})
                return
            if path == "/api/motions":
                write_json_response(self, 200, {"ok": True, "motions": self.player.list_motions()})
                return
            if path == "/api/recordings":
                write_json_response(self, 200, {"ok": True, "recordings": self.player.list_motions()})
                return
            write_json_response(self, 404, {"ok": False, "error": "not found"})
        except Exception as exc:
            write_json_response(self, 500, {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(body or "{}")
            if path == "/api/start":
                self.player.start(payload)
                write_json_response(self, 200, {"ok": True, "message": "playback started"})
                return
            if path == "/api/stop":
                self.player.stop()
                write_json_response(self, 200, {"ok": True, "message": "stop requested"})
                return
            if path == "/api/open-rviz":
                message = self.player.open_rviz()
                write_json_response(self, 200, {"ok": True, "message": message})
                return
            if path == "/api/manual/apply":
                point = self.player.manual_apply(
                    payload.get("positions", []),
                    real=bool(payload.get("real", True)),
                    rviz=bool(payload.get("rviz", True)),
                )
                write_json_response(self, 200, {"ok": True, "message": "manual point applied", "positions": point})
                return
            if path == "/api/manual/read-current":
                point = self.player.read_current_positions()
                write_json_response(self, 200, {"ok": True, "positions": point})
                return
            write_json_response(self, 404, {"ok": False, "error": "not found"})
        except Exception as exc:
            write_json_response(self, 500, {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)})

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))


def main():
    parser = argparse.ArgumentParser(description="Simple SO101 real/RViz synchronized playback frontend.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--demo-root", default=str(DEFAULT_DEMO_ROOT))
    parser.add_argument("--joint-map", default=str(DEFAULT_JOINT_MAP))
    args = parser.parse_args()

    Handler.player = SyncPlayer(args)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("SO101 simple sync player: http://%s:%d" % (args.host, args.port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        Handler.player.stop()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
