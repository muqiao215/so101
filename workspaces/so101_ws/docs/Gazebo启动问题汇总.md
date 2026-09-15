# Gazebo 启动问题汇总（so101_ws）

- `pkill` 一次只能接收一个匹配模式。
- 解决：

  ```bash
  pkill -9 -x gzserver || true
  pkill -9 -x gzclient || true
  ```

## 3. `gzserver exit code 255`

- 现象：
  - 启动日志中 `gzserver ... process has died ... exit code 255`。
- 根因（主要）：
  - 端口 `11345` 被旧 `gzserver` 占用，新进程启动失败。
- 解决：
  - 启动前清理旧进程（已写入 `scene.launch.py` 自动执行）。
  - 手动兜底：

  ```bash
  pkill -9 -x gzserver || true
  pkill -9 -x gzclient || true
  ```

## 4. `gzclient` 打开后闪退（`Assertion 'px != 0' failed`）

- 现象：
  - 页面弹出后立刻关闭，日志有 `boost::shared_ptr ... Camera ... px != 0`。
- 原因：
  - 虚拟机图形/OpenGL 环境不稳定，Gazebo GUI 渲染层崩溃。
  - GUI 模式使用软件渲染：

  ```bash
  export LIBGL_ALWAYS_SOFTWARE=1
  export MESA_GL_VERSION_OVERRIDE=3.3
  ros2 launch so101_gazebo scene.launch.py use_gzclient:=true software_rendering:=true
  ```

## 5. `libcurl: (35)` 网络提示

- 现象：
  - `gzclient` 日志出现 `libcurl: (35) ... unexpected eof while reading`。
- 原因：
  - Gazebo 在线模型资源访问失败（网络/证书/代理环境）。
- 影响：
  - 通常不是致命错误，不影响本地 world 与本地模型运行。
- 处理：
  - 已在启动中禁用在线模型库环境变量，减少卡顿与干扰日志。

## 6. `/clock` 检查时报 `!rclpy.ok()`

- 现象：
  - `ros2 topic echo /clock` 报 `xmlrpc.client.Fault ... !rclpy.ok()`。
- 常见原因：
  - 终端上下文异常或刚经历异常中断，ROS2 CLI 状态不干净。
- 解决：
  - 关闭该终端后重开，重新 `source` 环境，再执行 `echo`。
  - 并确认 Gazebo 服务端确实在运行

```

## 当前推荐启动方式（需要 GUI）

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export LIBGL_ALWAYS_SOFTWARE=1
export MESA_GL_VERSION_OVERRIDE=3.3
ros2 launch so101_gazebo scene.launch.py use_gzclient:=true software_rendering:=true
```

## 结论

- 你的仿真主链路（`gzserver + spawn_entity + /clock`）已经可用。
- 目前不稳定点主要在虚拟机 GUI 渲染层，不影响后续推进 `ros2_control` 和 MoveIt2 任务。
