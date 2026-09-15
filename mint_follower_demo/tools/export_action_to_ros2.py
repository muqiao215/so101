#!/usr/bin/env python3
"""把已发布的 mint 产品动作导出为 ROS2 仿真可回放的命令。

背景：
- mint 侧（action_templates.json, schema=so101_mint_action_templates.v3）
  使用官方 LeRobot SO101 当前单位:
  前 5 关节 = RANGE_M100_100，gripper = RANGE_0_100。
- ros2 侧（task_executor.py 订阅 /mes_task_cmd）：
  * 整条轨迹通过 /joint_trajectory_controller/joint_trajectory 下发，
    所有 6 个关节(含 gripper)在仿真里都是「弧度」。
  * /mes_task_cmd 的 JSON 只接受两类输入：
      (A) actionTemplateId 指向节点启动时加载好的模板(模板=多帧序列)；
      (B) actionTemplateId == "preview_pose" 且 params.previewPose 给出 6 维单点。
    换句话说，/mes_task_cmd 不能在运行时直接吞下任意多点轨迹。
  * 因此本转换器同时产出：
      - 单点 preview 命令(走 /mes_task_cmd，验证链路用)；
      - 完整多点 JointTrajectory YAML/JSON(直接 pub 到轨迹控制器，整段回放)；
      - 注入用 waypoints 插件 YAML(启动时喂给 task_executor，走模板回放)。

单位换算：
- mint/action 数据只能是官方 SO101 单位。
- ROS2/RViz/Gazebo 边界使用 URDF radians。
- 转换只通过 so101_official_to_urdf.yaml 的 sign/scale/offset 完成。
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import yaml


JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
ARM_JOINTS = JOINT_NAMES[:-1]
GRIPPER_INDEX = 5
GRIPPER_JOINT = JOINT_NAMES[GRIPPER_INDEX]

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
DEFAULT_URDF_MAP = Path(__file__).resolve().parents[2] / "so101_gz_scene/so101_official_to_urdf.yaml"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_action(product_actions: dict, selector: str) -> dict:
    """按 id 或 name 找一条产品动作；找不到就报错。"""
    actions = product_actions.get("actions", [])
    for action in actions:
        if str(action.get("id")) == selector or action.get("name") == selector:
            return action
    # 模糊：name 包含
    for action in actions:
        if selector in str(action.get("name", "")):
            return action
    available = ", ".join("%s(%s)" % (a.get("id"), a.get("name")) for a in actions)
    raise SystemExit("找不到动作 %r。可用：%s" % (selector, available))


def resolve_frame_sequence(templates_doc: dict, execution_template: str) -> Tuple[List[str], List[List[float]]]:
    """根据 execution_template 取帧名序列与对应的 6 维坐标列表。"""
    templates = templates_doc.get("templates", {})
    waypoints = templates_doc.get("waypoints", {})
    if execution_template not in templates:
        raise SystemExit("execution_template %r 不在 templates 里" % execution_template)
    frame_names = templates[execution_template]
    if not isinstance(frame_names, list) or not frame_names:
        raise SystemExit("execution_template %r 帧序列为空" % execution_template)
    frames: List[List[float]] = []
    for name in frame_names:
        wp = waypoints.get(name)
        if not isinstance(wp, list) or len(wp) != len(JOINT_NAMES):
            raise SystemExit("帧 %r 不是 %d 维列表：%r" % (name, len(JOINT_NAMES), wp))
        frames.append([float(v) for v in wp])
    return list(frame_names), frames


def default_frame_delay(templates_doc: dict, execution_template: str) -> float:
    delays = templates_doc.get("template_delays", {})
    value = delays.get(execution_template)
    try:
        return float(value) if value is not None else 0.08
    except (TypeError, ValueError):
        return 0.08


def convert_frame(official_frame: Sequence[float], urdf_map: dict) -> List[float]:
    source_by_name = {name: float(official_frame[idx]) for idx, name in enumerate(JOINT_NAMES)}
    out = []
    mapping = urdf_map.get("mapping", {})
    limits = urdf_map.get("limits", {})
    for target in urdf_map.get("joint_order", JOINT_NAMES):
        cfg = mapping.get(target, {})
        source = str(cfg.get("source", target))
        sign = float(cfg.get("sign", 1.0))
        scale = float(cfg.get("scale", 1.0))
        offset = float(cfg.get("offset", 0.0))
        if source not in source_by_name:
            raise SystemExit("URDF map source %r for target %r not found" % (source, target))
        value = sign * scale * source_by_name[source] + offset
        if target in limits:
            low, high = limits[target]
            value = min(max(value, float(low)), float(high))
        out.append(float(value))
    return out


def value_range(frames: Sequence[Sequence[float]]) -> List[Tuple[float, float]]:
    cols = list(zip(*frames))
    return [(min(c), max(c)) for c in cols]


def fmt_array(values: Sequence[float], precision: int = 6) -> str:
    return "[" + ", ".join(("%.*f" % (precision, v)) for v in values) + "]"


def build_trajectory_points(frames_ros: Sequence[Sequence[float]], frame_delay: float) -> List[dict]:
    """按累积时间生成 JointTrajectory 点(ros2 侧 create_multi_point_trajectory_message 的格式)。"""
    points = []
    for idx, positions in enumerate(frames_ros):
        t = idx * frame_delay
        points.append({"positions": [float(v) for v in positions], "time_from_start_sec": round(t, 6)})
    return points


def duration_to_sec_nanosec(time_from_start_sec: float) -> dict:
    total_ns = int(round(time_from_start_sec * 1e9))
    return {"sec": total_ns // 1_000_000_000, "nanosec": total_ns % 1_000_000_000}


def trajectory_to_yaml(joint_names: Sequence[str], points: Sequence[dict]) -> str:
    """生成可直接 ros2 topic pub 的 JointTrajectory YAML。"""
    lines: List[str] = []
    lines.append("joint_names:")
    lines.extend("  - %s" % name for name in joint_names)
    lines.append("points:")
    for p in points:
        t = duration_to_sec_nanosec(float(p["time_from_start_sec"]))
        pos = ", ".join(repr(float(v)) for v in p["positions"])
        lines.append("  - positions: [%s]" % pos)
        lines.append("    time_from_start:")
        lines.append("      sec: %d" % t["sec"])
        lines.append("      nanosec: %d" % t["nanosec"])
    lines.append("")
    return "\n".join(lines)


def trajectory_to_dict(joint_names: Sequence[str], points: Sequence[dict]) -> dict:
    return {"joint_names": list(joint_names), "points": points}


def build_preview_payload(joint_names: Sequence[str], frame_ros: Sequence[float], duration_sec: float,
                          name: str = "preview_pose", request_id: str = "mint-preview") -> dict:
    """单点 /mes_task_cmd 的 JSON 载荷(actionTemplateId=preview_pose)。"""
    return {
        "requestId": request_id,
        "actionTemplateId": "preview_pose",
        "params": {
            "previewPose": {
                "name": name,
                "positions": [float(v) for v in frame_ros],
                "durationSec": round(max(duration_sec, 0.1), 6),
            }
        },
    }


def build_plugin_yaml(joint_names: Sequence[str], frame_names: Sequence[str], frames_ros: Sequence[Sequence[float]],
                      template_id: str, frame_delay: float) -> str:
    """生成可注入 task_executor waypoints_file 的插件 YAML(waypoints + action_templates)。

    注入后用 actionTemplateId=<template_id> 走 /mes_task_cmd 即可整段回放。
    """
    lines: List[str] = []
    lines.append("# 自动生成：注入到 task_executor 的 waypoints_file 即可用模板回放")
    lines.append("joint_names:")
    lines.extend("  - %s" % n for n in joint_names)
    lines.append("units:")
    for n in joint_names:
        lines.append("  %s: rad" % n)
    lines.append("waypoints:")
    for name, frame in zip(frame_names, frames_ros):
        pos = ", ".join(repr(float(v)) for v in frame)
        lines.append("  %s: [%s]" % (name, pos))
    lines.append("action_templates:")
    lines.append("  %s:" % template_id)
    lines.append("    detection_required: false")
    lines.append("    sequence:")
    lines.extend("      - %s" % n for n in frame_names)
    lines.append("template_delays:")
    lines.append("  %s: %.6f" % (template_id, frame_delay))
    lines.append("")
    return "\n".join(lines)


def publish_trajectory_script(topic: str, traj_json_path: str) -> str:
    """生成一个最小 rclpy 发布脚本（多点整段回放最稳，规避 ros2 topic pub 长度限制）。"""
    return (
        "#!/usr/bin/env python3\n"
        "# 自动生成：读取同目录 trajectory.json，整段发布到 %s。\n"
        "# 用法：先 source ROS2 环境，再 python3 此脚本。\n"
        "import json, sys\n"
        "from pathlib import Path\n"
        "import rclpy\n"
        "from rclpy.node import Node\n"
        "from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint\n"
        "from builtin_interfaces.msg import Duration\n"
        "\n"
        "def main():\n"
        "    data = json.loads(Path(%r).read_text(encoding='utf-8'))\n"
        "    rclpy.init()\n"
        "    node = Node('mint_traj_publisher')\n"
        "    pub = node.create_publisher(JointTrajectory, %r, 10)\n"
        "    msg = JointTrajectory()\n"
        "    msg.joint_names = list(data['joint_names'])\n"
        "    for p in data['points']:\n"
        "        pt = JointTrajectoryPoint()\n"
        "        pt.positions = [float(x) for x in p['positions']]\n"
        "        t = float(p['time_from_start_sec'])\n"
        "        ns = int(round(t * 1e9))\n"
        "        pt.time_from_start = Duration(sec=ns // 1000000000, nanosec=ns %% 1000000000)\n"
        "        msg.points.append(pt)\n"
        "    # 等订阅者就绪\n"
        "    node.get_logger().info('publishing %%d points to %%s' %% (len(msg.points), %r))\n"
        "    import time\n"
        "    time.sleep(0.5)\n"
        "    pub.publish(msg)\n"
        "    time.sleep(0.5)\n"
        "    node.destroy_node()\n"
        "    rclpy.shutdown()\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    ) % (topic, str(traj_json_path), topic, topic)


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="把 mint 产品动作导出为 ROS2 仿真回放命令")
    p.add_argument("--action", default=None, help="产品动作的 id 或 name（默认取第一条 released）")
    p.add_argument("--config-dir", default=str(CONFIG_DIR), help="mint config 目录")
    p.add_argument("--urdf-map", default=str(DEFAULT_URDF_MAP),
                   help="官方 SO101 单位到 URDF radians 的 YAML 映射")
    p.add_argument("--out-dir", default=None, help="产物输出目录（默认 tools/_ros2_export/<action_id>）")
    p.add_argument("--step-duration", type=float, default=None,
                   help="帧间隔(秒)，默认用 template_delays，一般 0.08")
    p.add_argument("--stride", type=int, default=1, help="帧抽样步长，>1 可降采样")
    p.add_argument("--max-frames", type=int, default=0, help="最多保留多少帧，0=全部")
    p.add_argument("--preview-frame", type=int, default=0,
                   help="单点 preview 用第几帧(默认第 0 帧，即初始位姿)")
    p.add_argument("--no-write", action="store_true", help="只打印校验，不落盘")
    p.add_argument("--formats", default="all",
                   help="逗号分隔：all/preview/trajectory/plugin/publisher")
    return p.parse_args(argv)


def select_frames(frames: List[List[float]], names: List[str], stride: int, max_frames: int):
    picked_frames = frames[::max(1, stride)]
    picked_names = names[::max(1, stride)]
    if max_frames and max_frames > 0:
        picked_frames = picked_frames[:max_frames]
        picked_names = picked_names[:max_frames]
    return picked_names, picked_frames


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    config_dir = Path(args.config_dir)
    product_actions = load_json(config_dir / "product_actions.json")
    templates_doc = load_json(config_dir / "action_templates.json")
    urdf_map = load_yaml(Path(args.urdf_map))

    # 校验 mint 侧关节顺序
    if templates_doc.get("joint_names") != JOINT_NAMES:
        raise SystemExit("mint joint_names 与预期不一致：%r" % templates_doc.get("joint_names"))

    # 选动作
    if args.action:
        action = resolve_action(product_actions, args.action)
    else:
        released = [a for a in product_actions.get("actions", []) if a.get("status") == "released"]
        if not released:
            released = product_actions.get("actions", [])
        if not released:
            raise SystemExit("product_actions.json 里没有动作")
        action = released[0]
        print("未指定 --action，默认取：%s(%s)" % (action.get("id"), action.get("name")))

    exec_template = action.get("execution_template")
    if not exec_template:
        raise SystemExit("动作 %r 缺 execution_template" % action.get("id"))

    frame_names, frames_mint = resolve_frame_sequence(templates_doc, exec_template)
    frame_delay = args.step_duration if args.step_duration else default_frame_delay(templates_doc, exec_template)

    names_full, frames_full = select_frames(frames_mint, frame_names, args.stride, args.max_frames)

    frames_ros = [convert_frame(f, urdf_map) for f in frames_full]

    # ---- 静态校验打印 ----
    print("=" * 64)
    print("动作: %s | name=%s | status=%s" % (action.get("id"), action.get("name"), action.get("status")))
    print("execution_template: %s" % exec_template)
    print("原始帧数: %d   抽样后帧数: %d   帧间隔: %.4fs" %
          (len(frames_mint), len(frames_ros), frame_delay))
    print("关节顺序(ros2): %s" % JOINT_NAMES)
    print("值域(已转 ros2 弧度，gripper 已映射):")
    rng = value_range(frames_ros)
    for name, (lo, hi) in zip(JOINT_NAMES, rng):
        flag = ""
        if name == GRIPPER_JOINT:
            flag = "  <- official 0..100 via urdf map"
        print("  %-13s [%+.4f, %+.4f]%s" % (name, lo, hi, flag))
    print("首帧(ros2): %s" % fmt_array(frames_ros[0]))
    print("末帧(ros2): %s" % fmt_array(frames_ros[-1]))

    # 合理性提示
    for name, (lo, hi) in zip(JOINT_NAMES, rng):
        if name != GRIPPER_JOINT and (abs(lo) > math.pi or abs(hi) > math.pi):
            print("  ⚠ %s 超出 ±π rad，注意仿真关节限位" % name, file=sys.stderr)
    g_lo, g_hi = rng[GRIPPER_INDEX]
    if g_lo < -0.2 or g_hi > 1.8:
        print("  ⚠ gripper 弧度 [%+.3f,%+.3f] 超出预期范围" % (g_lo, g_hi), file=sys.stderr)

    if args.no_write:
        return 0

    # ---- 落盘 ----
    action_id = str(action.get("id") or "action")
    out_dir = Path(args.out_dir) if args.out_dir else (Path(__file__).resolve().parent / "_ros2_export" / action_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    formats = set(args.formats.split(","))
    want_all = "all" in formats

    traj_points = build_trajectory_points(frames_ros, frame_delay)
    summary: Dict[str, str] = {}

    if want_all or "preview" in formats:
        preview_idx = min(max(args.preview_frame, 0), len(frames_ros) - 1)
        preview = build_preview_payload(JOINT_NAMES, frames_ros[preview_idx],
                                        duration_sec=max(frame_delay * 4, 1.2),
                                        name="%s_frame%03d" % (action_id, preview_idx),
                                        request_id="mint-%s-preview" % action_id)
        preview_path = out_dir / "mes_task_cmd_preview.json"
        write_text(preview_path, json.dumps(preview, ensure_ascii=False, indent=2) + "\n")
        summary["preview_json"] = str(preview_path)
        # 一行 ros2 topic pub（单点，走 /mes_task_cmd）
        data_str = json.dumps(preview, ensure_ascii=False)
        cmd = ('ros2 topic pub --once /mes_task_cmd std_msgs/String "data: \'%s\'"' % data_str)
        summary["preview_pub_cmd"] = cmd

    if want_all or "trajectory" in formats:
        traj_yaml = trajectory_to_yaml(JOINT_NAMES, traj_points)
        traj_json = trajectory_to_dict(JOINT_NAMES, traj_points)
        yaml_path = out_dir / "trajectory.yaml"
        json_path = out_dir / "trajectory.json"
        write_text(yaml_path, traj_yaml)
        write_text(json_path, json.dumps(traj_json, ensure_ascii=False, indent=2) + "\n")
        summary["trajectory_yaml"] = str(yaml_path)
        summary["trajectory_json"] = str(json_path)
        summary["trajectory_pub_cmd"] = (
            'ros2 topic pub --once /joint_trajectory_controller/joint_trajectory '
            'trajectory_msgs/msg/JointTrajectory "$(cat %s)"' % yaml_path
        )

    if want_all or "publisher" in formats:
        script = publish_trajectory_script("/joint_trajectory_controller/joint_trajectory",
                                           str(out_dir / "trajectory.json"))
        script_path = out_dir / "publish_trajectory.py"
        write_text(script_path, script)
        summary["publisher_script"] = str(script_path)

    if want_all or "plugin" in formats:
        plugin_template_id = "mint_%s" % action_id
        plugin_yaml = build_plugin_yaml(JOINT_NAMES, names_full, frames_ros, plugin_template_id, frame_delay)
        plugin_path = out_dir / "waypoints_plugin.yaml"
        write_text(plugin_path, plugin_yaml)
        summary["plugin_yaml"] = str(plugin_path)
        summary["plugin_use_cmd"] = (
            '# 启动 task_executor 时把 waypoints_file 指向本文件，再发：\n'
            'ros2 topic pub --once /mes_task_cmd std_msgs/String '
            '"data: \'{\\"actionTemplateId\\":\\"%s\\"}\'"' % plugin_template_id
        )

    print("=" * 64)
    print("产物目录: %s" % out_dir)
    for key, val in summary.items():
        print("  [%s]" % key)
        print("    %s" % val)
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
