# SO101 Episode Asset Spec (Leader-Only)

更新时间：2026-04-15

## 1. 目标

在进入 `EP-001/EP-002/EP-003` 前，先固定 episode 资产组织规则，避免后续出现：

- 命名漂移
- 字段漂移
- 回放口径不一致
- 无法追溯配置版本
- “原始脏数据”和“清洗后可用数据”混在一起

本版规范把单层 episode 资产升级为三层：

- `raw`
- `cleaned`
- `annotated`

核心原则：

1. `raw` 永不覆盖
2. `cleaned` 必须能追溯回 `raw`
3. `annotated` 只在 `raw/cleaned` 之上追加解释，不直接改写原始事实

## 2. 目录结构

根目录：

- `docs/generated/leader-episodes/`

单个 episode 目录：

- `docs/generated/leader-episodes/<episode_id>/`

推荐升级后的目录布局：

- `docs/generated/leader-episodes/<episode_id>/raw/`
- `docs/generated/leader-episodes/<episode_id>/cleaned/`
- `docs/generated/leader-episodes/<episode_id>/annotated/`
- `docs/generated/leader-episodes/<episode_id>/manifest.json`

### 2.1 raw 层

用途：

- 保留最原始、未经修正的录制与验证结果

最小文件集：

- `raw/episode.jsonl`
- `raw/episode.meta.json`
- `raw/replay-raw.json`
- `raw/replay-waypoints.json`（可选）
- `raw/source-summary.json`（可选）

要求：

- 不覆盖
- 不重排
- 不修正时间戳
- 不删除异常帧

### 2.2 cleaned 层

用途：

- 在不改变任务语义的前提下，做结构清洗，使 replay / validator / 后续训练能够稳定消费

最小文件集：

- `cleaned/episode.jsonl`
- `cleaned/episode.meta.json`
- `cleaned/replay-raw.json`
- `cleaned/replay-waypoints.json`（可选）
- `cleaned/cleaning-report.json`

典型清洗内容：

- 删除重复时间戳
- 裁掉局部非单调段
- 丢弃明显损坏帧
- 修正仅影响格式、不改变任务语义的辅助字段

要求：

- 必须保留清洗报告
- 必须记录来源 raw 文件
- 必须记录清洗规则版本

### 2.3 annotated 层

用途：

- 在 raw / cleaned 之上追加任务解释、质量标签和人工说明

最小文件集：

- `annotated/task.json`
- `annotated/labels.json`
- `annotated/notes.md`
- `annotated/waypoints.generated.yaml`（可选）
- `annotated/waypoints.generated.summary.json`（可选）

典型内容：

- 任务阶段标签
- 人工备注
- 成功/失败说明
- 标准动作集对照
- 从连续轨迹提炼出的 waypoint 草稿

## 3. episode_id 命名规则

统一格式：

- `<task_name>_<mode>_<YYYYMMDD-HHMMSS>_<operator>`

示例：

- `pick_demo_real_20260415-101530_muqiao`
- `pick_demo_offline_20260415-103000_muqiao`

约束：

- 只允许小写字母、数字、下划线、中划线
- 不允许空格
- 同秒冲突时在末尾追加 `-01`、`-02`

## 4. 配对样本命名思路

从现在开始，`raw` 和 `cleaned` 样本要显式成对出现，而不是靠口头记忆。

推荐命名：

- `l1_smoke_002_raw_invalid`
- `l1_smoke_002_clean_passed`

含义：

- `raw_invalid`
  - 原始 episode 存在结构问题
  - 保留为 validator 的负样本
- `clean_passed`
  - 由对应 `raw` 清洗得到
  - 用于 validator / replay / manifest 的正样本

最小要求：

1. `cleaned_from_episode_id` 必须指回原始样本
2. `pair_group_id` 必须一致
3. `cleaning_report.json` 必须说明清洗动作

## 5. 状态机

episode 级状态从现在开始统一使用以下五种：

- `passed`
- `soft_failed`
- `hard_failed`
- `invalid_result`
- `cleaned_from_invalid`

### 5.1 状态语义

`passed`

- 结果可信
- hard / soft 检查均通过

`soft_failed`

- 结果可信
- hard 通过
- soft 超限
- 可进入观察资产，但不进金样本

`hard_failed`

- 结果可信
- hard 超限
- 不进入正式资产链

`invalid_result`

- 结果本身不可信
- 常见于：
  - joint 集不一致
  - 非单调时间戳
  - 重复时间戳
  - 空比较窗口
  - 数据结构坏

`cleaned_from_invalid`

- 原始样本先是 `invalid_result`
- 经清洗后重新生成了可消费样本
- cleaned 样本必须保留与 raw 的血缘关系

### 5.2 状态流转

允许的最小流转：

1. `raw -> invalid_result`
2. `raw -> cleaned_from_invalid`
3. `cleaned -> passed`
4. `cleaned -> soft_failed`
5. `cleaned -> hard_failed`

不允许的口径：

- 直接把 `invalid_result` 改写成 `passed`
- 删除原始 invalid 样本后只保留 cleaned 样本
- 不记录清洗动作就覆盖 manifest

## 6. manifest schema（当前已实现最小集 + 下一步 planned）

### 6.1 当前已实现字段

当前 `tools/hardware/episode_manifest.py` 已能稳定生成并消费以下字段：

- 标识字段
  - `manifest_schema_version`
  - `episode_id`
  - `task_name`
  - `created_at`
  - `operator`
- 追溯字段
  - `source_mode`
  - `robot_profile`
  - `calibration_version`
  - `asset_status`
  - `source_sha256`
