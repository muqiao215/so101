import test from 'node:test';
import assert from 'node:assert/strict';
import { useConsoleWorkspace } from '../useConsoleWorkspace.js';

test('useConsoleWorkspace owns polling and live-runtime orchestration', async () => {
  const events = [];
  const calls = [];
  let intervalCallback = null;
  let clearedIntervalId = null;

  const workspace = useConsoleWorkspace({
    systemRuntime: {
      refreshSystemStatus: async () => calls.push('system'),
      refreshRosbridgeHealth: async () => calls.push('health'),
    },
    orderWorkflow: {
      refreshOrders: async () => calls.push('orders'),
    },
    realtimeFeed: {
      connectWs: async () => calls.push('connect-ws'),
      closeWs: () => calls.push('close-ws'),
    },
    pushEvent: (...args) => events.push(args),
    timerApi: {
      setInterval(callback, ms) {
        calls.push(`set-interval:${ms}`);
        intervalCallback = callback;
        return 42;
      },
      clearInterval(id) {
        clearedIntervalId = id;
      },
    },
  });

  await workspace.onMountedInit();

  assert.deepEqual(calls.slice(0, 4), ['orders', 'system', 'health', 'set-interval:3000']);
  assert.equal(events[0][1], '演示舱已就绪');

  await intervalCallback();
  assert.deepEqual(calls.slice(4, 7), ['orders', 'system', 'health']);

  workspace.onUnmountedCleanup();
  assert.equal(clearedIntervalId, 42);
  assert.equal(calls.at(-1), 'close-ws');
});

test('useConsoleWorkspace can open developer workspace from URL state', () => {
  const calls = [];
  const workspace = useConsoleWorkspace({
    systemRuntime: {
      refreshSystemStatus: async () => calls.push('system'),
      refreshRosbridgeHealth: async () => calls.push('health'),
    },
    orderWorkflow: {
      refreshOrders: async () => calls.push('orders'),
    },
    realtimeFeed: {
      connectWs: async () => calls.push('connect-ws'),
      closeWs: () => calls.push('close-ws'),
    },
    pushEvent: () => {},
    timerApi: {
      location: {
        search: '?tab=developer',
        hash: '',
      },
    },
  });

  assert.equal(workspace.activeTab.value, 'developer');
});

test('switching to developer workspace keeps realtime websocket alive', () => {
  const calls = [];
  const workspace = useConsoleWorkspace({
    systemRuntime: {
      refreshSystemStatus: async () => calls.push('system'),
      refreshRosbridgeHealth: async () => calls.push('health'),
    },
    orderWorkflow: {
      refreshOrders: async () => calls.push('orders'),
    },
    realtimeFeed: {
      connectWs: async () => calls.push('connect-ws'),
      closeWs: () => calls.push('close-ws'),
    },
    pushEvent: () => {},
    timerApi: {},
  });

  workspace.openDeveloperWorkspace();

  assert.equal(workspace.activeTab.value, 'developer');
  assert.equal(workspace.drawerOpen.value, false);
  assert.deepEqual(calls, []);
});
