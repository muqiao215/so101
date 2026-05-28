#!/usr/bin/env python
"""Windows 7 compatible SO101 follower demo server.

This file intentionally avoids ROS2, Java, Node.js, and non-standard web
frameworks. The default lightweight runtime uses only the Python standard
library.
"""

from __future__ import print_function

import json
import math
import os
import platform
import re
import select
import subprocess
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
RECORDINGS_DIR = os.path.join(CONFIG_DIR, "recordings")
RECORDINGS_TRASH_DIR = os.path.join(RECORDINGS_DIR, ".trash")
TELEOP_CALIBRATION_PATH = os.path.join(CONFIG_DIR, "teleop_calibration.json")
STATIC_DIR = os.path.join(ROOT, "static")
LOG_DIR = os.path.join(ROOT, "logs")
JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
MANUAL_LIMITS = {
    "shoulder_pan": (-math.pi, math.pi),
    "shoulder_lift": (-math.pi, math.pi),
    "elbow_flex": (-math.pi, math.pi),
    "wrist_flex": (-math.pi, math.pi),
    "wrist_roll": (-math.pi, math.pi),
    "gripper": (0.0, 1.0),
}
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


def write_json(path, payload):
    with open(path, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=False)


def write_jsonl(path, payload):
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, "a") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def clamp(value, low, high):
    return max(low, min(high, value))


def parse_int_list(value, fallback):
    if value is None:
        return [int(v) for v in fallback]
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",")]
    else:
        items = list(value)
    result = []
    for item in items:
        if item == "":
            continue
        result.append(int(item))
    if not result:
        return [int(v) for v in fallback]
    return result


def parse_float_list(value, count, default_value):
    if value is None:
        return [float(default_value)] * count
    if isinstance(value, str):
        raw_items = [item.strip() for item in value.split(",")]
    else:
        raw_items = list(value)
    result = []
    for item in raw_items:
        if item == "":
            continue
        result.append(float(item))
    while len(result) < count:
        result.append(float(default_value))
    return result[:count]


def load_teleop_calibration():
    if not os.path.exists(TELEOP_CALIBRATION_PATH):
        return {"schema": "so101_teleop_calibration.v1", "calibrated": False}
    payload = read_json(TELEOP_CALIBRATION_PATH)
    payload.setdefault("schema", "so101_teleop_calibration.v1")
    payload.setdefault("calibrated", False)
    return payload


def normalize_raw_by_id(payload):
    result = {}
    for key, value in (payload or {}).items():
        result[int(key)] = int(value)
    return result


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


def normalize_manual_positions(positions):
    if not isinstance(positions, list) or len(positions) != len(JOINT_NAMES):
        raise ValueError("positions must be a 6-item list")
    normalized = []
    for index, name in enumerate(JOINT_NAMES):
        try:
            value = float(positions[index])
        except Exception:
            raise ValueError("invalid position for %s" % name)
        low, high = MANUAL_LIMITS[name]
        normalized.append(clamp(value, low, high))
    return normalized


def raw_present_to_manual_positions(observation, calibration, mapping):
    present = observation.get("present_positions") or {}
    positions = []
    scales = mapping.get("position_scales", {})
    offsets = mapping.get("position_offsets_deg", {})
    for name in JOINT_NAMES:
        cal = calibration[name]
        raw = present.get(str(cal["id"]))
        if raw is None:
            raw = present.get(int(cal["id"]))
        if raw is None:
            return None
        raw = float(raw)
        scale = float(scales.get(name, 1.0)) or 1.0
        if name == "gripper":
            pct = (raw - float(cal["range_min"])) / (float(cal["range_max"]) - float(cal["range_min"])) * 100.0
            gripper_scale = float(mapping.get("gripper_scale", 100.0)) or 100.0
            gripper_offset = float(mapping.get("gripper_offset", 0.0))
            positions.append(clamp((pct - gripper_offset) / (gripper_scale * scale), 0.0, 1.0))
        else:
            action_deg = (raw - (float(cal["range_min"]) + float(cal["range_max"])) / 2.0) * 360.0 / STS_MAX_RESOLUTION
            control_deg = (action_deg - float(offsets.get(name, 0.0))) / scale
            positions.append(math.radians(control_deg))
    return positions


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


class NativePosixSerial(object):
    """Tiny Linux/macOS serial wrapper implemented with Python stdlib only."""

    BAUD_BY_VALUE = {
        9600: "B9600",
        19200: "B19200",
        38400: "B38400",
        57600: "B57600",
        115200: "B115200",
        230400: "B230400",
        460800: "B460800",
        500000: "B500000",
        576000: "B576000",
        921600: "B921600",
        1000000: "B1000000",
    }

    def __init__(self, port, baudrate, read_timeout_ms, write_timeout_ms):
        self.port = port
        self.baudrate = int(baudrate)
        self.read_timeout_ms = int(read_timeout_ms)
        self.write_timeout_ms = int(write_timeout_ms)
        self.fd = None

    def open(self):
        if os.name == "nt":
            raise RuntimeError("native_posix backend only works on Linux/macOS")
        import termios

        self.termios = termios
        flags = os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK
        self.fd = os.open(self.port, flags)
        attrs = termios.tcgetattr(self.fd)
        baud_name = self.BAUD_BY_VALUE.get(self.baudrate)
        if not baud_name or not hasattr(termios, baud_name):
            os.close(self.fd)
            self.fd = None
            raise RuntimeError("unsupported POSIX baudrate: %s" % self.baudrate)
        baud = getattr(termios, baud_name)

        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CLOCAL | termios.CREAD | termios.CS8
        attrs[3] = 0
        attrs[4] = baud
        attrs[5] = baud
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = max(1, int(self.read_timeout_ms / 100))
        termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        termios.tcflush(self.fd, termios.TCIOFLUSH)

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def write(self, data):
        raw = bytes(bytearray(data))
        deadline = time.time() + (self.write_timeout_ms / 1000.0)
        view = memoryview(raw)
        total = 0
        while total < len(raw):
            remaining = deadline - time.time()
            if remaining <= 0:
                raise RuntimeError("serial write timeout")
            _, writable, _ = select.select([], [self.fd], [], remaining)
            if not writable:
                continue
            total += os.write(self.fd, view[total:])

    def read(self, size):
        if size <= 0:
            return bytearray()
        timeout = self.read_timeout_ms / 1000.0
        readable, _, _ = select.select([self.fd], [], [], timeout)
        if not readable:
            return bytearray()
        return bytearray(os.read(self.fd, size))