- 文件字段
  - `raw_record_path`
  - `recording_meta_path`
  - `cleaned_record_path`
  - `cleaning_report_path`
  - `annotation_path`
  - `replay_raw_result_path`
  - `replay_waypoint_result_path`
- 分层摘要
  - `recording_layers.raw`
  - `recording_layers.cleaned`
- 质量字段
  - `quality_metadata.input_recording`
  - `quality_metadata.cleaning`
  - `quality_metadata.annotation`
  - `quality_metadata.replay_validation`
  - `quality_summary.source`
  - `quality_summary.frame_count`
  - `quality_summary.duration_sec`
  - `quality_summary.sample_rate_hz`
  - `quality_summary.non_monotonic_stamp_count`
  - `quality_summary.avg_frame_gap_sec`
  - `quality_summary.max_frame_gap_sec`
- 任务字段
  - `task_metadata.start_condition`
  - `task_metadata.end_condition`
  - `task_metadata.outcome`
  - `task_metadata.interrupted`
  - `notes`

### 6.2 planned 字段

以下字段保留为下一步 contract，本轮不要求代码已全部落下：

- `pair_group_id`
- `asset_tier`
- `parent_episode_id`
- `cleaned_from_episode_id`
- `annotation_source_episode_id`
- `promotion_state`
- `input_topic`
- `mapping_version`
- `cleaning_rule_version`
- `ros_distro`
- `package_name`
- `waypoint_draft_path`
- `waypoint_summary_path`
- `replay_waypoint_result_path`

## 7. manifest 示例

```json
{
  "manifest_schema_version": "v1",
  "episode_id": "l1_smoke_002_clean_passed",
  "created_at": "2026-04-15T13:45:00+08:00",
  "task_name": "sim_headless_replay",
  "operator": "muqiao",
  "asset_status": "cleaned_from_invalid",
  "source_sha256": "4958e81fd98ac91bf96dfe5bb450d002ea663aedcdc9c42ff69850f36e9f7ddd",
  "source_mode": "leader_only",
  "robot_profile": "so101_leader",
  "calibration_version": "leader-cal-20260415",
  "raw_record_path": "docs/generated/leader-episodes/l1_smoke_002_clean_passed/raw/leader-recording-20260409-113201.jsonl",
  "recording_meta_path": "docs/generated/leader-episodes/l1_smoke_002_clean_passed/raw/leader-recording-20260409-113201.meta.json",
  "cleaned_record_path": "docs/generated/leader-episodes/l1_smoke_002_clean_passed/cleaned/leader-recording-20260409-113201.cleaned.jsonl",
  "annotation_path": "docs/generated/leader-episodes/l1_smoke_002_clean_passed/annotated/annotation.json",
  "cleaning_report_path": "docs/generated/leader-episodes/l1_smoke_002_clean_passed/annotated/cleaning-report.json",
  "replay_raw_result_path": "docs/generated/leader-episodes/l1_smoke_002_clean_passed/replay-raw.json",
  "recording_layers": {
    "raw": {
      "status": "invalid_result"
    },
    "cleaned": {
      "status": "cleaned_from_invalid"
    }
  },
  "quality_summary": {
    "source": "cleaned_report",
    "frame_count": 1390,
    "duration_sec": 46.332871,
    "sample_rate_hz": 30.0,
    "non_monotonic_stamp_count": 0,
    "avg_frame_gap_sec": 0.033357,
    "max_frame_gap_sec": 0.068057
  },
  "notes": "cleaned candidate derived from raw invalid episode"
}
```

## 8. 金样本晋升门槛

从现在开始，金样本不是“跑过一次就算”，而是必须满足明确门槛。

### 8.1 candidate

进入 `candidate` 至少满足：

1. `manifest.json` 完整
2. `replay-raw.json` 存在
3. 文件路径可解析
4. 血缘关系可追溯

### 8.2 baseline

进入 `baseline` 至少满足：

1. `validator_status` 不为 `invalid_result`
2. 结果能复跑
3. `cleaning_report` 完整（若 asset_tier=`cleaned`）
4. 任务说明与来源清晰

### 8.3 golden

进入 `golden` 必须全部满足：

1. `validator_status=passed`
2. 不依赖人工临时修补
3. `raw/cleaned/annotated` 血缘链完整
4. 至少复跑两次结果口径一致
5. 质量字段稳定，无明显漂移
6. 可被后续 replay / manifest / 回归脚本稳定消费

### 8.4 不得晋升为 golden 的情况

以下任一成立，不能进金样本：

- `invalid_result`
- `hard_failed`
- `soft_failed`
- 只有 cleaned，没有 raw
- 没有清洗报告
- 无法追溯 calibration / mapping / cleaning rule 版本

## 9. 版本与变更纪律

规则：

1. `raw/episode.jsonl` 一旦写入，不可覆盖
2. `cleaned` 可以重算，但必须更新 `cleaning_report.json` 与 `manifest.json`
3. `annotated` 只追加解释，不直接改写 raw / cleaned 内容
4. `schema_version` 升级时，必须补迁移说明
5. 任何临时字段不得直接进入正式 manifest

## 10. 合格 episode 判定（准入）

判定为“合格 episode”至少满足：

1. 对应 tier 的文件集存在
2. `manifest.json` 字段齐全，路径可解析
3. 至少一种 replay 结果存在
4. 质量字段不为空
5. 能追溯到 calibration、mapping、cleaning rule 版本

## 11. 与现有计划的关系

- 本规范是 `docs/plans/2026-04-09-episode-closure.md` 的资产落地补充
- 本规范不替代 `P0/P1/P2` 准入门槛
- 只有 `P0/P1/P2` 通过，才进入正式 episode 批量生产
