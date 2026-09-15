# Findings & Decisions

## 2026-05-12 - Real follower adapter first contact

- A real follower software bridge now exists: `so101_follower_trajectory_adapter.py`.
- The bridge now has a dry-run proof mode for software-only validation: `/joint_trajectory_controller/joint_trajectory` is converted to LeRobot-style follower actions without touching hardware.
- Evidence: `docs/generated/real-follower/follower_software_link_smoke_20260512.json` reports `passed=true`, `software_ready=true`, `hardware_bus_ready=false`, `received_trajectory_count=1`, and `sent_command_count=1`.
- Backend/frontend now expose `/real_follower/status` via `/topic/real-follower-status`, so the development workbench can show follower software readiness separately from hardware bus readiness.
- Backend/frontend startup can reach the real-hardware path through `runtimeTarget=real_hardware`, but actual motion is blocked by hardware bus discovery.
- `/dev/ttyACM0` is visible as `1a86:55d3 USB Single Serial`; permissions are fine.
- LeRobot/Feetech SDK dependency import is now usable from user site.
- Feetech bus scan returns `{}` across common baud rates, and the adapter cannot find motor IDs `1..6`.
- Interpretation: current blocker is likely follower power, motor-chain wiring, wrong board/port, motor IDs, or baudrate/config mismatch, not the MES/frontend/ROS software path.
- The new hardware board may require the correct LeRobot environment/board setup before Feetech scan is meaningful; until then keep backend default `SO101_FOLLOWER_DRY_RUN=true`.
- Boundary: no real follower closed-loop success, no real grasp success, no `trainable_real`.

## 2026-05-07 - GZV-018F Multi-Episode Suite Smoke

- Added `tools/e2e/run_mtc_reach_benchmark_suite.py` as an external suite runner around the single-episode MTC execution-grounded launch.
- The runner supports `episode_count`, `target_xyz`, `jitter_xyz`, per-episode directories, `report.yaml`, `tcp_trace.csv`, `joint_trace.csv`, `selected_candidate.yaml`, `planned_goal_proxy.yaml`, `execution_grounded_metrics.yaml`, and top-level `summary_report.yaml`.
- The first smoke suite `docs/generated/vision-episodes/mtc-reach-suite-20260507-smoke` contains one execution-grounded successful episode and summary rates of `1.0`; this validates suite mechanics, not broad stability.
- Larger 20/50/100 episode randomized benchmark runs remain pending and should be used before claiming robustness.

## 2026-05-07 - GZV-018F Jitter20 Stability Run

- Completed `docs/generated/vision-episodes/mtc-reach-suite-20260507-jitter20` with `total_episodes=20`.
- Summary metrics: `planning_success_rate=1.0`, `trajectory_execution_success_rate=1.0`, `controller_converged_rate=1.0`, `execution_success_rate=1.0`, `reach_success_rate=1.0`.
- Distance stats from execution-grounded TCP traces: `mean=0.057951`, `p50=0.059958`, `p90=0.072043`, `min=0.034315`, `max=0.073573` (threshold `0.08`).
- `failure_reason_counts` is empty in this run; no `no_ik`/`plan_failed`/`controller_not_converged`/`reach_failed` episodes were observed in the 20-episode jitter window.

## 2026-05-07 - GZV-018G Jitter50 Stability Run

- Completed `docs/generated/vision-episodes/mtc-reach-suite-20260507-jitter50` with `total_episodes=50`.
- Summary metrics: `planning_success_rate=1.0`, `trajectory_execution_success_rate=0.96`, `controller_converged_rate=0.96`, `execution_success_rate=0.96`, `reach_success_rate=1.0`.
- Execution-grounded distance stats: `mean=0.056418`, `p50=0.055355`, `p90=0.073416`, `min=0.033084`, `max=0.076531` (threshold `0.08`).
- Failure breakdown: `trajectory_publish_failed=2` (episodes 48, 49), while all episodes still met the L1 reach threshold in the reported traces.

## 2026-05-07 - GZV-018H Pre-grasp L2 Evaluator Wiring

- Added Level-2 pre-grasp evaluator fields into the same MTC execution-grounded report path: `pregrasp_success`, `pregrasp_height_m`, `pregrasp_approach_angle_error_deg`, `pregrasp_height_ok`, `pregrasp_approach_ok`.
- `mtc_reach_benchmark.launch.py` now passes `evaluator_level` / `pregrasp_*` parameters through to `mtc_reach_benchmark_node`.
- Validation run: `docs/generated/vision-episodes/mtc-pregrasp-benchmark-report-20260507.yaml` with `evaluator_level=pregrasp_l2` reports `reach_success=true` but `pregrasp_success=false`, `result_label=trainable_smoke_failed`, `failure_reason=pregrasp_constraints_not_met`.
- Current failure is geometric orientation mismatch (`pregrasp_approach_angle_error_deg=92.75`), not planning or execution failure; this is the next convergence target.