class NativeFeetechSTSBus(object):
    """Minimal Feetech STS protocol 0 bus for SO101 demo motion."""

    def __init__(self, serial_config):
        self.serial_config = serial_config
        self.serial = None

    def connect(self):
        backend = str(self.serial_config.get("backend", "")).lower()
        if backend in ("native_posix", "native_linux"):
            serial_class = NativePosixSerial
            default_port = "/dev/ttyACM0"
        else:
            serial_class = NativeWin32Serial
            default_port = "COM6"
        self.serial = serial_class(
            self.serial_config.get("port", default_port),
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
        retries = int(self.serial_config.get("scan_retries", 5))
        retry_delay = float(self.serial_config.get("scan_retry_delay_sec", 0.25))
        scan_window_sec = float(self.serial_config.get("scan_window_sec", 0))
        deadline = time.time() + scan_window_sec if scan_window_sec > 0 else None
        expected = [int(motor_id) for motor_id in ids]
        attempt = 0
        while True:
            attempt += 1
            for motor_id in expected:
                if motor_id in found:
                    continue
                try:
                    model = self.read_word(motor_id, STS_ADDR_MODEL_NUMBER)
                    found[int(motor_id)] = int(model)
                except Exception:
                    pass
            if len(found) >= len(expected):
                break
            if deadline is not None:
                if time.time() >= deadline:
                    break
            elif attempt >= max(1, retries):
                break
            time.sleep(retry_delay)
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


class RawTeleopSession(object):
    """Reads a leader STS bus and sends relative raw goals to the follower bus."""

    def __init__(self, serial_config, calibration):
        self.serial_config = serial_config
        self.calibration = calibration
        self.teleop_calibration = load_teleop_calibration()
        self.leader_bus = None
        self.follower_driver = None
        self.thread = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.lock = threading.RLock()
        self.running = False
        self.started_ms = 0
        self.last_error = ""
        self.last_leader_raw = {}
        self.last_follower_raw = {}
        self.last_goal_raw = {}
        self.last_step_ms = 0
        self.frames = 0

    def _joint_count(self):
        return len(JOINT_NAMES)

    def _follower_ids(self):
        return [int(self.calibration[name]["id"]) for name in JOINT_NAMES]

    def _leader_ids(self):
        return parse_int_list(self.serial_config.get("leader_ids"), self._follower_ids())

    def _leader_config(self):
        cfg = dict(self.serial_config)
        cfg["port"] = self.serial_config.get("leader_port", "/dev/ttyACM1")
        cfg["backend"] = self.serial_config.get("leader_backend", self.serial_config.get("backend", "native_posix"))
        return cfg

    def is_active(self):
        with self.lock:
            return bool(self.running)

    def status(self):
        with self.lock:
            return {
                "running": bool(self.running),
                "paused": bool(self.pause_event.is_set()),
                "leader_port": self.serial_config.get("leader_port", "/dev/ttyACM1"),
                "follower_port": self.serial_config.get("port", "/dev/ttyACM0"),
                "leader_ids": self._leader_ids(),
                "follower_ids": self._follower_ids(),
                "started_ms": self.started_ms,
                "frames": self.frames,
                "last_error": self.last_error,
                "last_leader_raw": dict(self.last_leader_raw),
                "last_follower_raw": dict(self.last_follower_raw),
                "last_goal_raw": dict(self.last_goal_raw),
                "last_step_ms": self.last_step_ms,
                "calibration": dict(self.teleop_calibration),
            }

    def read_leader_once(self, leader_ids=None, port=None):
        cfg = self._leader_config()
        if port:
            cfg["port"] = port
        ids = parse_int_list(leader_ids, self._leader_ids())
        bus = NativeFeetechSTSBus(cfg)
        try:
            bus.connect()
            time.sleep(float(cfg.get("serial_settle_sec", 0.2)))
            found = bus.scan_expected(ids)
            missing = [motor_id for motor_id in ids if motor_id not in found]
            present = {}
            for motor_id in ids:
                if motor_id in found:
                    present[int(motor_id)] = bus.read_word(motor_id, STS_ADDR_PRESENT_POSITION)
            return {"ok": not bool(missing), "found": found, "missing": missing, "present_raw": present}
        finally:
            bus.disconnect()

    def set_calibration(self, payload):
        with self.lock:
            self.teleop_calibration = dict(payload)

    def make_calibration(self, follower_driver, options=None):
        options = options or {}
        leader_ids = parse_int_list(options.get("leader_ids", self.serial_config.get("leader_ids")), self._leader_ids())
        follower_ids = self._follower_ids()
        if len(leader_ids) != len(follower_ids):
            raise RuntimeError("主臂 ID 数量必须等于从臂 6 个关节")
        if follower_driver is None or not getattr(follower_driver, "connected", False):
            raise RuntimeError("请先连接从臂")
        if not isinstance(follower_driver, NativeSTSFollowerDriver):
            raise RuntimeError("主从校准需要 native_posix/native_sts 从臂驱动")
        leader_cfg = self._leader_config()
        if options.get("leader_port"):
            leader_cfg["port"] = options.get("leader_port")
        leader_bus = NativeFeetechSTSBus(leader_cfg)
        try:
            leader_bus.connect()
            time.sleep(float(leader_cfg.get("serial_settle_sec", 0.3)))
            found = leader_bus.scan_expected(leader_ids)
            missing = [motor_id for motor_id in leader_ids if motor_id not in found]
            if missing:
                raise RuntimeError("主臂缺少 ID %s，found=%s" % (",".join([str(v) for v in missing]), found))
            leader_raw = leader_bus.read_present_positions(leader_ids)
            follower_raw = follower_driver.bus.read_present_positions(follower_ids)
        finally:
            leader_bus.disconnect()
        by_joint = {}
        for index, name in enumerate(JOINT_NAMES):
            leader_id = int(leader_ids[index])
            follower_id = int(follower_ids[index])
            by_joint[name] = {
                "leader_id": leader_id,
                "follower_id": follower_id,
                "leader_raw": int(leader_raw[leader_id]),
                "follower_raw": int(follower_raw[follower_id]),
                "offset_raw": int(follower_raw[follower_id]) - int(leader_raw[leader_id]),
            }
        payload = {
            "schema": "so101_teleop_calibration.v1",
            "calibrated": True,
            "created_ms": now_ms(),
            "leader_port": leader_cfg.get("port", ""),
            "follower_port": self.serial_config.get("port", ""),
            "leader_ids": [int(v) for v in leader_ids],
            "follower_ids": [int(v) for v in follower_ids],
            "joint_names": list(JOINT_NAMES),
            "leader_raw": dict((str(k), int(v)) for k, v in leader_raw.items()),
            "follower_raw": dict((str(k), int(v)) for k, v in follower_raw.items()),
            "by_joint": by_joint,
            "teleop_gains": parse_float_list(options.get("gains", self.serial_config.get("teleop_gains")), self._joint_count(), 1.0),
            "teleop_invert": parse_float_list(options.get("invert", self.serial_config.get("teleop_invert")), self._joint_count(), 1.0),
            "notes": "Put leader and follower into the same physical pose, then save this file. It is intended to be committed and migrated with the project.",
        }
        write_json(TELEOP_CALIBRATION_PATH, payload)
        self.set_calibration(payload)
        return payload

    def start(self, follower_driver, options=None):
        options = options or {}
        with self.lock:
            if self.running:
                return {"ok": True, "already_running": True, "teleop": self.status()}
            self.stop_event.clear()
            self.pause_event.clear()
            self.last_error = ""
            self.frames = 0
            self.follower_driver = follower_driver
            self.thread = threading.Thread(target=self._run, args=(options,), daemon=True)
            self.running = True
            self.started_ms = now_ms()
            self.thread.start()
            return {"ok": True, "teleop": self.status()}

    def pause(self):
        with self.lock:
            if not self.running:
                return {"ok": False, "error": "当前没有正在运行的主从遥操作"}
            self.pause_event.set()
            return {"ok": True, "teleop": self.status()}

    def resume(self):
        with self.lock:
            if not self.running:
                return {"ok": False, "error": "当前没有正在运行的主从遥操作"}
            self.pause_event.clear()
            return {"ok": True, "teleop": self.status()}

    def stop(self):
        with self.lock:
            self.stop_event.set()
            self.pause_event.clear()
            thread = self.thread
        if thread is not None and thread.is_alive():
            thread.join(2.0)
        with self.lock:
            return {"ok": True, "teleop": self.status()}

    def _run(self, options):
        leader_ids = parse_int_list(options.get("leader_ids", self.serial_config.get("leader_ids")), self._leader_ids())
        follower_ids = self._follower_ids()
        if len(leader_ids) != len(follower_ids):
            self._finish_with_error("主臂 ID 数量必须等于从臂 6 个关节")
            return
        frequency = clamp(float(options.get("frequency_hz", self.serial_config.get("teleop_frequency_hz", 20.0))), 5.0, 50.0)
        interval = 1.0 / frequency
        gains = parse_float_list(options.get("gains", self.serial_config.get("teleop_gains")), self._joint_count(), 1.0)
        invert = parse_float_list(options.get("invert", self.serial_config.get("teleop_invert")), self._joint_count(), 1.0)
        max_delta = parse_float_list(
            options.get("max_delta_raw", self.serial_config.get("teleop_max_delta_raw")),
            self._joint_count(),
            480.0,
        )
        max_step_raw = clamp(float(options.get("max_step_raw", self.serial_config.get("teleop_max_step_raw", 24.0))), 2.0, 200.0)
        leader_cfg = self._leader_config()
        if options.get("leader_port"):
            leader_cfg["port"] = options.get("leader_port")
        self.leader_bus = NativeFeetechSTSBus(leader_cfg)
        try:
            if self.follower_driver is None or not getattr(self.follower_driver, "connected", False):
                raise RuntimeError("请先连接从臂")
            if not isinstance(self.follower_driver, NativeSTSFollowerDriver):
                raise RuntimeError("主从遥操作需要 native_posix/native_sts 从臂驱动")
            self.leader_bus.connect()
            time.sleep(float(leader_cfg.get("serial_settle_sec", 0.3)))
            found = self.leader_bus.scan_expected(leader_ids)
            missing = [motor_id for motor_id in leader_ids if motor_id not in found]
            if missing:
                raise RuntimeError("主臂缺少 ID %s，found=%s" % (",".join([str(v) for v in missing]), found))
            calibration_payload = self.teleop_calibration if bool(options.get("use_calibration", True)) else {}
            calibration_ok = bool(calibration_payload.get("calibrated"))
            if not calibration_ok:
                raise RuntimeError("请先点击“同步当前位置为校准”，保存主从同姿态校准后再开始跟随")
            leader_now_at_start = self.leader_bus.read_present_positions(leader_ids)
            follower_now_at_start = self.follower_driver.bus.read_present_positions(follower_ids)
            cal_leader_ids = parse_int_list(calibration_payload.get("leader_ids"), leader_ids)
            cal_follower_ids = parse_int_list(calibration_payload.get("follower_ids"), follower_ids)
            if cal_leader_ids != leader_ids or cal_follower_ids != follower_ids:
                raise RuntimeError("主从校准 ID 与当前 ID 不一致，请重新同步校准")
            leader_start = normalize_raw_by_id(calibration_payload.get("leader_raw"))
            follower_start = normalize_raw_by_id(calibration_payload.get("follower_raw"))
            if sorted(leader_start.keys()) != sorted([int(v) for v in leader_ids]) or sorted(follower_start.keys()) != sorted([int(v) for v in follower_ids]):
                raise RuntimeError("主从校准文件不完整，请重新同步当前位置为校准")
            self.follower_driver.bus.sync_write_word(STS_ADDR_GOAL_POSITION, follower_now_at_start)
            for motor_id in follower_ids:
                self.follower_driver.bus.write_byte(motor_id, STS_ADDR_TORQUE_ENABLE, 1)
            self.follower_driver.torque_enabled = True
            current_goal = dict(follower_now_at_start)
            with self.lock:
                self.last_leader_raw = dict(leader_now_at_start)
                self.last_follower_raw = dict(follower_now_at_start)
                self.last_goal_raw = dict(current_goal)
            while not self.stop_event.is_set():
                if self.pause_event.is_set():
                    self.stop_event.wait(0.05)
                    continue
                loop_start = time.time()
                leader_now = self.leader_bus.read_present_positions(leader_ids)
                goal = {}
                for index, follower_id in enumerate(follower_ids):
                    leader_id = leader_ids[index]
                    leader_delta = int(leader_now[leader_id]) - int(leader_start[leader_id])
                    bounded_delta = clamp(leader_delta * gains[index] * invert[index], -max_delta[index], max_delta[index])
                    wanted = int(round(int(follower_start[follower_id]) + bounded_delta))
                    previous = int(current_goal[follower_id])
                    step = clamp(wanted - previous, -max_step_raw, max_step_raw)
                    goal[follower_id] = int(round(previous + step))
                self.follower_driver.bus.sync_write_word(STS_ADDR_GOAL_POSITION, goal)
                current_goal = dict(goal)
                try:
                    follower_now = self.follower_driver.bus.read_present_positions(follower_ids)
                except Exception:
                    follower_now = {}
                with self.lock:
                    self.frames += 1
                    self.last_step_ms = now_ms()
                    self.last_leader_raw = dict((int(k), int(v)) for k, v in leader_now.items())
                    self.last_follower_raw = dict((int(k), int(v)) for k, v in follower_now.items())
                    self.last_goal_raw = dict((int(k), int(v)) for k, v in goal.items())
                    self.last_error = ""
                elapsed = time.time() - loop_start
                wait = max(0.0, interval - elapsed)
                if self.stop_event.wait(wait):
                    break
        except Exception as exc:
            self._finish_with_error("%s: %s" % (type(exc).__name__, exc))
            return
        finally:
            try:
                if self.leader_bus is not None:
                    self.leader_bus.disconnect()
            except Exception:
                pass
            with self.lock:
                self.running = False
                self.pause_event.clear()

    def _finish_with_error(self, message):
        with self.lock:
            self.last_error = message
            self.running = False
            self.pause_event.clear()


class DryRunFollowerDriver(FollowerDriver):
    def __init__(self, mapping):
        self.mapping = mapping
        self.connected = False
        self.last_positions = [0.0, -0.2, 0.4, -0.2, 0.0, 0.2]
        self.last_action = ros_positions_to_lerobot_action(self.last_positions, mapping)

    def connect(self):
        self.connected = True
        return {"ok": True, "dry_run": True, "message": "模拟连接已就绪"}

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
            "connected": self.connected,
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
        # Imported lazily so the lightweight runtime works on machines without LeRobot.
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
        result = {str(k): float(v) for k, v in obs.items() if str(k).endswith(".pos")}
        result["connected"] = True
        return result


class NativeSTSFollowerDriver(FollowerDriver):
    """No-third-party Feetech STS serial driver for the SO101 follower demo."""

    def __init__(self, serial_config, calibration, mapping):
        self.serial_config = serial_config
        self.calibration = calibration
        self.mapping = mapping
        self.bus = NativeFeetechSTSBus(serial_config)
        self.connected = False
        self.torque_enabled = False
        self.last_action = {}
        self.last_raw_goal = {}

    def _ids(self):
        return [int(self.calibration[name]["id"]) for name in JOINT_NAMES]

    def connect(self):
        self.bus.connect()
        time.sleep(float(self.serial_config.get("serial_settle_sec", 0.8)))
        found = self.bus.scan_expected(self._ids())
        missing = [motor_id for motor_id in self._ids() if motor_id not in found]
        wrong = dict((motor_id, model) for motor_id, model in found.items() if int(model) != STS_MODEL_NUMBER)
        if missing or wrong:
            self.bus.disconnect()
            if missing:
                raise RuntimeError(
                    "只扫到 %d/%d 个舵机，缺少 ID %s；已等待 %.0f 秒。请检查从 ID 2 到 ID 3 的串联线、ID 3-6 供电和舵机 ID 配置。found=%s"
                    % (
                        len(found),
                        len(self._ids()),
                        ",".join([str(motor_id) for motor_id in missing]),
                        float(self.serial_config.get("scan_window_sec", 0)),
                        found,
                    )
                )
            raise RuntimeError("舵机型号不匹配 wrong=%s found=%s" % (wrong, found))
        self.connected = True
        return {
            "ok": True,
            "dry_run": False,
            "backend": self.serial_config.get("backend", "native_sts"),
            "found": found,
        }

    def disconnect(self):
        self.release_torque()
        self.bus.disconnect()
        self.connected = False
        self.torque_enabled = False

    def release_torque(self):
        if not self.connected:
            return
        for motor_id in self._ids():
            try:
                self.bus.write_byte(motor_id, STS_ADDR_TORQUE_ENABLE, 0)
            except Exception:
                pass
        self.torque_enabled = False

    def _enable_torque_at_current_position(self):
        present_by_id = self.bus.read_present_positions(self._ids())
        self.bus.sync_write_word(STS_ADDR_GOAL_POSITION, present_by_id)
        for motor_id in self._ids():
            self.bus.write_byte(motor_id, STS_ADDR_TORQUE_ENABLE, 1)
        self.torque_enabled = True
        return present_by_id

    def send_positions(self, positions):
        if not self.connected:
            self.connect()
        if not self.torque_enabled:
            self._enable_torque_at_current_position()
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
            "connected": True,
            "present_positions": {str(k): v for k, v in present_by_id.items()},
            "raw_present": present_by_name,
            "last_raw_goal": dict(self.last_raw_goal),
        }


