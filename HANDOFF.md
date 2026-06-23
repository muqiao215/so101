# SO101 Mint Follower Demo 交接文档

日期：2026-06-23

## Git 节点

写本文档前的最新代码/数据提交：

```text
632d240 chore: commit remaining project data
```

最近关键提交：

```text
632d240 chore: commit remaining project data
90a3f7f fix: smooth teleop and recording motion
2b8213b chore: record mint follower milestone
```

工作区在写本文档前已确认干净。

## 项目目录

主项目目录已从：

```text
win7_follower_demo
```

改为：

```text
mint_follower_demo
```

启动入口仍然是仓库根目录的：

```bash
./start.sh
```

`start.sh` 已指向 `mint_follower_demo`。仓库根目录名称仍包含历史 `win7` 字样，这是当前工作区路径，不要在代码内继续依赖旧子目录名。

## 当前产品方向

项目定位是 Linux Mint 上的轻量级 SO101 从臂控制台，不融合 ROS、摄像头、训练系统。

核心功能方向：

- 管理员/员工登录。
- 员工登录记录保存和查看。
- 录制动作作为原始动作素材。
- 管理员把录制动作发布为产品动作。
- 员工只执行已发布的产品动作。
- 业务运行日志保持简洁，只记录关键执行结果。
- `PRODUCT_PLAN.md` 已记录轻量 MES 思路和产品规划。

## 夹爪问题和修复

之前的问题表现：

```text
夹爪闭合测试: start=1572 target=586 final=1572 error=986
```

关键判断：

- `target=586` 是正确的闭合端。
- 软件校准文件 `follower_calibration.json` 已经知道从臂夹爪闭合端是 `586`。
- 真正的问题是舵机内部的 angle limit 仍可能停留在旧范围，导致动作模式下发 `586` 时舵机不执行。
- 监控模式能手动闭合，是因为监控模式释放力矩，绕过了舵机主动控制限制。

已修复：

- 动作模式连接时同步从臂夹爪舵机内部 `min/max angle limit`。
- 直接夹爪闭合测试前强制同步内部限位。
- 保存从臂夹爪闭合端后立即同步内部限位。
- 主从跟随启动前也同步内部限位。
- 当前从臂夹爪范围：

```text
range_min=586
range_max=3146
```

如果以后夹爪再次不闭合，优先看测试输出里的：

```text
limit old_min-old_max -> 586-3146
```

如果 limit 没变成 `586-3146`，说明舵机内部限位没有写入成功。如果 limit 正确但 final 仍不接近 586，再查扭矩、供电、机械阻力。

## 主从晃动和卡顿优化

已完成优化提交：

```text
90a3f7f fix: smooth teleop and recording motion
```

改动：

- 主从默认频率从 `20Hz` 降为 `12Hz`。
- 主从单步限速从 `24 raw` 降为 `12 raw`。
- 新增主臂 raw 死区：

```json
[4, 4, 4, 4, 4, 6]
```

- 新增主从低通滤波：

```text
teleop_smoothing_alpha=0.35
```

- 保存录制动作时默认做 1 次轻平滑：

```text
recording_smoothing_passes=1
```

目的：

- 小抖动不下发。
- 主臂噪声不直接变成从臂目标。
- 录制动作不把主从噪声永久保存进产品动作。

## 当前重要配置

文件：

```text
mint_follower_demo/config/serial_config.json
```

当前关键值：

```json
{
  "dry_run": false,
  "monitor_mode": false,
  "backend": "native_posix",
  "teleop_frequency_hz": 12.0,
  "teleop_max_step_raw": 12.0,
  "teleop_deadband_raw": [4, 4, 4, 4, 4, 6],
  "teleop_smoothing_alpha": 0.35,
  "recording_smoothing_passes": 1
}
```

当前串口使用 `/dev/serial/by-id/...`，不要轻易改回 `/dev/ttyACM0`，除非现场设备路径变了。

## 运行方式

在仓库根目录：

```bash
./start.sh
```

浏览器打开：

```text
http://127.0.0.1:8765
```

如果端口被占用，`start.sh` 会尝试关闭旧服务。

## 验证命令

代码语法检查：

```bash
python3 -m py_compile mint_follower_demo/app.py
node --check mint_follower_demo/static/app.js
```

夹爪映射静态检查：

```bash
python3 - <<'PY'
import json
from pathlib import Path
root = Path('mint_follower_demo/config')
cal = json.load(open(root / 'follower_calibration.json'))
tpl = json.load(open(root / 'action_templates.json'))
rmin = int(cal['gripper']['range_min'])
rmax = int(cal['gripper']['range_max'])
raws = []
for name, point in tpl.get('waypoints', {}).items():
    if isinstance(point, list) and len(point) >= 6:
        v = max(0.0, min(1.0, float(point[5])))
        raws.append((int(v * (rmax - rmin) + rmin), name))
print('gripper_range', rmin, rmax)
print('min_raw', min(raws) if raws else None)
print('max_raw', max(raws) if raws else None)
PY
```

预期至少应看到：

```text
gripper_range 586 3146
min_raw (586, ...)
```

## 新窗口继续注意事项

- 不要恢复旧的 `win7_follower_demo` 子目录。
- 不要删除或回滚当前用户现场录制数据，除非用户明确要求。
- 录制/发布/登录记录现在是项目功能的一部分，改动前先看 `product_actions.json`、`business_run_log.json`、`login_records.json`。
- 如果要继续调主从抖动，优先调小：

```text
teleop_max_step_raw
teleop_frequency_hz
```

- 如果动作太慢，再逐步加大，不要一次恢复到 20Hz/24raw。
- 如果夹爪再次不闭合，不要先怀疑录制动作，先看舵机内部 limit 是否同步到 `586-3146`。
