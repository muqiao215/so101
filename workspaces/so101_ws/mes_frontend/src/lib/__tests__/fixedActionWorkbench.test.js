import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_TEMPLATE_NAME,
  createWorkbenchPose,
  buildWaypointValues,
  buildPreviewPayload,
  buildMergePayload,
  createRealtimePreviewScheduler,
  formatWaypointSnippet,
  formatActionTemplateSnippet,
} from '../fixedActionWorkbench.js';

test('creates a default SO101 debug pose based on current home posture', () => {
  const pose = createWorkbenchPose(1);

  assert.equal(pose.name, 'debug_pose_1');
  assert.equal(pose.durationMs, 1200);
  assert.equal(pose.joints.shoulder_panDeg, 0);
  assert.equal(pose.joints.shoulder_liftDeg, -11.46);
  assert.equal(pose.joints.elbow_flexDeg, 22.92);
  assert.equal(pose.joints.wrist_flexDeg, -11.46);
  assert.equal(pose.joints.wrist_rollDeg, 0);
  assert.equal(pose.joints.gripper, 0.2);
});

test('converts pose degrees into waypoint radian array with gripper preserved', () => {
  const pose = createWorkbenchPose(2);
  pose.joints.shoulder_panDeg = 90;
  pose.joints.shoulder_liftDeg = -45;
  pose.joints.elbow_flexDeg = 30;
  pose.joints.wrist_flexDeg = -30;
  pose.joints.wrist_rollDeg = 180;
  pose.joints.gripper = 0.85;

  const values = buildWaypointValues(pose);
  assert.deepEqual(values, [1.5708, -0.7854, 0.5236, -0.5236, 3.1416, 0.85]);
});

test('formats waypoint snippet for multiple captured poses', () => {
  const poseA = createWorkbenchPose(1);
  poseA.name = 'wave_left_debug';
  const poseB = createWorkbenchPose(2);
  poseB.name = 'wave_right_debug';
  poseB.joints.shoulder_panDeg = -18;

  const snippet = formatWaypointSnippet([poseA, poseB]);
  assert.match(snippet, /waypoints:/);
  assert.match(snippet, /wave_left_debug:/);
  assert.match(snippet, /wave_right_debug:/);
  assert.match(snippet, /- -0\.3142/);
});

test('formats action template snippet from captured pose names', () => {
  const poses = [createWorkbenchPose(1), createWorkbenchPose(2)];
  const snippet = formatActionTemplateSnippet(DEFAULT_TEMPLATE_NAME, poses);

  assert.match(snippet, /action_templates:/);
  assert.match(snippet, /debug_sequence:/);
  assert.match(snippet, /detection_required: false/);
  assert.match(snippet, /- debug_pose_1/);
  assert.match(snippet, /- debug_pose_2/);
});

test('builds preview payload from the current pose', () => {
  const pose = createWorkbenchPose(3);
  pose.name = 'pose_live';
  pose.durationMs = 950;
  pose.joints.shoulder_panDeg = 45;

  const payload = buildPreviewPayload(pose);

  assert.equal(payload.name, 'pose_live');
  assert.equal(payload.durationSec, 0.95);
  assert.deepEqual(payload.positions, [0.7854, -0.2, 0.4, -0.2, 0, 0.2]);
});

test('builds merge payload for workbench export', () => {
  const poses = [createWorkbenchPose(1), createWorkbenchPose(2)];
  const payload = buildMergePayload('wave_template', poses);

  assert.equal(payload.templateName, 'wave_template');
  assert.equal(payload.poses.length, 2);
  assert.equal(payload.poses[0].name, 'debug_pose_1');
  assert.equal(payload.poses[0].positions.length, 6);
});

test('realtime preview scheduler coalesces rapid updates', async () => {
  const seen = [];
  const scheduler = createRealtimePreviewScheduler((payload) => {
    seen.push(payload.name);
  }, 20);

  scheduler.schedule({ name: 'pose-a' });
  scheduler.schedule({ name: 'pose-b' });
  scheduler.schedule({ name: 'pose-c' });

  await new Promise((resolve) => setTimeout(resolve, 50));

  assert.deepEqual(seen, ['pose-c']);
});