## 2026-05-08 - GZV-018I Pre-grasp Convergence Passed

- The main issue was evaluator inconsistency, not planner failure: candidate fallback scoring and L2 evaluation were using different approach references, and L2 initially evaluated the closest-to-target trace point instead of the best pre-grasp trace point.
- Fallback candidate ranking now uses a combined pre-grasp score (`distance + approach + nominal height`) instead of first-hit under threshold only.
- `pregrasp_l2` now evaluates against a side-approach reference (`desired_pregrasp_approach_world=[0,1,0]`) and selects the best pre-grasp trace sample instead of the absolute closest TCP sample.
- Validation run `docs/generated/vision-episodes/mtc-pregrasp-benchmark-report-20260508.yaml` now reports `reach_success=true`, `pregrasp_success=true`, `pregrasp_eval_distance_m=0.045062`, `pregrasp_height_m=0.042445`, `pregrasp_approach_angle_error_deg=32.312`, `result_label=trainable_smoke`.

## 2026-05-08 - GZV-018J Minimal Contact/Lift Evaluator Wiring

- Added `contact_success` into the same execution-grounded metrics contract using a gripper-to-object AABB geometric approximation (`contact_distance_m <= contact_distance_threshold_m`).
- Added `lift_success` using Gazebo model state object z tracking and `object_lift_delta_m >= lift_success_threshold_m`.
- Current world limitation is explicit: `pick_bin` is static in `so101_workcell.world`, so `lift_success` cannot become true until a dynamic graspable object is added.
- Validation run `docs/generated/vision-episodes/mtc-contact-lift-benchmark-report-20260508.yaml` shows the fields are wired and traceable: `contact_success=false`, `lift_success=false`, `object_trace.available=false`, `object_lift_delta_m=0`. This is an expected world/model limitation, not hidden failure.

## 2026-05-08 - GZV-018K Dynamic Target Review Fix

- Review finding was valid: object state availability must not block reach execution. The benchmark now waits only for joint state readiness before publishing the trajectory; missing `target_model_name` or `model_states_topic` leaves object/contact/lift unavailable while reach remains evaluated from the TCP trace.
- Added explicit `contact_available` and `lift_available` metrics so unavailable object state is not confused with a contact/lift failure.
- Default dynamic `grasp_target` and benchmark `target_xyz` are now aligned at the settled object center `[0.312, 0.192, 0.758]` for the current 1.6 cm box on the 0.75 m table.
- This still does not prove simulated grasp/lift success. The remaining gap is physical grasp stability: the object state chain is available, but `object_lift_delta_m` has not yet crossed the lift threshold.

## 2026-05-08 - GZV-018L Contact Proxy And Stage Isolation

- The contact metric now evaluates a configurable moving-jaw contact proxy instead of the TCP/link origin. Default proxy offset is `[0.0, -0.03, 0.02]`, matching the moving jaw collision offset used by the current URDF.
- Single-stage reach remains the default path with `execute_grasp_stages=false`. This keeps the L1 reach benchmark stable while close/squeeze/lift tuning remains experimental.
- Validation `docs/generated/vision-episodes/mtc-dynamic-lift-reach-l1-final-20260508.yaml` reports `planning_success=true`, `trajectory_execution_success=true`, `execution_success=true`, `reach_success=true`, and execution-grounded `min_distance_m=1.3278e-05`.
- The same report also shows the current contact/lift gap: `contact_success=false`, `contact_distance_m=0.0233065` with threshold `0.02`, `lift_success=false`, and `object_lift_delta_m≈0`.
- `pregrasp_l2` against the dynamic object center correctly fails as a pre-grasp pose (`pregrasp_height_m≈-1.3e-05`) even though L1 reach succeeds. This prevents a target-center touch/reach from being mislabeled as a pre-grasp or lift success.

## 2026-05-08 - Simulation And Software Loop Review

- The original benchmark goal is mostly achieved: there is now a common evaluator/report contract for reach/pregrasp/contact/lift metrics, execution trace, selected candidate, target canonicalization, and artifact evidence.
- Gazebo simulated lift is blocked by contact physics/geometry ROI, not by the core software chain. The useful assets are the evaluator contract, trace recorder, candidate/debug artifact, and success/failure labels.
- The system currently has two meaningful closed loops:
  - Software/business loop: MES/frontend command/status flow through ROS task execution and `/mes_task_status`.
  - Simulation execution loop: vision/MTC target -> trajectory/controller -> Gazebo `/joint_states` -> FK TCP trace -> evaluator/report.
