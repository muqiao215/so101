# Progress Log

## 2026-05-08 - Validation: RLG-005 Live Leader To Gazebo Direction Mapping

- Live `so101_leader` on `/dev/ttyUSB0` was used only as an input device for the Gazebo simulated arm.
- `leader_input_bridge.launch.py port:=/dev/ttyUSB0` reported `READY connected=True calibrated=True publishing=True`.
- `/leader/joint_states` published at about 30 Hz.
- `leader_to_gazebo.launch.py` spawned the Gazebo `so101` model and the `joint_trajectory_controller` continuously accepted and completed short-horizon action goals.
- Confirmed real-leader-to-Gazebo mapping:
  - joint order: `[shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper]`
  - `leader_position_scales=[1.0,1.0,1.0,1.0,-1.0,1.0]`
  - `leader_position_offsets=[0.0,0.0,0.0,0.0,0.0,0.0]`
  - axis 2 / `shoulder_lift` is not inverted.
  - axis 5 / `wrist_roll` is inverted.
- Scope remains live leader input driving a Gazebo simulated arm. This is not follower execution, real grasp success, real YOLO quality closure, or `trainable_real`.

## 2026-05-07 - Implementation: GZV-018F Multi-Episode Suite Runner

- Added `tools/e2e/run_mtc_reach_benchmark_suite.py`, a multi-episode wrapper around `mtc_reach_benchmark.launch.py`.
- Runner supports target jitter, deterministic seed, per-episode artifact directories, failure classification, and aggregate `summary_report.yaml`.
- Episode artifacts include `report.yaml`, `tcp_trace.csv`, `joint_trace.csv`, `selected_candidate.yaml`, `planned_goal_proxy.yaml`, `execution_grounded_metrics.yaml`, `target.json`, and `command.txt`.
- Smoke output `docs/generated/vision-episodes/mtc-reach-suite-20260507-smoke/summary_report.yaml`: `total_episodes=1`, `planning_success_rate=1.0`, `trajectory_execution_success_rate=1.0`, `controller_converged_rate=1.0`, `reach_success_rate=1.0`, `mean_min_distance_m=0.06583573984782319`.
- Scope remains Gazebo execution-grounded simulated reach benchmark. This does not establish robustness yet; larger randomized suites are next.

## 2026-05-07 - Validation: GZV-018F Jitter20 Execution-Grounded Suite

- Fixed runner robustness issues discovered during longer runs:
  - timeout path no longer crashes on bytes/str mismatch.
  - per-episode launch is now terminated after report is written, instead of waiting for long-lived Gazebo/move_group processes.
  - joint trace CSV export no longer includes non-declared fields.
- Ran 2-episode jitter verification first, then full 20-episode jitter suite:
  - `python3 tools/e2e/run_mtc_reach_benchmark_suite.py --episode-count 20 --output-dir docs/generated/vision-episodes/mtc-reach-suite-20260507-jitter20 --suite-name mtc-reach-suite-20260507-jitter20 --target-xyz 0.32,0.18,0.8 --jitter-xyz 0.01,0.01,0.0 --seed 20 --timeout-sec 180`
- `summary_report.yaml` results:
  - `total_episodes=20`
  - `planning_success_rate=1.0`
  - `trajectory_execution_success_rate=1.0`
  - `controller_converged_rate=1.0`
  - `execution_success_rate=1.0`
  - `reach_success_rate=1.0`
  - `mean_min_distance_m=0.057951129453973016`
  - `p90_min_distance_m=0.07204289494184068`
  - `max_min_distance_m=0.07357325380813022`
  - `failure_reason_counts={}`
- Verified artifact completeness: all 20 episode directories include `report.yaml`, `tcp_trace.csv`, `joint_trace.csv`, `selected_candidate.yaml`, `planned_goal_proxy.yaml`, `execution_grounded_metrics.yaml`, `target.json`, `command.txt`.

## 2026-05-07 - Validation: GZV-018G Jitter50 Execution-Grounded Suite

- Ran 50-episode jitter suite:
  - `python3 tools/e2e/run_mtc_reach_benchmark_suite.py --episode-count 50 --output-dir docs/generated/vision-episodes/mtc-reach-suite-20260507-jitter50 --suite-name mtc-reach-suite-20260507-jitter50 --target-xyz 0.32,0.18,0.8 --jitter-xyz 0.01,0.01,0.0 --seed 20 --timeout-sec 180`
- Summary results (`summary_report.yaml`):
  - `total_episodes=50`
  - `planning_success_rate=1.0`
  - `trajectory_execution_success_rate=0.96`
  - `controller_converged_rate=0.96`
  - `execution_success_rate=0.96`
  - `reach_success_rate=1.0`
  - `mean_min_distance_m=0.05641791260679569`
  - `p90_min_distance_m=0.07341615370443462`
  - `max_min_distance_m=0.07653105055293548`
  - `failure_reason_counts={trajectory_publish_failed: 2}`
- Notable detail: episodes 48 and 49 reported `trajectory_execution_success=false` / `controller_converged=false` with failure reason `trajectory_publish_failed`, while reported `reach_success` remained true under the same L1 threshold.
- Scope remains Gazebo execution-grounded simulated reach benchmark; not real hardware, not grasp/lift/place, not `trainable_real`.

## 2026-05-07 - Implementation: GZV-018E Execution-Grounded Reach

- Added execution trace support to `mtc_reach_benchmark_node.cpp`: publish the selected MTC joint goal to `/joint_trajectory_controller/joint_trajectory`, subscribe to `/joint_states`, compute FK TCP samples, and evaluate L1 reach on actual simulated execution.
- Added report fields for `trajectory_execution_success`, `controller_converged`, `execution_trace.sample_count`, actual TCP trace, joint tracking error, planned-goal proxy metrics, and execution-grounded evaluator scope.
- Added `sensor_msgs` and `trajectory_msgs` dependencies, and exposed execution parameters in `mtc_reach_benchmark.launch.py`.
- Verified `so101_moveit_config` builds successfully.
- Ran Gazebo/MTC execution smoke: `docs/generated/vision-episodes/mtc-execution-reach-benchmark-report-20260507.yaml` shows `planning_success=true`, `execution_success=true`, `controller_converged=true`, `reach_success=true`, `min_distance_m=0.06684279743349834`, and `sample_count=80`.
- Scope remains Gazebo execution-grounded benchmark smoke. This is not a real follower loop, real grasp success rate, contact/lift/place, or `trainable_real`.

## 2026-05-07 - Implementation: GZV-018D Vision Target Position-Only Reach

- Expanded MTC Cartesian candidate diagnostics from target-centered pose IK into a two-layer search: pose IK candidates first, then position-only FK sample fallback when pose IK is too strict.
- Removed the home TCP as a valid fallback candidate so `planned` cannot silently mean “returned to home but still reported a solution”.
- Expanded the FK sample grid across the full shoulder pan range; the vision canonical target now finds `selected_candidate_id=18` within threshold.
- Verified `docs/generated/vision-episodes/mtc-cartesian-reach-benchmark-report-20260507.yaml`: `diagnostic_level=position_only_cartesian_ik_reach`, `planning_success=true`, `reach_success=true`, `min_distance_m=0.07945588278083793`, `threshold_m=0.08`, `result_label=trainable_smoke`.
- Scope remains planned-goal Gazebo/MTC benchmark smoke. `execution_success` is still null until Gazebo trajectory execution trace is wired into this backend.

## 2026-05-07 - Implementation: GZV-018C Oracle Reach Sanity

- Added `target_mode` launch passthrough for `mtc_reach_benchmark_node`, including `oracle_near_home` mode for a hand-written near-home target sanity check.
- Extended the MTC report with IK candidate debug artifacts and top-level split metrics: `planning_success`, `execution_success`, `reach_success`, `min_distance_m`, and `selected_candidate_id`.
- Verified `so101_moveit_config` builds successfully with `source /opt/ros/humble/setup.bash && colcon build --packages-select so101_moveit_config`.
- Ran oracle smoke with `target_mode:=oracle_near_home`; `docs/generated/vision-episodes/mtc-oracle-reach-benchmark-report-20260507.yaml` reports `status=planned`, `solution_count=1`, `planning_success=true`, `reach_success=true`, `selected_candidate_id=0`, and `min_distance_m=0`.
- Scope remains Gazebo/MTC planned-goal benchmark smoke. This is not a real grasp, not a real follower closure, and not `trainable_real`.

## 2026-05-07 - Implementation: GZV-018B Cartesian IK MTC Baseline

