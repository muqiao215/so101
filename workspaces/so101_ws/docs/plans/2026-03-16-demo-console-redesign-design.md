# SO-101 演示控制台前端重构方案

**日期：** 2026-03-16

**目标：** 将当前偏开发调试风格的控制台，重构为面向“演示机 / 答辩机”的引导式前端，降低误操作概率，提高首次使用成功率，同时保留高级调试能力。

**结论先行：**
- 默认首页应从“全控制面板”改为“演示流程向导”。
- `打开干净浏览器` 这类开发/自动化按钮不应出现在默认主路径中，应收进高级模式。
- `唤起 rosbridge` 文案存在误导，应改成 `连接 rosbridge`，因为当前它只做 client connect，不负责启动 rosbridge 进程。
- 在后端接口保持稳定的前提下，前端可以大改；重点先改信息架构、文案、状态机和引导，再决定是否做一键演示模式。

---

## 1. 当前问题

### 1.1 当前首页的问题不是“能不能用”，而是“太像开发台”

现有首页把系统控制、链路控制、工单下发、事件流、调试注入都平铺在一个页面里。对开发者来说这没问题，但对演示机来说会带来几个风险：

1. 关键路径不突出。
2. 使用者不知道先点哪一个按钮。
3. 文案混杂了技术语义和演示语义。
4. 高级调试能力暴露过度，容易把演示路径打断。
5. 页面状态缺少“下一步提示”，用户只能靠猜。

### 1.2 目前最典型的误导点

1. `打开干净浏览器`
   - 对演示机默认用户价值不高。
   - 浏览器本来就开着时，这个按钮反而让人困惑。

2. `唤起 rosbridge`
   - 文案会让人误以为这是“启动 rosbridge 进程”。
   - 实际上它只是让 backend 连接 `ws://127.0.0.1:9090`。

3. `连接 WebSocket`
   - 技术上准确，但演示机视角不够友好。
   - 用户真正关心的是“实时状态有没有连上”。

---

## 2. 设计目标与边界

### 2.1 设计目标

1. 让不熟悉系统的人也能按顺序完成演示。
2. 把默认操作压缩成 2 到 4 步。
3. 页面自己告诉用户“当前状态”和“下一步该做什么”。
4. 保留高级调试入口，但不干扰主路径。
5. 兼容当前 backend 接口，不先动业务协议。

### 2.2 非目标

1. 本轮不先改订单协议。
2. 本轮不先改后端核心业务逻辑。
3. 本轮不把所有调试工具都删掉，只是降级到高级模式。

### 2.3 当前前后端边界

前端重构时默认保留以下接口契约：

- `/api/system/status`
- `/api/system/start-sim`
- `/api/system/open-rviz`
- `/api/system/stop-sim`
- `/api/ros/connect`
- `/api/ros/health`
- 订单相关 REST 接口
- WebSocket 订阅链路

因此结论是：**可以大改前端，但先不要随意改 backend API 语义。**

---

## 3. 方案比较

### 方案 A：保留当前控制台，只做文案和排序微调

**优点**
- 实现最快。
- 代码改动最小。
- 风险低。

**缺点**
- 本质还是开发控制台。
- 首次使用门槛依然高。
- 不能从根上解决“先点什么”的问题。

### 方案 B：默认进入“演示模式”，高级能力收进抽屉或二级页（推荐）

**优点**
- 最符合演示机场景。
- 主路径清晰。
- 高级能力仍可保留。
- 兼顾答辩演示与开发联调。

**缺点**
- 前端结构需要明显调整。
- 组件要重新拆分。

### 方案 C：彻底改成“一键演示模式”大屏，普通按钮全部隐藏

**优点**
- 演示感最强。
- 最少误操作。

**缺点**
- 对调试不友好。
- 对当前 backend 自动化能力要求更高。
- 一旦状态机没写好，排障会很难。

### 推荐结论

先做 **方案 B**。

原因：
- 当前项目还需要联调和排障。
- 还没有必要把所有操作都封成一键黑盒。
- 方案 B 可以先把默认体验做对，后续再演进到方案 C。

---

## 4. 页面结构建议

默认首页改成三层结构：

1. 演示总览区
2. 操作向导区
3. 实时反馈区

高级模式单独放在：
- 右上角 `高级模式`
- 或一个可折叠抽屉

### 4.1 默认首页信息架构

**顶部：演示总览**
- 当前系统状态
- 仿真
- rosbridge
- 实时状态流
- 当前工单
- 大状态灯：`未就绪 / 启动中 / 可演示 / 执行中 / 已完成 / 异常`

**中部：操作向导**
- Step 1 启动仿真
- Step 2 连接 rosbridge
- Step 3 连接实时状态
- Step 4 创建并下发工单

**底部：实时反馈**
- 事件时间线
- 当前工单摘要
- 最近状态流

**高级模式**
- 打开/关闭干净浏览器
- 打开 RViz
- 停止仿真
- 注入演示状态
- 注入检测
- 原始接口状态
- 日志路径

---

