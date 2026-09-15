import test from 'node:test';
import assert from 'node:assert/strict';
import { useSystemRuntimeModel } from '../useSystemRuntimeModel.js';

test('useSystemRuntimeModel exposes busy flags without owning fetch details', async () => {
  const calls = [];
  let releaseStart = null;
  const api = {
    fetchSystemStatus: async () => ({
      runtimeTarget: 'simulation',
      simRunning: false,
      gazeboRunning: false,
      realHardware: { allowExecute: false },
    }),
    startSimulation: () =>
      new Promise((resolve) => {
        calls.push('start');
        releaseStart = () =>
          resolve({
            status: {
              runtimeTarget: 'simulation',
              simRunning: true,
              gazeboRunning: true,
              realHardware: { allowExecute: false },
            },
          });
      }),
  };

  const model = useSystemRuntimeModel({ api, pushEvent: () => {} });
  const pending = model.startSimulation();

  assert.equal(calls[0], 'start');
  assert.equal(model.busy.value.startSim, true);

  releaseStart();
  await pending;

  assert.equal(model.busy.value.startSim, false);
  assert.equal(model.systemStatus.value.simRunning, true);
  assert.equal(model.systemStatus.value.gazeboRunning, true);
});

test('useSystemRuntimeModel can switch explicit runtime target', async () => {
  const api = {
    fetchSystemStatus: async () => ({
      runtimeTarget: 'simulation',
      simRunning: false,
      gazeboRunning: false,
      realHardware: { allowExecute: false },
    }),
    setRuntimeTarget: async (runtimeTarget) => ({
      status: {
        runtimeTarget,
        simRunning: false,
        gazeboRunning: false,
        realHardware: { allowExecute: false },
      },
    }),
  };

  const model = useSystemRuntimeModel({ api, pushEvent: () => {} });
  await model.refreshSystemStatus();
  assert.equal(model.systemStatus.value.runtimeTarget, 'simulation');

  await model.setRuntimeTarget('real_hardware');

  assert.equal(model.busy.value.setRuntimeTarget, false);
  assert.equal(model.systemStatus.value.runtimeTarget, 'real_hardware');
});

test('useSystemRuntimeModel can switch to real leader to gazebo target', async () => {
  const events = [];
  const api = {
    fetchRosbridgeHealth: async () => ({ connected: false }),
    setRuntimeTarget: async (runtimeTarget) => ({
      status: {
        runtimeTarget,
        simRunning: false,
        gazeboRunning: false,
        realHardware: { allowExecute: false },
      },
    }),
  };

  const model = useSystemRuntimeModel({
    api,
    pushEvent: (level, title, detail) => events.push({ level, title, detail }),
  });

  await model.setRuntimeTarget('real_leader_to_gazebo');

  assert.equal(model.systemStatus.value.runtimeTarget, 'real_leader_to_gazebo');
  assert.match(events[0].title, /leader -> Gazebo/);
  assert.match(events[0].detail, /leader -> Gazebo/);
});