### Action

- Added launch parameters for `backend_mode`, `ik_frame`, `reach_threshold_m`, and `target_base_z_offset` so MTC backend probes actually reach the node.
- Added `cartesian_ik_move_to` backend mode: it uses `RobotState.setFromIK` on target-driven Cartesian candidates, then sends the resulting IK joint goal through MTC `MoveTo`.
- Added IK candidate attempts, home TCP world/base coordinates, selected Cartesian candidate, and backend comparison fields to the YAML report.
- Fixed evaluator gating so failed planning cannot emit `reach_success=true`; metrics now use the selected Cartesian candidate rather than the original target when MTC falls back.

### Verification

- `source /opt/ros/humble/setup.bash && colcon build --packages-select so101_moveit_config`
  - `Summary: 1 package finished`.
- `source /opt/ros/humble/setup.bash && source install/setup.bash && timeout 140s ros2 launch so101_moveit_config mtc_reach_benchmark.launch.py report_path:=docs/generated/vision-episodes/mtc-cartesian-reach-benchmark-report-20260507.yaml target_xyz:='[0.32,0.18,0.8]' backend_mode:=cartesian_ik_move_to use_rviz:=false use_gzclient:=false`
  - launch timed out because Gazebo/move_group are long-running, but `mtc_reach_benchmark_node` exited cleanly.
  - report shows `diagnostic_level=cartesian_ik_reach_smoke`, `status=planned`, `solution_count=1`, `reach_success=false`, `min_distance_m=0.172742`.

### Current Conclusion

- MTC has advanced from joint-goal smoke to Cartesian-IK-driven planning smoke.
- It is not yet a successful reach baseline under the shared evaluator; next work is improving Cartesian candidate generation/IK seeds and wiring execution trace.

## 2026-05-07 - Implementation: GZV-018 Minimum MTC Joint-Goal Smoke

### Action

- Added structured diagnostic reporting to `mtc_reach_benchmark_node.cpp`, including failure phase/type/message/details for MTC init/plan exceptions.
- Confirmed the Cartesian `FixedCartesianPoses -> ComputeIK -> Connect` chain failed due to MTC stage interface mismatch.
- Replaced the first runnable baseline with `FixedState(home) -> MoveTo(target-driven joint goal)` so `GZV-018` has a minimal planned MTC backend without claiming Cartesian grasp capability.
- Generated `docs/generated/vision-episodes/mtc-reach-benchmark-report-20260507.yaml` as the current MTC benchmark evidence.

### Verification

- `source /opt/ros/humble/setup.bash && colcon build --packages-select so101_moveit_config`
  - `Summary: 1 package finished`.
- `source /opt/ros/humble/setup.bash && source install/setup.bash && timeout 140s ros2 launch so101_moveit_config mtc_reach_benchmark.launch.py report_path:=docs/generated/vision-episodes/mtc-reach-benchmark-report-20260507.yaml target_xyz:='[0.32,0.18,0.8]' use_rviz:=false use_gzclient:=false`
  - launch timed out because Gazebo/move_group are long-running, but `mtc_reach_benchmark_node` exited cleanly after writing the report.
  - report shows `diagnostic_level=joint_goal_smoke`, `status=planned`, `solution_count=1`.

### Current Conclusion

- `GZV-018` minimum MTC baseline is complete only as a target-driven joint-goal planning smoke.
- Cartesian reach/grasp MTC stages remain follow-up work and must reuse the same report/evaluator vocabulary before any success claim.

## 2026-05-07 - Review Fix: Patch Safety And Target Alignment

### Action

- Fixed review issue P1 by ensuring `src/so101_moveit_config/src/mtc_reach_benchmark_node.cpp` is part of the working patch instead of leaving CMake pointing at an untracked missing source.
- Fixed review issue P2 by adding the new MTC benchmark executable dependencies to `src/so101_moveit_config/package.xml`.
- Fixed review issue P2 in the LeRobot candidate exporter: benchmark canonical target is now used as primary `action.target_xyz` only when it matches the currently selected target object; non-default-category exports fall back to the selected vision target and clear benchmark-only action result fields.
- Added a multi-object/non-default-category regression test.

### Verification

- `python3 -m unittest tools/hardware/test_export_vision_dataset_to_lerobot_candidate.py -v`
  - 3 tests OK.
- `source /opt/ros/humble/setup.bash && colcon build --packages-select so101_moveit_config`
  - `Summary: 1 package finished`.

### Current Conclusion

- The review blockers are addressed at code/build level.
- `GZV-018` remains an optional experimental MTC backend until a planned smoke produces `status=planned`; current validated result is buildability, not MTC reach success.

## 2026-05-06 - Implementation: GZV-017C Recorder/Dataset Upgrade

### Action

- Added benchmark result topic publishing in `task_executor.py`.
- Extended `vision_episode_recorder_node.py` to record `/sim_grasp/benchmark_result`.
- Extended `build_vision_dataset_adapter.py` to attach `benchmark_result` to each sample.
- Extended `export_vision_dataset_to_lerobot_candidate.py` to preserve benchmark action/result metadata.
- Ran a fresh recorder smoke episode with benchmark enabled.

### Result

- New episode:
  - `docs/generated/vision-episodes/gzv017c_benchmark_smoke_20260506/`
- `manifest.json` now counts `benchmark_result`.
- `dataset/samples.jsonl` now includes benchmark target/candidate/plan/execution/evaluation trace.
- candidate export now includes `result_label=trainable_smoke`, selected candidate id, and uses canonical benchmark `target_xyz` while preserving `raw_target_xyz`.

### Follow-up

- Candidate primary action was then switched from raw projector target to benchmark canonical target.
- Verified real export row now shows:
  - `action.target_xyz=[0.32, 0.1832, 0.8]`
  - `action.raw_target_xyz=[0.6516, 0.1832, 0.8]`

### Verification

- Tests:
  - `python3 -m unittest src/so101_bringup/test/test_vision_episode_recorder.py tools/hardware/test_build_vision_dataset_adapter.py tools/hardware/test_export_vision_dataset_to_lerobot_candidate.py -v`
  - 13 tests OK
- Syntax:
  - `python3 -m py_compile src/so101_bringup/scripts/task_executor.py src/so101_bringup/scripts/vision_episode_recorder_node.py src/so101_bringup/launch/sim_bringup.launch.py tools/hardware/build_vision_dataset_adapter.py tools/hardware/export_vision_dataset_to_lerobot_candidate.py`
- Build:
  - `source /opt/ros/humble/setup.bash && colcon build --packages-select so101_bringup`
  - `Summary: 1 package finished`
- Recorder smoke:
  - `DETECTION_BACKEND=gazebo_color USE_VISION_EPISODE_RECORDER=true VISION_EPISODE_ID=gzv017c_benchmark_smoke_20260506 BENCHMARK_REACH_ENABLED=true BENCHMARK_TRIGGER_COOLDOWN_SEC=4.0 BENCHMARK_REACH_THRESHOLD_M=0.12 bash tools/e2e/start_sim_vision_stack.sh`
  - stop after capture window
  - `python3 tools/hardware/build_vision_dataset_adapter.py docs/generated/vision-episodes/gzv017c_benchmark_smoke_20260506 --max-delta-sec 0.25 --max-task-status-delta-sec 2.0`
  - `python3 tools/hardware/export_vision_dataset_to_lerobot_candidate.py docs/generated/vision-episodes/gzv017c_benchmark_smoke_20260506/dataset/dataset-index.json --warn-policy debug_only --target-category red --fps 5.0`
- Result:
  - dataset validation `passed`
  - candidate `train_sample_count=6`
  - benchmark result stream persisted end-to-end

### Next Step

- Decide whether candidate primary action should remain raw `vision_target_xyz` or migrate to canonical target / executed joint action.
- Add viewer/artifact summary for benchmark failure reasons.

## 2026-05-07 - GZV-017C Viewer Summary Closure

### Action

- Reused `tools/hardware/build_episode_viewer.py` instead of creating a new viewer path.
- Added `benchmark_summary` to viewer data, exposing:
  - `reach_success`
  - `min_distance_m`
  - `selected_candidate_id`
  - `canonical_target_xyz`
  - `raw_target_xyz`
- Rebuilt the viewer for:
  - `docs/generated/vision-episodes/gzv017c_benchmark_smoke_20260506/dataset/dataset-index.json`

### Result

