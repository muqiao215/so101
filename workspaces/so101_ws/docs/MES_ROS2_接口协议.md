# MES 与 ROS2 接口协议（v1）

本协议用于 `Spring Boot + rosbridge` 与 `so101_bringup` 任务执行节点联调。

## 1. Topics

- `/mes_task_cmd`：`std_msgs/String`，JSON 字符串
- `/mes_task_status`：`std_msgs/String`，JSON 字符串
- `/detections`：`std_msgs/String`，JSON 字符串

## 2. 命令消息（MES -> ROS2）

Topic: `/mes_task_cmd`

```json
{
  "requestId": "req-20260227-001",
  "orderId": "order-001",
  "actionTemplateId": "pick_place_red",
  "params": {
    "priority": 1
  }
}
```

字段说明：
- `requestId`：请求唯一ID（幂等键）
- `orderId`：工单ID
- `actionTemplateId`：动作模板ID，默认支持：
  - `pick_place_default`
  - `pick_place_red`
  - `pick_place_blue`
- `params`：扩展参数

## 3. 状态消息（ROS2 -> MES）

Topic: `/mes_task_status`

```json
{
  "requestId": "req-20260227-001",
  "state": "执行中",
  "code": "STEP",
  "message": "2/8 -> above_pick",
  "ts": 1772188888123
}
```

状态字段：
- `state`：`待执行 | 执行中 | 完成 | 异常`
- `code`：`DETECTION_TRIGGER | STARTED | STEP | OK | BUSY | BAD_REQUEST | DETECTION_MISMATCH | EXECUTION_ERROR`
- `message`：可读文本
- `ts`：毫秒时间戳

MES 侧建议按 `code` 驱动工单状态：
- `DETECTION_TRIGGER | STARTED | STEP` -> `RUNNING`
- `OK` -> `DONE`
- `BUSY | BAD_REQUEST | DETECTION_MISMATCH | EXECUTION_ERROR` -> `ERROR`

工单在 MES 发起 dispatch 后可保持 `PENDING`，等待 ROS2 首条状态回传后再转入 `RUNNING`，避免“已下发但未真正执行”被提前标记为运行中。

## 4. 检测消息（YOLO -> ROS2）

Topic: `/detections`

```json
{
  "source": "real_yolo",
  "frame_id": "camera_color_optical_frame",
  "stamp": {
    "sec": 1772188888,
    "nanosec": 123000000
  },
  "ts": 1772188888123,
  "count": 1,
  "detections": [
    {
      "category": "red",
      "confidence": 0.92,
      "bbox_xyxy": [120, 80, 220, 180],
      "bbox_xywh": [170, 130, 100, 100]
    }
  ]
}
```

检测字段说明：
- `source`：建议显式区分来源，当前前端用它判断“是否来自真实 YOLO”
  - `real_yolo`
  - `demo_inject`
  - `mock_yolo`
- `frame_id` / `stamp`：真实相机帧信息
- `bbox_xyxy`：左上 / 右下像素框
- `bbox_xywh`：像素中心点 + 宽高

`pick_place_red` / `pick_place_blue` 模板会检查 `category` 与模板期望是否一致。

## 5. rosbridge 建议

`rosbridge_websocket` 默认端口：`9090`

建议 MES 后端连接策略：
- 自动重连（指数退避）
- 发送命令前确认 topic advertisement
- 以 `requestId` 作为幂等键，避免重复下发