- Dataset judgment is usable for smoke data: recorder -> adapter -> LeRobot candidate -> native LeRobot export -> trainability gate -> viewer. The remaining limitation is that most action labels are Gazebo/smoke labels, not real follower hardware actions.
- Detector validation is not fully complete: Gazebo color detection and YOLO smoke/export path are available, but real YOLO quality闭环、真实标注质量和真实场景误检/漏检统计仍未完成.
- Recommendation: mark Gazebo lift as deferred and shift to `REAL-001` once the physical object is assembled, reusing the same evaluator/report fields instead of spending more time on Gazebo Classic contact tuning.

## 2026-05-08 - GZV-021/022/023/024 Pre-Real Acceptance Closure

- A pre-real non-hardware acceptance suite now exists at `tools/e2e/run_pre_real_acceptance_suite.py`. It can run the MTC reach smoke/small jitter suite directly, or reuse latest artifacts with `--reuse-latest-artifacts` for fast regression evidence assembly.
- The passing acceptance evidence is `docs/generated/acceptance/pre-real-acceptance-20260508-134536/acceptance_report.yaml`; it aggregates vision smoke, vision projection quality smoke, MTC reach smoke, jitter benchmark, trainability gate, and contact/lift optional diagnostics.
- The artifact index is `docs/generated/acceptance/latest_runs.yaml`; it records timestamp, command, report/dashboard paths, status, reach success rate, min-distance summary, failure reason counts, and dataset trainability status.
- Vision projection quality smoke reports raw projector target and canonical benchmark target separately. Current recorded artifact shows raw-to-canonical clamp count `7`, canonical world error `0.0`, miss counts `{}`, and false positive counts `{}`. This validates recorded Gazebo detector/projection data quality, not real YOLO quality.
- Dashboard `docs/generated/acceptance/pre-real-acceptance-20260508-134536/dashboard.md` is intentionally Markdown first and explicitly states current boundaries: not real grasp, not real follower closed loop, not real YOLO quality closure, not `trainable_real`, and not simulated grasp/lift success.
- Contact/lift remains `blocked/deferred` optional diagnostic. `contact_success=false` or `lift_success=false` must not fail the pre-real acceptance gate.

## 2026-05-07 - GZV-018E Execution-Grounded Reach Passed

- The MTC-selected joint goal is now published to `/joint_trajectory_controller/joint_trajectory`, and `/joint_states` are sampled to build a FK-derived TCP execution trace.
- `docs/generated/vision-episodes/mtc-execution-reach-benchmark-report-20260507.yaml` reports `execution_success=true`, `controller_converged=true`, `sample_count=80`, and execution-grounded `min_distance_m=0.066843` under the `0.08` threshold.
- The planned-goal proxy remains recorded separately: planned proxy `min_distance_m=0.079456`; execution trace found a closer point at `[0.273116, 0.138757, 0.823851]`.
- This is the first Gazebo execution-grounded MTC reach smoke in this line. It is still not contact/enclosure/lift/place, real hardware success, or `trainable_real`.

## 2026-05-07 - GZV-018D Vision Canonical Position-Only Reach Passed

- Target-centered pose IK still fails for the vision canonical target; every pose candidate reports `pose_ik_failed`, confirming the pose constraint is too strict for this stage.
- A position-only FK sample fallback can find a planned-goal candidate inside the L1 threshold: `selected_candidate_id=18`, TCP `[0.249475, 0.165453, 0.833583]`, `min_distance_m=0.079456`, threshold `0.08`.
- The selected joint goal is `{shoulder_pan=-0.6, shoulder_lift=-0.1, elbow_flex=0.3, wrist_flex=0, wrist_roll=0, gripper=0.2}` and MTC planned it successfully with `solution_count=1`.
- This is a planned-goal position-only reach smoke. `execution_success` remains null, and this is not contact, enclosure, lift, place, real grasp success, or `trainable_real`.

## 2026-05-07 - GZV-018C Oracle Target Sanity Passed

- `target_mode` was declared and passed through `mtc_reach_benchmark.launch.py`; the previous oracle run was invalid because the report still showed `target_mode=vision_canonical`.
- The oracle smoke report `docs/generated/vision-episodes/mtc-oracle-reach-benchmark-report-20260507.yaml` now shows `target_mode=oracle_near_home`, `status=planned`, `planning_success=true`, `reach_success=true`, `selected_candidate_id=0`, and `min_distance_m=0`.
- This narrows the current failure: MTC Cartesian IK plus the shared L1 evaluator can reach a near-home oracle point, so the vision-target failure path should focus on target coordinate calibration, `target_base_z_offset`, and target-centered 3D candidate generation.
- `execution_success` remains null in this MTC smoke because this report evaluates the planned-goal proxy, not a Gazebo execution trace.

