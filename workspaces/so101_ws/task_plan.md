# Task Plan: SO101 Sim Grasp Benchmark Harness

## Goal

建立一个可插拔的“抓取算法接入与评价台架”：把 Gazebo 视觉目标接入抓取候选、规划器或 policy baseline，在 Gazebo 中执行，并用统一 evaluator 输出 reach/contact/enclosure/lift/place 指标和可训练 episode 数据。

## Current Phase

Phase 4

## Phases

### Phase 1: Scope Freeze And Interfaces

- [x] 明确当前纯仿真基础链路已完成：camera -> detector -> `/detections` -> `/vision/targets` -> task executor -> trajectory -> Gazebo joint motion -> overlay。
- [x] 明确下一阶段不是“先训练”，而是“抓取算法接入与评价台架”。
- [x] 固化接口 schema：TargetObject、GraspCandidate、PlanResult、ExecutionTrace、EvaluationResult、EpisodeRecord。
- [x] 将 `GZV-017` 拆成 A/B/C 小任务，写入正式任务清单。
- **Status:** complete

### Phase 2: GZV-017A Target-Driven Reach Baseline

- [x] 新增 target adapter：从 `/vision/targets` 选择目标，输出标准 `target_object`。
- [x] 新增 grasp proposal baseline：生成 top-down 或 front/top 简化 `grasp_candidate`，先只覆盖 reach。
- [x] 新增 motion backend baseline：根据 target xyz 生成目标相关 joint trajectory，证明目标变化会导致动作变化。
- [x] 接入 Gazebo `/joint_trajectory_controller/joint_trajectory`，不绕过现有 ros2_control 执行链。
- [x] smoke 断言：同一场景 red/blue target 会产生不同 trajectory，并且 Gazebo joint motion 朝目标方向变化。
- **Status:** complete

### Phase 3: GZV-017B Grasp/Reach Evaluator

- [x] 实现 evaluator CLI/node，输入 target_object、joint_states、trajectory trace、可选 Gazebo model/link states。
- [x] 第一版只强制 L1 `reach_success = min_distance(gripper_tcp, target_xyz) < threshold`。
- [ ] 指标分层预留：L2 contact、L3 enclosure、L4 lift、L5 place。
- [x] 输出 JSON report：target、candidate、plan、execution、metrics、failure_reason。
- [x] smoke 断言 evaluator report 可复现，不把 reach 误称为 grasp success。
- **Status:** complete

### Phase 4: GZV-017C Episode Recorder Upgrade

- [x] 扩展现有 vision episode/dataset：记录 target_object、grasp_candidates、selected_candidate、trajectory、metrics。
- [x] 输出 `trainable_smoke` 口径 label，不生成 `trainable_real`。
- [x] 更新 viewer/overlay 或 artifact 摘要，让失败原因可见。
- [x] 为后续 LeRobot exporter 保留 action/result 字段。
- **Status:** complete

### Phase 5: GZV-018 MoveIt Task Constructor Baseline

- [x] 调研并安装/声明当前 MoveIt2 MTC 依赖，保持 MTC 为显式 experimental backend。
- [x] 新增最小 MTC benchmark node/launch，输出结构化 YAML report。
- [x] 收敛 `GOAL_STATE_INVALID` 后的 stage init 问题：Cartesian `FixedCartesianPoses -> ComputeIK -> Connect` 当前 interface 拓扑不成立，诊断已写入 report/finding。
- [x] 降级实现 target-driven `MoveTo` joint-goal smoke，证明 target xyz 会进入 MTC backend 并产生 `status=planned`。
- [x] 新增 Cartesian IK MTC backend：`RobotState.setFromIK(Cartesian target candidates) -> MoveTo(IK joint goal)`。
- [x] 接入统一 L1 reach evaluator 对比字段：programmatic baseline 与 MTC baseline 共享 `reach_success = min_distance(gripper_tcp, target_xyz) < threshold` 口径。
- [x] 新增 oracle target sanity check：`target_mode=oracle_near_home` 可验证 IK/MTC/evaluator 口径在近 home 可达点上得到 `reach_success=true`。
- [x] 新增 IK candidate debug artifact：记录 candidate id、world/base xyz、IK 成败、FK 后 TCP、distance、reason、joint solution。
- [x] 拆分报告顶层指标：`planning_success`、`execution_success`、`reach_success`、`min_distance_m`、`selected_candidate_id`。
- [x] 后续优化视觉 target 周围 3D candidate / IK seed / 坐标校准，让视觉目标 MTC baseline 从 `planned but reach_failed` 推进到 `reach_success=true`。
- [x] 新增 execution-grounded reach smoke：MTC joint goal -> Gazebo joint trajectory controller -> `/joint_states` FK TCP trace -> 同一 L1 evaluator。
- [x] 新增 multi-episode benchmark suite runner：支持 episode_count、target jitter、episode artifact 目录和 summary_report 汇总。
- [x] 跑完 `jitter20` execution-grounded suite 并输出稳定性统计（success rates / min_distance 分位数 / failure counts）。
- [x] 跑完 `jitter50` execution-grounded suite 并输出更稳分位统计与失败归因。
- [x] 新增 Level-2 pre-grasp evaluator（`pregrasp_l2`）并在同一 execution-grounded report 中输出 `pregrasp_success`、`pregrasp_height_m`、`pregrasp_approach_angle_error_deg`。
- **Status:** complete for 50-episode jitter suite; Level-2 pre-grasp evaluator and contact/lift/place remain pending

