#!/usr/bin/env python3
"""Simple detection publisher for integration tests."""

import json
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class MockYoloNode(Node):
    def __init__(self) -> None:
        super().__init__("mock_yolo_node")
        self.declare_parameter("period_sec", 1.0)
        self.declare_parameter("categories", ["red", "blue"])
        self._period = float(self.get_parameter("period_sec").value)
        self._categories = list(self.get_parameter("categories").value)
        if not self._categories:
            self._categories = ["red"]
        self._idx = 0
        self._pub = self.create_publisher(String, "/detections", 10)
        self._timer = self.create_timer(self._period, self._on_timer)
        self.get_logger().info(f"Mock YOLO ready: categories={self._categories}")

    def _on_timer(self):
        cat = self._categories[self._idx % len(self._categories)]
        self._idx += 1
        payload = {
            "source": "mock_yolo",
            "mock": True,
            "category": cat,
            "confidence": 0.90,
            "bbox": [160, 120, 80, 80],
            "ts": int(time.time() * 1000),
        }
        self._pub.publish(String(data=json.dumps(payload, ensure_ascii=False)))


def main():
    rclpy.init()
    node = MockYoloNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
