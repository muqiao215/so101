import test from 'node:test';
import assert from 'node:assert/strict';
import {
  defaultRealHardwareStatus,
  describeRealHardwareGate,
  describeRealHardwareRefresh,
  describeRealHardwareSummary,
  describeRealHardwareStage,
  describeRecentHardwareIssue,
  describeRecentHardwareIssueSummary,
  resolveRealHardwareStatus,
} from '../realHardwareStatus.js';

test('default real hardware status starts in protected waiting state', () => {
  const status = defaultRealHardwareStatus();
  assert.equal(status.allowExecute, false);
  assert.equal(status.safetyState, 'LOCKED');
  assert.equal(status.gateReasonCode, 'WAITING_FOR_HARDWARE');
  assert.equal(describeRealHardwareStage(status), '未接入');
  assert.equal(describeRealHardwareSummary(status), '等待接入真机');
  assert.equal(describeRealHardwareGate(status), '演示仍停留在接机准备阶段，接入真机状态后再进入下一步。');
  assert.equal(describeRealHardwareRefresh(status), '待接入后自动刷新');
  assert.equal(describeRecentHardwareIssue(status), '无');
  assert.equal(describeRecentHardwareIssueSummary(status), '无异常');
});

test('resolved status describes powered but uncalibrated state', () => {
  const status = resolveRealHardwareStatus({
    realHardware: {
      online: true,
      powerState: '已上电',
      calibrationState: 'UNCALIBRATED',
      gateReasonCode: 'UNCALIBRATED',
      gateReasonLabel: '尚未完成真机校准',
      allowExecute: false,
      safetyState: 'LOCKED',
      updatedAt: '2026-04-07 11:40:00',
      safetyChecks: [
        { key: 'status_fresh', label: '状态新鲜', ok: true, detail: '最近已刷新' },
      ],
    },
  });

  assert.equal(describeRealHardwareStage(status), '已上电但未校准');
  assert.equal(describeRealHardwareSummary(status), '先完成校准');
  assert.equal(describeRealHardwareGate(status), '真机已上电，下一步先完成校准与安全回中。');
});

test('resolved status describes calibrated but not released state', () => {
  const status = resolveRealHardwareStatus({
    realHardware: {
      online: true,
      powerState: '已上电',
      calibrationState: 'READY',
      homed: true,
      gateReasonCode: 'HWS_002_PENDING',
      gateReasonLabel: '安全基线未完成，继续锁执行',
      allowExecute: false,
      safetyState: 'LOCKED',
      updatedAt: '2026-04-07 11:50:00',
      safetyChecks: [
        { key: 'status_fresh', label: '状态新鲜', ok: true, detail: '最近已刷新' },
      ],
    },
  });

  assert.equal(describeRealHardwareStage(status), '已校准但未放行');
  assert.equal(describeRealHardwareSummary(status), '已完成准备，待人工放行');
  assert.equal(describeRealHardwareGate(status), '当前只展示准备就绪状态，仍需人工确认后再进入动作演示。');
});

test('stage ladder keeps the minimum demo stages stable', () => {
  assert.equal(describeRealHardwareStage({ online: false }), '未接入');
  assert.equal(
    describeRealHardwareStage({ online: true, powerState: '未上电', calibrationState: 'UNCALIBRATED' }),
    '已接入但未上电',
  );
  assert.equal(
    describeRealHardwareStage({ online: true, powerState: '已上电', calibrationState: 'UNCALIBRATED' }),
    '已上电但未校准',
  );
  assert.equal(
    describeRealHardwareStage({
      online: true,
      powerState: '已上电',
      calibrationState: 'READY',
      allowExecute: false,
    }),
    '已校准但未放行',
  );
});

test('unclear or stale status keeps protection-first summary', () => {
  const staleStatus = resolveRealHardwareStatus({
    realHardware: {
      online: true,
      powerState: '已上电',
      calibrationState: 'READY',
      allowExecute: false,
      safetyState: 'LOCKED',
      updatedAt: '',
      safetyChecks: [
        { key: 'status_fresh', label: '状态新鲜', ok: false, detail: '等待状态刷新' },
        { key: 'gate_enabled', label: '系统已放行', ok: false, detail: '默认保护态' },
      ],
    },
  });

  assert.equal(describeRealHardwareSummary(staleStatus), '状态待确认，先不演示');
  assert.equal(describeRealHardwareGate(staleStatus), '最近状态还未确认，系统继续保持保护，暂不进入动作演示。');
  assert.equal(describeRealHardwareRefresh(staleStatus), '暂未收到最新时间戳');
  assert.equal(describeRecentHardwareIssueSummary(staleStatus), '待确认');
});

test('ready status uses demo-facing summary without exposing debug wording', () => {
  const readyStatus = resolveRealHardwareStatus({
    realHardware: {
      online: true,
      powerState: '已上电',
      calibrationState: 'READY',
      allowExecute: true,
      safetyState: 'READY',
      updatedAt: '2026-04-07 11:58:00',
      lastError: '无',
      safetyChecks: [
        { key: 'status_fresh', label: '状态新鲜', ok: true, detail: '最近已刷新' },
      ],
    },
  });

  assert.equal(describeRealHardwareSummary(readyStatus), '可安排空载演示');
  assert.equal(describeRealHardwareRefresh(readyStatus), '2026-04-07 11:58:00');
  assert.equal(describeRecentHardwareIssue(readyStatus), '无');
  assert.equal(describeRecentHardwareIssueSummary(readyStatus), '无异常');
});

test('recent issue summary stays concise when a hardware error exists', () => {
  const alertStatus = resolveRealHardwareStatus({
    realHardware: {
      online: true,
      powerState: '已上电',
      calibrationState: 'READY',
      allowExecute: false,
      safetyState: 'LOCKED',
      updatedAt: '2026-04-07 12:08:00',
      lastError: '串口状态刷新失败',
      safetyChecks: [
        { key: 'status_fresh', label: '状态新鲜', ok: true, detail: '最近已刷新' },
      ],
    },
  });

  assert.equal(describeRecentHardwareIssue(alertStatus), '串口状态刷新失败');
  assert.equal(describeRecentHardwareIssueSummary(alertStatus), '需查看');
});
