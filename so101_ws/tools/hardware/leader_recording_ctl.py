#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Any

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


START_RECORDING_SERVICE = "/leader/start_recording"
STOP_RECORDING_SERVICE = "/leader/stop_recording"
RECORDING_STATUS_SERVICE = "/leader/recording_status"
CONTROL_SCRIPT = "bash tools/hardware/control_leader_recording.sh"


def call_trigger(node: Node, service_name: str, timeout_sec: float) -> Trigger.Response:
    client = node.create_client(Trigger, service_name)
    if not client.wait_for_service(timeout_sec=timeout_sec):
        raise RuntimeError(f"service not available within {timeout_sec:.1f}s: {service_name}")

    future = client.call_async(Trigger.Request())
    rclpy.spin_until_future_complete(node, future, timeout_sec=timeout_sec)
    if not future.done():
        raise RuntimeError(f"service call timed out: {service_name}")

    response = future.result()
    if response is None:
        raise RuntimeError(f"service call failed without response: {service_name}")
    return response


def parse_status_payload(message: str) -> dict[str, Any]:
    payload = json.loads(message)
    if not isinstance(payload, dict):
        raise ValueError("recording_status payload is not a JSON object")
    return payload


def _format_warnings(warnings: Any) -> str:
    if isinstance(warnings, list) and warnings:
        return ", ".join(str(item) for item in warnings)
    return "none"


def format_status_text(payload: dict[str, Any]) -> str:
    if payload.get("active"):
        return "\n".join(
            [
                "Recording status: ACTIVE",
                f"File: {payload.get('path')}",
                f"Frames: {payload.get('frame_count')}",
                f"Duration sec: {payload.get('duration_sec')}",
                f"Warnings: {_format_warnings(payload.get('warnings'))}",
                "Next:",
                f"  Check again: {CONTROL_SCRIPT} status",
                f"  Stop now:    {CONTROL_SCRIPT} stop",
            ]
        )

    last_session = payload.get("last_session")
    if isinstance(last_session, dict):
        return "\n".join(
            [
                "Recording status: IDLE",
                f"Last file: {last_session.get('path')}",
                f"Last frames: {last_session.get('frame_count')}",
                f"Stop reason: {last_session.get('stop_reason')}",
                f"Warnings: {_format_warnings(last_session.get('warnings'))}",
                "Next:",
                f"  Start new:   {CONTROL_SCRIPT} start",
            ]
        )
    return "\n".join(
        [
            "Recording status: IDLE",
            "Last session: none",
            "Next:",
            f"  Start new:   {CONTROL_SCRIPT} start",
        ]
    )


def format_start_text(message: str, status: dict[str, Any] | None) -> str:
    lines = [
        "Recording started successfully.",
        f"Recorder reply: {message}",
        "Background recording: still running",
        f"Stop condition: run `{CONTROL_SCRIPT} stop` when you are done moving the leader",
    ]
    if status is not None:
        lines.extend(
            [
                f"First frame seen: yes",
                f"File: {status.get('path')}",
                f"Frames so far: {status.get('frame_count')}",
                "Next:",
                f"  Check status: {CONTROL_SCRIPT} status",
                f"  Watch live:    {CONTROL_SCRIPT} watch",
                f"  Stop record:  {CONTROL_SCRIPT} stop",
            ]
        )
    else:
        lines.extend(
            [
                "First frame wait: skipped",
                "Next:",
                f"  Check status: {CONTROL_SCRIPT} status",
                f"  Watch live:    {CONTROL_SCRIPT} watch",
                f"  Stop record:  {CONTROL_SCRIPT} stop",
            ]
        )
    return "\n".join(lines)


def format_stop_text(message: str) -> str:
    return "\n".join(
        [
            "Recording stopped.",
            f"Recorder reply: {message}",
            "Next:",
            f"  Inspect last status: {CONTROL_SCRIPT} status",
            f"  Start new recording: {CONTROL_SCRIPT} start",
        ]
    )


def wait_for_first_frame(node: Node, timeout_sec: float, poll_interval_sec: float) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    while time.time() <= deadline:
        response = call_trigger(node, RECORDING_STATUS_SERVICE, timeout_sec=max(poll_interval_sec, 1.0))
        payload = parse_status_payload(response.message)
        if payload.get("active") and int(payload.get("frame_count", 0)) > 0:
            return payload
        time.sleep(poll_interval_sec)
    raise RuntimeError(f"recording started but no frames arrived within {timeout_sec:.1f}s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Control SO101 leader recording services.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Start recording and optionally wait for first frame.")
    start_parser.add_argument("--timeout-sec", type=float, default=8.0)
    start_parser.add_argument("--poll-interval-sec", type=float, default=0.25)
    start_parser.add_argument("--no-wait-first-frame", action="store_true")
    start_parser.add_argument("--json", action="store_true")

    stop_parser = subparsers.add_parser("stop", help="Stop recording.")
    stop_parser.add_argument("--timeout-sec", type=float, default=8.0)
    stop_parser.add_argument("--json", action="store_true")

    status_parser = subparsers.add_parser("status", help="Query current recording status.")
    status_parser.add_argument("--timeout-sec", type=float, default=5.0)
    status_parser.add_argument("--json", action="store_true")

    watch_parser = subparsers.add_parser("watch", help="Continuously print recording status until Ctrl+C.")
    watch_parser.add_argument("--timeout-sec", type=float, default=5.0)
    watch_parser.add_argument("--interval-sec", type=float, default=1.0)
    watch_parser.add_argument("--json", action="store_true")

    return parser


def print_watch_payload(payload: dict[str, Any], as_json: bool) -> None:
    stamp = datetime.now().astimezone().strftime("%H:%M:%S")
    if as_json:
        print(
            json.dumps(
                {
                    "observed_at": stamp,
                    "status": payload,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"[{stamp}]")
        print(format_status_text(payload))
        print("")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    rclpy.init()
    node = Node("leader_recording_ctl")
    try:
        if args.command == "start":
            response = call_trigger(node, START_RECORDING_SERVICE, args.timeout_sec)
            if not response.success:
                if args.json:
                    print(json.dumps({"success": False, "message": response.message}, ensure_ascii=False))
                else:
                    print(response.message)
                return 1

            result: dict[str, Any] = {"success": True, "message": response.message}
            if not args.no_wait_first_frame:
                payload = wait_for_first_frame(node, args.timeout_sec, args.poll_interval_sec)
                result["status"] = payload

            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(format_start_text(response.message, result.get("status")))
            return 0

        if args.command == "stop":
            response = call_trigger(node, STOP_RECORDING_SERVICE, args.timeout_sec)
            if args.json:
                print(
                    json.dumps(
                        {"success": bool(response.success), "message": response.message},
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                print(format_stop_text(response.message))
            return 0 if response.success else 1

        if args.command == "status":
            response = call_trigger(node, RECORDING_STATUS_SERVICE, args.timeout_sec)
            payload = parse_status_payload(response.message)
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(format_status_text(payload))
            return 0

        print("Watching recording status. Press Ctrl+C to stop watching.")
        try:
            while True:
                response = call_trigger(node, RECORDING_STATUS_SERVICE, args.timeout_sec)
                payload = parse_status_payload(response.message)
                print_watch_payload(payload, args.json)
                time.sleep(max(args.interval_sec, 0.2))
        except KeyboardInterrupt:
            print("Stopped watching.")
            return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
