import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildDemoFlow,
  getOverallStateLabel,
  getPrimaryPrompt,
  getPrimaryPromptDetail,
} from '../demoConsole.js';

test('shows simulation as the first required step on initial state', () => {
  const systemStatus = {
    runtimeTarget: 'simulation',
    simRunning: false,
    gazeboRunning: false,
    rvizRunning: false,
    rosbridgeConnected: false,
    browserRunning: false,
  };

  const flow = buildDemoFlow({
    systemStatus,
    rosbridgeConnected: false,
    socketState: 'idle',
    selectedOrder: null,
  });

  assert.equal(flow.activeStepKey, 'start-runtime');
  assert.equal(flow.steps[0].enabled, true);
  assert.equal(flow.steps[1].enabled, false);
  assert.match(getPrimaryPrompt(flow), /启动 Gazebo 仿真/);
  assert.match(getPrimaryPromptDetail(flow), /3 到 8 秒/);
  assert.equal(getOverallStateLabel(flow), '未就绪');
});

test('asks for rosbridge connection after simulation is ready but backend is not connected', () => {
  const flow = buildDemoFlow({
    systemStatus: {
      runtimeTarget: 'simulation',
      simRunning: true,
      gazeboRunning: true,
      rvizRunning: false,
      rosbridgeConnected: false,
      browserRunning: false,
    },
    rosbridgeConnected: false,
    socketState: 'idle',
    selectedOrder: null,
  });

  assert.equal(flow.activeStepKey, 'connect-rosbridge');
  assert.equal(flow.steps[0].status, 'completed');
  assert.equal(flow.steps[1].enabled, true);
  assert.equal(flow.steps[2].enabled, false);
  assert.match(getPrimaryPrompt(flow), /连接 rosbridge/);
  assert.match(getPrimaryPromptDetail(flow), /点一次即可/);
  assert.equal(getOverallStateLabel(flow), '启动中');
});

test('keeps simulation path locked to gazebo even if stale real hardware status looks ready', () => {
  const flow = buildDemoFlow({
    systemStatus: {
      runtimeTarget: 'simulation',
      simRunning: false,
      gazeboRunning: false,
      rvizRunning: false,
      rosbridgeConnected: false,
      browserRunning: false,
      realHardware: {
        online: true,
        allowExecute: true,
        safetyState: 'READY',
      },
    },
    rosbridgeConnected: false,
    socketState: 'idle',
    selectedOrder: null,
  });

  assert.equal(flow.runtimeSource, 'none');
  assert.equal(flow.activeStepKey, 'start-runtime');
  assert.equal(flow.steps[0].status, 'active');
  assert.equal(flow.steps[1].enabled, false);
  assert.match(getPrimaryPrompt(flow), /启动 Gazebo 仿真/);
  assert.equal(getOverallStateLabel(flow), '未就绪');
});

test('treats real hardware ready state as the active main path only when target is real hardware', () => {
  const flow = buildDemoFlow({
    systemStatus: {
      runtimeTarget: 'real_hardware',
      simRunning: false,
      gazeboRunning: false,
      rvizRunning: false,
      rosbridgeConnected: false,
      browserRunning: false,
      realHardware: {
        online: true,
        allowExecute: true,
        safetyState: 'READY',
      },
    },
    rosbridgeConnected: false,
    socketState: 'idle',
    selectedOrder: null,
  });

  assert.equal(flow.runtimeSource, 'hardware');
  assert.equal(flow.activeStepKey, 'connect-rosbridge');
  assert.equal(flow.steps[0].status, 'completed');
  assert.equal(flow.steps[1].enabled, true);
  assert.match(getPrimaryPrompt(flow), /连接 rosbridge/);
  assert.equal(getOverallStateLabel(flow), '启动中');
});

