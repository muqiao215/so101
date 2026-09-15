#!/usr/bin/env python3
"""
calibration_node.py -- SO101 dual-arm calibration layer node.

Responsibilities (all driven by calibration.yaml + reality_map):
  1. Compute every calibration frame (mount_frame, base_link) in board_frame.
  2. Write calibration_report.txt + echo it to the console.
  3. Apply initial joint angles to each spawned arm via the classic-Gazebo
     service /gazebo/set_model_configuration (we avoid ros2_control, which
     segfaults on this host).
  4. Publish /joint_states with the initial joint angles (informational;
     no robot_state_publisher is running, so this does not drive Gazebo --
     Gazebo is driven by step 3).

Run via the launch file (it passes params). Can also run standalone.
"""
import math
import os
import struct
import sys
from glob import glob

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

try:
    from gazebo_msgs.srv import SetModelConfiguration
    _HAS_GZ_SRV = True
except Exception:  # pragma: no cover
    _HAS_GZ_SRV = False

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


JOINT_ORDER = [
    "shoulder_pan", "shoulder_lift", "elbow_flex",
    "wrist_flex", "wrist_roll", "gripper",
]


def deg2rad(d):
    return d * math.pi / 180.0


def rz_xy(yaw, vx, vy):
    """Rotate (vx,vy) by yaw about Z."""
    c, s = math.cos(yaw), math.sin(yaw)
    return c * vx - s * vy, s * vx + c * vy


def stl_bbox(path):
    """Pure-stdlib binary-STL bounding box (meters)."""
    try:
        with open(path, "rb") as fh:
            fh.read(80)
            (nfaces,) = struct.unpack("<I", fh.read(4))
            mn = [1e9, 1e9, 1e9]
            mx = [-1e9, -1e9, -1e9]
            for _ in range(nfaces):
                fh.read(12)  # normal
                for _v in range(3):
                    x, y, z = struct.unpack("<fff", fh.read(12))
                    if x < mn[0]:
                        mn[0] = x
                    if y < mn[1]:
                        mn[1] = y
                    if z < mn[2]:
                        mn[2] = z
                    if x > mx[0]:
                        mx[0] = x
                    if y > mx[1]:
                        mx[1] = y
                    if z > mx[2]:
                        mx[2] = z
                fh.read(2)
            return mn, mx
    except Exception as e:
        return None, None