## 2026-05-07 - GZV-018B Cartesian IK MTC Planned But Reach-Failed

- `backend_mode` was initially not declared or passed through `mtc_reach_benchmark.launch.py`, so CLI probes were silently running the default backend; launch now exposes `backend_mode`, `ik_frame`, `reach_threshold_m`, and `target_base_z_offset`.
- Direct MTC Cartesian `MoveTo(point/pose + ik_frame)` initializes correctly but still fails planning with `GOAL_STATE_INVALID` for the canonical target.
- Adding `RobotState.setFromIK` preflight makes the Cartesian path diagnosable and allows fallback candidate scanning from the home TCP toward the target.
- The current successful MTC Cartesian IK smoke selected the home TCP candidate as the only IK-solvable point, then MTC planned a joint goal successfully: `status=planned`, `solution_count=1`.
- The same L1 evaluator correctly marks this as `reach_success=false`, `min_distance_m=0.172742`, `threshold_m=0.08`, `result_label=trainable_smoke_failed`; this is planned MTC plumbing, not reach success.

## 2026-05-07 - GZV-018 MTC Baseline Scope Correction

- The earlier MTC Cartesian chain failed before planning because the stage interfaces were wired incorrectly, not because the target coordinate alone was invalid.
- Structured failure evidence from `docs/generated/vision-episodes/mtc-reach-benchmark-report-20260507.yaml` showed: `compute_reach_ik: interface of 'reach_target_pose' (← →) does not match external one (→ →)`, plus task pipeline connect interface mismatches.
- To finish a minimum runnable `GZV-018` baseline without overclaiming grasp/reach success, the node was reduced to `FixedState(home) -> MoveTo(target-driven joint goal)`.
- The reduced baseline is still target-driven: canonical target xyz maps into a deterministic joint goal, and the YAML report records `joint_goal`, `canonical_target_xyz`, `reach_candidate_world_xyz`, `status`, and `solution_count`.
- Fresh smoke produced `status=planned` and `solution_count=1`; this is a MoveIt Task Constructor joint-goal planning smoke, not a Cartesian grasp, contact, lift, place, or real follower result.

## 2026-05-06 - GZV-017C Recorder/Dataset Upgrade

## 2026-05-07 - Review Findings: GZV-017C/GZV-018 Patch Safety

- Review correctly identified that `src/so101_moveit_config/CMakeLists.txt` referenced `mtc_reach_benchmark_node` while the new source file was still untracked; clean clones would fail to build if the source is not included in the patch.
- `so101_moveit_config/package.xml` also needed manifest dependencies for the new MTC executable: `rclcpp`, `geometry_msgs`, MoveIt/MTC packages, `tf2_geometry_msgs`, and `yaml-cpp`.
- Candidate export must keep `target_category`、`confidence`、`target_xyz` tied to the same selected object. Benchmark canonical coordinates are now promoted to `action.target_xyz` only when `benchmark_result.target_object` matches the selected vision target by category and raw/world xyz.
- If the exporter is run with a non-default category or a multi-object sample where benchmark target differs from selected target, action metadata now falls back to the selected vision target and clears benchmark-only result fields in `action`; the full benchmark trace remains in `source.benchmark_result` for audit.
- Verification: `python3 -m unittest tools/hardware/test_export_vision_dataset_to_lerobot_candidate.py -v` passed 3 tests, including the new non-default-category regression; `source /opt/ros/humble/setup.bash && colcon build --packages-select so101_moveit_config` passed.


### What Was Implemented

- `task_executor.py` 现在除了落本地 benchmark JSON，也会发布 `/sim_grasp/benchmark_result`。
- `vision_episode_recorder_node.py` 新增 `benchmark_result_topic`，默认订阅 `/sim_grasp/benchmark_result`，并把 `benchmark_result` 事件写入 `events.jsonl`。
- `build_vision_dataset_adapter.py` 现在会把最近 `benchmark_result` 对齐进每条 sample。
- `export_vision_dataset_to_lerobot_candidate.py` 现在会把以下字段带进 candidate：
  - `action.selected_candidate_id`
  - `action.result_label`
  - `action.reach_success`
  - `action.min_distance_m`
  - `action.planner_backend`
  - `source.benchmark_result`

### Verified Episode Evidence