### Phase 5: Pre-grasp Evaluator

- [x] `GZV-018H`：在 `mtc_reach_benchmark_node` 引入 `evaluator_level=pregrasp_l2`，复用 L1 reach 指标并新增 pre-grasp 约束（高度窗 + approach 方向误差）与失败原因。
- [x] `GZV-018I`：收敛 candidate orientation / approach 约束口径，把 `pregrasp_success` 从 false 推到 true。
- [x] `GZV-018J`：在同一 execution-grounded artifact 口径下接入最小 `contact_success / lift_success` evaluator。
- [x] `GZV-018K`：补动态 `grasp_target` world 资产与 `/model_states` object trace，同时修复 review 指出的 object-state 前置条件回归和默认 target z/动态物体高度不一致问题。
- [x] `GZV-018L`：新增 contact proxy 诊断、execution trace failure reason、`execute_grasp_stages` 开关，并把默认单阶段 reach baseline 与实验性 close/lift 阶段隔离，避免 contact/lift 调试回归 L1 reach。
- [ ] `GZV-018M`：仿真 contact/lift 物理成功调参暂缓；当前 contact proxy 到 object AABB 仍约 `0.0233m`，高于 `0.02m` 阈值，object z 未上升。真实物体即将到位，后续优先转真实物体 contact/lift acceptance harness。
- **Status:** `GZV-018H/I/J/K/L` complete, `GZV-018M` blocked/deferred by Gazebo contact physics ROI

### Phase 6: Later Backends And Training Bridge

- [x] `GZV-021`：新增 pre-real acceptance suite 总入口，聚合 vision smoke、MTC reach smoke、small jitter suite、dataset trainability gate，并输出 `acceptance_report.yaml`。
- [x] `GZV-022`：新增 acceptance artifact run index，记录 latest run、report/dashboard 路径、reach/min-distance/failure/trainability 摘要，避免人工翻找 YAML。
- [x] `GZV-023`：新增 vision projection / detector quality smoke，从 recorded episode artifact 统计 raw/canonical target、pixel/world error、miss/false positive 与 clamp reason。
- [x] `GZV-024`：新增 pre-real benchmark Markdown dashboard，集中展示 acceptance 状态、reach 分布、failure counts、trainability 状态和边界说明。
- [x] `E2E-HW-002-software-link`：新增 follower adapter dry-run smoke，证明 `/joint_trajectory_controller/joint_trajectory` 可进入 follower adapter 并转换为 LeRobot action；证据 `docs/generated/real-follower/follower_software_link_smoke_20260512.json` 显示 `software_ready=true`、`hardware_bus_ready=false`，因此只能称软件链路证明，不能称真实 follower 闭环。
- [ ] GZV-019：GraspNet/AnyGrasp/Dex-Net-style grasp proposal adapter，占位接口先行，具体模型后接。
- [ ] GZV-020：cuRobo/cuMotion backend feasibility，先做 CUDA/robot model/collision world compatibility check。
- [ ] TRN bridge：把成功/失败 episode 导出为 LeRobot `trainable_smoke` dataset，后续训练 ACT/SmolVLA/Diffusion Policy。
- [ ] REAL-001：真实物体 contact/lift acceptance harness，复用当前 evaluator/report 字段，不要求先把 Gazebo lift 调成 true。
- **Status:** `GZV-021/022/023/024` complete for pre-real non-hardware acceptance; `GZV-019/020/REAL-001` pending

## Key Questions