- Viewer manifest:
  - `docs/generated/vision-episodes/gzv017c_benchmark_smoke_20260506/dataset/viewer/index.html`
  - `docs/generated/vision-episodes/gzv017c_benchmark_smoke_20260506/dataset/viewer/viewer-data.json`
- The viewer data now directly exposes benchmark closure fields per sample.

### Verification

- Tests:
  - `python3 -m unittest tools/hardware/test_build_episode_viewer.py tools/hardware/test_build_vision_dataset_adapter.py tools/hardware/test_export_vision_dataset_to_lerobot_candidate.py src/so101_bringup/test/test_vision_episode_recorder.py -v`
  - 14 tests OK
- Real viewer rebuild:
  - `python3 tools/hardware/build_episode_viewer.py docs/generated/vision-episodes/gzv017c_benchmark_smoke_20260506/dataset/dataset-index.json`
- Spot check:
  - `viewer-data.json` sample now shows `reach_success=true`、`min_distance_m=0.070547`、`selected_candidate_id=red_reach_baseline`、`canonical_target_xyz=[0.32,0.1832,0.8]`、`raw_target_xyz=[0.6516,0.1832,0.8]`

### Current Conclusion

- `GZV-017C` is closed for this benchmark phase:
  - recorder
  - dataset
  - candidate export
  - viewer summary
- Remaining future question is no longer visibility; it is whether to keep canonical target as the primary action or move to executed joint action.

---

## 2026-05-06 - Implementation: GZV-017A/B Minimum Runnable Benchmark

### Action

- Added `src/so101_bringup/scripts/sim_grasp_benchmark.py` for:
  - target selection
  - grasp candidate baseline
  - target-driven trajectory planning
  - L1 reach evaluator
  - artifact generation
- Extended `task_executor.py` with a new `/vision/targets` driven benchmark path gated by `benchmark_reach_enabled`.
- Added `create_multi_point_trajectory_message()` in `trajectory_builder.py`.
- Extended `sim_bringup.launch.py`, `start_visible_demo_stack.sh`, `start_sim_vision_stack.sh`, and `assert_sim_vision_closed_loop.py` to support the benchmark path and `bench-*` request prefix assertions.
- Kept the old detection-template execution path intact when `benchmark_reach_enabled=false`.

### Result

- `/vision/targets` can now drive a minimum runnable programmatic reach baseline:
  - select `target_object`
  - generate `grasp_candidate`
  - generate target-driven multi-point trajectory
  - publish trajectory to `/joint_trajectory_controller/joint_trajectory`
  - evaluate `reach_success`
  - write benchmark artifact JSON
- The benchmark artifact preserves both:
  - `raw_world_xyz`
  - canonicalized benchmark `world_xyz`
- Output label remains `trainable_smoke`.

### Verification

- Unit tests:
  - `python3 -m unittest src/so101_bringup/test/test_sim_grasp_benchmark.py src/so101_bringup/test/test_trajectory_builder.py tools/e2e/test_assert_sim_vision_closed_loop.py -v`
  - 7 tests OK
- Affected regression tests:
  - `python3 -m unittest src/so101_bringup/test/test_task_execution_service.py src/so101_bringup/test/test_detection_trigger_policy.py src/so101_bringup/test/test_vision_target_projector.py src/so101_bringup/test/test_task_status_publisher.py -v`
  - 6 tests OK
- Syntax:
  - `python3 -m py_compile src/so101_bringup/scripts/sim_grasp_benchmark.py src/so101_bringup/scripts/task_executor.py src/so101_bringup/scripts/trajectory_builder.py src/so101_bringup/launch/sim_bringup.launch.py tools/e2e/assert_sim_vision_closed_loop.py`
- Build:
  - `source /opt/ros/humble/setup.bash && colcon build --packages-select so101_bringup`
  - `Summary: 1 package finished`
- Gazebo smoke:
  - `DETECTION_BACKEND=gazebo_color USE_VISION_EPISODE_RECORDER=false BENCHMARK_REACH_ENABLED=true BENCHMARK_TRIGGER_COOLDOWN_SEC=4.0 BENCHMARK_REACH_THRESHOLD_M=0.12 bash tools/e2e/start_sim_vision_stack.sh`
  - `python3 tools/e2e/assert_sim_vision_closed_loop.py --detection-backend gazebo_color --require-task-close --require-trajectory-command --require-joint-motion --require-overlay-image --task-request-prefix bench- --min-joint-delta 0.03 --timeout-sec 180 --report-path docs/generated/vision-episodes/sim-grasp-benchmark-closed-loop-gazebo-color-20260506.json`
  - result: `status=passed`

### Next Step

- Upgrade `vision_episode_recorder_node.py` / dataset path for `GZV-017C`, so benchmark target/candidate/metrics/action can enter the existing episode and dataset pipeline instead of only benchmark JSON.

---

## 2026-05-06 - Planning Only: Sim Grasp Benchmark Harness

### Action

- Used `planning-with-files` skill at user request: “plan with files先”.
- Ran session catchup; no unsynced context was reported.
- Read current `task_plan.md`, `findings.md`, `progress.md`, `docs/任务清单.md`, and `docs/进度日志.md` context.
- Rewrote `task_plan.md` to focus on `SO101 Sim Grasp Benchmark Harness`.
- Prepended current architecture findings to `findings.md`.
- Prepended this progress entry to `progress.md`.

### Result

- No code changes were made in this planning pass.
- The plan now defines phases for:
  - `GZV-017A` target-driven reach baseline
  - `GZV-017B` grasp/reach evaluator
  - `GZV-017C` episode recorder upgrade
  - `GZV-018` MoveIt Task Constructor baseline
  - later GraspNet/AnyGrasp/Dex-Net, cuRobo/cuMotion, and LeRobot policy bridges

### Next Step

- Before implementation, inspect gripper TCP frame, Gazebo state topics, existing MoveIt config, and episode recorder extension points.
- Then implement Phase 1 schema and `GZV-017A/B` minimum reach benchmark.

---


## Session: 2026-04-26

### Phase 2C: GZV-006 Frontend Simulation Vision Path

- **Status:** complete
- **Started:** 2026-04-27
- Actions taken:
  - 前端新增 `gazebo_color_detector` 来源语义，显示为 `Gazebo 仿真视觉`。
  - `VisionConsolePanel` 增加 Gazebo 仿真视觉说明，不再把它混同于真实 YOLO。
  - backend `SimulationRuntimeService.startSimulation()` 默认以 `use_gazebo_color_detector:=true` 启动仿真。
  - backend stop 路径清理 `sim_color_detector_node.py`。
  - Playwright 浏览器自测主页面：点击“连接实时状态”后，最新回传显示 `Gazebo 仿真视觉`、`red`、`pick_place_red`，状态时间线出现检测触发。
  - Playwright 浏览器自测开发工作台：修复并确认 `getDetectionSourceMeta` 不再触发 Vue render warning。
- Remaining:
  - 从浏览器实际点击“启动仿真”做一次端到端截图/日志证据。
  - 进入 `GZV-004`：pixel center -> table target。

### Phase 2D: GZV-004 Vision Target Projection

- **Status:** complete
- **Started:** 2026-04-27
- Actions taken:
  - 新增 `vision_target_projector_node.py`，订阅 `/detections`，发布 `/vision/targets`。
  - 第一版固定俯视 pinhole projection 将 bbox center 投影到 `table_z=0.80`。
  - backend 订阅 `/vision/targets` 并广播 `/topic/vision-targets`。
  - frontend 订阅 `/topic/vision-targets`，视觉卡片新增 `TARGET` world 坐标。
  - Playwright headless Chrome 端到端验证页面显示目标坐标。
- Remaining:
  - 将 projection 参数外置成 calibration/config 文件。
  - 进入 `GZV-005` 数据采集链。

### Phase 2E: GZV-005 Vision Episode Recording

- **Status:** complete
- **Started:** 2026-04-27
- Actions taken:
  - 新增 `vision_episode_recorder_node.py`。
  - 记录 `/camera/color/image_raw` metadata/snapshots、`/detections`、`/vision/targets`、`/mes_task_status`、`/joint_states`。
  - 输出 `events.jsonl`、`manifest.json` 与低频 JPEG snapshots。
  - `sim_bringup.launch.py` 和 `start_sim_vision_stack.sh` 增加显式采集开关。
  - 产出 smoke episode：`docs/generated/vision-episodes/gzv005_smoke_20260427_003158/`。
- Remaining:
  - 做 episode viewer / validator。
  - 对齐 LeRobot/dataset schema。

### Phase 2F: GZV-007 Vision Episode Validator / Viewer

