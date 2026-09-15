import test from 'node:test';
import assert from 'node:assert/strict';
import { actionTemplateOptions } from '../actionTemplates.js';

test('includes extended demo action templates for the dispatcher', () => {
  const ids = actionTemplateOptions.map((item) => item.id);

  assert.ok(ids.includes('pick_place_default'));
  assert.ok(ids.includes('inspection_sweep'));
  assert.ok(ids.includes('wave_hello'));
  assert.ok(ids.includes('pick_present_place'));
  assert.ok(ids.includes('dance_demo'));
});
