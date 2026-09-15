# SO101 Real Hardware Parallel Execution Plan

> **For Claude/Codex:** This file is a parallel execution handoff. Use one worker per prompt. Do not let multiple workers edit the same file set. Shared project docs must be updated only by the integration worker.

**Goal:** Parallelize the next round of SO101 real-hardware work after main-arm attach, without colliding on shared files or prematurely opening real motion.

**Architecture:** Split work into four bounded workers plus one integration worker. Workers A-D each own a disjoint write set. The integration worker is the only one allowed to update the task board and progress log after reviewing the outputs from the other workers.

**Tech Stack:** Bash, Python 3.10, ROS2 Humble, Spring Boot, Vue 3, Node test, Maven test

---

## Current Baseline

- Main arm is already attached from Windows `COM4` into WSL and visible as `/dev/ttyUSB0`.
- `bash tools/hardware/start_real_min_bringup.sh` now auto-refreshes main-arm runtime state and starts a watcher.
- `curl -fsS http://127.0.0.1:8080/api/system/status | jq '.realHardware'` stays fresh beyond the previous timeout window.
- Current remaining software gap is not “device attach”, but “calibration runtime sync + stable demo semantics + preflight tooling + startup hardening”.
- Real motion is still out of scope for this batch. Do not add trajectory execution, visual grasping, or free-form action logic.

## Parallelization Rules

- Worker A-D may run in parallel.
- Worker A-D must not edit:
  - `docs/任务清单.md`
  - `docs/进度日志.md`
- Only the integration worker may edit shared project docs.
- If a worker discovers it needs a file owned by another worker, it must stop and report the overlap instead of expanding scope.
- All workers must keep `allowExecute=false` as the default result.
- All workers must preserve the existing `/api/system/status` contract unless their prompt explicitly says otherwise.

## Batch Layout

### Parallel Batch 1

1. Worker A: `CAL-002` runtime calibration sync hardening
2. Worker B: `RHS-002` minimal real-hardware status semantics polish
3. Worker C: `HWP-002/HWP-005` one-command bringup hardening
4. Worker D: `HWS-001/HWS-002` CLI-first preflight and evidence harness

### Serial Batch 2

5. Integration Worker: merge results, run verification, update board and log

## Worker Output Contract

Every worker must return:

- `Changed files:` exact file paths
- `What changed:` 3-8 flat bullets
- `Verification:` exact commands run and whether they passed
- `Residual risks:` short list
- `Did not do:` anything intentionally left out

## Coordinator Prompt

```text
You are the SO101 real-hardware coordinator. Your job is to run four independent workers in parallel, review their outputs, resolve only light integration issues, run the final verification set, then update project tracking docs.

Project root:
/home/muqiao/dev/ros2/workspaces/so101_ws

Current facts you can rely on:
- Main arm is attached in WSL as /dev/ttyUSB0.
- start_real_min_bringup.sh now auto-refreshes main-arm state and starts a watcher.
- /api/system/status.realHardware stays fresh and no longer falls back to STATUS_TIMEOUT.
- Software must keep allowExecute=false by default.
- Real motion is not part of this batch.

Hard boundaries:
- Do not redesign the homepage.
- Do not change unrelated UI.
- Do not add YOLO or trajectory features.
- Do not let workers edit the same file set.
- Only you may edit docs/任务清单.md and docs/进度日志.md.

Execution order:
1. Dispatch Worker A, Worker B, Worker C, Worker D in parallel using the prompts below.
2. Wait for all four to finish.
3. Review their changed files for overlap and regressions.
4. Integrate the changes with minimal conflict resolution.
5. Run the final verification commands listed in the Integration Worker prompt.
6. Update docs/任务清单.md and docs/进度日志.md with concrete evidence.

Final return format:
- Parallel results summary
- Integrated files
- Verification commands and outcomes
- Remaining blockers
```

## Worker A Prompt

