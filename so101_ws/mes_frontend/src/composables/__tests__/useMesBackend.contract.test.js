import test from 'node:test';
import assert from 'node:assert/strict';
import { useMesBackend } from '../useMesBackend.js';

test('useMesBackend keeps transport failure out of component code', async () => {
  const events = [];
  let injectedCalls = 0;
  let globalCalls = 0;
  const originalFetch = global.fetch;

  global.fetch = async () => {
    globalCalls += 1;
    throw new Error('global fetch should not be used in this contract test');
  };

  try {
    const apiBase = { value: 'http://127.0.0.1:8080' };
    const model = useMesBackend(apiBase, {
      pushEvent: (...args) => events.push(args),
      fetchImpl: async () => {
        injectedCalls += 1;
        return { ok: false, status: 500, statusText: 'boom' };
      },
    });

    await model.refreshSystemStatus();

    assert.equal(injectedCalls, 1);
    assert.equal(globalCalls, 0);
    assert.equal(events.at(-1)[0], 'warn');
    assert.match(events.at(-1)[2], /500 boom/);
  } finally {
    global.fetch = originalFetch;
  }
});
