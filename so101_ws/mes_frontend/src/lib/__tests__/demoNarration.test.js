import test from 'node:test';
import assert from 'node:assert/strict';
import {
  describeTaskStatus,
  formatOrderState,
  formatStatusCode,
  summarizeOrderMessage,
} from '../demoNarration.js';

test('translates step messages into teacher-readable Chinese narration', () => {
  assert.equal(
    describeTaskStatus({ state: '执行中', code: 'STEP', message: '2/8 -> above_pick' }),
    '第 2 / 8 步：移动到抓取点上方',
  );
  assert.equal(
    describeTaskStatus({ state: '执行中', code: 'STEP', message: '5/8 -> above_place' }),
    '第 5 / 8 步：移动到放置点上方',
  );
});

test('formats start and completion states into presentation wording', () => {
  assert.equal(
    describeTaskStatus({ state: '执行中', code: 'STARTED', message: 'template=pick_place_default' }),
    '任务已启动，执行模板 pick_place_default',
  );
  assert.equal(
    describeTaskStatus({ state: '完成', code: 'OK', message: 'Task completed' }),
    '任务完成，结果正常',
  );
});

test('maps order state and status code to Chinese labels', () => {
  assert.equal(formatOrderState('RUNNING'), '执行中');
  assert.equal(formatOrderState('DONE'), '已完成');
  assert.equal(formatStatusCode('STEP'), '步骤推进');
  assert.equal(formatStatusCode('OK'), '正常完成');
});

test('summarizes order messages for the focused order card', () => {
  assert.equal(summarizeOrderMessage({ state: 'RUNNING', lastStatusCode: 'STEP', message: '4/8 -> lift_from_pick' }), '第 4 / 8 步：抓取后抬升');
  assert.equal(summarizeOrderMessage({ state: 'DONE', lastStatusCode: 'OK', message: 'Task completed' }), '任务完成，结果正常');
});