1. 当前 Gazebo/URDF 中是否有稳定 gripper TCP frame，可直接计算 gripper_tip 到 target_xyz 的距离？
2. 是否已有 Gazebo `/gazebo/model_states` 或 link states 可用来评估 object z、place 区域和 contact/enclosure？
3. 第一版 target-driven reach baseline 应使用简单 joint mapping，还是优先走 MoveIt IK？
4. MoveIt Task Constructor 在当前 ROS Humble/WSL 环境是否已安装，缺失时安装成本多大？
5. Episode 数据字段如何兼容现有 `vision_episode_recorder_node.py`、dataset adapter 和 LeRobot candidate exporter？

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 下一阶段命名为 `sim grasp benchmark harness`，不再只叫 executor | 核心价值是算法接入、执行、评价、数据记录，而不是单一路径动作生成 |
| 先做 evaluator 与 programmatic reach baseline，再接 MTC | 没有统一 evaluator 时无法比较算法；programmatic baseline 是最小可控 teacher |
| 指标分层 L1-L5 | Gazebo 抓取物理可能不稳，先用 reach 成功建立主动性和可比较标准 |
| 所有算法共享同一 evaluator | 程序化 baseline、MTC、cuRobo、GraspNet/AnyGrasp、LeRobot policy 才能横向比较 |
| LeRobot 放在数据和 policy 层 | 当前应先建立 teacher/evaluator/episode label，再做训练 |
| 不声明真实 follower 或真实抓取 | 当前实体 follower 未到货，所有结论限定为 Gazebo simulation smoke/benchmark |
| `target_object.world_xyz` 第一版使用 canonical benchmark workspace | `vision_target_projector` 当前投影值更适合触发/记录，直接规划会落到不可达域；保留 `raw_world_xyz` 便于后续校准 |
| reach evaluator 第一版使用程序化 TCP 近似，不要求 TF/link_state 依赖 | 当前目的是建立统一 L1 benchmark 口径，先减少 Gazebo/TF 运行时依赖 |
| `GZV-017C` 第一轮先把 benchmark result 原样落入 episode/dataset/source sidecar | 先保留完整 traceability，后续再决定 action 主字段切 canonical target 还是 executed joint action |
| candidate 主 `action.target_xyz` 现已切到 benchmark canonical target，但只在 benchmark target 与当前选中对象匹配时使用 | 让 candidate 主字段与当前 planning/evaluation 基准一致，同时避免多目标或非默认类别导出时标签、置信度和坐标错配；不匹配时回退到选中 vision target |
| `GZV-018` MTC work must remain optional until planned smoke passes | 当前只允许作为可构建实验 backend，不得替换 programmatic baseline 或声明 MTC reach 成功 |
| `GZV-018B` Cartesian IK backend 可以声明 `planned`，但不能声明 `reach_success` | 当前 MTC 通过 IK candidate 找到可规划点，report 为 `status=planned`；同一 L1 evaluator 给出 `min_distance_m=0.172742`，超过 `0.08m` threshold，因此 result label 仍是 `trainable_smoke_failed` |
| `GZV-018C` oracle target sanity check 可以声明 `reach_success=true`，但只限近 home 手写目标 | `target_mode=oracle_near_home` 报告显示 `planning_success=true`、`reach_success=true`、`selected_candidate_id=0`、`min_distance_m=0`；这证明 MTC/IK/evaluator 链路可用，但不能推导视觉目标或真实抓取成功 |
| `GZV-018D` 视觉 canonical target 可以声明 planned-goal position-only reach smoke 成功 | 视觉 canonical target 路径报告显示 `diagnostic_level=position_only_cartesian_ik_reach`、`planning_success=true`、`reach_success=true`、`selected_candidate_id=18`、`min_distance_m=0.079456 < 0.08`；成功来自 FK sample fallback，不是 pose IK、真实执行、contact/lift/place 或真实抓取 |
| `GZV-018E` 可以声明 execution-grounded Gazebo/MTC reach smoke 成功 | `mtc-execution-reach-benchmark-report-20260507.yaml` 显示 MTC joint goal 已发布到 Gazebo controller，`execution_success=true`、`controller_converged=true`、`sample_count=80`、actual TCP trace `min_distance_m=0.066843 < 0.08`；仍不是 contact/lift/place、真实抓取或 `trainable_real` |
| `GZV-018F` multi-episode suite 已完成 `jitter20` 稳定性评估 | `mtc-reach-suite-20260507-jitter20/summary_report.yaml`：`total_episodes=20`、`planning/trajectory_execution/controller_converged/reach success rates=1.0`、`mean_min_distance_m=0.057951`、`p90_min_distance_m=0.072043`、`max_min_distance_m=0.073573`、`failure_reason_counts={}`；结论仍限于 Gazebo execution-grounded simulated reach benchmark |
| `GZV-018G` multi-episode suite 已完成 `jitter50` 稳定性评估 | `mtc-reach-suite-20260507-jitter50/summary_report.yaml`：`total_episodes=50`、`planning_success_rate=1.0`、`trajectory_execution_success_rate=0.96`、`controller_converged_rate=0.96`、`execution_success_rate=0.96`、`reach_success_rate=1.0`、`mean_min_distance_m=0.056418`、`p90_min_distance_m=0.073416`、`max_min_distance_m=0.076531`、`failure_reason_counts={trajectory_publish_failed: 2}`；结论仍限于 Gazebo execution-grounded simulated reach benchmark |
| object state 不能作为 reach execution 前置条件 | `GZV-018K` review 修复后，`target_model_name` 或 `model_states_topic` 缺失只会让 `object_trace/contact/lift` 标为 unavailable，joint trajectory 仍会发布并继续用 TCP trace 计算 reach |
| 默认动态 grasp target 必须与 benchmark target 对齐 | `grasp_target` 为动态物体时，默认 target z 使用桌面高度 `0.75` + 半高 `0.008` = `0.758`，避免规划/评估仍瞄准 `z=0.8` 的旧静态料盒中心 |
| contact/lift 调试不能破坏 L1 reach 默认路径 | `GZV-018L` 后默认 `execute_grasp_stages=false`，单阶段 trajectory 保持 `trajectory_execution_success=true/reach_success=true`；实验性 close/squeeze/lift 只在显式打开时运行 |
| contact proxy 比 TCP 中心更接近真实接触诊断 | TCP 到 target center 可达到 `~1e-5m`，但 moving jaw proxy 到 object AABB 仍约 `0.0233m > 0.02m`，所以不能把 reach 成功解释成 contact/lift 成功 |
| Gazebo lift 不再作为短期主线门槛 | 当前软件目标是统一 evaluator、数据集判断、检测验证和执行 trace。Gazebo contact/lift 物理调参 ROI 低，真实物体到位后优先做 real acceptance harness |
| 接真机前先收口非实机 acceptance gate | 真机前需要一条可回归、可索引、可读的工程证据链；`tools/e2e/run_pre_real_acceptance_suite.py` 聚合现有 smoke/benchmark/trainability/vision quality artifact，contact/lift 只作为 blocked/deferred optional diagnostic |
| 实物主臂到 Gazebo simulated arm 的方向映射固定为 `[1.0,1.0,1.0,1.0,-1.0,1.0]` | 2026-05-08 现场确认 `/dev/ttyUSB0` leader 输入 READY 且 `/leader/joint_states` 约 30Hz；关节顺序为 `[shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper]`，二轴 `shoulder_lift` 不反，五轴 `wrist_roll` 反向。该结论只表示 leader 输入对应 Gazebo simulated arm，不表示 follower 真机执行或真实抓取 |