test('treats real leader to gazebo as a simulation execution body with leader source semantics', () => {
  const flow = buildDemoFlow({
    systemStatus: {
      runtimeTarget: 'real_leader_to_gazebo',
      simRunning: true,
      gazeboRunning: true,
      rvizRunning: false,
      rosbridgeConnected: false,
      browserRunning: false,
      realHardware: {
        online: false,
        allowExecute: false,
        safetyState: '',
      },
    },
    rosbridgeConnected: false,
    socketState: 'idle',
    selectedOrder: null,
  });

  assert.equal(flow.runtimeSource, 'leader_to_gazebo');
  assert.equal(flow.activeStepKey, 'connect-rosbridge');
  assert.equal(flow.steps[0].title, '启动 leader -> Gazebo');
  assert.match(flow.steps[0].caption, /leader 输入驱动 Gazebo/);
  assert.equal(flow.steps[1].enabled, true);
});

test('switches focus to dispatch after simulation, rosbridge, and realtime are ready', () => {
  const order = {
    orderId: 'order-001',
    actionTemplateId: 'pick_place_default',
    state: 'PENDING',
    lastRequestId: null,
    lastStatusCode: null,
    updatedAt: Date.now(),
  };

  const flow = buildDemoFlow({
    systemStatus: {
      runtimeTarget: 'simulation',
      simRunning: true,
      gazeboRunning: true,
      rvizRunning: false,
      rosbridgeConnected: true,
      browserRunning: false,
    },
    rosbridgeConnected: true,
    socketState: 'connected',
    selectedOrder: order,
  });

  assert.equal(flow.activeStepKey, 'dispatch-order');
  assert.equal(flow.steps[2].status, 'completed');
  assert.equal(flow.steps[3].enabled, true);
  assert.match(getPrimaryPrompt(flow), /创建并下发工单/);
  assert.match(getPrimaryPromptDetail(flow), /pick_place_default/);
  assert.equal(getOverallStateLabel(flow), '可演示');
});

test('switches focus to dispatch after real hardware main path is ready', () => {
  const order = {
    orderId: 'order-hw-001',
    actionTemplateId: 'pick_place_red',
    state: 'PENDING',
    lastRequestId: null,
    lastStatusCode: null,
    updatedAt: Date.now(),
  };

  const flow = buildDemoFlow({
    systemStatus: {
      runtimeTarget: 'real_hardware',
      simRunning: false,
      gazeboRunning: false,
      rvizRunning: false,
      rosbridgeConnected: true,
      browserRunning: false,
      realHardware: {
        online: true,
        allowExecute: true,
        safetyState: 'READY',
      },
    },
    rosbridgeConnected: true,
    socketState: 'connected',
    selectedOrder: order,
  });

  assert.equal(flow.runtimeSource, 'hardware');
  assert.equal(flow.activeStepKey, 'dispatch-order');
  assert.equal(flow.steps[3].enabled, true);
  assert.match(getPrimaryPrompt(flow), /创建并下发工单/);
  assert.equal(getOverallStateLabel(flow), '可演示');
});

test('shows a completion prompt after the current order is done', () => {
  const order = {
    orderId: 'order-001',
    actionTemplateId: 'pick_place_default',
    state: 'DONE',
    lastRequestId: 'req-001',
    lastStatusCode: 'OK',
    updatedAt: Date.now(),
  };

  const flow = buildDemoFlow({
    systemStatus: {
      runtimeTarget: 'simulation',
      simRunning: true,
      gazeboRunning: true,
      rvizRunning: false,
      rosbridgeConnected: true,
      browserRunning: false,
    },
    rosbridgeConnected: true,
    socketState: 'connected',
    selectedOrder: order,
  });

  assert.equal(flow.steps[3].status, 'completed');
  assert.match(getPrimaryPrompt(flow), /已完成|复演/);
  assert.match(getPrimaryPromptDetail(flow), /DONE \/ OK|新工单/);
  assert.equal(getOverallStateLabel(flow), '已完成');
});