```text
You are Worker A for SO101. Own only the CAL-002 software slice: runtime calibration sync hardening.

Project root:
/home/muqiao/dev/ros2/workspaces/so101_ws

Goal:
Make the existing calibration skeleton easier to consume in the real-hardware path, without touching motion execution. The result should make it obvious where the real calibration profile goes, how it is validated, and how runtime sync is verified before any execution is allowed.

Allowed files:
- tools/hardware/real_hardware_calibration.py
- tools/hardware/validate_real_hardware_calibration.py
- tools/hardware/sync_real_hardware_calibration.py
- tools/hardware/test_real_hardware_calibration.py
- tools/hardware/real_hardware_calibration.example.json
- new files under tools/hardware/ if they are calibration-only helpers

Forbidden files:
- tools/hardware/start_real_min_bringup.sh
- tools/hardware/refresh_main_arm_runtime_state.sh
- docs/任务清单.md
- docs/进度日志.md
- any frontend file
- any backend Java file

Required outcomes:
- Calibration profile path ingestion remains explicit and easy to verify.
- Invalid calibration input produces clear failure messages.
- Runtime sync path to .vscode/.runtime/real_hardware_calibration.json is easy to smoke-test.
- No code path may imply allowExecute=true by default.

Suggested work:
- Harden error messages and validation output.
- Add one small CLI helper if needed for calibration-only smoke verification.
- Extend unit tests around missing poses, invalid payloads, and homed semantics.
- Keep the schema centered on home/pick/place/gripper_open/gripper_close.

Verification:
- python3 -m unittest tools/hardware/test_real_hardware_calibration.py
- python3 tools/hardware/validate_real_hardware_calibration.py tools/hardware/real_hardware_calibration.example.json
- If you add a helper, run it against the example profile and report output.

Return:
- Changed files
- What changed
- Verification
- Residual risks
- Did not do
```

## Worker B Prompt

```text
You are Worker B for SO101. Own only the RHS-002 frontend slice: minimal real-hardware status semantics polish.

Project root:
/home/muqiao/dev/ros2/workspaces/so101_ws

Goal:
Improve the existing real-hardware status expression in the current frontend without redesigning the page. Keep the card small and demo-oriented. Make it easier to explain the current real-hardware stage to a non-developer audience.

Allowed files:
- mes_frontend/src/components/RealHardwareStatusCard.vue
- mes_frontend/src/lib/realHardwareStatus.js
- mes_frontend/src/lib/__tests__/realHardwareStatus.test.js
- new test files under mes_frontend/src/ if strictly needed for this card

Forbidden files:
- mes_frontend/src/App.vue
- any other large page/layout file
- docs/任务清单.md
- docs/进度日志.md
- any backend Java file
- any tools/hardware shell script

Required outcomes:
- Keep the current minimum stage ladder stable:
  - 未接入
  - 已接入但未上电
  - 已上电但未校准
  - 已校准但未放行
- Make the copy demo-facing, not driver-facing.
- Preserve the protection-first meaning when the status source is stale or unclear.
- Do not expose raw debugging detail as the main message.

Suggested work:
- Tighten summary labels and fallback wording.
- Make “最近异常 / 最近刷新 / 当前阶段” easier to scan.
- Keep safetyChecks supportive, not dominant.
- Add or update tests for stage classification and fallback defaults.

Verification:
- cd mes_frontend && node --test src/lib/__tests__/realHardwareStatus.test.js
- cd mes_frontend && npm test
- cd mes_frontend && npm run build

Return:
- Changed files
- What changed
- Verification
- Residual risks
- Did not do
```

## Worker C Prompt

```text
You are Worker C for SO101. Own only the HWP-002/HWP-005 startup hardening slice.

Project root:
/home/muqiao/dev/ros2/workspaces/so101_ws

Goal:
Harden the one-command real-hardware bringup path so that “main arm connected -> run script -> runtime state stays online and fresh” is the default behavior. Keep this strictly in the bringup/orchestration layer. Do not introduce motion.

Allowed files:
- tools/hardware/start_real_min_bringup.sh
- tools/hardware/stop_real_min_bringup.sh
- tools/hardware/refresh_main_arm_runtime_state.sh
- tools/hardware/watch_main_arm_runtime_state.sh
- tools/hardware/stop_main_arm_runtime_state_watch.sh
- new shell helpers under tools/hardware/ if they are startup/watch-only

Forbidden files:
- tools/hardware/real_hardware_calibration.py
- tools/hardware/sync_real_hardware_calibration.py
- docs/任务清单.md
- docs/进度日志.md
- any frontend file
- any backend Java file

Required outcomes:
- Re-running startup must not create duplicate watcher chaos.
- Stop flow must clean watcher state reliably.
- Logs should make it obvious whether refresh ran, whether watcher started, and what port is being watched.
- Default behavior remains allowExecute=false.

Suggested work:
- Harden PID cleanup and duplicate-process detection.
- Improve startup/stop log messages.
- Add a tiny status helper if needed to inspect watcher state.
- Keep the path centered on /dev/ttyUSB0-style serial presence and runtime freshness only.

Verification:
- bash -n tools/hardware/start_real_min_bringup.sh
- bash -n tools/hardware/stop_real_min_bringup.sh
- bash -n tools/hardware/refresh_main_arm_runtime_state.sh
- bash -n tools/hardware/watch_main_arm_runtime_state.sh
- bash -n tools/hardware/stop_main_arm_runtime_state_watch.sh
- If you add a helper, run it and include output

Return:
- Changed files
- What changed
- Verification
- Residual risks
- Did not do
```