- 新 episode:
  - `docs/generated/vision-episodes/gzv017c_benchmark_smoke_20260506/`
- `manifest.json` 关键计数：
  - `benchmark_result=7`
  - `image_snapshot_count=6`
- `events.jsonl` 已包含 `benchmark_result` 流。
- `dataset/dataset-index.json`：
  - `sample_count=6`
  - `validation.status=passed`
- `dataset/samples.jsonl`：
  - 每条 sample 已包含 `benchmark_result`
- `dataset/lerobot-candidate/train_samples.jsonl`：
  - `action.result_label=trainable_smoke`
  - `action.selected_candidate_id=red_reach_baseline`
  - `source.benchmark_result` 完整保留 benchmark trace

### Important Current Semantics

- 当前 candidate 主 action 已切到 benchmark 口径：
  - `action.type=vision_target_xyz`
  - `action.target_xyz` = benchmark canonical target
  - `action.raw_target_xyz` = projector 原始 target
- 这意味着 `trainable_smoke` candidate 的主字段现在与 benchmark planning/evaluation 口径一致。
- `source.benchmark_result.target_object.world_xyz` 与完整 trace 仍保留，后续若迁移到 executed joint action 仍有依据。

### Decision

- 本轮已把 candidate 主 action 语义切到 canonical benchmark target，并保留 `raw_target_xyz`。
- 下一轮若继续收口 `GZV-017C`，重点变成：
  - 是否从 canonical target action 继续迁移到 executed joint action

### Viewer Summary

- `tools/hardware/build_episode_viewer.py` 现已把 benchmark 摘要直接带进 `viewer-data.json`：
  - `reach_success`
  - `min_distance_m`
  - `selected_candidate_id`
  - `canonical_target_xyz`
  - `raw_target_xyz`
- 对 `gzv017c_benchmark_smoke_20260506` 重新生成 viewer 后，首条 sample 的 benchmark 摘要已可直接展示上述字段。

---

## 2026-05-06 - GZV-017A/B Minimum Runnable Implementation

### What Was Implemented

- 新增 `src/so101_bringup/scripts/sim_grasp_benchmark.py`，实现最小可运行 benchmark 基础件：
  - `select_target_object()`
  - `build_reach_candidate()`
  - `create_target_driven_plan()`
  - `evaluate_reach_execution()`
  - benchmark artifact builder
- `task_executor.py` 增加一条独立于旧 detection-template 路径的新执行链：
  - 订阅 `/vision/targets`
  - 选择 `target_object`
  - 生成 programmatic reach baseline
  - 发送多点 `JointTrajectory`
  - 输出 L1 reach evaluator
  - 写出 JSON artifact
- `trajectory_builder.py` 新增 `create_multi_point_trajectory_message()`。
- `assert_sim_vision_closed_loop.py` 新增 `--task-request-prefix`，可以验证 `bench-*` 请求而不是只认 `det-*`。

### Runtime Findings

- 当前 `vision_target_projector_node.py` 产出的 `world_xyz` 可用于闭环触发和记录，但直接拿来做 target-driven reach 时，`x≈0.65m` 会落在当前 SO101 程序化 baseline 的不可达域外。
- 第一版 benchmark 因此将 target 分成两层：
  - `raw_world_xyz`: projector 原始投影，完整保留
  - `world_xyz`: canonical benchmark workspace 内的 target，用于当前 baseline/evaluator
- 本轮 canonical workspace 实际采用：
  - `x ∈ [0.26, 0.32]`
  - `y ∈ [-0.22, 0.22]`
  - `z` 保持 table 值

### Evaluator Findings

- 第一版 evaluator 不依赖 TF/listener 或 Gazebo link states，而是使用程序化 TCP 近似：
  - 输入 joint positions
  - 估计 `gripper_frame_link` 对应 TCP world xyz
  - 计算 `min_distance(gripper_tcp, target_xyz)`
- 这满足当前 L1 benchmark 的统一口径要求，但不应误称为真实 grasp/contact/lift 指标。

### Verified Evidence

- 单测：
  - `python3 -m unittest src/so101_bringup/test/test_sim_grasp_benchmark.py src/so101_bringup/test/test_trajectory_builder.py tools/e2e/test_assert_sim_vision_closed_loop.py -v`
  - 7 tests OK
- 相关回归：
  - `python3 -m unittest src/so101_bringup/test/test_task_execution_service.py src/so101_bringup/test/test_detection_trigger_policy.py src/so101_bringup/test/test_vision_target_projector.py src/so101_bringup/test/test_task_status_publisher.py -v`
  - 6 tests OK
