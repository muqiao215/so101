import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildVisionTrace,
  getDetectionSourceMeta,
  getLatestDetectionItem,
  normalizeDetectionItems,
  summarizeDetectionPayload,
} from '../visionConsole.js';

test('marks frame-based payloads as real yolo detections', () => {
  const payload = {
    frame_id: 'camera_link',
    stamp: { sec: 1, nanosec: 2 },
    count: 1,
    detections: [
      {
        category: 'red',
        confidence: 0.91,
        bbox_xyxy: [120, 80, 220, 180],
      },
    ],
  };

  const meta = getDetectionSourceMeta(payload);
  const item = getLatestDetectionItem(payload);

  assert.equal(meta.key, 'real_yolo');
  assert.equal(meta.isReal, true);
  assert.equal(item.centerLabel, '170, 130');
});

test('keeps demo injection source explicit in summaries and trace', () => {
  const payload = {
    source: 'demo_inject',
    count: 1,
    detections: [
      {
        category: 'blue',
        confidence: 0.95,
        bbox_xywh: [170, 130, 100, 100],
      },
    ],
  };

  const summary = summarizeDetectionPayload(payload);
  const trace = buildVisionTrace(payload, null);

  assert.match(summary, /演示消息/);
  assert.equal(trace.coordinate, '像素中心 170, 130');
  assert.equal(trace.command, 'pick_place_blue');
});

test('keeps gazebo simulated vision distinct from real yolo', () => {
  const payload = {
    source: 'gazebo_color_detector',
    frame_id: 'overhead_camera_link',
    stamp: { sec: 10, nanosec: 20 },
    count: 1,
    detections: [
      {
        category: 'red',
        confidence: 0.88,
        bbox_xyxy: [20, 40, 80, 100],
      },
    ],
  };

  const meta = getDetectionSourceMeta(payload);
  const summary = summarizeDetectionPayload(payload);
  const trace = buildVisionTrace(payload, null);

  assert.equal(meta.key, 'gazebo_color_detector');
  assert.equal(meta.isReal, false);
  assert.match(summary, /仿真检测/);
  assert.equal(trace.coordinate, '像素中心 50, 70');
  assert.equal(trace.command, 'pick_place_red');
});

test('supports legacy single-detection payloads from mock yolo', () => {
  const payload = {
    source: 'mock_yolo',
    category: 'red',
    confidence: 0.9,
    bbox: [160, 120, 80, 80],
  };

  const items = normalizeDetectionItems(payload);

  assert.equal(items.length, 1);
  assert.equal(items[0].bboxKind, 'xywh');
  assert.equal(items[0].centerLabel, '160, 120');
});
