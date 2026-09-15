# SO101 Leader Input Closure Weekly Execution

更新时间：2026-04-14

## 1. 目标

本周不直接开启 `EP-001/EP-002/EP-003`。

本周唯一目标是把 `P0/P1/P2` 变成可执行、可判定、可留证据的输入可信度收口任务：

1. `P0` leader 标定复核
2. `P1` `/leader/joint_states` 连续稳定复测
3. `P2` RViz / 虚拟模型镜像联动验收

只有 `P0/P1/P2` 全部通过，才进入 episode 阶段。

## 2. 执行顺序

按这个顺序做，不要跳：

1. 先跑 `P0`
2. `P0` 过后再跑 `P1`
3. `P1` 过后再跑 `P2`
4. `P0/P1/P2` 全过后，更新 `docs/任务清单.md` / `docs/进度日志.md`
5. 然后才允许开启 `EP-001`

## 3. 环境前提

默认工作区：

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
```

默认 leader 串口：

```bash
/dev/ttyUSB0
```

建议先确认工作区已构建：

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 pkg prefix so101_bringup
```

判定：

- 若 `ros2 pkg prefix so101_bringup` 成功返回安装路径，继续执行
- 若失败，先执行：

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select so101_bringup
source install/setup.bash
```

## 4. 本周执行清单

### `P0` leader 标定复核

#### 目标

- 完成一轮有效的 leader 标定
- 重新启动 bridge 后，`/leader/joint_states` 能稳定输出
- 不出现明显方向翻转、零位漂移、姿态一动就错位

#### 执行命令

终端 1：执行标定

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
bash tools/hardware/run_calibrate_so101_leader.sh /dev/ttyUSB0
```

终端 2：标定完成后，启动录制会话但先不自动录制

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
bash tools/hardware/run_leader_recording_session.sh /dev/ttyUSB0
```

终端 3：确认 bridge 已经有输出

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 topic echo --once /leader/joint_states
```

#### 通过标准

- 标定过程完整结束，无脚本异常退出
- `ros2 topic echo --once /leader/joint_states` 能收到一帧合法消息
- 关节名数量和顺序稳定，不是空消息
- 手掰 leader 小范围动作时，重复执行 `ros2 topic echo --once /leader/joint_states`，关节值会变化且变化方向符合预期

#### 失败信号

- 标定脚本报错或中断
- `/leader/joint_states` 无输出
- 输出为空、关节数量不对、顺序前后变化
- 不动 leader 时数值明显漂移
- 轻微动作却出现大幅突变

#### 证据

- 终端输出记录
- `docs/进度日志.md` 中写明：
  - 使用的串口
  - 标定是否成功
  - `/leader/joint_states` 是否恢复
  - 是否存在漂移 / 翻转 / 零位异常

### `P1` `/leader/joint_states` 连续稳定复测

#### 目标

- 连续录制至少 `60s`
- 用 recorder 的 `.meta.json` 对输入质量做定量判定
- 确认这条输入链已经达到“可作为后续 episode 地基”的水平

#### 执行命令

前提：保持 `run_leader_recording_session.sh` 仍在运行。

开始录制：

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
bash tools/hardware/control_leader_recording.sh start
```

录制期间观察：

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
bash tools/hardware/control_leader_recording.sh watch
```

持续操作 leader 约 `60s` 后停止：

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
bash tools/hardware/control_leader_recording.sh stop
```

查看最近一份 metadata：

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
ls -1t docs/generated/leader-recordings/*.meta.json | head -n 1
python3 -m json.tool "$(ls -1t docs/generated/leader-recordings/*.meta.json | head -n 1)"
```

#### 通过标准

硬门槛：

- `duration_sec >= 60`
- `frame_count > 0`
- `invalid_frame_count == 0`
- `joint_name_mismatch_count == 0`
- `non_monotonic_stamp_count == 0`

建议门槛：

- `sample_rate_hz` 稳定在本轮设备可接受范围，且不出现明显异常低值
- `warnings` 为空或仅包含可解释的单项轻微提示；若出现 `invalid_frames_detected` / `joint_name_mismatch_detected` / `non_monotonic_stamps_detected`，本轮直接不通过

#### 失败信号

- 录制不到 `60s`
- `.meta.json` 中任何一个异常计数非零
- `sample_rate_hz` 明显异常，且无法解释
- `warnings` 提示输入质量有问题

#### 证据

- `docs/generated/leader-recordings/*.jsonl`
- `docs/generated/leader-recordings/*.meta.json`
- `docs/进度日志.md` 中写明：
  - 录制文件名
  - 时长
  - 帧数
  - 采样率
  - 三个异常计数
  - 是否判定通过

### `P2` RViz / 虚拟模型镜像联动验收

#### 目标

- 验证 leader 输入映射到虚拟 SO101 后，joint mapping、方向和零位理解是一致的
- 明确“输入到模型”的可信性，而不是只看 topic 在跳

#### 执行命令

终端 1：启动镜像链

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch so101_bringup leader_rviz_mirror.launch.py port:=/dev/ttyUSB0
```

终端 2：如需只看 joint_states，可额外观察

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 topic echo /joint_states
```

#### 验收动作

按固定动作序列人工验收：

1. `home` 附近静止
2. 只动单个关节，逐轴确认
3. 切到中间姿态
4. 再切到另一姿态
5. 返回 `home` 附近

每一步都看三件事：

1. 模型是否跟着动
2. 动的是不是对应关节
3. 方向和预期是否一致

#### 通过标准

- 虚拟模型连续跟随，不出现明显卡死或乱跳
- 单轴动作时，对应 joint mapping 正确
- 方向一致，无反向联动
- 回到 `home` 附近时，整体姿态理解一致

#### 失败信号

- 某个关节动了，但模型上是别的关节在动
- 同方向手掰，模型反向运动
- 返回 `home` 后模型姿态明显不对
- 持续存在跳变、抖动、断裂

#### 证据

- `docs/进度日志.md` 中写明：
  - 验收日期
  - 验收动作序列
  - joint mapping 是否一致
  - 方向是否一致
  - 零位理解是否一致
  - 是否通过
- 若现场方便，补一张 RViz 截图或一段短录屏到 `docs/evidence/`

## 5. 本周收口判定

以下条件全部满足，才允许进入 episode 阶段：

1. `P0` 通过
2. `P1` 通过
3. `P2` 通过
4. `docs/任务清单.md` 已补证据与状态判断
5. `docs/进度日志.md` 已记录本轮命令与结果

如果只做到 `P0` 或 `P0 + P1`，结论只能写成：

- 输入链部分可信
- 但还未完成 episode 阶段准入

不能提前把 `EP-001` 标为开始。

## 6. 完成后的下一步

只有在本文件对应的 `P0/P1/P2` 全部通过后，才进入：

- `docs/plans/2026-04-09-episode-closure.md`

进入顺序固定为：

1. `EP-001` 连续轨迹 episode 录制
2. `EP-002` replay validator
3. `EP-003` episode dataset schema