- **Status:** complete
- **Started:** 2026-04-27
- Actions taken:
  - 新增 `tools/hardware/validate_vision_episode.py`。
  - 新增 `tools/hardware/test_validate_vision_episode.py`。
  - 对 `docs/generated/vision-episodes/gzv005_smoke_20260427_003158` 生成 `validation-report.json` 和 `REPORT.md`。
  - validator 状态为 `warn`，无 errors；关键流齐全。
- Remaining:
  - 后续 dataset 转换时按 stream/stamp 做更严格时间对齐，不直接依赖全局 receive wall time。

### Phase 2G: GZV-008 Vision Dataset Adapter

- **Status:** complete
- **Started:** 2026-04-27
- Actions taken:
  - 新增 `tools/hardware/build_vision_dataset_adapter.py`。
  - 新增 `tools/hardware/test_build_vision_dataset_adapter.py`。
  - 将 `docs/generated/vision-episodes/gzv005_smoke_20260427_003158` 转换为 `dataset/dataset-index.json` 与 `dataset/samples.jsonl`。
  - 默认以带 snapshot 的 image event 为样本锚点，对齐 detection、vision target、joint_state、task_status。
  - 每条样本保留时间偏差字段，dataset index 汇总缺失流和超阈值对齐告警。
- Result:
  - `sample_count=15`。
  - 关键流缺失均为 0。
  - `validation.status=warn`，原因是部分样本的 `joint_state` 或 `task_status` 时间差超过 250ms。
- Remaining:
  - 后续 LeRobot converter 需要基于该中间格式做 schema 映射，并决定是否丢弃 `warn` 样本或提高采集频率。

### Phase 2H: GZV-009 / TRN-001 LeRobot Candidate Export

- **Status:** complete
- **Started:** 2026-04-27
- Actions taken:
  - 新增 `tools/hardware/export_vision_dataset_to_lerobot_candidate.py`。
  - 新增 `tools/hardware/test_export_vision_dataset_to_lerobot_candidate.py`。
  - 将 GZV-008 的 `dataset-index.json` + `samples.jsonl` 导出成 `lerobot-candidate` 包。
  - 默认 `warn_policy=debug_only`，`warn` 样本保留为 debug，不进入 train，也不得晋升 golden。
  - candidate sample 的 `action.type=vision_target_xyz`，明确它是目标候选坐标，不是真实 follower 关节动作。
- Result:
  - `sample_count=15`。
  - `train_sample_count=8`。
  - `debug_sample_count=7`。
  - `rejected_sample_count=0`。
  - native LeRobotDataset 写入被本机 `pandas` / `numpy` 版本冲突阻塞，已写入 manifest。
- Remaining:
  - 如果要生成原生 LeRobot v3 dataset，需要先固定 Python 依赖环境。
  - 如果要训练动作策略，需要接入 follower action 或真实/仿真执行动作标签。

### Phase 2I: GZV-010 Vision Capture Sync Quality

- **Status:** complete
- **Started:** 2026-04-27
- Actions taken:
  - `vision_episode_recorder_node.py` 新增 snapshot readiness gate。
  - 默认只在 `detections`、`vision_targets`、`joint_states` 已出现且最近 0.75s 内更新时保存 snapshot。
  - `sim_bringup.launch.py` 和 e2e 启动脚本暴露 snapshot sync 参数。
  - dataset adapter 新增 per-stream delta threshold，`task_status` 默认按 2.0s 低频上下文处理。
  - LeRobot candidate exporter 读取并记录 per-stream threshold。
- Result:
  - 新 smoke `gzv010_sync_smoke_20260427_010005` 生成 `sample_count=8`。
  - `detection/vision_target/joint_state` large_delta 均为 0。
  - candidate 导出 `train_sample_count=7`、`debug_sample_count=1`、`rejected_sample_count=0`。
- Remaining:
  - 若要把最后 1 个 debug 也消掉，应给 `task_status` 增加 heartbeat 或在采集结束前停止 snapshot。

### Phase 2J: GZV-011 MES Task Status Heartbeat

- **Status:** complete
- **Started:** 2026-04-27
- Actions taken:
  - `TaskStatusPublisher` 新增 `heartbeat()`，复发最后状态并刷新 `ts`。
  - `task_executor.py` 默认开启 1.0s `/mes_task_status` heartbeat。
  - `sim_bringup.launch.py` 和 e2e 启动脚本暴露 heartbeat 参数。
  - 新增 `test_task_status_publisher.py`。
- Result:
  - 新 smoke `gzv011_status_heartbeat_smoke_20260427_010757` 记录 35 条 status heartbeat。
  - dataset adapter validation `passed`。
  - candidate 导出 `sample_count=9`、`train_sample_count=9`、`debug_sample_count=0`、`rejected_sample_count=0`。
- Remaining:
  - 后续可在前端对 `heartbeat=true` 降噪显示，避免实时事件流刷屏；当前不影响数据采集。

### Phase 2K: GZV-012 Frontend Heartbeat Denoise

- **Status:** complete
- **Started:** 2026-04-27
- Actions taken:
  - `useRealtimeFeed.js` 识别 task status `heartbeat=true`。
  - heartbeat 不进入系统事件流，不触发 `refreshOrders()`。
  - `useEventFeed.js` 对同一 `requestId/code/message` heartbeat 只刷新已有状态条目。
  - 新增 `useEventFeed.test.js`。
- Result:
  - heartbeat 保留状态新鲜度，但不制造 UI 事件噪声。
- Remaining:
  - 如果需要更强可视化，可在状态条目上显示 `heartbeatCount`，当前先不增加界面复杂度。

### Phase 2B: GZV-001/GZV-002 Gazebo Vision Minimum Loop

- **Status:** in_progress
- **Started:** 2026-04-26
- Actions taken:
  - 在 `so101_workcell.world` 加入 `overhead_vision_camera` 固定俯视 RGB camera。
  - Gazebo ROS camera 插件发布口径固定为 `/camera/color/image_raw` 与 `/camera/color/camera_info`。
  - 新增 `sim_color_detector_node.py`，用红/蓝颜色阈值从 Gazebo RGB 图像生成 `/detections`。
  - `sim_bringup.launch.py` 增加 `use_gazebo_color_detector`、`use_real_yolo`、`camera_image_topic`、`detections_topic`、`yolo_model_path`、`yolo_device`。
  - `start_visible_demo_stack.sh` 支持显式视觉源与 `ENABLE_ROSBRIDGE=false`。
  - 新增 `tools/e2e/start_sim_vision_stack.sh`，用于无 GUI、无前后端、无 rosbridge 的 Gazebo 视觉核心启动。
- Remaining:
  - 补 ROS CLI 级别 image topic 自动断言。
  - 后续做相机标定/TF 和像素到桌面坐标桥接。

### Phase 2: RLG-001 Minimal Bridge

- **Status:** in_progress
- **Started:** 2026-04-26
- Actions taken:
  - 新增 `leader_to_gazebo_bridge.py`：
    - `/leader/joint_states` 输入。
    - `FollowJointTrajectory` action 短 horizon 输出。
    - joint_names 校验、URDF limit clamp、velocity gate、status JSON。
  - 新增 `leader_to_gazebo.launch.py`：
    - Gazebo scene + controller spawner + bridge。
    - 可选 `leader_recording_replay.py` 离线驱动。
  - 新增 `test_leader_to_gazebo_bridge.py` 覆盖 mapping、limit gate、短 horizon trajectory 与 status payload。
  - 更新 `CMakeLists.txt` 安装新 bridge。
  - 已用历史 `elbow_flex_probe_stretch25_clamped.jsonl` 完成离线 replay smoke：
    - bridge ready。
    - Gazebo `joint_trajectory_controller` 连续接受 action goal。
    - controller 输出 `Goal reached, success!`。
  - 更新正式追踪文件：
    - `docs/任务清单.md`
    - `docs/进度日志.md`
- Remaining:
  - 真实 leader 真机输入尚未实测，所以 `RLG-001` 在正式看板保持 `in_progress`。

### Phase 1: Plan Sync

