import test from 'node:test';
import assert from 'node:assert/strict';
import { DANCE_TEMPLATE_ID, buildDanceOrderId, createDanceDemoRunner } from '../danceDemo.js';

test('buildDanceOrderId uses a stable prefix', () => {
  assert.equal(buildDanceOrderId(() => 1234567890), 'dance-1234567890');
});

test('dance demo runner switches template, plays audio, and dispatches order', async () => {
  const calls = [];
  const runner = createDanceDemoRunner({
    now: () => 42,
    setActionTemplateId(value) {
      calls.push(['template', value]);
    },
    setOrderId(value) {
      calls.push(['order', value]);
    },
    async playAudio() {
      calls.push(['audio', 'play']);
    },
    async createAndDispatchOrder() {
      calls.push(['dispatch', DANCE_TEMPLATE_ID]);
    },
    pushEvent(type, title, detail) {
      calls.push(['event', type, title, detail]);
    },
  });

  const orderId = await runner();

  assert.equal(orderId, 'dance-42');
  assert.deepEqual(calls[0], ['template', DANCE_TEMPLATE_ID]);
  assert.deepEqual(calls[1], ['order', 'dance-42']);
  assert.deepEqual(calls[2], ['audio', 'play']);
  assert.deepEqual(calls[3], ['dispatch', DANCE_TEMPLATE_ID]);
  assert.equal(calls[4][0], 'event');
});

test('dance demo runner still dispatches when audio playback fails', async () => {
  const calls = [];
  const runner = createDanceDemoRunner({
    now: () => 77,
    setActionTemplateId(value) {
      calls.push(['template', value]);
    },
    setOrderId(value) {
      calls.push(['order', value]);
    },
    async playAudio() {
      throw new Error('audio blocked');
    },
    async createAndDispatchOrder() {
      calls.push(['dispatch', DANCE_TEMPLATE_ID]);
    },
    pushEvent(type, title) {
      calls.push(['event', type, title]);
    },
  });

  await runner();

  assert.ok(calls.some((item) => item[0] === 'dispatch'));
  assert.ok(calls.some((item) => item[0] === 'event' && item[1] === 'warn'));
});