class MonitorFollowerDriver(FollowerDriver):
    def __init__(self, serial_config, calibration, mapping):
        self.serial_config = serial_config
        self.calibration = calibration
        self.mapping = mapping
        self.bus = None
        self.connected = False
        self.present_positions = {}

    def _ids(self):
        return [int(self.calibration[name]["id"]) for name in JOINT_NAMES]

    def _cleanup(self):
        self.connected = False
        if self.bus is not None:
            try:
                self.bus.disconnect()
            except Exception:
                pass
        self.bus = None

    def connect(self):
        self._cleanup()
        port = self.serial_config.get("port", "/dev/ttyACM0")
        if not os.path.exists(port):
            return {"ok": False, "dry_run": False, "monitor_mode": True,
                    "error": "\u4E32\u53E3 %s \u4E0D\u5B58\u5728\uFF0C\u8BF7\u68C0\u67E5\u786C\u4EF6\u8FDE\u63A5" % port}
        if not os.access(port, os.R_OK | os.W_OK):
            return {"ok": False, "dry_run": False, "monitor_mode": True,
                    "error": "\u4E32\u53E3 %s \u6743\u9650\u4E0D\u8DB3" % port}
        try:
            self.bus = NativeFeetechSTSBus(self.serial_config)
            self.bus.connect()
            time.sleep(float(self.serial_config.get("serial_settle_sec", 0.8)))
            found = self.bus.scan_expected(self._ids())
            if len(found) < len(self._ids()):
                self._cleanup()
                return {"ok": False, "dry_run": False, "monitor_mode": True,
                        "error": "只扫到 %d/%d 个舵机: %s" % (len(found), len(self._ids()), found)}
            self.connected = True
            for motor_id in self._ids():
                try:
                    self.bus.write_byte(motor_id, STS_ADDR_TORQUE_ENABLE, 0)
                except Exception:
                    pass
            self.present_positions = self.bus.read_present_positions(self._ids())
            return {"ok": True, "dry_run": False, "monitor_mode": True,
                    "backend": self.serial_config.get("backend", "native_posix"),
                    "found": found,
                    "present_positions": {str(k): v for k, v in self.present_positions.items()}}
        except Exception as exc:
            self._cleanup()
            return {"ok": False, "dry_run": False, "monitor_mode": True,
                    "error": "%s: %s" % (type(exc).__name__, exc)}

    def disconnect(self):
        self.release_torque()
        self._cleanup()

    def release_torque(self):
        if not self.connected or self.bus is None:
            return
        for motor_id in self._ids():
            try:
                self.bus.write_byte(motor_id, STS_ADDR_TORQUE_ENABLE, 0)
            except Exception:
                pass

    def send_positions(self, positions):
        action = ros_positions_to_lerobot_action(positions, self.mapping)
        raw_goal_by_name = lerobot_action_to_raw_goal(action, self.calibration)
        return {"monitor_mode": True, "motion_blocked": True,
                "planned_action": action, "planned_raw_goal": raw_goal_by_name}

    def read_once(self):
        if not self.connected or self.bus is None:
            return {"monitor_mode": True, "connected": False}
        try:
            self.present_positions = self.bus.read_present_positions(self._ids())
            return {"monitor_mode": True, "connected": True,
                    "present_positions": {str(k): v for k, v in self.present_positions.items()}}
        except Exception:
            self._cleanup()
            return {"monitor_mode": True, "connected": False}