## Current Closed-Loop Review

| Loop | Status | Evidence / Gap |
|------|--------|----------------|
| Gazebo vision detection loop | passed smoke | Gazebo camera -> detector -> `/detections` -> `/vision/targets` 已通过 GZV-014/016，overlay 可用 |
| Programmatic sim execution loop | passed smoke | `/vision/targets` -> task_executor -> trajectory -> Gazebo joint_states -> `/mes_task_status` 已通过 GZV-015/017A/B |
| MTC execution-grounded reach loop | passed benchmark | MTC target -> joint goal -> Gazebo controller -> FK TCP trace -> evaluator 已通过 GZV-018E/G/F/G/L |
| Dataset quality loop | mostly passed smoke | recorder、adapter、candidate exporter、native LeRobot smoke、trainability gate、viewer 已有；真实 action/follower label 仍待真机补强 |
| Detector quality loop | partial | Gazebo color detector 和 YOLO smoke/导出链路可验证；真实 YOLO 质量闭环仍在 `YOL-004`，不能声称模型质量闭环完成 |
| Pre-real acceptance loop | passed smoke | `docs/generated/acceptance/pre-real-acceptance-20260508-134536/acceptance_report.yaml`：status passed；`latest_runs.yaml` 可索引；dashboard 明确不是 real grasp、real follower、real YOLO quality closure 或 `trainable_real` |
| Live leader to Gazebo mapping loop | passed manual calibration | `/dev/ttyUSB0` -> `leader_input_bridge` -> `/leader/joint_states` -> `leader_to_gazebo_bridge` -> Gazebo controller 已通；实物对应 scale 为 `[1.0,1.0,1.0,1.0,-1.0,1.0]` |
| Software MES/UI loop | passed local smoke | MES command/status、frontend runtime/quality panel、rosbridge 状态流已通；真实硬件 acceptance 仍待 |
| Frontend to real follower loop | blocked hardware bus | 软件入口已接：frontend/backend `runtimeTarget=real_hardware` -> `real_bringup` -> `so101_follower_trajectory_adapter`；`/dev/ttyACM0` 存在但 Feetech scan 为 `{}`，adapter 找不到 1..6 号电机 |
| Contact/lift loop | blocked/deferred | contact/lift fields 和 object trace 已接入，但 Gazebo lift physics 未成功；不再阻塞主线 |