- 构建：
  - `source /opt/ros/humble/setup.bash && colcon build --packages-select so101_bringup`
  - `Summary: 1 package finished`
- Gazebo benchmark smoke：
  - `DETECTION_BACKEND=gazebo_color USE_VISION_EPISODE_RECORDER=false BENCHMARK_REACH_ENABLED=true BENCHMARK_TRIGGER_COOLDOWN_SEC=4.0 BENCHMARK_REACH_THRESHOLD_M=0.12 bash tools/e2e/start_sim_vision_stack.sh`
  - `python3 tools/e2e/assert_sim_vision_closed_loop.py --detection-backend gazebo_color --require-task-close --require-trajectory-command --require-joint-motion --require-overlay-image --task-request-prefix bench- --min-joint-delta 0.03 --timeout-sec 180 --report-path docs/generated/vision-episodes/sim-grasp-benchmark-closed-loop-gazebo-color-20260506.json`
  - assertion report `status=passed`
- 代表性 artifact：
  - `docs/generated/vision-episodes/sim-grasp-benchmark-bench-red-1778057149129-20260506-164549.json`
  - `evaluation_result.metrics.reach_success=true`
  - `result_label=trainable_smoke`

### Limits Kept Explicit

- 当前 benchmark 仍是 Gazebo simulation benchmark/smoke。
- `reach_success` 只证明 L1 主动靠近，不是 grasp success。
- 当前 artifact 明确不宣称：
  - 真实 follower 执行
  - 真实抓取成功率
  - 真实 YOLO 质量闭环
  - `trainable_real`

---

## 2026-05-06 - Sim Grasp Benchmark Harness Planning

### Requirements Captured

- 当前不要直接进入训练或端到端 policy。
- 下一阶段核心是建立“抓取算法接入与评价台架”。
- 台架必须支持复用成熟算法，而不是重写抓取算法。
- 所有算法共享统一 evaluator：programmatic baseline、MoveIt Task Constructor、cuRobo/cuMotion、GraspNet/AnyGrasp/Dex-Net-style proposal、LeRobot policy、未来真机 leader/follower。
- 当前仍限定为 Gazebo 纯仿真；不得声称真实 follower、真实抓取成功率或 `trainable_real`。

### Current Baseline

- `GZV-014`：Gazebo camera -> detector -> `/detections` -> `/vision/targets` -> task status 触发闭环已通过。
- `GZV-015`：程序化轨迹发布与 Gazebo `/joint_states` 实际运动已通过。
- `GZV-016`：实时 overlay topic `/vision/debug/image_overlay` 已通过。
- 当前动作仍主要来自 waypoint/template，`/vision/targets` 主要用于触发和记录；下一步要让 target xyz 真正参与动作生成和评价。

### Architecture Decision

Use a benchmark harness architecture:

```text
PerceptionAdapter -> GraspProposalAdapter -> MotionPlannerBackend -> Executor -> Evaluator -> EpisodeRecorder
```

This keeps mature algorithms pluggable and makes comparisons meaningful.

### Metric Decision

Metrics must be layered:

- L1 `reach_success`: gripper TCP approaches target.
- L2 `contact_success`: gripper/object contact or distance proxy.
- L3 `enclosure_success`: target enclosed by fingers.
- L4 `lift_success`: target z increases.
- L5 `place_success`: target reaches place region.

First implementation should require only L1 reach, because Gazebo grasp/contact physics may be unstable.

### Backend Priority

1. Programmatic target-driven reach baseline.
2. MoveIt Task Constructor baseline.
3. Grasp proposal adapter for GraspNet/AnyGrasp/Dex-Net-style models.
4. cuRobo/cuMotion feasibility and backend.
5. LeRobot `trainable_smoke` dataset and policy baselines.

### Open Technical Questions

- Which URDF frame is the best gripper TCP frame for L1 reach distance?
- Are Gazebo model/link/contact states available and stable enough for L2-L5?
- Should first target-driven reach baseline use simple joint mapping or MoveIt IK?
- Is MoveIt Task Constructor installed in the current ROS Humble environment?
- How should new candidate/metrics fields attach to existing vision episode recorder and dataset adapter?

---


## Current Architecture Findings

