#!/usr/bin/env python
"""Windows 7 compatible SO101 follower demo server.

This file intentionally avoids ROS2, Java, Node.js, and non-standard web
frameworks. Dry-run mode uses only the Python standard library.
"""

from __future__ import print_function

import json
import math
import os
import platform
import sys
import threading
import time
import traceback

try:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from socketserver import ThreadingMixIn
except ImportError:  # pragma: no cover - Python 2 fallback
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from SocketServer import ThreadingMixIn

try:
    from urllib.parse import unquote
except ImportError:  # pragma: no cover - Python 3 fallback
    from urllib import unquote

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(ROOT, "config")
STATIC_DIR = os.path.join(ROOT, "static")
LOG_DIR = os.path.join(ROOT, "logs")
JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
STS_MODEL_NUMBER = 777
STS_MAX_RESOLUTION = 4095
STS_ADDR_MODEL_NUMBER = 3
STS_ADDR_TORQUE_ENABLE = 40
STS_ADDR_GOAL_POSITION = 42
STS_ADDR_PRESENT_POSITION = 56
STS_INST_PING = 1
STS_INST_READ = 2
STS_INST_WRITE = 3
STS_INST_SYNC_WRITE = 131


def now_ms():
    return int(time.time() * 1000)


def read_json(path):
    with open(path, "r") as f:
        return json.load(f)


def write_jsonl(path, payload):
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, "a") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def clamp(value, low, high):
    return max(low, min(high, value))


def load_config():
    serial_config = read_json(os.path.join(CONFIG_DIR, "serial_config.json"))
    templates = read_json(os.path.join(CONFIG_DIR, "action_templates.json"))
    calibration_path = os.path.join(ROOT, serial_config.get("calibration_file", "config/follower_calibration.json"))
    calibration = read_json(calibration_path)
    return serial_config, templates, calibration


def ros_positions_to_lerobot_action(positions, mapping):
    scales = mapping.get("position_scales", {})
    offsets = mapping.get("position_offsets_deg", {})
    gripper_scale = float(mapping.get("gripper_scale", 100.0))
    gripper_offset = float(mapping.get("gripper_offset", 0.0))
    action = {}
    for index, name in enumerate(JOINT_NAMES):
        value = float(positions[index])
        scale = float(scales.get(name, 1.0))
        if name == "gripper":
            mapped = value * gripper_scale * scale + gripper_offset
            action[name + ".pos"] = clamp(mapped, 0.0, 100.0)
        else:
            mapped = math.degrees(value) * scale + float(offsets.get(name, 0.0))
            action[name + ".pos"] = mapped
    return action


def lerobot_action_to_raw_goal(action, calibration):
    raw = {}
    for name in JOINT_NAMES:
        value = float(action[name + ".pos"])
        cal = calibration[name]
        min_value = int(cal["range_min"])
        max_value = int(cal["range_max"])
        if name == "gripper":
            bounded = clamp(value, 0.0, 100.0)
            raw_value = int((bounded / 100.0) * (max_value - min_value) + min_value)
        else:
            mid = (min_value + max_value) / 2.0
            raw_value = int((value * STS_MAX_RESOLUTION / 360.0) + mid)
        raw[name] = int(clamp(raw_value, min_value, max_value))
    return raw


def decode_signed_15bit(value):
    # Feetech STS uses bit 15 as sign for signed position-like values.
    if value & 0x8000:
        return -(value & 0x7FFF)
    return value


def encode_signed_15bit(value):
    value = int(value)
    if value < 0:
        return (abs(value) & 0x7FFF) | 0x8000
    return value & 0x7FFF


