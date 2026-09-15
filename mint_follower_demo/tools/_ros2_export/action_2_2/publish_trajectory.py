#!/usr/bin/env python3
# 自动生成：读取同目录 trajectory.json，整段发布到 /joint_trajectory_controller/joint_trajectory。
# 用法：先 source ROS2 环境，再 python3 此脚本。
import json, sys
from pathlib import Path
import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

def main():
    data = json.loads(Path('/home/muqiao/桌面/dev/ros2/projects/so101-win7-follower-demo/mint_follower_demo/tools/_ros2_export/action_2_2/trajectory.json').read_text(encoding='utf-8'))
    rclpy.init()
    node = Node('mint_traj_publisher')
    pub = node.create_publisher(JointTrajectory, '/joint_trajectory_controller/joint_trajectory', 10)
    msg = JointTrajectory()
    msg.joint_names = list(data['joint_names'])
    for p in data['points']:
        pt = JointTrajectoryPoint()
        pt.positions = [float(x) for x in p['positions']]
        t = float(p['time_from_start_sec'])
        ns = int(round(t * 1e9))
        pt.time_from_start = Duration(sec=ns // 1000000000, nanosec=ns % 1000000000)
        msg.points.append(pt)
    # 等订阅者就绪
    node.get_logger().info('publishing %d points to %s' % (len(msg.points), '/joint_trajectory_controller/joint_trajectory'))
    import time
    time.sleep(0.5)
    pub.publish(msg)
    time.sleep(0.5)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
