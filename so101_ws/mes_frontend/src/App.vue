<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref } from 'vue';
import AdvancedDrawer from './components/AdvancedDrawer.vue';
import DemoHeroPanel from './components/DemoHeroPanel.vue';
import EventTimelinePanel from './components/EventTimelinePanel.vue';
import FocusedOrderPanel from './components/FocusedOrderPanel.vue';
import LiveConnectionCard from './components/LiveConnectionCard.vue';
import RealHardwareStatusCard from './components/RealHardwareStatusCard.vue';
import RuntimeLaunchCard from './components/RuntimeLaunchCard.vue';
import RuntimeTargetCard from './components/RuntimeTargetCard.vue';
import StatusTimelinePanel from './components/StatusTimelinePanel.vue';
import VisionConsolePanel from './components/VisionConsolePanel.vue';
import WorkOrderComposerCard from './components/WorkOrderComposerCard.vue';
import {
  buildDemoFlow,
  getOverallStateLabel,
  getOverallStateTone,
  getPrimaryPrompt,
  getPrimaryPromptDetail,
} from './lib/demoConsole.js';
import { resolveRealHardwareStatus } from './lib/realHardwareStatus.js';
import { useConsoleWorkspace } from './composables/useConsoleWorkspace.js';
import { useEventFeed } from './composables/useEventFeed.js';
import { useMesBackend } from './composables/useMesBackend.js';
import { useRealtimeFeed } from './composables/useRealtimeFeed.js';
import { normalizeDetectionItems, summarizeDetectionPayload } from './lib/visionConsole.js';