## 5. 页面线框方案

### 5.1 首页线框（默认演示模式）

```text
+----------------------------------------------------------------------------------+
| SO-101 演示控制台                                              [高级模式]       |
| 当前状态: 可演示 / 执行中 / 异常                                                   |
| 仿真: 就绪   rosbridge: 在线   实时状态: 已连接   当前工单: order-xxx            |
+----------------------------------------------------------------------------------+
| Step 1 启动仿真                                                                  |
| [启动 Gazebo 仿真]    状态: 未启动 / 启动中 / 已就绪                             |
| 提示: 启动后通常需要 3-8 秒                                                      |
+----------------------------------------------------------------------------------+
| Step 2 连接 rosbridge                                                            |
| [连接 rosbridge]       状态: 未连接 / 已连接                                      |
| 提示: 仅连接 9090 上已存在的 rosbridge 服务                                      |
+----------------------------------------------------------------------------------+
| Step 3 连接实时状态                                                              |
| [连接实时状态]       状态: 未连接 / 已连接                                        |
| 提示: 成功后会自动接收工单状态和检测消息                                         |
+----------------------------------------------------------------------------------+
| Step 4 下发工单                                                                  |
| 模板 [pick_place_default v]   工单ID [auto-generated            ]                |
| [创建工单] [直接下发]                                                             |
+----------------------------------------------------------------------------------+
| 时间线                                                                            |
| 12:30 仿真启动                                                                    |
| 12:30 rosbridge ready                                                             |
| 12:31 实时状态已连接                                                               |
| 12:31 工单 order-xxx 已下发                                                       |
+----------------------------------------------------------------------------------+
```

### 5.2 高级模式线框

```text
+-----------------------------------------------------------+
| 高级模式                                                   |
| 系统控制                                                   |
| [打开 RViz] [停止仿真] [打开干净浏览器] [关闭干净浏览器]   |
|                                                           |
| 调试工具                                                   |
| [刷新系统状态] [注入演示状态] [注入红色检测] [注入蓝色检测] |
|                                                           |
| 运行信息                                                   |
| simPid / rvizPid / browserPid / logs / debugUrl           |
+-----------------------------------------------------------+
```

### 5.3 页面状态切换

页面应至少有 4 个明显的 UI 状态：

1. **初始态**
- 全部未就绪
- 只强调第一步

2. **启动中**
- Step 1 loading
- 显示等待说明

3. **演示就绪**
- Step 1/2/3 都完成
- Step 4 高亮

4. **执行中/完成态**
- 工单卡片突出显示
- 时间线持续追加

---

## 6. 组件拆分清单

建议不要继续把所有逻辑都堆在 `App.vue`。

### 6.1 页面级容器

1. `DemoConsolePage`
- 默认演示首页容器
- 负责组织布局

2. `AdvancedPanelDrawer`
- 高级模式抽屉
- 收纳开发/调试动作

### 6.2 核心展示组件

1. `SystemOverviewBar`
- 展示仿真、rosbridge、实时状态、工单总览

2. `DemoStepCard`
- 通用步骤卡片
- 支持状态、说明、按钮、禁用原因

3. `DemoTimeline`
- 事件时间线
- 统一显示系统事件和工单事件

4. `FocusedOrderCard`
- 当前工单摘要
- 展示模板、requestId、状态、更新时间

5. `StatusBadge`
- 统一状态视觉语言
- `idle / pending / ready / running / done / error`

### 6.3 表单与动作组件

1. `OrderTemplateSelector`
- 模板选择

2. `OrderDispatchForm`
- 工单 ID + 创建 + 下发

3. `RealtimeConnectCard`
- 连接 rosbridge
- 连接实时状态
- 展示当前链路解释

### 6.4 高级模式组件

1. `BrowserControlPanel`
- 浏览器相关按钮

2. `RuntimeDebugPanel`
- log / pid / debugUrl / 原始状态

3. `DemoInjectionPanel`
- 注入状态 / 注入检测

### 6.5 状态管理建议

建议拆成 composables：

1. `useSystemStatus()`
- 轮询 `/api/system/status`
- 管理仿真、RViz、browser、rosbridge 状态

2. `useRosbridgeControl()`
- `/api/ros/connect`
- `/api/ros/health`

3. `useOrderFlow()`
- 创建工单
- 下发工单
- 刷新工单列表

4. `useRealtimeFeed()`
- WebSocket 连接
- 事件流
- 状态流
- 检测流

---

## 7. 关键交互规则

### 7.1 按钮启用规则

1. 未启动仿真时
- `连接 rosbridge` 禁用
- `连接实时状态` 禁用
- `创建工单/下发` 可以显示但不推荐主高亮

2. rosbridge 未 ready 时
- Step 2 显示“等待 9090 就绪”

3. rosbridge 已 ready 但 backend 未连接时
- Step 2 主高亮

4. backend 已连接 rosbridge 但前端实时流未连接时
- Step 3 主高亮

5. 实时流已连接后
- Step 4 主高亮

### 7.2 文案重命名建议