- 前端对应仿真链已经存在：前端/runtime 能启动和观察 Gazebo、RViz、仿真状态。
- 实物主臂对应 RViz 链已经存在：`/leader/joint_states -> /joint_states` 镜像和 RViz/replay 入口已具备。
- 视觉链路不是零实现：已有 YOLOv8 detector、mock detector、后端 rosbridge `/detections` 订阅、前端视觉控制台和 task trigger。
- 原视觉缺口是 Gazebo 没有 ROS 相机图像源，旧 `so101_workcell.world` 只有 GUI camera，不会发布 `/camera/color/image_raw`。
- 2026-04-26 已新增 Gazebo 固定俯视 RGB camera，插件日志确认发布 `/camera/color/camera_info`。
- 2026-04-26 已新增 `sim_color_detector_node.py`，用于无训练模型时从 Gazebo RGB 图像中检测红/蓝目标并发布 `/detections`。
- 2026-04-27 已形成 Gazebo vision episode -> dataset adapter：`dataset-index.json` 负责索引与质量状态，`samples.jsonl` 负责 image snapshot、detection、vision target、joint_state、task_status 的逐样本对齐。
- 当前 `gzv005_smoke_20260427_003158` 转换结果关键流不缺失，但存在对齐告警；这说明链路已可产生训练前置资产，但进入 golden/LeRobot 前仍需要同步质量门槛。
- 2026-04-27 已形成 LeRobot candidate exporter：`warn` 样本默认只进入 debug，不进入 train；追加 per-stream threshold 后，旧 15 个仿真视觉样本中有 8 个满足 train 口径。
- 2026-04-27 采集同步质量提升后，旧 15 样本 episode 按 per-stream threshold 可训练样本提升到 8；新采集 `gzv010_sync_smoke_20260427_010005` 在 8 个 snapshot 中有 7 个进入 train，且 detection / vision_target / joint_state 均无超时。
- 2026-04-27 `/mes_task_status` heartbeat 后，新采集 `gzv011_status_heartbeat_smoke_20260427_010757` 达到 dataset validation `passed`，LeRobot candidate `train_sample_count=9`、`debug_sample_count=0`。
- 2026-04-27 前端已对 `heartbeat=true` 降噪：heartbeat 刷新状态时间，不进入系统事件流，不触发订单刷新。
- 本机 `lerobot` 包存在，但 native LeRobotDataset import 被 `pandas` / `numpy` 版本冲突阻塞；当前不能声称已经生成原生 LeRobot v3 dataset。
- `RLG-001` 离线桥接链已具备：历史 leader recording replay 发布 `/leader/joint_states`，`leader_to_gazebo_bridge.py` 转成短 horizon `FollowJointTrajectory` action goal，Gazebo `joint_trajectory_controller` 可连续接受并成功完成。
- 2026-05-08 已完成实物主臂到 Gazebo simulated arm 的方向映射现场确认：`leader_position_scales=[1.0,1.0,1.0,1.0,-1.0,1.0]`，关节顺序为 `[shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper]`；二轴 `shoulder_lift` 不反，五轴 `wrist_roll` 反向。
- leader-only episode 软件链已经具备：
  - recorder
  - replay validator v2
  - source episode quality gate
  - L1 headless replay
  - replay diagnostics
  - manifest
- 当前主缺口从“bridge 不存在”收窄为“真实 leader live 输入尚未实测，live source quality gate 仍待正式扩展”。

## Replay Quality Findings

- `header.stamp`、topic/action、录制窗口污染已排查过。
- 最新诊断修正后，controller state 必须按绝对 `stamp_ns` 对齐到 candidate 录制窗口。
- `elbow_flex` 原 hard fail 的主要根因是源轨迹 peak velocity 超过 URDF limit。
- `wrist_flex` 原 hard fail 的主要根因是源姿态超过 URDF position upper limit。
- 慢速 + URDF clamp 后 L1 replay 已能 `passed`。

## GPU / Training Findings

- 当前机器为 Windows + WSL2，GPU 为 NVIDIA GeForce RTX 3050 Laptop GPU。
- 本机适合：
  - 数据清洗
  - episode/replay/manifest
  - dataset viewer
  - 推理验证
  - 小 batch smoke training
- 本机不适合：
  - 大规模 imitation learning
  - 多相机视频训练
  - VLA/GR00T 类大模型微调
  - 长时间高显存训练
- 正式训练建议：
  - 首选 Colab Pro/Pro+ 跑 LeRobot 示例与轻量微调。
  - 需要稳定长时 GPU 时用 RunPod。
  - 工程化和长期资产再考虑 Google Cloud。

## Decisions