class NativeWin32Serial(object):
    """Tiny Windows COM wrapper implemented with ctypes only."""

    def __init__(self, port, baudrate, read_timeout_ms, write_timeout_ms):
        self.port = port
        self.baudrate = int(baudrate)
        self.read_timeout_ms = int(read_timeout_ms)
        self.write_timeout_ms = int(write_timeout_ms)
        self.handle = None

    def open(self):
        if os.name != "nt":
            raise RuntimeError("native_win32 backend only works on Windows")
        import ctypes
        from ctypes import wintypes

        self.ctypes = ctypes
        self.wintypes = wintypes
        self.kernel32 = ctypes.windll.kernel32
        path = self.port
        if not path.startswith("\\\\.\\"):
            path = "\\\\.\\" + path
        handle = self.kernel32.CreateFileA(
            path.encode("ascii"),
            0xC0000000,  # GENERIC_READ | GENERIC_WRITE
            0,
            None,
            3,  # OPEN_EXISTING
            0,
            None,
        )
        if handle == -1 or handle == 0xFFFFFFFF:
            raise RuntimeError("failed to open serial port %s" % self.port)
        self.handle = handle
        self._setup_comm()

    def _setup_comm(self):
        ctypes = self.ctypes

        class DCB(ctypes.Structure):
            _fields_ = [
                ("DCBlength", ctypes.c_uint32),
                ("BaudRate", ctypes.c_uint32),
                ("flags", ctypes.c_uint32),
                ("wReserved", ctypes.c_uint16),
                ("XonLim", ctypes.c_uint16),
                ("XoffLim", ctypes.c_uint16),
                ("ByteSize", ctypes.c_ubyte),
                ("Parity", ctypes.c_ubyte),
                ("StopBits", ctypes.c_ubyte),
                ("XonChar", ctypes.c_char),
                ("XoffChar", ctypes.c_char),
                ("ErrorChar", ctypes.c_char),
                ("EofChar", ctypes.c_char),
                ("EvtChar", ctypes.c_char),
                ("wReserved1", ctypes.c_uint16),
            ]

        class COMMTIMEOUTS(ctypes.Structure):
            _fields_ = [
                ("ReadIntervalTimeout", ctypes.c_uint32),
                ("ReadTotalTimeoutMultiplier", ctypes.c_uint32),
                ("ReadTotalTimeoutConstant", ctypes.c_uint32),
                ("WriteTotalTimeoutMultiplier", ctypes.c_uint32),
                ("WriteTotalTimeoutConstant", ctypes.c_uint32),
            ]

        dcb = DCB()
        dcb.DCBlength = ctypes.sizeof(DCB)
        if not self.kernel32.GetCommState(self.handle, ctypes.byref(dcb)):
            raise RuntimeError("GetCommState failed")
        dcb.BaudRate = self.baudrate
        dcb.ByteSize = 8
        dcb.Parity = 0
        dcb.StopBits = 0
        # fBinary=1, DTR/RTS enabled enough for common USB serial adapters.
        dcb.flags = 0x00000001 | 0x00000010 | 0x00001000
        if not self.kernel32.SetCommState(self.handle, ctypes.byref(dcb)):
            raise RuntimeError("SetCommState failed")
        timeouts = COMMTIMEOUTS()
        timeouts.ReadIntervalTimeout = self.read_timeout_ms
        timeouts.ReadTotalTimeoutMultiplier = 0
        timeouts.ReadTotalTimeoutConstant = self.read_timeout_ms
        timeouts.WriteTotalTimeoutMultiplier = 0
        timeouts.WriteTotalTimeoutConstant = self.write_timeout_ms
        if not self.kernel32.SetCommTimeouts(self.handle, ctypes.byref(timeouts)):
            raise RuntimeError("SetCommTimeouts failed")
        self.kernel32.PurgeComm(self.handle, 0x0008 | 0x0004)  # RXCLEAR | TXCLEAR

    def close(self):
        if self.handle is not None:
            self.kernel32.CloseHandle(self.handle)
            self.handle = None

    def write(self, data):
        ctypes = self.ctypes
        raw = bytes(bytearray(data))
        written = ctypes.c_uint32(0)
        ok = self.kernel32.WriteFile(self.handle, raw, len(raw), ctypes.byref(written), None)
        if not ok or int(written.value) != len(raw):
            raise RuntimeError("serial write failed")

    def read(self, size):
        ctypes = self.ctypes
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_uint32(0)
        ok = self.kernel32.ReadFile(self.handle, buf, size, ctypes.byref(read), None)
        if not ok:
            raise RuntimeError("serial read failed")
        return bytearray(buf.raw[: int(read.value)])