- **Status:** complete
- **Started:** 2026-04-26
- Actions taken:
  - 复盘当前链路边界：
    - frontend -> Gazebo/RViz 已有。
    - real leader -> RViz 已有。
    - leader-only replay -> validator -> manifest 已有。
    - real leader -> Gazebo 缺失。
  - 明确下一阶段主线为 `RLG: real leader to Gazebo`。
  - 明确训练策略：
    - 本机 WSL/Windows 做数据、验证、推理、smoke。
    - 正式训练优先 Colab/RunPod/Google Cloud。
  - 新增正式计划文档：
    - `docs/plans/2026-04-26-real-leader-to-gazebo-and-training-plan.md`
  - 更新 planning-with-files 工作文件：
    - `task_plan.md`
    - `findings.md`
    - `progress.md`
  - 更新项目正式追踪文件：
    - `docs/任务清单.md`
    - `docs/进度日志.md`

### Pending

- `TRN-002`：已用 `uv run --isolated` 完成原生 LeRobot v3 dataset 落盘；产物为 `docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset/lerobot-native-uvrun/`，9 frames / 1 episode。关键标准是不使用显式 venv，并清掉 ROS `PYTHONPATH`。
- `TRN-003`：Gazebo 执行动作标签已完成；`lerobot-candidate-exec-actions/` 中 8 条 train 样本使用 6 维 `joint_positions` action，native LeRobot 导出为 `lerobot-native-exec-actions-uvrun/`。下一步是真机恢复后补 follower hardware command 标签。
- `GZV-013`：前端采集质量面板已完成，后续只需要在后端提供真实 latest episode API 后接入动态数据。
- `RLG-001-live`：live smoke 脚本已完成；真实 `/leader/joint_states` 输入未出现时只能生成 blocked report，真机恢复后再跑实测。
- `YOL-004`：YOLO dataset smoke、1 epoch train/predict smoke、前端 latest artifact 展示已完成；`docs/generated/yolo-smoke/gzv011-train-infer/yolo-smoke-report.json` 记录 `status=done`，前端通过 `/api/workbench/vision/latest-quality` 可见。真实 YOLO 质量闭环仍未完成，当前 Gazebo 视觉主干仍依赖颜色检测器。
- `OPS-002`：证据策略和 git status 分类脚本已完成；下一步按该策略分批提交。

## Test Results

| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Planning update | 用户要求使用 planning-with-files skill 更新计划 | 计划文件落盘 | `task_plan.md/findings.md/progress.md` 已更新，正式计划文档已新增 | passed |
| RLG-001 unit tests | `python3 -m unittest src/so101_bringup/test/test_leader_to_gazebo_bridge.py src/so101_bringup/test/test_leader_recording_replay.py src/so101_bringup/test/test_leader_recording_trajectory_player.py -v` | bridge/replay/player tests pass | 20 tests OK | passed |
| RLG-001 py_compile | `python3 -m py_compile src/so101_bringup/scripts/leader_to_gazebo_bridge.py src/so101_bringup/launch/leader_to_gazebo.launch.py` | no syntax/import compile errors | passed | passed |
| RLG-001 build | `colcon build --packages-select so101_bringup` | package builds | `Summary: 1 package finished` | passed |
| RLG-001 offline smoke | `timeout 80s ros2 launch so101_bringup leader_to_gazebo.launch.py ... start_recording_replay:=true ...` | replay drives Gazebo controller through bridge | controller repeatedly logged `Received new action goal`, `Accepted new action goal`, `Goal reached, success!`; timeout exit expected because bridge is long-running | passed |
| GZV-001 unit tests | `python3 -m unittest src/so101_bringup/test/test_sim_color_detector.py -v` | simulated detector finds red/blue regions | 2 tests OK | passed |
| GZV syntax checks | `python3 -m py_compile src/so101_bringup/scripts/sim_color_detector_node.py src/so101_bringup/launch/sim_bringup.launch.py` and `xmllint --noout src/so101_gazebo/worlds/so101_workcell.world` | no syntax/XML errors | passed | passed |
| GZV build | `source /opt/ros/humble/setup.bash && colcon build --packages-select so101_gazebo so101_bringup yolov8_detector` | modified packages build | `Summary: 3 packages finished` | passed |
| GZV camera smoke | `bash tools/e2e/start_sim_vision_stack.sh`, then grep `.vscode/.runtime/so101_visible_ros.log` | simulated detector and Gazebo camera plugin start | `Sim color detector ready...`; `Publishing camera info to [/camera/color/camera_info]` | passed |
| GZV-006 frontend source semantics | `cd mes_frontend && node --test src/lib/__tests__/visionConsole.test.js` | Gazebo detector is distinct from real YOLO | 4 tests OK | passed |
| GZV-006 frontend build | `cd mes_frontend && npm run build` | frontend production build succeeds | build passed | passed |
| GZV-006 backend startup command | `cd mes_backend && mvn -q -Dtest=SystemControlServiceTest,SimulationRuntimeServiceTest test` | simulation startup command enables Gazebo detector | passed | passed |
| GZV-006 browser smoke | Playwright opened `http://127.0.0.1:5173`, clicked `连接实时状态`, then opened developer workbench | frontend shows Gazebo simulated vision and no render warning | screenshots saved to `docs/evidence/gzv-frontend-vision-connected-20260427.png` and `docs/evidence/gzv-developer-workbench-20260427.png` | passed |
| GZV-004 projector tests | `python3 -m unittest src/so101_bringup/test/test_vision_target_projector.py src/so101_bringup/test/test_sim_color_detector.py -v` | projection and color detector tests pass | 4 tests OK | passed |
| GZV-004 backend tests | `cd mes_backend && mvn -q -Dtest=RosbridgeClientServiceTest,SystemControlServiceTest,SimulationRuntimeServiceTest test` | backend subscribes and broadcasts vision targets | passed | passed |
| GZV-004 frontend build | `cd mes_frontend && node --test src/lib/__tests__/visionConsole.test.js && npm run build` | frontend handles Gazebo source and vision target UI | passed | passed |
| GZV-004 browser smoke | Playwright opened frontend, clicked `连接实时状态` | UI shows `TARGET 0.652, 0.183, 0.800` and target coordinate events | screenshot `docs/evidence/gzv-004-vision-targets-frontend-20260427.png` | passed |
| GZV-005 recorder tests | `python3 -m unittest src/so101_bringup/test/test_vision_episode_recorder.py src/so101_bringup/test/test_vision_target_projector.py src/so101_bringup/test/test_sim_color_detector.py -v` | recorder/projector/detector tests pass | 8 tests OK | passed |
| GZV-005 recorder smoke | `VISION_EPISODE_ID=... USE_VISION_EPISODE_RECORDER=true bash tools/e2e/start_sim_vision_stack.sh` | events and manifest are written | `docs/generated/vision-episodes/gzv005_smoke_20260427_003158/manifest.json` has image/detections/vision_targets/task_status/joint_states | passed |
| GZV-007 validator | `python3 tools/hardware/validate_vision_episode.py docs/generated/vision-episodes/gzv005_smoke_20260427_003158 --report-json ... --report-md ...` | validator checks required streams and writes reports | status `warn`, no errors, required streams present | passed |
| GZV-008 dataset adapter tests | `python3 -m unittest tools/hardware/test_build_vision_dataset_adapter.py -v` | adapter unit tests pass | 2 tests OK | passed |
| GZV-008 dataset adapter py_compile | `python3 -m py_compile tools/hardware/build_vision_dataset_adapter.py tools/hardware/test_build_vision_dataset_adapter.py` | no syntax/import compile errors | passed | passed |
| GZV-008 dataset conversion | `python3 tools/hardware/build_vision_dataset_adapter.py docs/generated/vision-episodes/gzv005_smoke_20260427_003158 --max-delta-sec 0.25 --max-task-status-delta-sec 2.0` | smoke episode converts to dataset index and samples | `sample_count=15`, missing streams all 0, status `warn`; task status uses 2.0s context threshold | passed |
| GZV-009 LeRobot candidate tests | `python3 -m unittest tools/hardware/test_export_vision_dataset_to_lerobot_candidate.py -v` | warn routing and export tests pass | 2 tests OK | passed |
| GZV-009 LeRobot candidate py_compile | `python3 -m py_compile tools/hardware/export_vision_dataset_to_lerobot_candidate.py tools/hardware/test_export_vision_dataset_to_lerobot_candidate.py` | no syntax/import compile errors | passed | passed |
| GZV-009 LeRobot candidate export | `python3 tools/hardware/export_vision_dataset_to_lerobot_candidate.py docs/generated/vision-episodes/gzv005_smoke_20260427_003158/dataset/dataset-index.json --warn-policy debug_only --target-category red --fps 5.0` | candidate package generated with warn samples excluded from train | `train_sample_count=8`, `debug_sample_count=7`, `rejected_sample_count=0`; native LeRobot blocked by pandas/numpy mismatch | passed |
| GZV-010 sync quality tests | `python3 -m unittest src/so101_bringup/test/test_vision_episode_recorder.py tools/hardware/test_build_vision_dataset_adapter.py tools/hardware/test_export_vision_dataset_to_lerobot_candidate.py -v` | recorder gate, per-stream thresholds, candidate routing pass | 12 tests OK | passed |
| GZV-010 syntax/build | `python3 -m py_compile ...`; `bash -n tools/e2e/start_visible_demo_stack.sh tools/e2e/start_sim_vision_stack.sh`; `colcon build --packages-select so101_bringup` | modified ROS/scripts build | passed | passed |
| GZV-010 fresh sync smoke | `VISION_EPISODE_ID=gzv010_sync_smoke_20260427_010005 USE_VISION_EPISODE_RECORDER=true VISION_MAX_IMAGE_SNAPSHOTS=8 VISION_IMAGE_SNAPSHOT_EVERY_N=15 bash tools/e2e/start_sim_vision_stack.sh` then adapter/export | new recorder avoids early/stale snapshots | `sample_count=8`, `train_sample_count=7`, `debug_sample_count=1`, high-rate streams large_delta all 0 | passed |
| GZV-011 heartbeat tests | `python3 -m unittest src/so101_bringup/test/test_task_status_publisher.py src/so101_bringup/test/test_vision_episode_recorder.py tools/hardware/test_build_vision_dataset_adapter.py tools/hardware/test_export_vision_dataset_to_lerobot_candidate.py -v` | heartbeat, recorder, adapter, candidate tests pass | 14 tests OK | passed |
| GZV-011 syntax/build | `python3 -m py_compile ...`; `bash -n tools/e2e/start_visible_demo_stack.sh tools/e2e/start_sim_vision_stack.sh`; `colcon build --packages-select so101_bringup` | modified ROS/scripts build | passed | passed |
| GZV-011 heartbeat smoke | `VISION_EPISODE_ID=gzv011_status_heartbeat_smoke_20260427_010757 USE_VISION_EPISODE_RECORDER=true VISION_MAX_IMAGE_SNAPSHOTS=8 VISION_IMAGE_SNAPSHOT_EVERY_N=15 STATUS_HEARTBEAT_ENABLED=true STATUS_HEARTBEAT_PERIOD_SEC=1.0 bash tools/e2e/start_sim_vision_stack.sh` then adapter/export | task_status heartbeat removes final debug sample | 35 heartbeat events recorded; dataset `passed`; `train_sample_count=9`, `debug_sample_count=0` | passed |
| GZV-012 frontend targeted tests | `cd mes_frontend && node --test src/composables/__tests__/useEventFeed.test.js src/lib/__tests__/visionConsole.test.js` | heartbeat denoise and vision console tests pass | 6 tests OK | passed |
| GZV-012 frontend full tests | `cd mes_frontend && find src -path '*__tests__/*.js' -print0 \| xargs -0 node --test` | all frontend node tests pass | 39 tests OK | passed |
| GZV-012 frontend build | `cd mes_frontend && npm run build` | production frontend builds | passed | passed |