const DeveloperWorkbenchPage = defineAsyncComponent(() => import('./components/DeveloperWorkbenchPage.vue'));
const apiBase = ref(import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8080');
const wsBase = computed(() => {
  if (import.meta.env.VITE_WS_BASE) {
    return import.meta.env.VITE_WS_BASE;
  }
  return apiBase.value.replace(/^http/, 'ws');
});

const {
  eventFeed,
  statusEvents,
  detections,
  visionTargets,
  leaderDebug,
  pushEvent,
  rememberStatusEvent,
  rememberDetection,
  rememberVisionTarget,
  rememberLeaderDebug,
} = useEventFeed();

const {
  orderId,
  actionTemplateId,
  rosbridgeConnected,
  systemStatus,
  systemBusy,
  selectedOrder,
  refreshOrders,
  refreshRosbridgeHealth,
  refreshSystemStatus,
  startSimulation,
  openRviz,
  stopSimulation,
  openBrowser,
  stopBrowser,
  setRuntimeTarget,
  createAndDispatchOrder,
  connectRosbridge,
  injectDemoStatus,
  injectDemoDetection,
  previewWorkbenchPose,
  saveWorkbenchExport,
  mergeWorkbenchWaypoints,
  fetchLatestVisionQuality,
  formatStamp,
} = useMesBackend(apiBase, { pushEvent });

const { socketState, socketLabel, connectBusy, connectWs, closeWs } = useRealtimeFeed({
  wsBase,
  rosbridgeConnected,
  connectRosbridge,
  refreshOrders,
  pushEvent,
  rememberStatusEvent,
  rememberDetection,
  rememberVisionTarget,
  rememberLeaderDebug,
  formatStamp,
});

const {
  activeTab,
  drawerOpen,
  workspaceTabs,
  connectLiveRuntime,
  onMountedInit,
  onUnmountedCleanup,
  openConsoleWorkspace,
  openDeveloperWorkspace,
  selectWorkspaceTab,
  toggleDrawer,
} = useConsoleWorkspace({
  systemRuntime: {
    refreshSystemStatus,
    refreshRosbridgeHealth,
  },
  orderWorkflow: {
    refreshOrders,
  },
  realtimeFeed: {
    connectWs,
    closeWs,
  },
  pushEvent,
});

const demoFlow = computed(() =>
  buildDemoFlow({
    systemStatus: systemStatus.value,
    rosbridgeConnected: rosbridgeConnected.value,
    socketState: socketState.value,
    selectedOrder: selectedOrder.value,
  }),
);

const overallStateLabel = computed(() => getOverallStateLabel(demoFlow.value));
const overallStateTone = computed(() => getOverallStateTone(demoFlow.value));
const primaryPrompt = computed(() => getPrimaryPrompt(demoFlow.value));
const primaryPromptDetail = computed(() => getPrimaryPromptDetail(demoFlow.value));

const latestDetection = computed(() => detections.value[0] || null);
const latestVisionTarget = computed(() => visionTargets.value[0] || null);
const latestVisionEpisodeQuality = ref(null);
const latestDetectionCount = computed(() => {
  const payload = latestDetection.value?.payload;
  return payload?.count ?? normalizeDetectionItems(payload).length ?? 0;
});
const latestDetectionCategories = computed(() => {
  const payload = latestDetection.value?.payload;
  return payload ? summarizeDetectionPayload(payload) : '尚未收到检测';
});
const topbarTime = ref(new Date());
let topbarTimerId = null;
const realHardwareStatus = computed(() => resolveRealHardwareStatus(systemStatus.value));
const runtimeTarget = computed(() => systemStatus.value.runtimeTarget || 'simulation');
const runtimeTargetIsHardware = computed(() => runtimeTarget.value === 'real_hardware');
const runtimeTargetIsLeaderToGazebo = computed(() => runtimeTarget.value === 'real_leader_to_gazebo');
const runtimeTargetLabel = computed(() => {
  if (runtimeTargetIsHardware.value) {
    return '真机链';
  }
  if (runtimeTargetIsLeaderToGazebo.value) {
    return 'leader -> Gazebo';
  }
  return '仿真链';
});

const runtimeLaunchState = computed(() => {
  if (runtimeTargetIsHardware.value) {
    if (demoFlow.value.runtimeReady) {
      return {
        eyebrow: 'Step 02',
        title: '确认真机链路',
        statusLabel: '真机已就绪',
        caption: '当前首页主路径已显式锁到真机链路，只要真机 READY 就继续后续步骤。',
        detail: '仿真状态不会再自动接管这一步，链路已经真正拆开。',
        actionLabel: '真机已就绪',
        disabled: true,
      };
    }
    return {
      eyebrow: 'Step 02',
      title: '确认真机链路',
      statusLabel: realHardwareStatus.value.online ? '等待放行' : '等待接入',
      caption: '当前选择的主路径是真机链路，首页不再接受 Gazebo READY 作为放行条件。',
      detail: realHardwareStatus.value.gateReasonLabel || '请先让真机进入 READY / allowExecute。',
      actionLabel: '等待真机就绪',
      disabled: true,
    };
  }

  const simTitle = runtimeTargetIsLeaderToGazebo.value ? '启动 leader -> Gazebo' : '启动 Gazebo 仿真';
  const readyCaption = runtimeTargetIsLeaderToGazebo.value
    ? 'Gazebo 执行体已在线；真实 leader 输入恢复后可通过 live smoke 验证。'
    : 'Gazebo 与基础服务已经在线，可以直接进入实时链路连接。';
  const waitingCaption = runtimeTargetIsLeaderToGazebo.value
    ? 'leader -> Gazebo 进程已拉起，正在等待 Gazebo 与 controller 稳定。'
    : '仿真进程已拉起，正在等待 Gazebo 与配套服务进入稳定状态。';
  const idleCaption = runtimeTargetIsLeaderToGazebo.value
    ? '先启动 Gazebo simulated arm，后续由实物 leader 输入驱动。'
    : '先启动可见仿真环境，建立本轮演示的运行底座。';

  if (demoFlow.value.runtimeReady) {
    return {
      eyebrow: 'Step 02',
      title: simTitle,
      statusLabel: runtimeTargetIsLeaderToGazebo.value ? 'Gazebo 已就绪' : '仿真已就绪',
      caption: readyCaption,
      detail: '如需重新演示，建议保留当前仿真环境，避免重复启动。',
      actionLabel: '仿真已启动',
      disabled: true,
    };
  }

  if (systemStatus.value.simRunning) {
    return {
      eyebrow: 'Step 02',
      title: simTitle,
      statusLabel: '启动中',
      caption: waitingCaption,
      detail: '首次启动通常需要 3 到 8 秒，页面会自动轮询状态。',
      actionLabel: systemBusy.value.startSim ? '启动中...' : '等待系统就绪',
      disabled: true,
    };
  }

  return {
    eyebrow: 'Step 02',
    title: simTitle,
    statusLabel: '未启动',
    caption: idleCaption,
    detail: '这一步会拉起 Gazebo 与基础服务，完成后再连接实时状态。',
    actionLabel: systemBusy.value.startSim ? '启动中...' : runtimeTargetIsLeaderToGazebo.value ? '启动 leader -> Gazebo' : '启动仿真',
    disabled: false,
  };
});

const liveConnectionState = computed(() => {
  if (socketState.value === 'connected') {
    return {
      statusLabel: '实时在线',
      caption: '状态流与检测流都已订阅，页面会自动接收执行回传。',
      detail: '现在可以直接创建并下发工单，观察状态与检测结果。',
      actionLabel: '实时链路已连接',
      disabled: true,
    };
  }

  if (socketState.value === 'connecting' || socketState.value === 'handshake' || connectBusy.value) {
    return {
      statusLabel: socketLabel.value,
      caption: '正在建立 rosbridge + WebSocket / STOMP 链路。',
      detail: '连接完成后，工单状态与检测结果会自动进入页面。',
      actionLabel: '连接中...',
      disabled: true,
    };
  }

  if (!demoFlow.value.runtimeReady) {
    const waitingCaption = runtimeTargetIsHardware.value
      ? '当前主链锁定为真机，必须先等真机 READY。'
      : runtimeTargetIsLeaderToGazebo.value
        ? '当前主链锁定为 leader -> Gazebo，必须先等 Gazebo 主链就绪。'
        : '当前主链锁定为仿真，必须先等 Gazebo 主链就绪。';
    const waitingDetail = runtimeTargetIsHardware.value
      ? '显式目标切到真机后，仿真状态不会再解锁实时链路。'
      : runtimeTargetIsLeaderToGazebo.value
        ? '该模式不会伪造 leader 输入；无真机时只能验证 Gazebo 执行体和状态链。'
        : '显式目标切到仿真后，真机 READY 状态不会再解锁实时链路。';
    return {
      statusLabel: '等待主链',
      caption: waitingCaption,
      detail: waitingDetail,
      actionLabel: '等待主链就绪',
      disabled: true,
    };
  }

  return {
    statusLabel: rosbridgeConnected.value ? '待订阅' : '未连接',
    caption: '把 backend 接入 rosbridge，并由页面订阅状态流与检测流。',
    detail: '首页只保留一个连接动作，内部会自动完成 rosbridge 与实时订阅。',
    actionLabel: '连接实时状态',
    disabled: false,
  };
});

const workOrderState = computed(() => {
  if (!demoFlow.value.realtimeConnected) {
    return {
      statusLabel: '等待实时链路',
      caption: '工单下发前建议先接通实时状态，确保执行过程可见。',
      detail: '连接完成后，这里会成为本轮演示的主操作位。',
      actionLabel: '等待实时链路',
      disabled: true,
    };
  }

  if (selectedOrder.value?.state === 'RUNNING') {
    return {
      statusLabel: '执行中',
      caption: '当前工单已经开始执行，请重点观察右侧状态时间线。',
      detail: '本轮执行完成前，首页不再鼓励重复下发，避免演示现场混乱。',
      actionLabel: '工单执行中',
      disabled: true,
    };
  }

  if (selectedOrder.value?.state === 'DONE') {
    return {
      statusLabel: '可复演',
      caption: '上一单已完成，可以直接创建并下发下一张演示工单。',
      detail: '默认模板仍然建议使用 pick_place_default。',
      actionLabel: systemBusy.value.createOrder || systemBusy.value.dispatchOrder ? '处理中...' : '创建并下发工单',
      disabled: false,
    };
  }

  if (selectedOrder.value?.state === 'ERROR') {
    return {
      statusLabel: '上一单异常',
      caption: '建议先看右侧状态时间线，再重新创建并下发工单。',
      detail: '首页保留复演能力，但不会把调试按钮拉回主路径。',
      actionLabel: systemBusy.value.createOrder || systemBusy.value.dispatchOrder ? '处理中...' : '重新创建并下发',
      disabled: false,
    };
  }

  return {
    statusLabel: selectedOrder.value ? '待下发' : '准备新工单',
    caption: '选择模板、确认工单 ID，然后直接发起本轮执行。',
    detail: '主页面只保留“创建并下发工单”这一条演示动作。',
    actionLabel: systemBusy.value.createOrder || systemBusy.value.dispatchOrder ? '处理中...' : '创建并下发工单',
    disabled: false,
  };
});

const heroMetrics = computed(() => [
  {
    label: '仿真环境',
    value: runtimeTargetIsHardware.value ? '真机目标' : runtimeLaunchState.value.statusLabel,
    meta: runtimeTargetIsHardware.value
      ? '首页主链已显式锁定真机'
      : runtimeTargetIsLeaderToGazebo.value
        ? 'Gazebo 执行体等待 leader 输入'
      : demoFlow.value.runtimeReady
        ? 'Gazebo 与基础服务就绪'
        : '单击启动后自动进入下一阶段',
    progress: demoFlow.value.runtimeReady ? 100 : systemStatus.value.simRunning ? 58 : 15,
    accent: 'metric-primary',
  },
  {
    label: '实时链路',
    value: liveConnectionState.value.statusLabel,
    meta: demoFlow.value.realtimeConnected ? '状态流、检测流与目标坐标在线' : '统一接管 rosbridge 与 WebSocket',
    progress: demoFlow.value.realtimeConnected ? 100 : socketState.value === 'connecting' || socketState.value === 'handshake' ? 56 : demoFlow.value.runtimeReady ? 18 : 0,
    accent: 'metric-accent',
  },
  {
    label: '当前工单',
    value: selectedOrder.value?.orderId || '未创建',
    meta: selectedOrder.value ? workOrderState.value.statusLabel : '准备发起新的演示工单',
    progress: selectedOrder.value?.state === 'DONE'
      ? 100
      : selectedOrder.value?.state === 'RUNNING'
        ? 72
        : selectedOrder.value?.state === 'ERROR'
          ? 24
          : selectedOrder.value
            ? 40
            : 0,
    accent: 'metric-soft',
  },
  {
    label: '检测结果',
    value: latestDetectionCount.value ? `${latestDetectionCount.value} 个目标` : '等待回传',
    meta: latestDetectionCount.value ? latestDetectionCategories.value : '视觉结果区会自动显示最新消息',
    progress: latestDetectionCount.value ? 82 : 8,
    accent: 'metric-primary',
  },
  {
    label: '真机门禁',
    value: realHardwareStatus.value.allowExecute ? '可演示' : realHardwareStatus.value.online ? '待放行' : '待接入',
    meta: realHardwareStatus.value.allowExecute ? '真机满足执行条件' : '校准、保护、放行仍需确认',
    progress: realHardwareStatus.value.allowExecute ? 100 : realHardwareStatus.value.online ? 42 : 5,
    accent: 'metric-accent',
  },
  {
    label: '系统模式',
    value: runtimeTargetLabel.value,
    meta: '显式目标切换已阻断仿真/真机互相串线',
    progress: 100,
    accent: 'metric-primary',
  },
]);

const systemToolMetrics = computed(() => [
  {
    label: '演示主链',
    value: demoFlow.value.runtimeReady ? '已就绪' : runtimeLaunchState.value.statusLabel,
    tone: demoFlow.value.runtimeReady ? 'metric-good' : 'metric-muted',
  },
  {
    label: '实时链路',
    value: socketLabel.value,
    tone: demoFlow.value.realtimeConnected ? 'metric-good' : socketState.value === 'error' ? 'metric-error' : 'metric-warn',
  },
  {
    label: 'RViz 观察',
    value: systemStatus.value.rvizRunning ? '已打开' : '未打开',
    tone: systemStatus.value.rvizRunning ? 'metric-info' : 'metric-muted',
  },
  {
    label: '当前工单',
    value: workOrderState.value.statusLabel,
    tone: selectedOrder.value?.state === 'DONE'
      ? 'metric-good'
      : selectedOrder.value?.state === 'ERROR'
        ? 'metric-error'
        : selectedOrder.value
          ? 'metric-info'
          : 'metric-muted',
  },
]);

function statusTone(state) {
  return {
    PENDING: 'tone-pending',
    RUNNING: 'tone-running',
    DONE: 'tone-done',
    ERROR: 'tone-error',
  }[state] || 'tone-neutral';
}

function feedTone(type) {
  return {
    success: 'feed-success',
    error: 'feed-error',
    warn: 'feed-warn',
    live: 'feed-live',
    info: 'feed-info',
  }[type] || 'feed-info';
}

async function refreshLatestVisionQuality() {
  try {
    latestVisionEpisodeQuality.value = await fetchLatestVisionQuality();
    pushEvent('success', '采集与训练质量摘要已读取', '前端已加载最新 vision / LeRobot / YOLO smoke artifact。');
  } catch (error) {
    latestVisionEpisodeQuality.value = null;
    pushEvent('warn', '采集质量摘要暂不可用', error?.message || '后端 latest artifact API 未返回数据。');
  }
}

onMounted(async () => {
  topbarTimerId = window.setInterval(() => {
    topbarTime.value = new Date();
  }, 1000);
  await onMountedInit();
  await refreshLatestVisionQuality();
});

onBeforeUnmount(() => {
  if (topbarTimerId) {
    window.clearInterval(topbarTimerId);
    topbarTimerId = null;
  }
  onUnmountedCleanup();
});
</script>

<template>
  <div class="figmake-root grid-bg scan-line">
    <div class="shimmer-strip figmake-shimmer" />
    <div class="demo-shell figmake-container">
      <header class="figmake-topbar fade-up">
        <div class="figmake-brand-block">
          <div class="figmake-logo-mark">
            <span>SO</span>
          </div>
          <div>
            <div class="figmake-title-row">
              <h1>SO-ARM101 CONTROL</h1>
              <span class="chip chip-amber">v2.6.0</span>
            </div>
            <div class="figmake-meta-row">
              <span>NODE-A1 / {{ runtimeTarget }}</span>
              <span>|</span>
              <span class="figmake-online">● {{ socketLabel }}</span>
              <span>|</span>
              <span>{{ runtimeTargetLabel }}</span>
            </div>
          </div>
        </div>

        <div class="figmake-top-actions">
          <div class="figmake-tab-group">
            <button class="tab-btn" :class="{ active: activeTab === 'console' }" @click="selectWorkspaceTab('console')">CONSOLE</button>
            <button class="tab-btn" :class="{ active: activeTab === 'developer' }" @click="openDeveloperWorkspace">DEV WORKSPACE</button>
          </div>
          <div class="panel-flat figmake-clock">{{ topbarTime.toLocaleTimeString('en-GB', { hour12: false }) }}</div>
          <button class="btn-secondary figmake-top-button" @click="toggleDrawer">CONFIG</button>
          <button class="btn-primary figmake-top-button" @click="stopSimulation">E-STOP</button>
        </div>
      </header>

    <section v-show="activeTab === 'console'" class="workspace-view figmake-console-view">
      <DemoHeroPanel
        :overall-state-label="overallStateLabel"
        :overall-state-tone="overallStateTone"
        :primary-prompt="primaryPrompt"
        :primary-prompt-detail="primaryPromptDetail"
        :hero-metrics="heroMetrics"
        :drawer-open="drawerOpen"
        @toggle-drawer="toggleDrawer"
        @start-runtime="startSimulation"
        @enter-workspace="openDeveloperWorkspace"
      />

      <main class="console-layout">
        <section class="workflow-column">
          <section class="action-rail workflow-panel fade-up fade-up-2">
            <div class="section-head rail-head">
              <p class="eyebrow">Primary Flow</p>
              <h2>当前轮次任务</h2>
              <p class="section-copy">主页面只保留本轮任务需要的动作。当前步骤前置，未解锁步骤明确锁定，避免操作者自己猜依赖关系。</p>
            </div>

            <div class="workflow-rail-note">
              <span class="workflow-rail-label">Current Step</span>
              <strong>{{ primaryPrompt }}</strong>
              <p>{{ primaryPromptDetail }}</p>
            </div>

            <div class="action-stack">
              <RuntimeTargetCard
                :runtime-target="runtimeTarget"
                :busy="systemBusy.setRuntimeTarget"
                :sim-running="systemStatus.simRunning"
                :real-hardware="realHardwareStatus"
                @set-target="setRuntimeTarget"
              />

              <RuntimeLaunchCard
                :eyebrow="runtimeLaunchState.eyebrow"
                :title="runtimeLaunchState.title"
                :status-label="runtimeLaunchState.statusLabel"
                :caption="runtimeLaunchState.caption"
                :detail="runtimeLaunchState.detail"
                :button-label="runtimeLaunchState.actionLabel"
                :busy="systemBusy.startSim"
                :disabled="runtimeLaunchState.disabled"
                @action="startSimulation"
              />

              <LiveConnectionCard
                :status-label="liveConnectionState.statusLabel"
                :caption="liveConnectionState.caption"
                :detail="liveConnectionState.detail"
                :button-label="liveConnectionState.actionLabel"
                :busy="connectBusy"
                :disabled="liveConnectionState.disabled"
                :socket-label="socketLabel"
                :rosbridge-connected="rosbridgeConnected"
                @action="connectLiveRuntime"
              />

              <WorkOrderComposerCard
                :status-label="workOrderState.statusLabel"
                :caption="workOrderState.caption"
                :detail="workOrderState.detail"
                :button-label="workOrderState.actionLabel"
                :busy="systemBusy.createOrder || systemBusy.dispatchOrder"
                :disabled="workOrderState.disabled"
                :order-id="orderId"
                :action-template-id="actionTemplateId"
                :selected-order="selectedOrder"
                @update:order-id="orderId = $event"
                @update:action-template-id="actionTemplateId = $event"
                @submit="createAndDispatchOrder"
              />
            </div>
          </section>
        </section>

        <aside class="monitor-column insight-column">
          <FocusedOrderPanel class="fade-up fade-up-3" :selected-order="selectedOrder" :format-stamp="formatStamp" :status-tone="statusTone" />
          <VisionConsolePanel class="fade-up fade-up-4" :detection-entry="latestDetection" :vision-target-entry="latestVisionTarget" :selected-order="selectedOrder" :format-stamp="formatStamp" />
          <StatusTimelinePanel class="fade-up fade-up-5" :status-events="statusEvents" />
        </aside>
      </main>

      <section class="secondary-grid">
        <RealHardwareStatusCard class="fade-up fade-up-5" :real-hardware="realHardwareStatus" />

        <EventTimelinePanel class="fade-up fade-up-6" :event-feed="eventFeed" :feed-tone="feedTone" />

        <article class="developer-entry-card fade-up fade-up-6">
          <div class="section-head compact">
            <p class="eyebrow">Secondary Entry</p>
            <h2>开发者工作区</h2>
            <p class="section-copy">调试浏览器、注入、姿态工作台仍然可达，但它们是二级入口，不再和首页主路径竞争注意力。</p>
          </div>

          <div class="developer-entry-stats">
            <article v-for="item in systemToolMetrics.slice(0, 3)" :key="item.label" class="developer-entry-stat" :class="item.tone">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </article>
          </div>

          <div class="developer-entry-actions">
            <button class="secondary-action" @click="openDeveloperWorkspace">进入开发工作台</button>
            <button class="subtle-action" @click="toggleDrawer">{{ drawerOpen ? '收起维护抽屉' : '打开维护抽屉' }}</button>
          </div>
        </article>
      </section>

      <AdvancedDrawer
        :drawer-open="drawerOpen"
        :developer-tools-enabled="true"
        :socket-label="socketLabel"
        :system-tool-metrics="systemToolMetrics"
        :system-busy="systemBusy"
        :rosbridge-connected="rosbridgeConnected"
        @close="drawerOpen = false"
        @open-rviz="openRviz"
        @stop-sim="stopSimulation"
        @refresh-system="refreshSystemStatus"
        @open-developer-page="openDeveloperWorkspace"
      />
    </section>

    <DeveloperWorkbenchPage
      v-show="activeTab === 'developer'"
      :system-busy="systemBusy"
      :system-status="systemStatus"
      :runtime-target="runtimeTarget"
      :rosbridge-connected="rosbridgeConnected"
      :socket-label="socketLabel"
      :detections="detections"
      :leader-debug="leaderDebug"
      :status-events="statusEvents"
      :vision-episode-quality="latestVisionEpisodeQuality"
      @refresh-system="refreshSystemStatus"
      @open-rviz="openRviz"
      @stop-sim="stopSimulation"
      @open-browser="openBrowser"
      @stop-browser="stopBrowser"
      @set-runtime-target="setRuntimeTarget"
      @connect-live="connectLiveRuntime"
      @inject-status="injectDemoStatus"
      @inject-red="injectDemoDetection('red')"
      @inject-blue="injectDemoDetection('blue')"
      @preview-pose="previewWorkbenchPose"
      @save-workbench="saveWorkbenchExport"
      @merge-waypoints="mergeWorkbenchWaypoints"
      @open-console="openConsoleWorkspace"
    />
    <footer class="figmake-footer">
      <div class="warn-stripes" />
      <div class="figmake-footer-row">
        <span>SO-ARM101 INDUSTRIAL CONSOLE v2.6 - LEROBOT</span>
        <span>SYS LOAD 0.42 · MODE {{ runtimeTargetLabel }} · NET {{ socketLabel }}</span>
        <span class="figmake-online">● SYSTEM ACTIVE</span>
      </div>
    </footer>
    </div>
  </div>
</template>