- `打开干净浏览器` -> 放入高级模式，不在默认首页显示
- `唤起 rosbridge` -> `连接 rosbridge`
- `连接 WebSocket` -> `连接实时状态`
- `System Control` -> `演示控制`
- `Connectivity` -> `链路状态`
- `Order Dispatch` -> `工单执行`

### 7.3 视觉反馈原则

- 不要只显示红绿状态，要显示“下一步建议”
- 加载中状态必须有文案
- 禁用按钮必须说明原因

---

## 8. Figma 产出建议

Figma 不需要一开始就画高保真，先做信息架构。

### 8.1 第一轮 Figma 建议产出

做 3 个 frame 就够：

1. `初始态`
- 全部未就绪
- 只强调 Step 1

2. `启动中`
- Step 1 loading
- Step 2/3 disabled

3. `演示就绪`
- Step 1/2/3 变绿
- Step 4 成为主操作区

### 8.2 Figma 组件建议

- Status Badge
- Step Card
- Overview Metric
- Timeline Item
- Focused Order Card
- Advanced Drawer Section

### 8.3 Figma 设计方向建议

风格不要继续沿用“赛博控制台但信息均匀平铺”的思路。

建议：
- 保留工业感和深色氛围
- 但层级要更明确
- 主操作区更大、更聚焦
- 次要调试能力弱化
- 用步骤感和留白而不是堆按钮来制造秩序

---

## 9. Stitch 使用策略

Stitch 适合产出静态 UI 骨架，不适合决定业务逻辑。

正确用法是：
1. 先用 Figma 定结构
2. 再让 Stitch 生成 Vue 页面骨架
3. 最后手工接当前 API、状态机和 WebSocket

### 9.1 Stitch 任务边界

让 Stitch 负责：
- 页面布局
- 组件外观
- stepper / timeline / badge / drawer 样式

不要让 Stitch 负责：
- API 设计
- 业务状态机
- rosbridge 启动语义
- WebSocket 连接逻辑

---

## 10. Figma 提示词草案

```text
为一个“SO-101 机械臂 MES 演示控制台”设计桌面端首页线框，目标用户是答辩演示操作者，而不是开发人员。

要求：
- 默认首页强调 4 步演示流程：启动仿真、连接 rosbridge、连接实时状态、创建并下发工单
- 页面必须清楚显示当前系统状态和下一步提示
- 高级调试能力不要放在首页主路径里，设计一个可折叠高级模式抽屉
- 风格偏工业、专业、清晰，不要做成花哨 dashboard
- 需要 3 个关键状态版本：初始态、启动中、演示就绪
- 顶部有总览状态条，中部是步骤引导，底部是时间线和当前工单信息
- 重点是“降低误操作”，不是“展示全部功能”
```

---

## 11. Stitch 提示词草案

```text
Generate a Vue 3 single-page interface for a demo-machine control console of an SO-101 robotic arm MES system.

Design goals:
- This is a guided demo console, not a developer dashboard.
- The primary user flow is four steps: Start Simulation, Connect Rosbridge, Connect Live Status, Create and Dispatch Order.
- The default page should prioritize clarity, sequencing, and next-step guidance.
- Advanced developer controls must be hidden inside a collapsible drawer labeled Advanced Mode.

Layout requirements:
- Top overview bar with system readiness, rosbridge state, live status connection, and current order summary.
- Middle area with four vertical or stacked step cards.
- Bottom area with a timeline and a focused order card.
- An advanced drawer with browser controls, RViz, stop simulation, injections, and raw runtime info.

Interaction requirements:
- Each step card supports states: idle, waiting, ready, running, success, error.
- Disabled actions must display a reason.
- The UI should visually highlight the next recommended action.

Style direction:
- Dark industrial interface with strong hierarchy.
- Large primary action area.
- Avoid generic analytics dashboard look.
- Keep typography clear and intentional.
- Make the page feel like an operator console for a live demo.

Technical note:
- Generate presentational Vue components only.
- Do not invent backend APIs.
- Use props and emitted events so business logic can be wired manually later.
```

---

## 12. 分期实施建议

### Phase 1：信息架构重构
- 默认首页改成演示模式
- 高级模式抽屉化
- 改文案与按钮层级

### Phase 2：状态机与引导
- 基于当前 backend 状态决定按钮可用性
- 增加下一步提示、等待文案、错误提示

### Phase 3：视觉重做
- Figma 定稿
- Stitch 生成静态骨架
- 手工接回现有 API

### Phase 4：自动化收口
- 评估是否把 `启动仿真 -> 等待 rosbridge -> connect -> 连接实时状态` 合并为一个组合动作

---

## 13. 最终建议

如果只选一件事优先做，建议先做：

**把默认首页从“开发控制台”改成“步骤引导页”。**

原因：
- 这是对演示成功率影响最大的改动。
- 它不依赖先改 backend。
- 它能立刻减少“为什么这个按钮没反应”的误解。

如果你确认这份方案方向对，下一步再进入实现计划，拆到具体文件和组件。 