## Local Browser Verification Standard

- Use local Playwright with `/usr/bin/google-chrome` and `headless: true` for frontend E2E against `127.0.0.1`.
- Do not use remote browser sessions for localhost validation; remote Firecrawl cannot reach local Vite/backend services.
- Save screenshots into `docs/evidence/` when validating visible UI behavior.

## Error Log

| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-04-26 | `set -u` broke direct sourcing of `/opt/ros/humble/setup.bash` during smoke command | First GZV smoke command | Re-ran with `set +u` around ROS setup source; same rule as `open_rviz.sh` |
| 2026-04-26 | Pure vision stack was blocked by mandatory rosbridge 9090 check | First `start_sim_vision_stack.sh` run | Added `ENABLE_ROSBRIDGE=false` support so Gazebo vision core is not bound to rosbridge/frontend/backend |

## 5-Question Reboot Check

| Question | Answer |
|----------|--------|
| Where am I? | Phase 2: RLG-001 Minimal Bridge |
| Where am I going? | Phase 2 RLG live smoke 与 Phase 2B Gazebo vision topic/assertion |
| What's the goal? | 打通真实 leader 主臂驱动 Gazebo，同时在无 follower 真机时推进 Gazebo 视觉仿真链 |
| What have I learned? | 离线 replay 可以通过短 horizon `FollowJointTrajectory` bridge 连续驱动 Gazebo controller；Gazebo 视觉原缺口是缺 ROS camera，不是前端显示问题 |
| What have I done? | 新增 RLG-001 bridge；新增 Gazebo RGB camera、仿真颜色检测节点和独立视觉启动入口 |

### 2026-04-27: No-Hardware Closeout Chunk

- Added `tools/e2e/assert_sim_camera_topics.sh` so Gazebo RGB camera visibility is asserted by ROS topics, not only log grep.
- Extended `leader_to_gazebo_bridge.py` live source quality handling:
  - live `/leader/joint_states` already goes through joint order, URDF position clamp/reject, and velocity gate before command dispatch.
  - added `status_period_sec` / `input_stale_sec`.
  - bridge publishes `WAITING_FOR_LEADER` when no sample arrives and `STALE` when input expires.
  - status payload now includes `last_sample_age_sec`.
- Added `real_leader_to_gazebo` as a persistent runtime target:
  - backend accepts and stores it.
  - frontend exposes a third explicit target button.
  - demo flow treats it as Gazebo execution body with real leader as input source; it does not fake leader readiness.
- Verification:
  - `python3 -m unittest src/so101_bringup/test/test_leader_to_gazebo_bridge.py -v`
  - `python3 -m py_compile src/so101_bringup/scripts/leader_to_gazebo_bridge.py src/so101_bringup/launch/leader_to_gazebo.launch.py`
  - `cd mes_backend && mvn -q -Dtest=SystemControlServiceTest test`
  - `cd mes_frontend && find src -path '*__tests__/*.js' -print0 | xargs -0 node --test`
  - `cd mes_frontend && npm run build`
  - `colcon build --packages-select so101_bringup`

## 2026-05-07 20:14 - GZV-018H：Level-2 pre-grasp evaluator 接入

- 代码变更：
  - `src/so101_moveit_config/src/mtc_reach_benchmark_node.cpp`
  - `src/so101_moveit_config/launch/mtc_reach_benchmark.launch.py`
- 新增 evaluator 参数：
  - `evaluator_level`
  - `pregrasp_min_height_m`
  - `pregrasp_max_height_m`
  - `pregrasp_max_approach_angle_error_deg`
- 新增 L2 指标（写入 `evaluation_result.metrics`）：
  - `pregrasp_success`
  - `pregrasp_height_m`
  - `pregrasp_approach_angle_error_deg`
  - `pregrasp_height_ok`
  - `pregrasp_approach_ok`
- 验证：
  - `source /opt/ros/humble/setup.bash && colcon build --packages-select so101_moveit_config` 通过。
  - `timeout 190s ros2 launch so101_moveit_config mtc_reach_benchmark.launch.py ... evaluator_level:=pregrasp_l2 ...` 产出 `docs/generated/vision-episodes/mtc-pregrasp-benchmark-report-20260507.yaml`。
  - 报告关键结果：`reach_success=true`，`pregrasp_success=false`，`pregrasp_approach_angle_error_deg=92.75074580686359`，`result_label=trainable_smoke_failed`，`failure_reason=pregrasp_constraints_not_met`。
- 结论：
  - Level-2 evaluator 已接入且可给出失败归因。
  - 当前失败主因是 approach 方向约束未满足，不是 planning/execution 链路失败。
- 结果仍仅限 Gazebo execution-grounded simulated benchmark，不代表真实抓取或 `trainable_real`。

## 2026-05-08 00:58 - GZV-018I：pre-grasp 收敛完成

### 背景

- `GZV-018H` 已把 Level-2 pre-grasp evaluator 接入，但当时 `reach_success=true`、`pregrasp_success=false`。
- 复盘后发现主因不是规划失败，而是 evaluator 口径不一致：
  - fallback candidate 只按距离选；
  - pre-grasp 方向约束先前仍按 `-Z` 判断；
  - L2 评估点选的是“最近 TCP 点”，不是“最优 pre-grasp 点”。

### 变更

