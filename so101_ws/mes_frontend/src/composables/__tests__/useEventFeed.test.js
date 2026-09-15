import test from 'node:test';
import assert from 'node:assert/strict';
import { useEventFeed } from '../useEventFeed.js';

test('rememberStatusEvent refreshes heartbeat without adding timeline noise', () => {
  const feed = useEventFeed();

  feed.rememberStatusEvent({
    requestId: 'req-1',
    state: '执行中',
    code: 'STEP',
    message: '1/8 -> home',
    summary: '第 1 / 8 步：回到 Home 位',
    time: '10:00:00',
  });
  feed.rememberStatusEvent({
    requestId: 'req-1',
    state: '执行中',
    code: 'STEP',
    message: '1/8 -> home',
    summary: '第 1 / 8 步：回到 Home 位',
    time: '10:00:01',
    heartbeat: true,
  });
  feed.rememberStatusEvent({
    requestId: 'req-1',
    state: '执行中',
    code: 'STEP',
    message: '1/8 -> home',
    summary: '第 1 / 8 步：回到 Home 位',
    time: '10:00:02',
    heartbeat: true,
  });

  assert.equal(feed.statusEvents.value.length, 1);
  assert.equal(feed.statusEvents.value[0].time, '10:00:02');
  assert.equal(feed.statusEvents.value[0].heartbeatCount, 2);
});

test('rememberStatusEvent keeps real state transitions as new rows', () => {
  const feed = useEventFeed();

  feed.rememberStatusEvent({
    requestId: 'req-1',
    state: '执行中',
    code: 'STEP',
    message: '1/8 -> home',
    time: '10:00:00',
  });
  feed.rememberStatusEvent({
    requestId: 'req-1',
    state: '执行中',
    code: 'STEP',
    message: '2/8 -> above_pick',
    time: '10:00:01',
    heartbeat: true,
  });

  assert.equal(feed.statusEvents.value.length, 2);
  assert.equal(feed.statusEvents.value[0].message, '2/8 -> above_pick');
  assert.equal(feed.statusEvents.value[0].heartbeatCount, 1);
});

test('rememberLeaderDebug stores latest leader diagnostic streams', () => {
  const feed = useEventFeed();

  feed.rememberLeaderDebug('leaderStatus', { state: 'READY', hz: 30 });
  feed.rememberLeaderDebug('bridgeStatus', { state: 'COMMANDING' });
  feed.rememberLeaderDebug('leaderJointState', { name: ['shoulder_pan'], position: [0.1] });
  feed.rememberLeaderDebug('gazeboJointState', { name: ['shoulder_pan'], position: [0.09] });
  feed.rememberLeaderDebug('followerStatus', { software_ready: true, hardware_bus_ready: false });

  assert.equal(feed.leaderDebug.value.leaderStatus.state, 'READY');
  assert.equal(feed.leaderDebug.value.bridgeStatus.state, 'COMMANDING');
  assert.deepEqual(feed.leaderDebug.value.leaderJointState.position, [0.1]);
  assert.deepEqual(feed.leaderDebug.value.gazeboJointState.position, [0.09]);
  assert.equal(feed.leaderDebug.value.followerStatus.software_ready, true);
  assert.ok(feed.leaderDebug.value.updatedAt);
});