class NativeFeetechSTSBus(object):
    """Minimal Feetech STS protocol 0 bus for SO101 demo motion."""

    def __init__(self, serial_config):
        self.serial_config = serial_config
        self.serial = None

    def connect(self):
        self.serial = NativeWin32Serial(
            self.serial_config.get("port", "COM6"),
            self.serial_config.get("baudrate", 1000000),
            self.serial_config.get("read_timeout_ms", 80),
            self.serial_config.get("write_timeout_ms", 80),
        )
        self.serial.open()

    def disconnect(self):
        if self.serial is not None:
            self.serial.close()
        self.serial = None

    def _checksum(self, packet_tail):
        return (~(sum(packet_tail) & 0xFF)) & 0xFF

    def _packet(self, motor_id, instruction, params):
        tail = [int(motor_id) & 0xFF, (len(params) + 2) & 0xFF, instruction & 0xFF] + [int(v) & 0xFF for v in params]
        return [0xFF, 0xFF] + tail + [self._checksum(tail)]

    def _txrx(self, motor_id, instruction, params, expected_min=6):
        packet = self._packet(motor_id, instruction, params)
        self.serial.write(packet)
        deadline = time.time() + (float(self.serial_config.get("read_timeout_ms", 80)) / 1000.0)
        data = bytearray()
        while time.time() < deadline and len(data) < expected_min:
            chunk = self.serial.read(64)
            if chunk:
                data.extend(chunk)
            else:
                time.sleep(0.002)
        if len(data) < expected_min:
            raise RuntimeError("timeout waiting for motor %s response" % motor_id)
        return list(data)

    def ping(self, motor_id):
        response = self._txrx(motor_id, STS_INST_PING, [], expected_min=6)
        return response

    def read_word(self, motor_id, address):
        response = self._txrx(motor_id, STS_INST_READ, [address, 2], expected_min=8)
        # Expected: FF FF ID LEN ERR LO HI CHECKSUM
        if len(response) < 8 or response[0] != 0xFF or response[1] != 0xFF:
            raise RuntimeError("invalid read response from motor %s: %r" % (motor_id, response))
        return int(response[5]) | (int(response[6]) << 8)

    def write_byte(self, motor_id, address, value):
        self._txrx(motor_id, STS_INST_WRITE, [address, int(value) & 0xFF], expected_min=6)

    def sync_write_word(self, address, ids_values):
        params = [address, 2]
        for motor_id, value in sorted(ids_values.items()):
            encoded = encode_signed_15bit(value)
            params.extend([int(motor_id) & 0xFF, encoded & 0xFF, (encoded >> 8) & 0xFF])
        packet = self._packet(0xFE, STS_INST_SYNC_WRITE, params)
        self.serial.write(packet)

    def scan_expected(self, ids):
        found = {}
        for motor_id in ids:
            try:
                model = self.read_word(motor_id, STS_ADDR_MODEL_NUMBER)
                found[int(motor_id)] = int(model)
            except Exception:
                pass
        return found

    def read_present_positions(self, ids):
        result = {}
        for motor_id in ids:
            raw = self.read_word(motor_id, STS_ADDR_PRESENT_POSITION)
            result[int(motor_id)] = decode_signed_15bit(raw)
        return result


class FollowerDriver(object):
    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        pass

    def send_positions(self, positions):
        raise NotImplementedError

    def get_observation(self):
        return {}


class DryRunFollowerDriver(FollowerDriver):
    def __init__(self, mapping):
        self.mapping = mapping
        self.connected = False
        self.last_positions = [0.0, -0.2, 0.4, -0.2, 0.0, 0.2]
        self.last_action = ros_positions_to_lerobot_action(self.last_positions, mapping)

    def connect(self):
        self.connected = True
        return {"ok": True, "dry_run": True, "message": "dry-run connected"}

    def disconnect(self):
        self.connected = False

    def send_positions(self, positions):
        if not self.connected:
            self.connect()
        self.last_positions = [float(v) for v in positions]
        self.last_action = ros_positions_to_lerobot_action(self.last_positions, self.mapping)
        return dict(self.last_action)

    def get_observation(self):
        return {
            "positions": list(self.last_positions),
            "last_action": dict(self.last_action),
        }


class LeRobotFollowerDriver(FollowerDriver):
    def __init__(self, serial_config, calibration, mapping):
        self.serial_config = serial_config
        self.calibration = calibration
        self.mapping = mapping
        self.robot = None
        self.connected = False

    def connect(self):
        # Imported lazily so dry-run works on machines without LeRobot.
        from lerobot.robots.so_follower.config_so_follower import SO101FollowerConfig
        from lerobot.robots.so_follower.so_follower import SO101Follower

        config = SO101FollowerConfig(
            port=self.serial_config.get("port", "COM6"),
            id=self.serial_config.get("robot_id", "win7_follower"),
            max_relative_target=float(self.serial_config.get("max_relative_target_deg", 2.0)),
            disable_torque_on_disconnect=False,
        )
        robot = SO101Follower(config)
        # Use existing motor-side calibration; avoid interactive calibration on demo machine.
        robot.connect(calibrate=False)
        self.robot = robot
        self.connected = True
        return {"ok": True, "dry_run": False, "message": "LeRobot follower connected"}

    def disconnect(self):
        if self.robot is not None:
            self.robot.disconnect()
        self.robot = None
        self.connected = False

    def send_positions(self, positions):
        if not self.connected or self.robot is None:
            self.connect()
        action = ros_positions_to_lerobot_action(positions, self.mapping)
        sent = self.robot.send_action(action)
        return {str(k): float(v) for k, v in sent.items()}

    def get_observation(self):
        if not self.connected or self.robot is None:
            return {}
        obs = self.robot.get_observation()
        return {str(k): float(v) for k, v in obs.items() if str(k).endswith(".pos")}