## Candidate Interfaces

```text
PerceptionAdapter
  input: /detections, /vision/targets
  output: target_object {category, confidence, image_xy, world_xyz, source}

GraspProposalAdapter
  input: target_object
  output: grasp_candidates[] {grasp_pose, pregrasp_pose, approach_vector, gripper_width, score, source}

MotionPlannerBackend
  input: grasp_candidate
  output: plan_result {trajectory, plan_status, planner_debug}

Executor
  input: trajectory
  output: execution_trace {joint_states, controller_status, timestamps}

Evaluator
  input: target_object, grasp_candidate, plan_result, execution_trace, optional object/gripper states
  output: metrics {reach_success, contact_success, enclosure_success, lift_success, place_success, score, failure_reason}

EpisodeRecorder
  output: image, overlay, detections, vision_targets, target_object, grasp_candidates, selected_candidate, trajectory, joint_states, metrics, result_label
```

## Metrics Ladder

| Level | Metric | Meaning | First Implementation |
|-------|--------|---------|----------------------|
| L1 | reach_success | 末端主动靠近目标 | `min_distance(gripper_tcp, target_xyz) < 0.04m` |
| L2 | contact_success | 末端/夹爪接触目标 | Gazebo contact 或距离近似 |
| L3 | enclosure_success | 夹爪包围目标 | finger/object geometry 近似 |
| L4 | lift_success | 目标被抬起 | `object_z_final - object_z_initial > threshold` |
| L5 | place_success | 目标被放到区域 | `distance(object_final_xy, place_xy) < threshold` |

## Files To Inspect Before Implementation

- `src/so101_bringup/scripts/vision_target_projector_node.py`
- `src/so101_bringup/scripts/task_executor.py`
- `src/so101_bringup/scripts/task_execution_service.py`
- `src/so101_bringup/scripts/trajectory_builder.py`
- `src/so101_bringup/scripts/vision_episode_recorder_node.py`
- `tools/e2e/assert_sim_vision_closed_loop.py`
- `src/so101_moveit_config/scripts/pick_place_runner.py`
- `src/so101_moveit_config/config/moveit_controllers.yaml`
- `src/so101_description/urdf/so101.urdf`
- `src/so101_gazebo/worlds/so101_workcell.world`
- `docs/任务清单.md`
- `docs/进度日志.md`

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| `benchmark_preferred_category:=` malformed launch arg | 1 | 启动脚本改为非空默认值 `auto` |
| `benchmark_trigger_cooldown_sec` integer override mismatched ROS double param | 1 | smoke 命令显式使用 `4.0`；后续脚本保持浮点字符串口径 |

## Notes

- Phase 1/2/3 minimum runnable version is implemented in this session.
- `GZV-017C` recorder/dataset integration is now partially complete: benchmark_result 已进入 episode/dataset/candidate source。
- `GZV-017C` 已完成本轮收口；下一决策点变为是否从 canonical target action 继续迁移到 executed joint action.
- 2026-05-07 review 修复已收口：MTC 新源码纳入 patch，`so101_moveit_config/package.xml` 声明新增依赖，candidate exporter 只在 benchmark target 匹配选中对象时使用 canonical target；验证 `python3 -m unittest tools/hardware/test_export_vision_dataset_to_lerobot_candidate.py -v` 与 `colcon build --packages-select so101_moveit_config` 通过。
- All evidence must keep the wording “Gazebo simulation benchmark/smoke” unless a real follower exists and is validated.