| Decision | Rationale |
|----------|-----------|
| 本地前端 E2E 优先使用 Playwright + `/usr/bin/google-chrome` headless | 远端浏览器无法访问本机 `127.0.0.1`，本机 headless Chrome 能真实验证 Vite 页面、WebSocket、点击和截图 |
| 下一阶段主线定为 `RLG: real leader to Gazebo` | 它是实物输入与仿真测试场之间缺失的关键桥 |
| 新增 `GZV: Gazebo vision` 并行主线 | 没有 follower 真机时，视觉图像源、检测链路和数据资产仍可在 Gazebo 中推进 |
| GZV 第一版用固定俯视相机，不先做腕部相机 | 无 follower/末端实物时，俯视相机更稳定，能先验证图像、检测、前后端和数据链 |
| Gazebo 视觉第一版补颜色检测，不强依赖 COCO YOLO | `yolov8n.pt` 不会天然识别项目的红/蓝料盒语义，直接接 YOLO 会造成“有图但无业务检测”的假失败 |
| vision dataset adapter 先输出中间格式，不直接写死 LeRobot schema | 当前还需要暴露时间偏差和质量告警；过早贴 LeRobot schema 会隐藏同步质量问题 |
| `warn` vision samples 默认 debug_only | 同步偏差样本可用于诊断采集链，但不能混入训练样本或 golden 样本 |
| image snapshot 必须由采集端做 readiness gate | 后处理只能过滤坏样本，不能恢复 `/joint_states` 未启动前或 detector 停止后的有效同步样本 |
| `task_status` 使用上下文阈值，不使用视觉帧级阈值 | task status 是低频状态上下文，不能与 camera/detection/joint_state 用同一个 250ms 门槛 |
| `/mes_task_status` 需要 heartbeat | 视觉数据集需要持续任务上下文；复发最后状态并刷新 `ts` 比在 recorder 中丢弃末尾快照更通用 |
| heartbeat 是 freshness signal，不是业务状态转移 | 前端应使用 heartbeat 保持状态新鲜，但不能把它当新事件刷屏 |
| 训练暂不抢主线 | 数据质量、输入可信度、仿真闭环未完全收口前训练价值低 |
| 本机只做训练 smoke | RTX 3050 Laptop GPU 更适合验证链，不适合正式训练 |
| 第一版只做主臂 | follower/视觉会放大定位难度 |
| `RLG-001` 第一版使用 `FollowJointTrajectory` action 短 horizon goal | 与已验证的 L1 replay action 路径一致，且离线 smoke 中 controller 连续返回 success |
| `RLG-005` 实物映射固定为 `[1.0,1.0,1.0,1.0,-1.0,1.0]` | 2026-05-08 现场用 `/dev/ttyUSB0` 主臂低速手掰确认：二轴不反，五轴反；该映射只用于 leader 输入驱动 Gazebo simulated arm，不代表 follower 真机执行 |

## Open Questions

- 真实 leader live smoke 中 `point_horizon_sec` 与 `min_command_period_sec` 的默认值是否需要按手掰噪声调整？
- live stream source quality gate 对超限输入是否保持当前 bridge 口径：position 默认 clamp、velocity 默认 reject？
- 后续转 LeRobot dataset 时，是否保留 replay/manifest/source-quality 作为 sidecar metadata？
- 原生 LeRobot v3 dataset 不需要显式 venv；可用 `uv run --isolated`，但必须清理 ROS 注入的 `PYTHONPATH`，否则临时解释器仍会导入系统 `numpy 1.21.5`。

## Explicit Open Work

| Task | Gap |
|------|-----|
| `TRN-002` native LeRobot v3 dataset | 已用 `uv run --isolated` 完成原生 `LeRobotDataset` 落盘；当前限制转移到 `TRN-003`，即 action 仍是 `vision_target_xyz` 而不是真实执行动作 |
| `TRN-003` action label source | Gazebo executed-state `joint_positions` 标签已接入并导出 native LeRobot；限制是它不是 follower hardware command，真机恢复后仍要替换/增强 |
| `GZV-013` frontend dataset quality panel | 前端静态/注入式质量面板已完成；后续缺后端 latest episode API |
| `RLG-001-live` real leader to Gazebo live smoke | live leader 输入已能驱动 Gazebo simulated arm，RLG-005 方向映射已收口；仍待录制 10-30 秒 episode 才能关闭 RLG-003 |
| `YOL-004` real YOLO loop | YOLO dataset smoke、train/predict smoke 和前端 latest artifact 展示已完成；真实训练质量闭环仍未完成，仿真业务检测仍依赖颜色检测器 |
| `OPS-002` commit/evidence policy | 证据策略和 git status 分类脚本已完成；实际分批提交尚未执行 |

## Resources

- `docs/plans/2026-04-26-real-leader-to-gazebo-and-training-plan.md`
- `docs/plans/2026-04-15-low-spec-wsl-sim-plan.md`
- `docs/plans/2026-04-09-episode-closure.md`
- `tools/hardware/source_episode_quality_gate.py`
- `tools/hardware/run_headless_sim_replay_episode.py`