class NativeWin32FollowerDriver(FollowerDriver):
    """No-third-party Windows serial driver for the SO101 follower demo."""

    def __init__(self, serial_config, calibration, mapping):
        self.serial_config = serial_config
        self.calibration = calibration
        self.mapping = mapping
        self.bus = NativeFeetechSTSBus(serial_config)
        self.connected = False
        self.last_action = {}
        self.last_raw_goal = {}

    def _ids(self):
        return [int(self.calibration[name]["id"]) for name in JOINT_NAMES]

    def connect(self):
        self.bus.connect()
        found = self.bus.scan_expected(self._ids())
        missing = [motor_id for motor_id in self._ids() if motor_id not in found]
        wrong = dict((motor_id, model) for motor_id, model in found.items() if int(model) != STS_MODEL_NUMBER)
        if missing or wrong:
            self.bus.disconnect()
            raise RuntimeError("motor check failed missing=%s wrong=%s found=%s" % (missing, wrong, found))
        self.connected = True
        return {"ok": True, "dry_run": False, "backend": "native_win32", "found": found}

    def disconnect(self):
        self.bus.disconnect()
        self.connected = False

    def send_positions(self, positions):
        if not self.connected:
            self.connect()
        action = ros_positions_to_lerobot_action(positions, self.mapping)
        raw_goal_by_name = lerobot_action_to_raw_goal(action, self.calibration)
        raw_goal_by_id = dict((int(self.calibration[name]["id"]), raw_goal_by_name[name]) for name in JOINT_NAMES)
        self.bus.sync_write_word(STS_ADDR_GOAL_POSITION, raw_goal_by_id)
        self.last_action = dict(action)
        self.last_raw_goal = dict(raw_goal_by_name)
        result = dict(action)
        for name, raw_value in raw_goal_by_name.items():
            result[name + ".raw_goal"] = int(raw_value)
        return result

    def get_observation(self):
        if not self.connected:
            return {}
        present_by_id = self.bus.read_present_positions(self._ids())
        present_by_name = {}
        for name in JOINT_NAMES:
            motor_id = int(self.calibration[name]["id"])
            present_by_name[name + ".raw_present"] = int(present_by_id.get(motor_id, 0))
        return {
            "raw_present": present_by_name,
            "last_raw_goal": dict(self.last_raw_goal),
        }