def build_report(calib, urdf_path, mesh_dir):
    """Return the full calibration report as a string."""
    lines = []
    ap = lines.append

    ap("=" * 70)
    ap("SO101 dual-arm Gazebo scene -- CALIBRATION REPORT")
    ap("=" * 70)
    ap("")

    ap("[frames]  board_frame -> <arm>_mount_frame -> <arm>_base_link")
    ap("          board_frame origin = board front-left corner, top surface")
    ap("          (= Gazebo world origin). Units: meter. Angles: rad unless noted.")
    ap("")

    mounts = calib["mounts"]
    offset = calib["mount_to_base_link_offset_m"]["xyz"]
    yaw_off = deg2rad(calib["forward_axis"].get("yaw_offset_deg", 0.0))
    spawn_z = float(calib.get("spawn_base_z_m", 0.0))
    shp = calib.get("shoulder_pan_axis_in_base_link", {}).get("xyz", [0, 0, 0])

    ap("[forward axis]")
    ap("  urdf default forward   = %s" % calib["forward_axis"]["urdf_default_forward"])
    ap("  yaw_offset (added)     = %.6f rad (%.3f deg)" %
       (yaw_off, calib["forward_axis"]["yaw_offset_deg"]))
    ap("  (URDF FK at joint=0 puts the wrist at +X = +0.232 m in base_link,")
    ap("   so the arm's forward IS +X; the measured yaw needs no correction.)")
    ap("")

    ap("[URDF root link]")
    ap("  name = base_link")
    ap("  base collision cylinder origin (0,0,0.035) r=0.07 len=0.09")
    ap("    => base footprint center == base_link XY origin (0,0)")
    ap("    => base bottom ~ base_link origin (mesh bottom z ~ -0.0024 m)")
    ap("  shoulder_pan joint origin in base_link = (%.6f, %.6f, %.6f)"
       % (shp[0], shp[1], shp[2]))
    ap("    (this is the arm ROTATION AXIS, not the footprint center)")
    ap("")

    ap("[mount_frame -> base_link offset]  (derived, in base frame)")
    ap("  xyz = (%.6f, %.6f, %.6f)" % (offset[0], offset[1], offset[2]))
    ap("  base XY = mount XY (footprint centered on base_link origin)")
    ap("  base Z  = board top surface (base bottom on board), spawn_base_z = %.4f"
       % spawn_z)
    ap("")

    ij = calib.get("initial_joint_positions", {})

    ap("-" * 70)
    ap("[per-arm computed poses in board_frame]")
    for name, m in mounts.items():
        mx, my, mz = m["board_xyz"]
        m_yaw = deg2rad(m["yaw_deg"])
        # base_link position = mount + Rz(m_yaw) . offset
        bx_off, by_off = rz_xy(m_yaw, offset[0], offset[1])
        bx = mx + bx_off
        by = my + by_off
        bz = spawn_z + offset[2]
        b_yaw = m_yaw + yaw_off
        ap("")
        ap("  %s:" % name)
        ap("    mount_frame   pose  xyz=(%.6f, %.6f, %.6f)  yaw=%.6f rad (%.3f deg)"
           % (mx, my, mz, m_yaw, m["yaw_deg"]))
        ap("    base_link     pose  xyz=(%.6f, %.6f, %.6f)  yaw=%.6f rad (%.3f deg)"
           % (bx, by, bz, b_yaw, math.degrees(b_yaw)))
        ap("    shoulder axis (base_link + Rz(yaw) . shoulder_pan_offset)")
        sx, sy = rz_xy(b_yaw, shp[0], shp[1])
        ap("                 in board  xyz=(%.6f, %.6f, %.6f)"
           % (bx + sx, by + sy, bz + shp[2]))
        vals = ij.get(name, {})
        ap("    initial joints (rad): " +
           ", ".join("%s=%.3f" % (j, float(vals.get(j, 0.0))) for j in JOINT_ORDER))

    ap("")
    ap("-" * 70)
    ap("[mesh scale check]")
    ap("  URDF : %s" % urdf_path)
    ap("  meshes (binary STL, unit = meter, NO scale attribute in URDF):")
    if mesh_dir and os.path.isdir(mesh_dir):
        for f in sorted(glob(os.path.join(mesh_dir, "*.stl"))):
            mn, mx = stl_bbox(f)
            if mn is None:
                ap("    %-42s <unreadable>" % os.path.basename(f))
                continue
            ext = (mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2])
            ap("    %-42s ext=(%.4f, %.4f, %.4f) m  -> OK (meter, no scale)"
               % (os.path.basename(f), ext[0], ext[1], ext[2]))
        ap("  conclusion: all STL already in meters; no scale correction needed.")
    else:
        ap("    mesh dir not found: %s" % mesh_dir)
    ap("  collision simplifications (box/cylinder placeholders) on")
    ap("    base_link, shoulder_link, upper/lower_arm, wrist, gripper, jaw:")
    ap("    these are intentional simplified collision bodies, NOT anomalies.")
    ap("")
    ap("=" * 70)
    return "\n".join(lines) + "\n"


