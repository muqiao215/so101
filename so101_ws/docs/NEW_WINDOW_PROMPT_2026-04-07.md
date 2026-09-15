# SO101 New Window Prompt

把下面整段复制到新窗口：

```text
继续 SO101 真机第一轮，不讨论其它项目。

先读：
- /home/muqiao/dev/ros2/workspaces/so101_ws/docs/任务清单.md
- /home/muqiao/dev/ros2/workspaces/so101_ws/docs/进度日志.md
- /home/muqiao/dev/ros2/workspaces/so101_ws/docs/AGENT_TRANSFER.md

当前已知事实：
- 当前只管主臂
- `/dev/ttyUSB0` 已接入过并可刷新状态
- watcher 已修稳
- 本地校准工作流已建立：
  - `/home/muqiao/dev/ros2/workspaces/so101_ws/tools/hardware/real_hardware_calibration.local.json`
- preflight 当前已达到：
  - `statusFresh=true`
  - `online=true`
  - `powerState=已上电`
  - `calibrationValid=true`
  - `homed=true`
  - `allowExecute=false`
  - `commandExecutionEnabled=false`
  - `gateReasonCode=HWS_002_PENDING`
- 安全证据入口已存在：
  - `/home/muqiao/dev/ros2/workspaces/so101_ws/tools/hardware/collect_real_hardware_safety_evidence.py`
- 当前不是链路问题，而是进入真机低速安全动作验证阶段

你的任务边界：
- 不做首页重构
- 不做高级模式重设计
- 不做 YOLO 大改
- 不做轨迹工作台新功能
- 前端不做无关改动
- 不放开 `allowExecute`
- 不把 `commandExecutionEnabled` 改成 true
- 不做复杂联动
- 不做视觉抓取

你的下一步只有这一条主线：
1. 先确认当前 watcher 和 preflight
2. 再推进 HWS-001 的真机低速安全动作验证
3. 用安全证据脚本留证
4. 更新 `docs/任务清单.md` 和 `docs/进度日志.md`

建议先执行：

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws

bash tools/hardware/main_arm_runtime_watch_status.sh
python3 tools/hardware/check_real_hardware_preflight.py \
  --root-dir /home/muqiao/dev/ros2/workspaces/so101_ws \
  --skip-backend-compare --json
```

如果状态仍可信，再做现场人工验证并留证：

```bash
cd /home/muqiao/dev/ros2/workspaces/so101_ws

python3 tools/hardware/collect_real_hardware_safety_evidence.py \
  --root-dir /home/muqiao/dev/ros2/workspaces/so101_ws \
  --operator muqiao \
  --estop-ok \
  --controlled-stop-ok \
  --limit-guard-ok \
  --speed-scaling-ok \
  --json
```

交付要求：
- 先汇报当前真实状态
- 再汇报安全验证推进到哪一步
- 如果改了代码或文档，必须同步更新：
  - `/home/muqiao/dev/ros2/workspaces/so101_ws/docs/任务清单.md`
  - `/home/muqiao/dev/ros2/workspaces/so101_ws/docs/进度日志.md`
```