class DemoRuntime(object):
    def __init__(self):
        self.lock = threading.RLock()
        self.serial_config, self.templates, self.calibration = load_config()
        self.log_path = os.path.join(LOG_DIR, "run-%s.jsonl" % time.strftime("%Y%m%d-%H%M%S"))
        self.state = {
            "schema": "so101_win7_runtime_status.v1",
            "started_ms": now_ms(),
            "connected": False,
            "busy": False,
            "dry_run": bool(self.serial_config.get("dry_run", True)),
            "port": self.serial_config.get("port", "COM6"),
            "backend": self.serial_config.get("backend", "lerobot"),
            "last_error": "",
            "last_template": "",
            "last_waypoint": "",
            "last_action": {},
            "last_observation": {},
            "event_count": 0,
            "boundary": "Win7 fallback follower demo; not ROS2, not grasp success, not trainable_real",
        }
        self.driver = self._make_driver()
        self._log("runtime_started", self.state)

    def _make_driver(self):
        mapping = self.serial_config.get("mapping", {})
        if bool(self.serial_config.get("dry_run", True)):
            return DryRunFollowerDriver(mapping)
        backend = str(self.serial_config.get("backend", "lerobot")).lower()
        if backend == "native_win32":
            return NativeWin32FollowerDriver(self.serial_config, self.calibration, mapping)
        if backend == "lerobot":
            return LeRobotFollowerDriver(self.serial_config, self.calibration, mapping)
        raise RuntimeError("unsupported backend: %s" % backend)

    def _log(self, event, payload=None):
        with self.lock:
            self.state["event_count"] = int(self.state.get("event_count", 0)) + 1
            row = {
                "ts_ms": now_ms(),
                "event": event,
                "payload": payload or {},
            }
            write_jsonl(self.log_path, row)

    def status(self):
        with self.lock:
            result = dict(self.state)
            result["templates"] = sorted(self.templates.get("templates", {}).keys())
            result["log_path"] = self.log_path
            return result

    def connect(self):
        with self.lock:
            try:
                result = self.driver.connect()
                self.state["connected"] = True
                self.state["last_error"] = ""
                self._log("connected", result)
                return result
            except Exception as exc:
                self.state["connected"] = False
                self.state["last_error"] = "%s: %s" % (type(exc).__name__, exc)
                self._log("connect_failed", {"error": self.state["last_error"], "trace": traceback.format_exc()})
                raise

    def disconnect(self):
        with self.lock:
            self.driver.disconnect()
            self.state["connected"] = False
            self._log("disconnected", {})
            return {"ok": True}

    def stop(self):
        # For this lightweight demo, stop means clear busy state. Hardware e-stop remains physical/procedural.
        with self.lock:
            self.state["busy"] = False
            self._log("stop_requested", {})
            return {"ok": True, "message": "busy flag cleared; use physical power/stop for hardware emergency"}

    def execute_template(self, template_name):
        with self.lock:
            if self.state.get("busy"):
                raise RuntimeError("runtime is busy")
            sequence = self.templates.get("templates", {}).get(template_name)
            if not sequence:
                raise ValueError("unknown template: %s" % template_name)
            self.state["busy"] = True
            self.state["last_template"] = template_name
            self.state["last_error"] = ""

        try:
            self.connect()
            results = []
            delay = float(self.serial_config.get("command_step_delay_sec", 0.8))
            waypoints = self.templates.get("waypoints", {})
            for waypoint_name in sequence:
                positions = waypoints.get(waypoint_name)
                if positions is None:
                    raise ValueError("missing waypoint: %s" % waypoint_name)
                sent = self.driver.send_positions(positions)
                observation = self.driver.get_observation()
                with self.lock:
                    self.state["last_waypoint"] = waypoint_name
                    self.state["last_action"] = sent
                    self.state["last_observation"] = observation
                    self._log(
                        "waypoint_sent",
                        {
                            "template": template_name,
                            "waypoint": waypoint_name,
                            "positions": positions,
                            "sent": sent,
                            "observation": observation,
                        },
                    )
                results.append({"waypoint": waypoint_name, "sent": sent})
                time.sleep(delay)
            return {"ok": True, "template": template_name, "steps": results}
        except Exception as exc:
            with self.lock:
                self.state["last_error"] = "%s: %s" % (type(exc).__name__, exc)
                self._log("template_failed", {"template": template_name, "error": self.state["last_error"], "trace": traceback.format_exc()})
            raise
        finally:
            with self.lock:
                self.state["busy"] = False


RUNTIME = DemoRuntime()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    server_version = "SO101Win7Demo/0.1"

    def _send_json(self, payload, status=200):
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path, content_type):
        with open(path, "rb") as f:
            raw = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def do_GET(self):
        path = unquote(self.path.split("?", 1)[0])
        try:
            if path == "/api/status":
                self._send_json(RUNTIME.status())
            elif path == "/api/templates":
                self._send_json(RUNTIME.templates)
            elif path in ("", "/"):
                self._send_file(os.path.join(STATIC_DIR, "index.html"), "text/html; charset=utf-8")
            elif path == "/app.js":
                self._send_file(os.path.join(STATIC_DIR, "app.js"), "application/javascript; charset=utf-8")
            elif path == "/style.css":
                self._send_file(os.path.join(STATIC_DIR, "style.css"), "text/css; charset=utf-8")
            else:
                self._send_json({"ok": False, "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json({"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}, status=500)

    def do_POST(self):
        path = unquote(self.path.split("?", 1)[0])
        try:
            body = self._read_body()
            if path == "/api/connect":
                self._send_json(RUNTIME.connect())
            elif path == "/api/disconnect":
                self._send_json(RUNTIME.disconnect())
            elif path == "/api/stop":
                self._send_json(RUNTIME.stop())
            elif path == "/api/action":
                template = str(body.get("template", "")).strip()
                self._send_json(RUNTIME.execute_template(template))
            else:
                self._send_json({"ok": False, "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json({"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}, status=500)

    def log_message(self, fmt, *args):
        sys.stdout.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))


def main():
    host = RUNTIME.serial_config.get("http_host", "127.0.0.1")
    port = int(RUNTIME.serial_config.get("http_port", 8765))
    print("SO101 Win7 follower demo")
    print("URL: http://%s:%d" % (host, port))
    print("dry_run=%s port=%s log=%s" % (RUNTIME.state["dry_run"], RUNTIME.state["port"], RUNTIME.log_path))
    server = ThreadedHTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        try:
            RUNTIME.disconnect()
        except Exception:
            pass
        server.server_close()


if __name__ == "__main__":
    main()