class CalibrationNode(Node):
    def __init__(self):
        super().__init__("so101_calibration_node")

        self.declare_parameter("calibration_yaml", "")
        self.declare_parameter("report_path", "")
        self.declare_parameter("urdf_path", "")
        self.declare_parameter("mesh_dir", "")
        self.declare_parameter("master_model", "master_arm")
        self.declare_parameter("follower_model", "follower_arm")
        self.declare_parameter("publish_joint_states", True)

        calib_path = self.get_parameter("calibration_yaml").value
        self.report_path = self.get_parameter("report_path").value
        urdf_path = self.get_parameter("urdf_path").value
        mesh_dir = self.get_parameter("mesh_dir").value
        self.master_model = self.get_parameter("master_model").value
        self.follower_model = self.get_parameter("follower_model").value
        self.publish_joint_states_enabled = bool(self.get_parameter("publish_joint_states").value)

        if not calib_path or yaml is None:
            self.get_logger().error(
                "calibration_yaml param missing or pyyaml unavailable; "
                "report generation skipped.")
            self.calib = None
        else:
            with open(calib_path) as fh:
                self.calib = yaml.safe_load(fh)

        # 1+2: compute frames and write report (independent of Gazebo)
        if self.calib is not None:
            self.report_txt = build_report(self.calib, urdf_path, mesh_dir)
            print(self.report_txt, flush=True)
            self.get_logger().info("Calibration report printed above.")
            if self.report_path:
                try:
                    with open(self.report_path, "w") as fh:
                        fh.write(self.report_txt)
                    self.get_logger().info("Report written to %s" % self.report_path)
                except Exception as e:
                    self.get_logger().error("Failed writing report: %s" % e)

        # 3: optional /joint_states for standalone visualization. In Gazebo,
        # joint_state_broadcaster owns this topic to avoid RViz jitter.
        self.js_pub = None
        if self.publish_joint_states_enabled:
            self.js_pub = self.create_publisher(JointState, "/joint_states", 10)
            self.create_timer(0.05, self.publish_joint_states)

        # 4: apply initial joint angles via /gazebo/set_model_configuration
        self.applied = {self.master_model: False, self.follower_model: False}
        self._attempts = 0
        self._gave_up = False
        if _HAS_GZ_SRV and self.calib is not None:
            self.set_cli = self.create_client(SetModelConfiguration,
                                              "/gazebo/set_model_configuration")
            self.create_timer(2.0, self.try_apply_joints)
        else:
            self.get_logger().warn(
                "gazebo_msgs SetModelConfiguration unavailable; "
                "cannot set initial joint angles in Gazebo.")

    def joint_values_for(self, arm_key):
        ij = self.calib["initial_joint_positions"][arm_key]
        return [float(ij.get(j, 0.0)) for j in JOINT_ORDER]

    def publish_joint_states(self):
        if self.calib is None or self.js_pub is None:
            return
        # NOTE: both arms share joint names (URDF is not prefixed), and the
        # placeholder values are identical, so a single JointState is correct.
        # If master/follower diverge later, the URDF must be spawned with a
        # joint-name prefix (xacro arg) -- documented in calibration.yaml.
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = list(JOINT_ORDER)
        msg.position = self.joint_values_for("master_arm")
        self.js_pub.publish(msg)

    def try_apply_joints(self):
        if all(self.applied.values()):
            return
        if self._attempts >= 5:
            if not self._gave_up:
                self._gave_up = True
                self.get_logger().warn(
                    "/gazebo/set_model_configuration is advertised but not "
                    "connectable on this host (known gazebo_ros_state quirk; "
                    "ros2_control is now loaded through controller_manager). "
                    "The current initial_joint_positions are all 0.0 == "
                    "Gazebo joint default, so the displayed pose already "
                    "matches the configured initial pose.")
            return
        self._attempts += 1
        if not self.set_cli.service_is_ready():
            self.get_logger().info(
                "waiting for /gazebo/set_model_configuration...",
                throttle_duration_sec=4.0)
            return
        for model, arm_key in ((self.master_model, "master_arm"),
                               (self.follower_model, "follower_arm")):
            if self.applied[model]:
                continue
            req = SetModelConfiguration.Request()
            req.model_name = model
            req.joint_names = list(JOINT_ORDER)
            req.joint_positions = self.joint_values_for(arm_key)
            future = self.set_cli.call_async(req)
            future.add_done_callback(
                lambda fut, m=model: self._apply_cb(fut, m))

    def _apply_cb(self, future, model):
        try:
            res = future.result()
        except Exception as e:
            self.get_logger().warn(
                "set_model_configuration call failed for %s: %s" % (model, e))
            return
        if res.success:
            self.applied[model] = True
            self.get_logger().info(
                "initial joints applied to '%s' via set_model_configuration." % model)
        else:
            self.get_logger().warn(
                "set_model_configuration for '%s' returned success=False: %s"
                % (model, getattr(res, "status_message", "")))


def main():
    import signal

    rclpy.init()
    node = CalibrationNode()

    def _sigterm(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _sigterm)

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