## Worker D Prompt

```text
You are Worker D for SO101. Own only the HWS-001/HWS-002 preflight harness slice.

Project root:
/home/muqiao/dev/ros2/workspaces/so101_ws

Goal:
Create a CLI-first preflight/evidence harness for the current real-hardware phase. This is not motion control. This is a checklist runner that answers: is the arm online, is the status fresh, is power reported, is calibration present, is homing complete, and is execution still correctly locked?

Allowed files:
- new files under tools/hardware/ for preflight/evidence only
- new tests under tools/hardware/ if needed

Forbidden files:
- docs/任务清单.md
- docs/进度日志.md
- any frontend file
- any backend Java file
- existing startup/watch scripts unless absolutely required

Required outcomes:
- The harness must be CLI-first.
- It must not send motion commands.
- It must summarize current safety/preflight state in one place.
- It must clearly fail when calibration is missing or stale status is detected.
- It must treat “still locked” as correct for this stage, not as a failure.

Suggested work:
- Build one script that reads current runtime artifacts and prints a clear pass/fail report.
- Include freshness, calibration, homed, estop, allowExecute, gateReasonCode, and controlInterface in the report.
- If useful, also write a JSON report file under .vscode/.runtime/.

Verification:
- Run the new preflight script against the current runtime files
- If the backend is up, also compare against:
  - curl -fsS http://127.0.0.1:8080/api/system/status | jq '.realHardware'

Return:
- Changed files
- What changed
- Verification
- Residual risks
- Did not do
```

## Integration Worker Prompt

```text
You are the integration worker for SO101 real-hardware parallel batch 1.

Project root:
/home/muqiao/dev/ros2/workspaces/so101_ws

Your inputs are the completed outputs from Worker A, Worker B, Worker C, and Worker D.

You may edit:
- docs/任务清单.md
- docs/进度日志.md
- any file with light conflict resolution needed to integrate worker outputs

Your job:
- Review all worker outputs.
- Merge only the accepted changes.
- Resolve small overlaps.
- Run the final verification set.
- Update docs/任务清单.md and docs/进度日志.md with concrete evidence and today’s results.

Required doc updates:
- Record the new evidence under the relevant E7 tasks:
  - CAL-002
  - RHS-002
  - HWP-002/HWP-005 if startup hardening changed
  - HWS-001/HWS-002 if preflight harness landed
- Keep wording factual.
- Do not mark done without real evidence.

Final verification set:
- python3 -m unittest tools/hardware/test_real_hardware_calibration.py
- cd mes_frontend && node --test src/lib/__tests__/realHardwareStatus.test.js
- cd mes_frontend && npm test
- cd mes_frontend && npm run build
- bash -n tools/hardware/start_real_min_bringup.sh
- bash -n tools/hardware/stop_real_min_bringup.sh
- bash -n tools/hardware/refresh_main_arm_runtime_state.sh
- bash -n tools/hardware/watch_main_arm_runtime_state.sh
- bash -n tools/hardware/stop_main_arm_runtime_state_watch.sh
- If backend is running:
  - curl -fsS http://127.0.0.1:8080/api/system/status | jq '.realHardware'

Final return format:
- Accepted worker results
- Final changed files
- Verification outcomes
- Task board updates
- Remaining blockers
```
