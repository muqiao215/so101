import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildVisionEpisodeQualityCards,
  normalizeVisionEpisodeQuality,
} from '../visionEpisodeQuality.js';

test('normalizes dataset index and candidate manifest into panel model', () => {
  const quality = normalizeVisionEpisodeQuality({
    datasetIndex: {
      source_episode_id: 'gzv011_status_heartbeat_smoke',
      sample_count: 9,
      validation: {
        status: 'passed',
        missing: { detection: 0, task_status: 0 },
        large_delta: { detection: 0, task_status: 0 },
      },
    },
    candidateManifest: {
      train_sample_count: 9,
      debug_sample_count: 0,
      rejected_sample_count: 0,
      manifest_path: '/tmp/lerobot-candidate/manifest.json',
      native_lerobot: {
        available: false,
        reason: 'ImportError: pandas/numpy mismatch',
      },
    },
    heartbeatCount: 35,
    yoloSmoke: {
      status: 'done',
      weights: { best: '/tmp/best.pt' },
      predict: { result_count: 1, first_box_count: 0 },
      train: { results_dict: { 'metrics/mAP50(B)': 0 } },
    },
  });

  assert.equal(quality.hasData, true);
  assert.equal(quality.episodeId, 'gzv011_status_heartbeat_smoke');
  assert.equal(quality.datasetValidationStatus, 'passed');
  assert.equal(quality.trainCount, 9);
  assert.equal(quality.debugCount, 0);
  assert.equal(quality.rejectedCount, 0);
  assert.equal(quality.heartbeatCount, 35);
  assert.equal(quality.candidateManifestPath, '/tmp/lerobot-candidate/manifest.json');
  assert.match(quality.nativeLeRobotBlockedReason, /pandas/);
  assert.equal(quality.yoloSmokeLabel, 'done');
  assert.equal(quality.yoloPredictCount, 1);
  assert.equal(quality.yoloBestWeightPath, '/tmp/best.pt');
});

test('sums heartbeat count from status timeline when no injected count exists', () => {
  const quality = normalizeVisionEpisodeQuality(
    {
      datasetValidationStatus: 'warn',
      candidateManifest: {
        sample_count: 4,
        train_sample_count: 2,
        debug_sample_count: 2,
      },
    },
    {
      statusEvents: [
        { requestId: 'a', heartbeatCount: 3 },
        { requestId: 'b', heartbeatCount: 2 },
      ],
    },
  );

  assert.equal(quality.heartbeatCount, 5);
  assert.equal(quality.datasetValidationLabel, 'warn');
});

test('returns empty injectable model when no episode quality data is present', () => {
  const quality = normalizeVisionEpisodeQuality(null);
  const cards = buildVisionEpisodeQualityCards(quality);

  assert.equal(quality.hasData, false);
  assert.equal(quality.datasetValidationStatus, 'unknown');
  assert.equal(cards[0].value, 'no report');
  assert.equal(cards[4].value, '0');
  assert.equal(cards[5].value, 'no smoke');
});