class DemoRuntime(object):
    def __init__(self):
        self.lock = threading.RLock()
        self.serial_config, self.templates, self.calibration = load_config()
        self.log_path = os.path.join(LOG_DIR, "run-%s.jsonl" % time.strftime("%Y%m%d-%H%M%S"))
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.state = {
            "schema": "so101_win7_runtime_status.v1",
            "started_ms": now_ms(),
            "connected": False,
            "busy": False,
            "execution_state": "idle",
            "dry_run": bool(self.serial_config.get("dry_run", True)),
            "monitor_mode": bool(self.serial_config.get("monitor_mode", False)),
            "port": self.serial_config.get("port", "COM6"),
            "backend": self.serial_config.get("backend", "lerobot"),
            "last_error": "",
            "last_template": "",
            "last_waypoint": "",
            "last_action": {},
            "last_observation": {},
            "control_initialized": False,
            "control_init_source": "",
            "event_count": 0,
            "boundary": "Win7 fallback follower demo; not ROS2, not grasp success, not trainable_real",
        }
        self.driver = self._make_driver()
        self.teleop = RawTeleopSession(self.serial_config, self.calibration)
        self._cached_obs = {"monitor_mode": self.state["monitor_mode"], "connected": False}
        self._watcher_stop = threading.Event()
        if bool(self.serial_config.get("monitor_mode", False)):
            t = threading.Thread(target=self._hardware_watcher, daemon=True)
            t.start()

    def _hardware_watcher(self):
        port = self.serial_config.get("port", "/dev/ttyACM0")
        while not self._watcher_stop.is_set():
            self._watcher_stop.wait(2)
            if self._watcher_stop.is_set():
                break
            if not os.path.exists(port):
                with self.lock:
                    self.state["connected"] = False
                    self.state["last_error"] = "\u7B49\u5F85\u786C\u4EF6..."
                    self._cached_obs = {"monitor_mode": True, "connected": False}
                continue
            if not os.access(port, os.R_OK | os.W_OK):
                subprocess.call(
                    ["sudo", "-n", "chmod", "666", port],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                if not os.access(port, os.R_OK | os.W_OK):
                    with self.lock:
                        self.state["connected"] = False
                        self.state["last_error"] = "\u6743\u9650\u4E0D\u8DB3"
                        self._cached_obs = {"monitor_mode": True, "connected": False}
                    continue
            if self.driver.connected:
                obs = self.driver.read_once()
                with self.lock:
                    if obs.get("connected"):
                        self._cached_obs = obs
                    else:
                        self.state["connected"] = False
                        self.state["last_error"] = "\u786C\u4EF6\u65AD\u5F00"
                        self._cached_obs = obs
                continue
            result = self.driver.connect()
            with self.lock:
                self.state["connected"] = result.get("ok", False)
                if result.get("ok"):
                    self.state["last_error"] = ""
                    self._cached_obs = self.driver.read_once()
                else:
                    self.state["last_error"] = result.get("error", "")
                    self._cached_obs = {"monitor_mode": True, "connected": False}
                self._log("auto_reconnect", result)

    def _make_driver(self):
        mapping = self.serial_config.get("mapping", {})
        if bool(self.serial_config.get("monitor_mode", False)):
            return MonitorFollowerDriver(self.serial_config, self.calibration, mapping)
        if bool(self.serial_config.get("dry_run", True)):
            return DryRunFollowerDriver(mapping)
        backend = str(self.serial_config.get("backend", "lerobot")).lower()
        if backend in ("native_win32", "native_posix", "native_linux", "native_sts"):
            return NativeSTSFollowerDriver(self.serial_config, self.calibration, mapping)
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
            teleop_status = self.teleop.status()
            if self.state.get("busy") and self.state.get("last_waypoint") == "teleop" and not teleop_status.get("running"):
                self.state["busy"] = False
                self.state["execution_state"] = "idle"
                if teleop_status.get("last_error"):
                    self.state["last_error"] = teleop_status.get("last_error")
            if self.state.get("connected") and not (
                self._cached_obs.get("present_positions") or self._cached_obs.get("raw_present")
            ):
                try:
                    if hasattr(self.driver, "read_once"):
                        observation = self.driver.read_once()
                    else:
                        observation = self.driver.get_observation()
                    if observation:
                        self._cached_obs = observation
                except Exception as exc:
                    self.state["last_error"] = "observation refresh failed: %s: %s" % (type(exc).__name__, exc)
            result = dict(self.state)
            result["templates"] = sorted(self.templates.get("templates", {}).keys())
            result["log_path"] = self.log_path
            result["last_observation"] = dict(self._cached_obs)
            result["teleop"] = teleop_status
            return result

    def _requires_control_initialization(self):
        return not bool(self.state.get("dry_run")) and not bool(self.state.get("monitor_mode"))

    def _assert_control_initialized(self):
        if self._requires_control_initialization() and not bool(self.state.get("control_initialized")):
            raise RuntimeError("control is not initialized from current hardware position")

    def _ensure_port_access(self):
        port = self.serial_config.get("port", "")
        if os.name == "nt" or not port or not str(port).startswith("/"):
            return
        if not os.path.exists(port):
            raise RuntimeError("serial port %s does not exist" % port)
        if os.access(port, os.R_OK | os.W_OK):
            return
        subprocess.call(
            ["sudo", "-n", "chmod", "666", port],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if not os.access(port, os.R_OK | os.W_OK):
            raise RuntimeError("serial port %s permission denied" % port)

    def _save_serial_config(self):
        write_json(os.path.join(CONFIG_DIR, "serial_config.json"), self.serial_config)

    def set_mode(self, mode):
        mode = str(mode or "").strip().lower()
        if mode not in ("monitor", "action"):
            raise ValueError("mode must be monitor or action")
        with self.lock:
            if self.state.get("busy"):
                raise RuntimeError("执行中只能暂停、继续或回安全点")
            self.stop_event.set()
            self.teleop.stop()
            try:
                self.driver.disconnect()
            except Exception:
                pass
            self.serial_config["monitor_mode"] = (mode == "monitor")
            self.state["monitor_mode"] = bool(self.serial_config.get("monitor_mode", False))
            self.state["connected"] = False
            self.state["busy"] = False
            self.state["execution_state"] = "idle"
            self.state["control_initialized"] = False
            self.state["control_init_source"] = ""
            self.state["last_error"] = ""
            self._cached_obs = {"monitor_mode": self.state["monitor_mode"], "connected": False}
            self.driver = self._make_driver()
            self.stop_event.clear()
            self.pause_event.clear()
            self._log("mode_changed", {"mode": mode})
            return {"ok": True, "mode": mode, "monitor_mode": self.state["monitor_mode"]}

    def read_observation(self):
        with self.lock:
            if not self.state.get("connected"):
                return {"ok": False, "connected": False, "error": "hardware is not connected"}
            if hasattr(self.driver, "read_once"):
                observation = self.driver.read_once()
            else:
                observation = self.driver.get_observation()
            if observation:
                self._cached_obs = observation
            return {"ok": bool(observation.get("connected", self.state.get("connected"))), "observation": observation}

    def scan_leader(self, leader_port, leader_ids):
        with self.lock:
            if self.state.get("busy"):
                raise RuntimeError("执行中不能扫描主臂")
            port = str(leader_port or self.serial_config.get("leader_port", "/dev/ttyACM1")).strip()
            ids = parse_int_list(leader_ids, self.serial_config.get("leader_ids", [1, 2, 3, 4, 5, 6]))
        result = self.teleop.read_leader_once(ids, port)
        result["leader_port"] = port
        result["leader_ids"] = ids
        with self.lock:
            self._log("leader_scanned", result)
        return result

    def calibrate_teleop(self, body):
        with self.lock:
            if self.state.get("monitor_mode"):
                raise RuntimeError("主从校准只能在动作模式下进行")
            if self.state.get("busy"):
                raise RuntimeError("执行中不能同步主从校准")
            if not (self.state.get("connected") and getattr(self.driver, "connected", False)):
                raise RuntimeError("请先连接从臂")
        payload = self.teleop.make_calibration(self.driver, body or {})
        with self.lock:
            self._log("teleop_calibrated", payload)
        return {"ok": True, "calibration": payload, "file": TELEOP_CALIBRATION_PATH}

    def start_teleop(self, body):
        with self.lock:
            if self.state.get("monitor_mode"):
                raise RuntimeError("主从遥操作只能在动作模式下运行")
            if self.state.get("busy"):
                raise RuntimeError("执行中只能暂停、继续或回安全点")
            if not (self.state.get("connected") and getattr(self.driver, "connected", False)):
                raise RuntimeError("请先连接从臂")
            if not bool(self.teleop.teleop_calibration.get("calibrated")):
                raise RuntimeError("请先点击“同步当前位置为校准”，保存主从同姿态校准后再开始跟随")
            self.state["busy"] = True
            self.state["execution_state"] = "running"
            self.state["last_template"] = ""
            self.state["last_waypoint"] = "teleop"
            self.state["last_error"] = ""
            self.stop_event.clear()
            self.pause_event.clear()
            self._log("teleop_start_requested", body)
        result = self.teleop.start(self.driver, body or {})
        if not result.get("ok"):
            with self.lock:
                self.state["busy"] = False
                self.state["execution_state"] = "idle"
                self.state["last_error"] = result.get("error", "teleop start failed")
        return result

    def pause_teleop(self):
        result = self.teleop.pause()
        with self.lock:
            if result.get("ok"):
                self.state["execution_state"] = "paused"
            self._log("teleop_pause_requested", result)
        return result

    def resume_teleop(self):
        result = self.teleop.resume()
        with self.lock:
            if result.get("ok"):
                self.state["execution_state"] = "running"
            self._log("teleop_resume_requested", result)
        return result

    def stop_teleop(self):
        result = self.teleop.stop()
        with self.lock:
            self.state["busy"] = False
            self.state["execution_state"] = "idle"
            if result.get("teleop", {}).get("last_error"):
                self.state["last_error"] = result["teleop"]["last_error"]
            self._log("teleop_stop_requested", result)
        return result

    def _recording_template_name(self, requested):
        base = self._normalize_recording_name(requested)
        name = base
        index = 2
        templates = self.templates.get("templates", {})
        while name in templates:
            name = "%s_%d" % (base, index)
            index += 1
        return name

    def _normalize_recording_name(self, requested):
        base = re.sub(r"[^A-Za-z0-9_]+", "_", str(requested or "").strip().lower()).strip("_")
        if not base:
            base = "recording"
        if not base.startswith("record_"):
            base = "record_" + base
        return base

    def _recording_display_name(self, requested, fallback):
        display_name = str(requested or "").strip()
        if not display_name:
            display_name = str(fallback or "").strip()
        return display_name[:80]

    def _generated_recording_template_name(self):
        base = "record_%s" % time.strftime("%Y%m%d_%H%M%S")
        name = base
        index = 2
        templates = self.templates.get("templates", {})
        while name in templates:
            name = "%s_%d" % (base, index)
            index += 1
        return name

    def _recording_file_name(self, template_name):
        safe_name = re.sub(r"[^A-Za-z0-9_]+", "_", str(template_name)).strip("_") or "recording"
        filename = "%s.json" % safe_name
        if not os.path.exists(os.path.join(RECORDINGS_DIR, filename)):
            return filename
        index = 2
        while True:
            filename = "%s_%d.json" % (safe_name, index)
            if not os.path.exists(os.path.join(RECORDINGS_DIR, filename)):
                return filename
            index += 1

    def _recording_file_name_for_rename(self, template_name, current_filename):
        current_filename = os.path.basename(str(current_filename or ""))
        safe_name = re.sub(r"[^A-Za-z0-9_]+", "_", str(template_name)).strip("_") or "recording"
        filename = "%s.json" % safe_name
        if filename == current_filename:
            return filename
        if not os.path.exists(os.path.join(RECORDINGS_DIR, filename)):
            return filename
        index = 2
        while True:
            filename = "%s_%d.json" % (safe_name, index)
            if filename == current_filename:
                return filename
            if not os.path.exists(os.path.join(RECORDINGS_DIR, filename)):
                return filename
            index += 1

    def _install_recording_template(self, template_name, points, delay):
        waypoints = self.templates.setdefault("waypoints", {})
        templates = self.templates.setdefault("templates", {})
        template_delays = self.templates.setdefault("template_delays", {})
        old_waypoints = list(templates.get(template_name, []))
        waypoint_names = []
        for index, point in enumerate(points):
            waypoint_name = "%s_%03d" % (template_name, index + 1)
            waypoints[waypoint_name] = point
            waypoint_names.append(waypoint_name)
        for waypoint_name in old_waypoints:
            if waypoint_name not in waypoint_names:
                waypoints.pop(waypoint_name, None)
        templates[template_name] = waypoint_names
        template_delays[template_name] = delay
        write_json(os.path.join(CONFIG_DIR, "action_templates.json"), self.templates)
        return waypoint_names

    def _delete_recording_template(self, template_name):
        template_name = str(template_name or "").strip()
        if not template_name.startswith("record_"):
            raise ValueError("only recorded templates can be deleted")
        templates = self.templates.setdefault("templates", {})
        if template_name not in templates:
            return False
        waypoint_names = list(templates.get(template_name, []))
        del templates[template_name]
        self.templates.setdefault("template_delays", {}).pop(template_name, None)
        waypoints = self.templates.setdefault("waypoints", {})
        for waypoint_name in waypoint_names:
            waypoints.pop(waypoint_name, None)
        write_json(os.path.join(CONFIG_DIR, "action_templates.json"), self.templates)
        return True

    def _rename_recording_template(self, old_name, new_name, update_files):
        old_name = str(old_name or "").strip()
        new_name = self._normalize_recording_name(new_name)
        if not old_name.startswith("record_"):
            raise ValueError("only recorded templates can be renamed")
        templates = self.templates.setdefault("templates", {})
        if old_name not in templates:
            raise ValueError("recording template not found: %s" % old_name)
        if new_name != old_name and new_name in templates:
            raise ValueError("recording already exists: %s" % new_name)

        sequence = list(templates.get(old_name, []))
        waypoints = self.templates.setdefault("waypoints", {})
        template_delays = self.templates.setdefault("template_delays", {})
        renamed_waypoints = []
        for index, waypoint_name in enumerate(sequence):
            new_waypoint_name = "%s_%03d" % (new_name, index + 1)
            waypoints[new_waypoint_name] = waypoints.get(waypoint_name, [])
            renamed_waypoints.append(new_waypoint_name)
        for waypoint_name in sequence:
            if waypoint_name not in renamed_waypoints:
                waypoints.pop(waypoint_name, None)

        if new_name != old_name:
            templates.pop(old_name, None)
        templates[new_name] = renamed_waypoints
        if old_name in template_delays:
            template_delays[new_name] = template_delays.pop(old_name)
        write_json(os.path.join(CONFIG_DIR, "action_templates.json"), self.templates)

        updated_files = []
        if update_files and os.path.isdir(RECORDINGS_DIR):
            for filename in sorted(os.listdir(RECORDINGS_DIR)):
                if not filename.endswith(".json"):
                    continue
                path = os.path.join(RECORDINGS_DIR, filename)
                try:
                    payload = read_json(path)
                except Exception:
                    continue
                if payload.get("template") != old_name:
                    continue
                payload["template"] = new_name
                payload["name"] = new_name
                new_filename = self._recording_file_name_for_rename(new_name, filename)
                new_path = os.path.join(RECORDINGS_DIR, new_filename)
                write_json(path, payload)
                if new_filename != filename:
                    os.rename(path, new_path)
                updated_files.append(new_filename)
        return new_name, updated_files

    def _set_recording_template_display_name(self, template_name, display_name, update_files):
        template_name = str(template_name or "").strip()
        templates = self.templates.setdefault("templates", {})
        if template_name not in templates:
            raise ValueError("recording template not found: %s" % template_name)
        display_name = self._recording_display_name(display_name, template_name)
        display_names = self.templates.setdefault("template_display_names", {})
        display_names[template_name] = display_name
        write_json(os.path.join(CONFIG_DIR, "action_templates.json"), self.templates)

        updated_files = []
        if update_files and os.path.isdir(RECORDINGS_DIR):
            for filename in sorted(os.listdir(RECORDINGS_DIR)):
                if not filename.endswith(".json"):
                    continue
                path = os.path.join(RECORDINGS_DIR, filename)
                try:
                    payload = read_json(path)
                except Exception:
                    continue
                if payload.get("template") != template_name:
                    continue
                payload["name"] = display_name
                write_json(path, payload)
                updated_files.append(filename)
        return display_name, updated_files

    def _trash_recording_file(self, filename):
        filename = os.path.basename(str(filename or "").strip())
        if not filename.endswith(".json"):
            raise ValueError("recording file id must be a json file")
        path = os.path.join(RECORDINGS_DIR, filename)
        if not os.path.isfile(path):
            raise ValueError("recording file not found: %s" % filename)
        if not os.path.isdir(RECORDINGS_TRASH_DIR):
            os.makedirs(RECORDINGS_TRASH_DIR)
        base, ext = os.path.splitext(filename)
        trashed_name = "%s.deleted_%s%s" % (base, time.strftime("%Y%m%d_%H%M%S"), ext)
        trashed_path = os.path.join(RECORDINGS_TRASH_DIR, trashed_name)
        index = 2
        while os.path.exists(trashed_path):
            trashed_name = "%s.deleted_%s_%d%s" % (base, time.strftime("%Y%m%d_%H%M%S"), index, ext)
            trashed_path = os.path.join(RECORDINGS_TRASH_DIR, trashed_name)
            index += 1
        payload = {}
        try:
            payload = read_json(path)
        except Exception:
            pass
        os.rename(path, trashed_path)
        return trashed_name, payload

    def _trash_recording_files_for_template(self, template_name):
        trashed = []
        if not os.path.isdir(RECORDINGS_DIR):
            return trashed
        for filename in sorted(os.listdir(RECORDINGS_DIR)):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(RECORDINGS_DIR, filename)
            try:
                payload = read_json(path)
            except Exception:
                continue
            if payload.get("template") == template_name:
                trashed_name, _payload = self._trash_recording_file(filename)
                trashed.append(trashed_name)
        return trashed

    def delete_recording(self, kind, recording_id):
        kind = str(kind or "").strip().lower()
        if ":" in str(recording_id):
            kind, recording_id = str(recording_id).split(":", 1)
            kind = kind.strip().lower()
        if kind not in ("file", "template"):
            raise ValueError("recording kind must be file or template")
        with self.lock:
            if self.state.get("busy"):
                raise RuntimeError("执行中不能删除动作")
        removed_template = False
        trashed_files = []
        if kind == "template":
            trashed_files = self._trash_recording_files_for_template(recording_id)
            removed_template = self._delete_recording_template(recording_id)
        else:
            trashed_file, payload = self._trash_recording_file(recording_id)
            trashed_files = [trashed_file]
            template_name = payload.get("template", "")
            if template_name.startswith("record_") and template_name in self.templates.get("templates", {}):
                removed_template = self._delete_recording_template(template_name)
        with self.lock:
            self._log("recording_deleted", {
                "kind": kind,
                "id": recording_id,
                "trashed_files": trashed_files,
                "removed_template": removed_template,
            })
        return {
            "ok": True,
            "kind": kind,
            "id": recording_id,
            "trashed_file": trashed_files[0] if trashed_files else "",
            "trashed_files": trashed_files,
            "removed_template": removed_template,
        }

    def rename_recording(self, kind, recording_id, new_name, display_only=True):
        kind = str(kind or "").strip().lower()
        if ":" in str(recording_id):
            kind, recording_id = str(recording_id).split(":", 1)
            kind = kind.strip().lower()
        if kind not in ("file", "template"):
            raise ValueError("recording kind must be file or template")

        with self.lock:
            if self.state.get("busy"):
                raise RuntimeError("执行中不能重命名动作")
            if display_only and kind == "template":
                display_name, updated_files = self._set_recording_template_display_name(recording_id, new_name, True)
                result = {
                    "ok": True,
                    "kind": kind,
                    "id": recording_id,
                    "new_id": recording_id,
                    "template": recording_id,
                    "display_name": display_name,
                    "updated_files": updated_files,
                }
            elif display_only and kind == "file":
                filename = os.path.basename(str(recording_id or "").strip())
                if not filename.endswith(".json"):
                    raise ValueError("recording file id must be a json file")
                path = os.path.join(RECORDINGS_DIR, filename)
                if not os.path.isfile(path):
                    raise ValueError("recording file not found: %s" % filename)
                payload = read_json(path)
                display_name = self._recording_display_name(new_name, payload.get("name", filename[:-5]))
                payload["name"] = display_name
                write_json(path, payload)
                template_name = payload.get("template", "")
                if template_name in self.templates.get("templates", {}):
                    self._set_recording_template_display_name(template_name, display_name, False)
                result = {
                    "ok": True,
                    "kind": kind,
                    "id": filename,
                    "new_id": filename,
                    "template": template_name,
                    "file": filename,
                    "display_name": display_name,
                }
            elif kind == "template":
                normalized = self._normalize_recording_name(new_name)
                renamed_template, updated_files = self._rename_recording_template(recording_id, normalized, True)
                result = {
                    "ok": True,
                    "kind": kind,
                    "id": recording_id,
                    "new_id": renamed_template,
                    "template": renamed_template,
                    "updated_files": updated_files,
                }
            else:
                normalized = self._normalize_recording_name(new_name)
                filename = os.path.basename(str(recording_id or "").strip())
                if not filename.endswith(".json"):
                    raise ValueError("recording file id must be a json file")
                path = os.path.join(RECORDINGS_DIR, filename)
                if not os.path.isfile(path):
                    raise ValueError("recording file not found: %s" % filename)
                payload = read_json(path)
                old_template = payload.get("template", os.path.splitext(filename)[0])
                renamed_template = normalized
                if old_template in self.templates.get("templates", {}):
                    renamed_template, _updated_files = self._rename_recording_template(old_template, normalized, False)
                payload["template"] = renamed_template
                payload["name"] = renamed_template
                new_filename = self._recording_file_name_for_rename(renamed_template, filename)
                write_json(path, payload)
                if new_filename != filename:
                    os.rename(path, os.path.join(RECORDINGS_DIR, new_filename))
                result = {
                    "ok": True,
                    "kind": kind,
                    "id": filename,
                    "new_id": new_filename,
                    "template": renamed_template,
                    "file": new_filename,
                }
            self._log("recording_renamed", result)
            return result

    def list_recordings(self):
        recordings = []
        template_delays = self.templates.get("template_delays", {})
        template_display_names = self.templates.get("template_display_names", {})
        for name, sequence in sorted(self.templates.get("templates", {}).items()):
            if str(name).startswith("record_"):
                recordings.append({
                    "kind": "template",
                    "id": name,
                    "name": name,
                    "display_name": template_display_names.get(name, name),
                    "samples": len(sequence),
                    "delay": template_delays.get(name, self.serial_config.get("command_step_delay_sec", 0.8)),
                })
        if os.path.isdir(RECORDINGS_DIR):
            for filename in sorted(os.listdir(RECORDINGS_DIR)):
                if not filename.endswith(".json"):
                    continue
                path = os.path.join(RECORDINGS_DIR, filename)
                try:
                    payload = read_json(path)
                    samples = len(payload.get("points", []))
                    delay = payload.get("delay", self.serial_config.get("command_step_delay_sec", 0.8))
                    name = payload.get("template", filename[:-5])
                    created_ms = payload.get("created_ms", 0)
                except Exception:
                    payload = {}
                    samples = 0
                    delay = ""
                    name = filename[:-5]
                    created_ms = 0
                recordings.append({
                    "kind": "file",
                    "id": filename,
                    "name": name,
                    "display_name": payload.get("name", name),
                    "filename": filename,
                    "samples": samples,
                    "delay": delay,
                    "created_ms": created_ms,
                })
        return {"ok": True, "recordings": recordings}

    def load_recording(self, recording_id):
        with self.lock:
            if self.state.get("busy"):
                raise RuntimeError("执行中不能导入动作")
        recording_id = os.path.basename(str(recording_id or "").strip())
        if not recording_id:
            raise ValueError("recording id is required")
        path = os.path.join(RECORDINGS_DIR, recording_id)
        if not os.path.isfile(path):
            raise ValueError("recording file not found: %s" % recording_id)
        payload = read_json(path)
        points = [normalize_manual_positions(point) for point in payload.get("points", [])]
        if len(points) < 2:
            raise ValueError("recording file has fewer than 2 samples")
        delay = clamp(float(payload.get("delay", 0.25)), 0.05, 3.0)
        requested_name = self._normalize_recording_name(payload.get("template", os.path.splitext(recording_id)[0]))
        template_name = requested_name
        self._install_recording_template(template_name, points, delay)
        with self.lock:
            self._log("recording_loaded", {"file": recording_id, "template": template_name, "samples": len(points), "delay": delay})
        return {"ok": True, "template": template_name, "samples": len(points), "delay": delay}

    def save_recording(self, name, points, delay):
        with self.lock:
            if self.state.get("busy"):
                raise RuntimeError("执行中不能保存动作")
        if not isinstance(points, list) or len(points) < 2:
            raise ValueError("recording requires at least 2 samples")
        normalized_points = [normalize_manual_positions(point) for point in points]
        delay = clamp(float(delay or 0.25), 0.05, 3.0)
        requested_name = str(name or "").strip()
        template_name = self._recording_template_name(requested_name) if requested_name else self._generated_recording_template_name()
        self._install_recording_template(template_name, normalized_points, delay)
        if not os.path.isdir(RECORDINGS_DIR):
            os.makedirs(RECORDINGS_DIR)
        filename = self._recording_file_name(template_name)
        write_json(os.path.join(RECORDINGS_DIR, filename), {
            "schema": "so101_recording.v1",
            "template": template_name,
            "name": requested_name or template_name,
            "created_ms": now_ms(),
            "delay": delay,
            "joint_names": JOINT_NAMES,
            "points": normalized_points,
        })
        with self.lock:
            self._log("recording_saved", {"template": template_name, "file": filename, "samples": len(normalized_points), "delay": delay})
        return {"ok": True, "template": template_name, "file": filename, "samples": len(normalized_points), "delay": delay}

    def connect(self, user_requested=True):
        with self.lock:
            if user_requested and self.state.get("busy"):
                return {"ok": False, "error": "系统正在连接或执行，请等待当前操作完成"}
            if self.state.get("connected") and getattr(self.driver, "connected", False):
                return {"ok": True, "already_connected": True, "message": "already connected"}
            if user_requested:
                self.state["busy"] = True
                self.state["execution_state"] = "connecting"
                self.state["last_error"] = "正在连接并扫描 6 个舵机，通常需要 10-20 秒"
            self.state["control_initialized"] = False
            self.state["control_init_source"] = ""

        try:
            self._ensure_port_access()
            result = self.driver.connect()
        except Exception as exc:
            result = {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}

        with self.lock:
            self.state["connected"] = result.get("ok", False)
            self.state["control_initialized"] = False
            self.state["control_init_source"] = ""
            if result.get("ok"):
                self.state["last_error"] = ""
                try:
                    observation = self.driver.get_observation()
                except Exception as exc:
                    observation = {}
                    self.state["last_error"] = "connected; observation failed: %s: %s" % (type(exc).__name__, exc)
                if not observation and result.get("present_positions"):
                    observation = {
                        "monitor_mode": result.get("monitor_mode", False),
                        "connected": True,
                        "present_positions": result.get("present_positions", {}),
                    }
                if observation:
                    self._cached_obs = observation
            else:
                self.state["last_error"] = result.get("error", "connect failed")
            if user_requested:
                self.state["busy"] = False
                self.state["execution_state"] = "idle"
            self._log("connected", result)
            return result

    def disconnect(self):
        with self.lock:
            self.driver.disconnect()
            self.state["connected"] = False
            self.state["control_initialized"] = False
            self.state["control_init_source"] = ""
            self._log("disconnected", {})
            return {"ok": True}

    def initialize_control(self, positions, source):
        normalized = normalize_manual_positions(positions)
        source = str(source or "current_observation").strip() or "current_observation"
        with self.lock:
            if self.state.get("busy"):
                raise RuntimeError("执行中不能重新同步读数")
            if self._requires_control_initialization() and not self.state.get("connected"):
                raise RuntimeError("connect hardware before initializing control")
            self.state["control_initialized"] = True
            self.state["control_init_source"] = source
            self.state["last_waypoint"] = source
            self._log("control_initialized", {"source": source, "positions": normalized})
            return {"ok": True, "positions": normalized, "source": source}

    def stop(self):
        # For this lightweight demo, stop means clear busy state. Hardware e-stop remains physical/procedural.
        with self.lock:
            self.stop_event.set()
            self.pause_event.clear()
            if self.teleop.is_active():
                self.teleop.stop()
            if hasattr(self.driver, "release_torque"):
                self.driver.release_torque()
            self.state["execution_state"] = "stopping"
            self._log("stop_requested", {})
            return {"ok": True, "message": "stop requested; torque release sent; wait for current step to settle before starting a new action"}

    def pause(self):
        with self.lock:
            if self.teleop.is_active():
                return self.pause_teleop()
            if not self.state.get("busy") or self.state.get("execution_state") not in ("running", "paused"):
                return {"ok": False, "error": "当前没有正在回放的动作"}
            self.pause_event.set()
            self.state["execution_state"] = "paused"
            self._log("pause_requested", {})
            return {"ok": True, "message": "已暂停，当前步完成后停在下一步前"}

    def resume(self):
        with self.lock:
            if self.teleop.is_active():
                return self.resume_teleop()
            if self.state.get("execution_state") != "paused":
                return {"ok": False, "error": "当前没有暂停中的动作"}
            self.pause_event.clear()
            self.state["execution_state"] = "running"
            self._log("resume_requested", {})
            return {"ok": True, "message": "继续回放"}

    def _wait_if_paused(self):
        while self.pause_event.is_set() and not self.stop_event.is_set():
            with self.lock:
                self.state["execution_state"] = "paused"
            self.pause_event.wait(0.1)
        if not self.stop_event.is_set():
            with self.lock:
                if self.state.get("busy"):
                    self.state["execution_state"] = "running"

    def execute_template(self, template_name, repeat):
        try:
            repeat = int(repeat or 1)
        except (TypeError, ValueError):
            repeat = 1
        repeat = int(clamp(repeat, 1, 20))
        with self.lock:
            if self.state.get("busy"):
                raise RuntimeError("runtime is busy")
            sequence = self.templates.get("templates", {}).get(template_name)
            if not sequence:
                raise ValueError("unknown template: %s" % template_name)
            self.state["busy"] = True
            self.state["execution_state"] = "running"
            self.state["last_template"] = template_name
            self.state["last_error"] = ""
            self.stop_event.clear()
            self.pause_event.clear()

        try:
            self._assert_control_initialized()
            if not (self.state.get("connected") and getattr(self.driver, "connected", False)):
                raise RuntimeError("请先连接硬件并同步当前关节读数")
            results = []
            template_delays = self.templates.get("template_delays", {})
            delay = float(template_delays.get(template_name, self.serial_config.get("command_step_delay_sec", 0.8)))
            waypoints = self.templates.get("waypoints", {})
            interrupted = False
            for repeat_index in range(repeat):
                for waypoint_name in sequence:
                    self._wait_if_paused()
                    if self.stop_event.is_set():
                        interrupted = True
                        break
                    positions = waypoints.get(waypoint_name)
                    if positions is None:
                        raise ValueError("missing waypoint: %s" % waypoint_name)
                    sent = self.driver.send_positions(positions)
                    if self.stop_event.is_set():
                        interrupted = True
                    if interrupted:
                        break
                    observation = self.driver.get_observation()
                    with self.lock:
                        self.state["last_waypoint"] = waypoint_name
                        self.state["last_action"] = sent
                        self.state["last_observation"] = observation
                        if observation:
                            self._cached_obs = observation
                        self._log(
                            "waypoint_sent",
                            {
                                "template": template_name,
                                "repeat": repeat_index + 1,
                                "repeat_total": repeat,
                                "waypoint": waypoint_name,
                                "positions": positions,
                                "sent": sent,
                                "observation": observation,
                            },
                        )
                    results.append({"repeat": repeat_index + 1, "waypoint": waypoint_name, "sent": sent})
                    if self.stop_event.wait(delay):
                        interrupted = True
                        break
                if interrupted:
                    break
            if interrupted:
                with self.lock:
                    self.state["last_error"] = "execution stopped by user"
                return {"ok": False, "stopped": True, "template": template_name, "repeat": repeat, "steps": results, "error": "execution stopped by user"}
            return {"ok": True, "template": template_name, "repeat": repeat, "steps": results}
        except Exception as exc:
            with self.lock:
                self.state["last_error"] = "%s: %s" % (type(exc).__name__, exc)
                self._log("template_failed", {"template": template_name, "error": self.state["last_error"], "trace": traceback.format_exc()})
            raise
        finally:
            with self.lock:
                self.state["busy"] = False
                self.state["execution_state"] = "idle" if not self.stop_event.is_set() else "stopped"
                self.pause_event.clear()

    def go_safe_point(self):
        had_running_action = False
        with self.lock:
            had_running_action = bool(self.state.get("busy"))
            if had_running_action:
                self.stop_event.set()
                self.pause_event.clear()
                self.state["execution_state"] = "stopping"
                if self.teleop.is_active():
                    self.teleop.stop()
                    self.state["busy"] = False
        deadline = time.time() + 8.0
        while had_running_action and time.time() < deadline:
            with self.lock:
                if not self.state.get("busy"):
                    break
            time.sleep(0.05)
        with self.lock:
            if self.state.get("busy"):
                raise RuntimeError("当前动作仍在停止中，请稍后再回安全点")
        safe_point = normalize_manual_positions(self.serial_config.get("safe_point_positions", []))
        steps = int(clamp(int(self.serial_config.get("safe_point_steps", 12)), 2, 60))
        delay = float(clamp(float(self.serial_config.get("safe_point_step_delay_sec", 0.25)), 0.05, 2.0))
        current = None
        try:
            observation = self.driver.get_observation()
            if observation:
                current = raw_present_to_manual_positions(observation, self.calibration, self.serial_config.get("mapping", {}))
        except Exception:
            current = None
        if current is None:
            current = raw_present_to_manual_positions(self._cached_obs, self.calibration, self.serial_config.get("mapping", {}))
        if current is None:
            raise RuntimeError("当前没有完整关节读数，不能安全回安全点")
        waypoints = []
        for index in range(1, steps + 1):
            ratio = float(index) / float(steps)
            waypoints.append([current[i] + (safe_point[i] - current[i]) * ratio for i in range(len(JOINT_NAMES))])
        return self.execute_position_sequence(waypoints, delay, "safe_point")

    def execute_position_sequence(self, sequence, delay, label):
        if not sequence:
            raise ValueError("position sequence is empty")
        with self.lock:
            if self.state.get("busy"):
                raise RuntimeError("runtime is busy")
            self.state["busy"] = True
            self.state["execution_state"] = "running"
            self.state["last_template"] = ""
            self.state["last_waypoint"] = label
            self.state["last_error"] = ""
            self.stop_event.clear()
            self.pause_event.clear()
        results = []
        try:
            self._assert_control_initialized()
            if not (self.state.get("connected") and getattr(self.driver, "connected", False)):
                raise RuntimeError("请先连接硬件并同步当前关节读数")
            for index, positions in enumerate(sequence):
                self._wait_if_paused()
                if self.stop_event.is_set():
                    return {"ok": False, "stopped": True, "label": label, "steps": results, "error": "execution stopped by user"}
                sent = self.driver.send_positions(normalize_manual_positions(positions))
                observation = self.driver.get_observation()
                with self.lock:
                    self.state["last_waypoint"] = "%s_%03d" % (label, index + 1)
                    self.state["last_action"] = sent
                    self.state["last_observation"] = observation
                    if observation:
                        self._cached_obs = observation
                    self._log("position_sequence_sent", {
                        "label": label,
                        "step": index + 1,
                        "step_total": len(sequence),
                        "positions": positions,
                        "sent": sent,
                        "observation": observation,
                    })
                results.append({"step": index + 1, "sent": sent})
                if self.stop_event.wait(delay):
                    return {"ok": False, "stopped": True, "label": label, "steps": results, "error": "execution stopped by user"}
            return {"ok": True, "label": label, "steps": results}
        except Exception as exc:
            with self.lock:
                self.state["last_error"] = "%s: %s" % (type(exc).__name__, exc)
                self._log("position_sequence_failed", {"label": label, "error": self.state["last_error"], "trace": traceback.format_exc()})
            raise
        finally:
            with self.lock:
                self.state["busy"] = False
                self.state["execution_state"] = "idle" if not self.stop_event.is_set() else "stopped"
                self.pause_event.clear()

    def execute_positions(self, positions, label):
        normalized = normalize_manual_positions(positions)
        label = str(label or "manual_six_axis").strip() or "manual_six_axis"
        with self.lock:
            if self.state.get("busy"):
                raise RuntimeError("runtime is busy")
            self.state["busy"] = True
            self.state["execution_state"] = "running"
            self.state["last_template"] = ""
            self.state["last_waypoint"] = label
            self.state["last_error"] = ""
            self.stop_event.clear()
            self.pause_event.clear()

        try:
            self._assert_control_initialized()
            if not (self.state.get("connected") and getattr(self.driver, "connected", False)):
                raise RuntimeError("请先连接硬件并同步当前关节读数")
            if self.stop_event.is_set():
                raise RuntimeError("execution stopped by user")
            sent = self.driver.send_positions(normalized)
            try:
                observation = self.driver.get_observation()
            except Exception as exc:
                observation = {"connected": True, "read_error": "%s: %s" % (type(exc).__name__, exc)}
            motion_blocked = bool(sent.get("motion_blocked")) if isinstance(sent, dict) else False
            with self.lock:
                self.state["last_action"] = sent
                self.state["last_observation"] = observation
                if observation:
                    self._cached_obs = observation
                if motion_blocked:
                    self.state["last_error"] = "monitor_mode is enabled; motion not sent"
                self._log(
                    "manual_positions_sent",
                    {
                        "label": label,
                        "positions": normalized,
                        "sent": sent,
                        "observation": observation,
                        "motion_blocked": motion_blocked,
                    },
                )
            if self.stop_event.is_set():
                return {
                    "ok": False,
                    "label": label,
                    "positions": normalized,
                    "sent": sent,
                    "observation": observation,
                    "motion_blocked": motion_blocked,
                    "stopped": True,
                    "error": "execution stopped by user",
                }
            return {
                "ok": not motion_blocked,
                "label": label,
                "positions": normalized,
                "sent": sent,
                "observation": observation,
                "motion_blocked": motion_blocked,
                "error": "monitor_mode is enabled; motion not sent" if motion_blocked else "",
            }
        except Exception as exc:
            with self.lock:
                self.state["last_error"] = "%s: %s" % (type(exc).__name__, exc)
                self._log("manual_positions_failed", {"label": label, "error": self.state["last_error"], "trace": traceback.format_exc()})
            raise
        finally:
            with self.lock:
                self.state["busy"] = False
                self.state["execution_state"] = "idle" if not self.stop_event.is_set() else "stopped"
                self.pause_event.clear()


RUNTIME = DemoRuntime()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


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
                templates_response = dict(RUNTIME.templates)
                templates_response["calibration"] = RUNTIME.calibration
                templates_response["mapping"] = RUNTIME.serial_config.get("mapping", {})
                templates_response["manual_limits"] = MANUAL_LIMITS
                self._send_json(templates_response)
            elif path == "/api/recordings":
                self._send_json(RUNTIME.list_recordings())
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
            elif path == "/api/pause":
                self._send_json(RUNTIME.pause())
            elif path == "/api/resume":
                self._send_json(RUNTIME.resume())
            elif path == "/api/safe-point":
                self._send_json(RUNTIME.go_safe_point())
            elif path == "/api/mode":
                self._send_json(RUNTIME.set_mode(body.get("mode", "")))
            elif path == "/api/observation":
                self._send_json(RUNTIME.read_observation())
            elif path == "/api/teleop/scan":
                self._send_json(RUNTIME.scan_leader(body.get("leader_port", ""), body.get("leader_ids", [])))
            elif path == "/api/teleop/calibrate":
                self._send_json(RUNTIME.calibrate_teleop(body))
            elif path == "/api/teleop/start":
                self._send_json(RUNTIME.start_teleop(body))
            elif path == "/api/teleop/pause":
                self._send_json(RUNTIME.pause_teleop())
            elif path == "/api/teleop/resume":
                self._send_json(RUNTIME.resume_teleop())
            elif path == "/api/teleop/stop":
                self._send_json(RUNTIME.stop_teleop())
            elif path == "/api/control/initialize":
                self._send_json(RUNTIME.initialize_control(body.get("positions", []), body.get("source", "current_observation")))
            elif path == "/api/recording/save":
                self._send_json(RUNTIME.save_recording(body.get("name", "recording"), body.get("points", []), body.get("delay", 0.25)))
            elif path == "/api/recording/load":
                self._send_json(RUNTIME.load_recording(body.get("id", "")))
            elif path == "/api/recording/rename":
                self._send_json(RUNTIME.rename_recording(body.get("kind", ""), body.get("id", ""), body.get("name", "")))
            elif path == "/api/recording/delete":
                self._send_json(RUNTIME.delete_recording(body.get("kind", ""), body.get("id", "")))
            elif path == "/api/action":
                if "positions" in body:
                    self._send_json(RUNTIME.execute_positions(body.get("positions"), body.get("label", "manual_six_axis")))
                else:
                    template = str(body.get("template", "")).strip()
                    self._send_json(RUNTIME.execute_template(template, body.get("repeat", 1)))
            else:
                self._send_json({"ok": False, "error": "not found"}, status=404)
        except Exception as exc:
            self._send_json({"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}, status=500)

    def log_message(self, fmt, *args):
        sys.stdout.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))


def main():
    host = RUNTIME.serial_config.get("http_host", "127.0.0.1")
    port = int(RUNTIME.serial_config.get("http_port", 8765))
    url = "http://%s:%d" % (host, port)
    server = ThreadedHTTPServer((host, port), Handler)
    print("SO101 Win7 follower demo")
    print("Frontend: %s" % url)
    print("API: %s/api/status" % url)
    print("mode=%s port=%s log=%s" % (
        "monitor" if RUNTIME.state["monitor_mode"] else "action",
        RUNTIME.state["port"],
        RUNTIME.log_path,
    ))
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