- `src/so101_moveit_config/src/mtc_reach_benchmark_node.cpp`
  - 为 FK/trace 样本补齐 `tcp_after_fk_approach_world` / `tcp_approach_world`。
  - 引入 `desired_pregrasp_approach_world=[0,1,0]` 的侧向进场口径。
  - 引入 `pregrasp_nominal_height_m` 和 candidate pre-grasp 综合评分。
  - fallback sample 改为先全量打分再选最优，不再“第一个过 threshold 就停”。
  - `pregrasp_l2` 改为基于轨迹中最优 pre-grasp sample 评估，而不是最近点。
- `src/so101_moveit_config/launch/mtc_reach_benchmark.launch.py`
  - 透传 `pregrasp_nominal_height_m`。

### 验证

- `source /opt/ros/humble/setup.bash && colcon build --packages-select so101_moveit_config`：通过。
- `timeout 190s ros2 launch so101_moveit_config mtc_reach_benchmark.launch.py report_path:=docs/generated/vision-episodes/mtc-pregrasp-benchmark-report-20260508.yaml target_xyz:='[0.32,0.18,0.8]' target_mode:=vision_canonical backend_mode:=cartesian_ik_move_to execute_in_gazebo:=true evaluator_level:=pregrasp_l2 use_rviz:=false use_gzclient:=false`：benchmark node clean exit 并写出报告。
- 报告关键值：
  - `reach_success=true`
  - `pregrasp_success=true`
  - `pregrasp_eval_distance_m=0.045062371989271655`
  - `pregrasp_height_m=0.042444629499748254`
  - `pregrasp_approach_angle_error_deg=32.312335789834265`
  - `result_label=trainable_smoke`

### 当前结论

- 视觉 canonical target 路径已从 L1 reach 成功推进到 L2 pre-grasp 成功。
- 当前结论仍只限 Gazebo execution-grounded simulated benchmark，不是 contact/grasp/lift/place，也不是 `trainable_real`。

## 2026-05-08 01:13 - GZV-018J：最小 contact/lift evaluator 接入

### 背景

- `GZV-018I` 已把视觉 canonical target 推进到 `pregrasp_success=true`。
- 这一步继续沿同一 execution-grounded artifact 契约推进，不另起 evaluator/report。

### 变更

- `src/so101_moveit_config/src/mtc_reach_benchmark_node.cpp`
  - 新增 `/gazebo/model_states` 订阅与 `object_trace`。
  - 新增参数：`target_model_name`、`target_model_size_xyz`、`contact_distance_threshold_m`、`lift_success_threshold_m`。
  - `contact_success` 第一版使用 gripper TCP 到目标 AABB 的几何距离近似。
  - `lift_success` 第一版使用 object `peak_z - initial_z`。
- `src/so101_moveit_config/{CMakeLists.txt,package.xml}`
  - 新增 `gazebo_msgs` 依赖。
- `src/so101_moveit_config/launch/mtc_reach_benchmark.launch.py`
  - 透传 contact/lift 参数。
- `tools/e2e/run_mtc_reach_benchmark_suite.py`
  - 新增 `contact_success_rate`、`lift_success_rate` 汇总口径。

### 验证

- `source /opt/ros/humble/setup.bash && colcon build --packages-select so101_moveit_config`：通过。
- `python3 -m py_compile tools/e2e/run_mtc_reach_benchmark_suite.py`：通过。
- `timeout 190s ros2 launch so101_moveit_config mtc_reach_benchmark.launch.py report_path:=docs/generated/vision-episodes/mtc-contact-lift-benchmark-report-20260508.yaml target_xyz:='[0.32,0.18,0.8]' target_mode:=vision_canonical backend_mode:=cartesian_ik_move_to execute_in_gazebo:=true evaluator_level:=pregrasp_l2 use_rviz:=false use_gzclient:=false`：benchmark node clean exit 并写出报告。
- 报告关键值：
  - `contact_success=false`
  - `contact_distance_m=0`
  - `lift_success=false`
  - `object_trace.available=false`
  - `object_lift_delta_m=0`

### 当前结论

- `contact_success / lift_success` 已成功纳入同一 execution-grounded artifact 契约。
- 当前 `so101_workcell.world` 中 `pick_bin` 是静态模型，不是可夹取/抬升动态目标，所以 `lift_success=false` 是预期结果。
- 下一步若要真正验证 lift，需要先补动态 graspable object world 资产。

## 2026-05-08 - GZV-018K：动态目标 review 修复

### 背景

- contact/lift 接线后 review 指出两个 P2：reach execution 被 object state availability 错误阻塞；动态目标落到桌面后中心高度与默认 `target_xyz.z=0.8` 不一致。

### 变更

- `src/so101_moveit_config/src/mtc_reach_benchmark_node.cpp`
  - trajectory 发布前只等待 `/joint_states` 具备目标关节，不再要求 `target_model_name` 出现在 model states。
  - object trace 改为可选观测；缺失时继续执行 reach，并把 `contact_available/lift_available` 标为 false。
  - 节点默认 `target_xyz`、`target_model_name`、`target_model_size_xyz`、`contact_distance_threshold_m` 与动态 `grasp_target` 场景对齐。
- `src/so101_moveit_config/launch/mtc_reach_benchmark.launch.py`
  - 默认 `target_xyz` 改为 `[0.312, 0.192, 0.758]`，对应桌面高度 `0.75` + box 半高 `0.008`。
- `src/so101_gazebo/worlds/so101_workcell.world`
  - 新增动态 `grasp_target` 和 `gazebo_ros_state`，默认对象中心与 benchmark target 对齐。

### 当前结论

- review 指出的默认 benchmark 可信度问题已修复：reach 是主任务，object/contact/lift 是附加观测；动态默认目标不再和 target z 错位。
- 仍不能声明 `lift_success=true` 或真实抓取成功；下一步是继续调 gripper/object/lift 物理交互。

### 验证

- `source /opt/ros/humble/setup.bash && colcon build --packages-select so101_gazebo so101_moveit_config`：通过。
- `docs/generated/vision-episodes/mtc-missing-object-reach-regression-20260508.yaml`：`trajectory_execution_success=true`、`reach_success=true`、`object_trace.available=false`、`contact_available=false`、`lift_available=false`。
- `docs/generated/vision-episodes/mtc-dynamic-target-review-fix-20260508.yaml`：`target_world_xyz=[0.312,0.192,0.758]`，`object_world_xyz≈[0.312,0.192,0.758]`，`object_trace.available=true`，`reach_success=true`，`lift_success=false`。

## 2026-05-08 - GZV-018L：contact proxy 诊断与 staged grasp 隔离

### 背景

- 动态目标与 object trace 已接入，但不能把 TCP reach 成功误判为 gripper contact/lift 成功。
- 上一轮多阶段 close/lift 调试会影响 trajectory execution 稳定性，因此先把默认 L1 reach 与实验性 grasp stages 隔离。

### 变更

- `src/so101_moveit_config/src/mtc_reach_benchmark_node.cpp`
  - `TcpTraceSample` 新增 `contact_proxy_world_xyz`，每个 execution trace sample 记录 moving jaw contact proxy。
  - contact distance 改为使用 contact proxy 到 object AABB 的距离，而不是 TCP/link origin。
  - 新增 `execution_trace.failure_reason`，区分 `execution_trace_missing_joint_states`、`trajectory_publish_no_subscriber`、`execution_trace_missing`、`controller_not_converged`。
  - 新增 `execute_grasp_stages` 参数，默认 `false`；默认只发布单阶段 reach trajectory，显式打开时才发布 reach/close/squeeze/lift 多阶段 trajectory。
  - 新增关节目标 clamp，避免实验性 close/lift 阶段生成超限关节目标。
- `src/so101_moveit_config/launch/mtc_reach_benchmark.launch.py`
  - 透传 `initial_state_wait_sec`、`contact_proxy_offset_xyz`、`execute_grasp_stages`。
- `src/so101_gazebo/worlds/so101_workcell.world`
  - 将默认 `grasp_target` 调整到当前 L1 reach 可稳定命中的动态目标位置 `[0.292,0.131,0.758]`。

### 验证

- `source /opt/ros/humble/setup.bash && colcon build --packages-select so101_gazebo so101_moveit_config`：通过。
- `docs/generated/vision-episodes/mtc-dynamic-lift-reach-l1-final-20260508.yaml`
  - `planning_success=true`
  - `trajectory_execution_success=true`
  - `execution_success=true`
  - `reach_success=true`
  - `min_distance_m=1.327765938827549e-05`
  - `object_trace.available=true`
  - `contact_success=false`
  - `contact_distance_m=0.023306535523293564`
  - `lift_success=false`
  - `object_lift_delta_m=9.2148511043888e-15`
