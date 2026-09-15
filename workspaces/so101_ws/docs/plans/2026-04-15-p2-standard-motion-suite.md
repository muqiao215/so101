# SO101 P2 Standard Motion Suite And Acceptance

更新时间：2026-04-15

## 1. 目的

把 `P2` 从“手动看起来差不多”变成“可重复、可记录、可追溯”的验收流程。

本文件只定义三件事：

1. 标准动作集
2. 验收判定口径
3. 记录模板

## 2. 适用范围

- `P2` 真机镜像验收（leader 实物在线）
- `P2` 离线镜像验收（使用历史 `leader-recording-*.jsonl` replay）

## 3. 前置条件

最小前置：

- `so101_bringup` 可正常 launch
- `leader_joint_state_mirror` 可起
- `robot_state_publisher` 可起
- RViz 可起（离线验收可选）

真机路径额外前置：

- `P0` 已完成并有有效标定结果
- `/leader/joint_states` 可稳定输出

## 4. 标准动作集

以下动作顺序固定。每次 `P2` 验收都按同一顺序执行。

### `S0` 静态基线

- 在 `home` 附近静止 `5s`
- 观察模型是否稳定，无抖动/跳变

### `S1` 单关节正负向动作（逐轴）

每个关节执行：

1. 从基线位正向小幅动作
2. 回到基线位
3. 反向小幅动作
4. 回到基线位

建议幅度（近似）：

- `shoulder_pan`: `±0.20 rad`
- `shoulder_lift`: `±0.20 rad`
- `elbow_flex`: `±0.20 rad`
- `wrist_flex`: `±0.20 rad`
- `wrist_roll`: `±0.25 rad`
- `gripper`: `±0.30 rad`

建议节奏：

- 每个动作保持 `1.0s ~ 1.5s`
- 相邻动作之间留 `0.5s`

### `S2` 双关节组合动作

固定三组：

1. `shoulder_pan + elbow_flex` 同向
2. `shoulder_lift + wrist_flex` 反向
3. `wrist_roll + gripper` 同向

每组执行：

1. 组合动作进入目标姿态
2. 保持 `1.5s`
3. 回到基线位

### `S3` 回零闭环

执行“离开基线 -> 中间姿态 -> 基线”一轮：

1. 从 `home` 附近离开到中间姿态
2. 保持 `2s`
3. 返回 `home` 附近
4. 再静止 `3s`

## 5. 判定口径

### 必过项

1. `joint mapping` 一致
2. 方向一致（正向动作在模型中不反向）
3. 单关节动作时无明显串轴联动
4. 回零后姿态理解一致
5. 全流程无持续抖动、断裂、突跳

### 失败项（任一命中即本轮失败）

1. 任一关节出现稳定反向
2. 任一关节映射到错误关节
3. 回零后存在明显零位偏置
4. 动作序列中出现不可解释的大跳变

## 6. 执行命令口径

### 真机验收

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch so101_bringup leader_rviz_mirror.launch.py port:=/dev/ttyUSB0
```

### 离线验收（无实物）

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch so101_bringup leader_rviz_replay.launch.py \
  input_path:=/home/muqiao/dev/ros2/workspaces/so101_ws/docs/generated/leader-recordings/leader-recording-20260409-113201.jsonl \
  use_rviz:=true \
  rate_scale:=1.0 \
  loop:=true
```

## 7. 验收记录模板

建议每轮保存一份记录，命名：

- `docs/evidence/p2-motion-suite-<YYYYMMDD-HHMMSS>.md`

模板：

```md
# P2 Motion Suite Record

- date:
- operator:
- mode: real | offline_replay
- input_source:
- launch_command:

## S0 Static Baseline
- pass:
- notes:

## S1 Single Joint
- shoulder_pan: mapping_pass / direction_pass / coupling_pass
- shoulder_lift: mapping_pass / direction_pass / coupling_pass
- elbow_flex: mapping_pass / direction_pass / coupling_pass
- wrist_flex: mapping_pass / direction_pass / coupling_pass
- wrist_roll: mapping_pass / direction_pass / coupling_pass
- gripper: mapping_pass / direction_pass / coupling_pass

## S2 Joint Combination
- combo_1 (shoulder_pan + elbow_flex):
- combo_2 (shoulder_lift + wrist_flex):
- combo_3 (wrist_roll + gripper):

## S3 Return To Home
- pass:
- notes:

## Result
- final_result: pass | fail
- blocker_type:
- next_action:
```

## 8. 结论约束

`P2` 通过条件：

1. 本文动作集完整执行
2. 必过项全部通过
3. 验收记录已落地并可追溯

若只执行了“随手动作”或缺失记录，不能标记 `P2` 通过。