- `docs/generated/vision-episodes/mtc-dynamic-lift-contact-proxy-final-20260508.yaml`
  - `pregrasp_success=false`
  - `failure_reason=pregrasp_constraints_not_met`
  - 说明当前动态 object center reach 不是 L2 pre-grasp 成功。

### 当前结论

- 默认 execution-grounded L1 reach baseline 已恢复稳定。
- contact/lift 仍未成功；当前真实缺口是 moving jaw contact proxy 到 object AABB 仍约 `2.33cm`，高于 `2cm` 阈值，且 object z 没有上升。
- 当前仍只能表述为 Gazebo execution-grounded simulated reach/contact/lift diagnostic，不是仿真抓取成功，更不是真实抓取或 `trainable_real`。

## 2026-05-08 - 主线回顾：仿真 lift 阻塞与闭环状态

### 阻塞点记录

- `GZV-018M` 暂缓继续死磕 Gazebo lift。
- 阻塞不是 planner 或 evaluator 缺失，而是 Gazebo Classic 中夹爪/目标物碰撞几何、摩擦、闭合姿态和抬升动作未形成稳定夹持。
- 当前证据：
  - `trajectory_execution_success=true`
  - `reach_success=true`
  - `object_trace.available=true`
  - `contact_success=false`
  - `contact_distance_m≈0.0233m > 0.02m`
  - `lift_success=false`
  - `object_lift_delta_m≈0`
- 真实物体即将组装完成，继续调 Gazebo contact/lift ROI 低。后续优先做真实物体 contact/lift acceptance harness，复用当前 evaluator/report 字段。

### 当前已打通的链路

- Gazebo 视觉 smoke：
  - Gazebo camera -> detector -> `/detections` -> `/vision/targets`
  - overlay `/vision/debug/image_overlay`
- 程序化仿真执行 smoke：
  - `/vision/targets` -> task_executor -> `/joint_trajectory_controller/joint_trajectory` -> Gazebo `/joint_states` -> `/mes_task_status`
- MTC execution-grounded reach benchmark：
  - target/candidate -> MTC/IK joint goal -> Gazebo controller -> `/joint_states` FK TCP trace -> unified evaluator
  - jitter20/jitter50 suite 已有统计和 failure artifact。
- 数据集 smoke：
  - vision episode recorder -> dataset adapter -> LeRobot candidate -> native LeRobot export -> trainability gate -> viewer。
- 软件/MES/UI smoke：
  - 后端启动/状态、前端 runtime/quality panel、rosbridge topic 展示和 `/mes_task_status` heartbeat 已有本地 smoke。

### 仍未完善

- 仿真 contact/lift 物理成功未完成；不再作为短期主线门槛。
- 真实 YOLO 质量闭环仍未完成；当前只能说有 Gazebo color detector、YOLO smoke、数据导出和前端展示，不能说真实检测质量闭环完成。
- 数据集判断已有 smoke gate，但 `trainable_real` 不成立；真实 follower/hardware action labels 仍待真实硬件补强。
- 双闭环可以说“软件/MES/UI 闭环”和“Gazebo execution-grounded reach 闭环”已通；不能说真实抓取闭环或真实 follower 闭环已通。

## 2026-05-08 - GZV-021/022/023/024：pre-real acceptance 非实机收口

### 背景

- 接真机前需要最后一条非实机 acceptance gate：可一键回归、可索引 artifacts、可判断 vision projection 数据质量，并能给人直接读 dashboard。
- 该 gate 不能因为 Gazebo contact/lift 失败而失败；contact/lift 只能作为 blocked/deferred optional diagnostic。

### 变更

- `tools/e2e/run_pre_real_acceptance_suite.py`
  - 新增总入口，聚合 vision smoke、vision projection quality smoke、MTC reach smoke、small jitter suite、dataset trainability gate。
  - 默认可直接运行 MTC smoke/jitter；`--reuse-latest-artifacts` 可快速复用现有 evidence 生成 acceptance report。
  - 输出 `docs/generated/acceptance/pre-real-acceptance-<timestamp>/acceptance_report.yaml` 与 `dashboard.md`。
- `tools/e2e/run_vision_projection_quality_smoke.py`
  - 从 recorded `events.jsonl` 统计 raw target、canonical target、expected target、pixel/world error、miss/false positive 与 clamp reason。
  - 明确只验证 Gazebo/recorded detector projection 数据质量，不声明真实 YOLO 质量闭环。
- `docs/generated/acceptance/latest_runs.yaml`
  - 新增 run index，记录 timestamp、command、report/dashboard paths、success/failure、reach success rate、min-distance summary、failure reason counts、dataset trainability status。
- `tools/e2e/test_pre_real_acceptance_suite.py`
  - 覆盖 projection quality clamp 统计与 dashboard 边界说明。

### 验证

- `python3 -m py_compile tools/e2e/run_pre_real_acceptance_suite.py tools/e2e/run_vision_projection_quality_smoke.py tools/e2e/test_pre_real_acceptance_suite.py`：通过。
- `python3 -m unittest tools/e2e/test_pre_real_acceptance_suite.py`：2 tests OK。
- `python3 tools/e2e/run_vision_projection_quality_smoke.py --events-path docs/generated/vision-episodes/gzv017c_benchmark_smoke_20260506/events.jsonl --report-path /tmp/vision_quality_smoke.yaml`：`status=passed`。
- `python3 tools/e2e/run_pre_real_acceptance_suite.py --reuse-latest-artifacts`：通过，输出 `docs/generated/acceptance/pre-real-acceptance-20260508-134536/acceptance_report.yaml`。

### 当前结论

- Pre-real non-hardware acceptance gate 已收口：status `passed`，jitter reach success rate `1.0`，min-distance mean `0.0564179m`、p50 `0.0553554m`、p90 `0.0734162m`、max `0.0765311m`，failure counts `{trajectory_publish_failed: 2}`。
- Dataset trainability 仍只能是 `trainable_smoke`；real-required trainability gate 仍 blocked，不能叫 `trainable_real`。
- Vision projection quality smoke 对 recorded artifact 通过：canonical world error `0.0`、miss `{}`、false positive `{}`、raw-to-canonical clamp reason `7`。
- 仍不能声明真实抓取成功、真实 follower 闭环、真实 YOLO 质量闭环、`trainable_real` 或仿真 grasp/lift 成功。

## 2026-05-12 - E2E-HW-002：frontend-to-follower smoke entry

### What Changed

- Added `so101_follower_trajectory_adapter.py` as the first real follower software bridge:
  - `/joint_trajectory_controller/joint_trajectory` -> LeRobot `SO101Follower.send_action`
  - publishes `/joint_states` and `/real_follower/status`
  - defaults to low-amplitude `max_relative_target_deg=2.0`
- `real_bringup.launch.py` now supports `enable_follower_adapter:=true`.
- Backend runtime startup now dispatches by `runtimeTarget`:
  - `simulation` -> Gazebo sim bringup
  - `real_hardware` -> `real_bringup.launch.py` with follower adapter and rosbridge.

### Evidence

- `/dev/ttyACM0` is present and permission-compatible for user `muqiao`.
- `SO101FollowerConfig` / `SO101Follower` import works after fixing Python user-site dependency precedence and installing `feetech-servo-sdk`.
- `py_compile`, `colcon build --packages-select so101_bringup`, and backend targeted tests pass.
- `real_bringup` starts `task_executor` and `rosbridge_websocket` on port 9090.
- Follow-up software-only smoke now passes in dry-run mode:
  - `docs/generated/real-follower/follower_software_link_smoke_20260512.json`
  - `software_ready=true`
  - `hardware_bus_ready=false`
  - `received_trajectory_count=1`
  - `sent_command_count=1`
  - `last_sent_action` contains converted six-axis follower action values.
- Frontend developer workbench now subscribes to follower status through backend `/topic/real-follower-status` and displays software readiness separately from hardware bus readiness.

### Current Blocker

- The Feetech bus behind `/dev/ttyACM0` returns no motors:
  - `FeetechMotorsBus.scan_port('/dev/ttyACM0') -> {}`
  - adapter reports missing IDs `1..6`, expected model `777`, found `{}`.
- This blocks real follower motion. Do not call this a real follower closed loop yet.
- Keep `SO101_FOLLOWER_DRY_RUN=true` until the new board/LeRobot environment and servo bus scan return expected IDs; then switch to `SO101_FOLLOWER_DRY_RUN=false` for low-amplitude real follower smoke.
