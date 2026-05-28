(function () {
  var templates = {};
  var waypoints = {};
  var mapping = {};
  var eventBox = document.getElementById('events');
  var statusGrid = document.getElementById('statusGrid');
  var compactStatusGrid = document.getElementById('compactStatusGrid');
  var templateButtons = document.getElementById('templateButtons');
  var lastAction = document.getElementById('lastAction');
  var hardwareBadge = document.getElementById('hardwareBadge');
  var modeBadge = document.getElementById('modeBadge');
  var executionBadge = document.getElementById('executionBadge');
  var connectBtn = document.getElementById('connectBtn');
  var jointGrid = document.getElementById('jointGrid');
  var jointTimestamp = document.getElementById('jointTimestamp');
  var workflowBar = document.getElementById('workflowBar');
  var manualControls = document.getElementById('manualControls');
  var manualSendBtn = document.getElementById('manualSendBtn');
  var manualHomeBtn = document.getElementById('manualHomeBtn');
  var manualSyncBtn = document.getElementById('manualSyncBtn');
  var manualModeHint = document.getElementById('manualModeHint');
  var monitorModeBtn = document.getElementById('monitorModeBtn');
  var actionModeBtn = document.getElementById('actionModeBtn');
  var repeatCountInput = document.getElementById('repeatCountInput');
  var recordHint = document.getElementById('recordHint');
  var recordNameInput = document.getElementById('recordNameInput');
  var recordIntervalInput = document.getElementById('recordIntervalInput');
  var recordCount = document.getElementById('recordCount');
  var recordStartBtn = document.getElementById('recordStartBtn');
  var recordStopBtn = document.getElementById('recordStopBtn');
  var recordSaveBtn = document.getElementById('recordSaveBtn');
  var playbackHint = document.getElementById('playbackHint');
  var recordingSelect = document.getElementById('recordingSelect');
  var recordingMeta = document.getElementById('recordingMeta');
  var recordingRefreshBtn = document.getElementById('recordingRefreshBtn');
  var recordingRenameBtn = document.getElementById('recordingRenameBtn');
  var recordingDeleteBtn = document.getElementById('recordingDeleteBtn');
  var recordingHomeBtn = document.getElementById('recordingHomeBtn');
  var recordingPauseBtn = document.getElementById('recordingPauseBtn');
  var recordingResumeBtn = document.getElementById('recordingResumeBtn');
  var recordingPlayBtn = document.getElementById('recordingPlayBtn');
  var teleopHint = document.getElementById('teleopHint');
  var leaderPortInput = document.getElementById('leaderPortInput');
  var leaderIdsInput = document.getElementById('leaderIdsInput');
  var teleopFreqInput = document.getElementById('teleopFreqInput');
  var teleopStepInput = document.getElementById('teleopStepInput');
  var teleopMeta = document.getElementById('teleopMeta');
  var teleopScanBtn = document.getElementById('teleopScanBtn');
  var teleopCalibrateBtn = document.getElementById('teleopCalibrateBtn');
  var teleopStartBtn = document.getElementById('teleopStartBtn');
  var teleopPauseBtn = document.getElementById('teleopPauseBtn');
  var teleopResumeBtn = document.getElementById('teleopResumeBtn');
  var teleopStopBtn = document.getElementById('teleopStopBtn');

  var JOINT_NAMES = ['shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_roll', 'gripper'];
  var JOINT_LABELS = ['\u5E95\u5EA7', '\u80A9\u90E8', '\u8098\u90E8', '\u8155\u4FEF\u4EF0', '\u8155\u65CB\u8F6C', '\u5939\u722A'];
  var AXIS_UI = [
    { min: -120, max: 120, step: 1, unit: '\u00B0' },
    { min: -120, max: 120, step: 1, unit: '\u00B0' },
    { min: -120, max: 120, step: 1, unit: '\u00B0' },
    { min: -120, max: 120, step: 1, unit: '\u00B0' },
    { min: -180, max: 180, step: 1, unit: '\u00B0' },
    { min: 0, max: 100, step: 2, unit: '%' }
  ];
  var CAL = null;
  var lastStatus = null;
  var manualState = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0];
  var manualInitialized = false;
  var autoSyncAttempted = false;
  var recording = false;
  var recordTimer = null;
  var recordedPoints = [];
  var recordings = [];
  var pendingRecordingSelection = '';

  function addEvent(type, text) {
    var item = document.createElement('div');
    item.className = 'event ' + type;
    item.innerHTML = '<strong>' + new Date().toLocaleTimeString() + '</strong><span>' + text + '</span>';
    eventBox.insertBefore(item, eventBox.firstChild);
    while (eventBox.children.length > 20) {
      eventBox.removeChild(eventBox.lastChild);
    }
  }

  function api(method, url, body, timeoutMs) {
    var controller = window.AbortController ? new AbortController() : null;
    var didAbort = false;
    var timeout = timeoutMs ? setTimeout(function () {
      didAbort = true;
      if (controller) controller.abort();
    }, timeoutMs) : null;
    return fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller ? controller.signal : undefined
    }).then(function (res) {
      return res.json();
    }).catch(function (err) {
      if (didAbort) {
        addEvent('error', '连接扫描超时，请确认 6 个舵机供电和线路后重试');
      } else {
        addEvent('error', '\u7F51\u7EDC\u9519\u8BEF: ' + err.message);
      }
      return null;
    }).then(function (payload) {
      if (timeout) clearTimeout(timeout);
      return payload;
    });
  }

  function clamp(value, low, high) {
    return Math.max(low, Math.min(high, value));
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  function normalizeRecordingName(value) {
    var name = String(value || '').trim().toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '');
    if (!name) return '';
    if (name.indexOf('record_') !== 0) name = 'record_' + name;
    return name;
  }

  function normalizeDisplayName(value) {
    return String(value || '').replace(/\s+/g, ' ').trim();
  }

  function parseIds(value) {
    return String(value || '').split(',').map(function (item) {
      return parseInt(item.replace(/^\s+|\s+$/g, ''), 10);
    }).filter(function (value) {
      return !isNaN(value);
    });
  }

  function rawToDeg(raw, name) {
    if (!CAL || !CAL[name]) return raw;
    var c = CAL[name];
    if (name === 'gripper') {
      var pct = ((raw - c.range_min) / (c.range_max - c.range_min) * 100).toFixed(1);
      return pct + '%';
    }
    return ((raw - (c.range_min + c.range_max) / 2) * 360 / 4095).toFixed(1) + '\u00B0';
  }

  function getRawFromObservation(obs, name) {
    if (!obs || !CAL || !CAL[name]) return null;
    if (obs.present_positions && obs.present_positions[String(CAL[name].id)] !== undefined) {
      return Number(obs.present_positions[String(CAL[name].id)]);
    }
    if (obs.raw_present && obs.raw_present[name + '.raw_present'] !== undefined) {
      return Number(obs.raw_present[name + '.raw_present']);
    }
    return null;
  }

  function getPositionFromObservation(obs, index) {
    if (!obs || !obs.positions || obs.positions.length !== JOINT_NAMES.length) return null;
    var value = Number(obs.positions[index]);
    return isNaN(value) ? null : value;
  }

  function rawToPosition(raw, name) {
    if (!CAL || !CAL[name]) return 0;
    var c = CAL[name];
    var scales = mapping.position_scales || {};
    var offsets = mapping.position_offsets_deg || {};
    var scale = Number(scales[name] === undefined ? 1 : scales[name]) || 1;
    if (name === 'gripper') {
      var pct = (raw - c.range_min) / (c.range_max - c.range_min) * 100;
      var gripperScale = Number(mapping.gripper_scale === undefined ? 100 : mapping.gripper_scale) || 100;
      var gripperOffset = Number(mapping.gripper_offset || 0);
      return clamp((pct - gripperOffset) / (gripperScale * scale), 0, 1);
    }
    var actionDeg = (raw - (c.range_min + c.range_max) / 2) * 360 / 4095;
    var controlDeg = (actionDeg - Number(offsets[name] || 0)) / scale;
    return controlDeg * Math.PI / 180;
  }

  function displayFromPosition(index, value) {
    if (JOINT_NAMES[index] === 'gripper') return value * 100;
    return value * 180 / Math.PI;
  }

  function positionFromDisplay(index, value) {
    if (JOINT_NAMES[index] === 'gripper') return value / 100;
    return value * Math.PI / 180;
  }

  function needsLiveInitialization() {
    return !!(lastStatus && !lastStatus.dry_run && !lastStatus.monitor_mode);
  }

  function canRunMotion() {
    if (!lastStatus) return false;
    if (lastStatus.monitor_mode) return false;
    if (lastStatus.dry_run) return true;
    return !!(manualInitialized && lastStatus.control_initialized);
  }

  function countObservationAxes(obs) {
    var count = 0;
    for (var i = 0; i < JOINT_NAMES.length; i++) {
      var raw = getRawFromObservation(obs, JOINT_NAMES[i]);
      var position = getPositionFromObservation(obs, i);
      if ((raw !== null && !isNaN(raw)) || position !== null) count += 1;
    }
    return count;
  }

  function positionsFromObservation(obs) {
    var positions = [];
    for (var i = 0; i < JOINT_NAMES.length; i++) {
      var position = getPositionFromObservation(obs, i);
      if (position !== null) {
        positions.push(position);
        continue;
      }
      var raw = getRawFromObservation(obs, JOINT_NAMES[i]);
      if (raw === null || isNaN(raw)) return null;
      positions.push(rawToPosition(raw, JOINT_NAMES[i]));
    }
    return positions;
  }

  function updateRecordCount() {
    if (recordCount) {
      recordCount.textContent = recordedPoints.length + ' frames';
    }
  }

  function selectedRecording() {
    if (!recordingSelect) return null;
    var raw = recordingSelect.value || '';
    for (var i = 0; i < recordings.length; i++) {
      if (recordings[i].kind + ':' + recordings[i].id === raw) {
        return recordings[i];
      }
    }
    return null;
  }

  function updateRecordingMeta() {
    var rec = selectedRecording();
    if (!recordingMeta) return;
    if (!rec) {
      recordingMeta.textContent = '暂无动作';
      return;
    }
    recordingMeta.textContent = (rec.display_name || rec.name || rec.id) + ' / ' + rec.samples + ' frames / ' + rec.delay + 's';
  }

  function getRepeatCount() {
    var repeat = clamp(parseInt((repeatCountInput && repeatCountInput.value) || '1', 10) || 1, 1, 20);
    if (repeatCountInput) repeatCountInput.value = repeat;
    return repeat;
  }

  function setManualValue(index, displayValue) {
    var spec = AXIS_UI[index];
    var bounded = clamp(Number(displayValue), spec.min, spec.max);
    manualState[index] = positionFromDisplay(index, bounded);
    var row = manualControls.querySelector('[data-axis-index="' + index + '"]');
    if (!row) return;
    var range = row.querySelector('input[type="range"]');
    var number = row.querySelector('input[type="number"]');
    var readout = row.querySelector('.axis-readout');
    range.value = bounded;
    number.value = bounded.toFixed(JOINT_NAMES[index] === 'gripper' ? 0 : 1);
    readout.textContent = bounded.toFixed(JOINT_NAMES[index] === 'gripper' ? 0 : 1) + spec.unit;
  }

  function setManualPositions(positions) {
    for (var i = 0; i < JOINT_NAMES.length; i++) {
      setManualValue(i, displayFromPosition(i, Number(positions[i] || 0)));
    }
  }

  function renderManualControls() {
    var html = '';
    for (var i = 0; i < JOINT_NAMES.length; i++) {
      var spec = AXIS_UI[i];
      var value = displayFromPosition(i, manualState[i]);
      html += '<div class="axis-row" data-axis-index="' + i + '">' +
        '<div class="axis-title"><strong>' + JOINT_LABELS[i] + '</strong><span>' + JOINT_NAMES[i] + '</span></div>' +
        '<button class="axis-step" data-nudge="' + (-spec.step) + '">-</button>' +
        '<input type="range" min="' + spec.min + '" max="' + spec.max + '" step="' + spec.step + '" value="' + value + '">' +
        '<input type="number" min="' + spec.min + '" max="' + spec.max + '" step="' + spec.step + '" value="' + value.toFixed(i === 5 ? 0 : 1) + '">' +
        '<div class="axis-readout">' + value.toFixed(i === 5 ? 0 : 1) + spec.unit + '</div>' +
        '<button class="axis-step" data-nudge="' + spec.step + '">+</button>' +
        '</div>';
    }
    manualControls.innerHTML = html;
  }

  function markControlInitialized(source, quiet) {
    api('POST', '/api/control/initialize', {
      source: source || 'current_observation',
      positions: manualState.slice(0)
    }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        manualInitialized = true;
        if (lastStatus) {
          lastStatus.control_initialized = true;
        }
        if (manualModeHint && needsLiveInitialization()) {
          manualModeHint.textContent = '\u5DF2\u6309\u5B9E\u673A\u5F53\u524D\u4F4D\u7F6E\u521D\u59CB\u5316\uFF0C\u53EF\u4EE5\u5C0F\u6B65\u8FD0\u884C\u3002';
        }
        updateMotionAvailability();
        if (!quiet) {
          addEvent('ok', '\u63A7\u5236\u5DF2\u6309\u5F53\u524D\u5B9E\u673A\u4F4D\u7F6E\u521D\u59CB\u5316');
        }
      } else {
        manualInitialized = false;
        updateMotionAvailability();
        addEvent('error', '\u521D\u59CB\u5316\u5931\u8D25: ' + (res.error || 'unknown'));
      }
    });
  }

  function syncManualFromObservation(quiet) {
    var obs = lastStatus ? (lastStatus.last_observation || {}) : {};
    var synced = 0;
    for (var i = 0; i < JOINT_NAMES.length; i++) {
      var position = getPositionFromObservation(obs, i);
      if (position !== null) {
        setManualValue(i, displayFromPosition(i, position));
        synced += 1;
        continue;
      }
      var raw = getRawFromObservation(obs, JOINT_NAMES[i]);
      if (raw !== null && !isNaN(raw)) {
        setManualValue(i, displayFromPosition(i, rawToPosition(raw, JOINT_NAMES[i])));
        synced += 1;
      }
    }
    if (synced === JOINT_NAMES.length) {
      markControlInitialized(quiet ? 'auto_current_observation' : 'current_observation', quiet);
      if (!quiet) {
        addEvent('ok', '\u5DF2\u540C\u6B65\u5F53\u524D\u5173\u8282\u8BFB\u6570: ' + synced + '/6');
      }
    } else if (synced) {
      manualInitialized = false;
      updateMotionAvailability();
      addEvent('warn', '\u53EA\u540C\u6B65\u5230 ' + synced + '/6 \u4E2A\u5173\u8282\uFF0C\u6682\u4E0D\u5141\u8BB8\u8FD0\u884C');
    } else {
      addEvent('warn', '\u6682\u65E0\u53EF\u540C\u6B65\u7684\u5173\u8282\u8BFB\u6570');
    }
  }

  function sendManualPositions() {
    if (!canRunMotion()) {
      addEvent('error', '\u5C1A\u672A\u6309\u5F53\u524D\u5B9E\u673A\u4F4D\u7F6E\u521D\u59CB\u5316\uFF0C\u4E0D\u5141\u8BB8\u53D1\u9001');
      return;
    }
    addEvent('info', '\u53D1\u9001\u516D\u8F74\u76EE\u6807...');
    api('POST', '/api/action', {
      label: 'manual_six_axis',
      positions: manualState.slice(0)
    }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        addEvent('ok', '\u516D\u8F74\u76EE\u6807\u5DF2\u53D1\u9001');
      } else {
        addEvent('error', '\u516D\u8F74\u63A7\u5236\u5931\u8D25: ' + (res.error || 'unknown'));
      }
      refreshStatus();
    });
  }

  function renderJoints(obs) {
    var hasJointData = !!(obs && (obs.present_positions || obs.raw_present || obs.positions));
    if (!hasJointData) {
      var connected = !!(lastStatus && lastStatus.connected);
      var monitor = !!(lastStatus && lastStatus.monitor_mode);
      var message = '\u26A0 \u786C\u4EF6\u672A\u8FDE\u63A5';
      if (monitor) {
        message = connected ? '\u76D1\u89C6\u6A21\u5F0F\u5DF2\u8FDE\u63A5\uFF0C\u7B49\u5F85\u5173\u8282\u8BFB\u6570\u3002' : '\u76D1\u89C6\u6A21\u5F0F\u4E0B\u5148\u8FDE\u63A5\u4ECE\u81C2\u3002';
      } else if (connected) {
        message = '\u52A8\u4F5C\u6A21\u5F0F\uFF1A\u5F53\u524D\u6CA1\u6709\u5173\u8282\u8BFB\u6570\uFF0C\u8BF7\u540C\u6B65\u5F53\u524D\u8BFB\u6570\u540E\u518D\u8FD0\u884C\u3002';
      }
      jointGrid.innerHTML = '<div class="joint-card empty" style="grid-column:1/-1">' +
        message +
        '</div>';
      jointTimestamp.textContent = '';
      return;
    }
    var html = '';
    for (var i = 0; i < JOINT_NAMES.length; i++) {
      var name = JOINT_NAMES[i];
      var mid = CAL ? CAL[name].id : (i + 1);
      var raw = getRawFromObservation(obs, name);
      var position = getPositionFromObservation(obs, i);
      var deg = raw !== null ? rawToDeg(raw, name) : (position !== null ? displayFromPosition(i, position).toFixed(name === 'gripper' ? 0 : 1) + (name === 'gripper' ? '%' : '\u00B0') : '-');
      html += '<div class="joint-card">' +
        '<div class="joint-name">' + JOINT_LABELS[i] + '</div>' +
        '<div class="joint-id">ID ' + mid + '</div>' +
        '<div class="joint-raw">' + (raw !== null ? ('raw: ' + raw) : '\u52A8\u4F5C\u4F4D\u7F6E') + '</div>' +
        '<div class="joint-deg">' + deg + '</div>' +
        '</div>';
    }
    jointGrid.innerHTML = html;
    jointTimestamp.textContent = new Date().toLocaleTimeString();
  }

  function setControlsDisabled(disabled) {
    if (!manualControls) return;
    var fields = manualControls.querySelectorAll('input, button');
    for (var i = 0; i < fields.length; i++) {
      fields[i].disabled = disabled;
    }
  }

  function updateTemplateButtonsDisabled(disabled) {
    var buttons = templateButtons.querySelectorAll('button');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].disabled = disabled;
    }
  }

  function updateMotionAvailability() {
    var monitor = !!(lastStatus && lastStatus.monitor_mode);
    var busy = !!(lastStatus && lastStatus.busy);
    var liveNeedsInit = needsLiveInitialization();
    var ready = canRunMotion();
    setControlsDisabled(monitor || busy);
    if (manualSendBtn) {
      manualSendBtn.disabled = monitor || busy || (liveNeedsInit && !ready);
    }
    if (manualHomeBtn) {
      manualHomeBtn.disabled = monitor || busy || (liveNeedsInit && !ready);
    }
    updateTemplateButtonsDisabled(monitor || busy || (liveNeedsInit && !ready));
    if (recordNameInput) {
      recordNameInput.disabled = recording || busy;
    }
  }

  function renderWorkflow(status) {
    if (!workflowBar) return;
    var monitor = !!(status && status.monitor_mode);
    var connected = !!(status && status.connected);
    var initialized = !!(status && status.control_initialized);
    var executionState = (status && status.execution_state) || 'idle';
    var steps = [
      { label: '1 连接', state: connected ? 'done' : 'pending' },
      { label: monitor ? '2 监视' : '2 动作', state: 'done' },
      { label: '3 初始化', state: initialized || monitor || canRunMotion() ? 'done' : 'pending' },
      { label: '4 执行', state: executionState === 'running' ? 'active' : (executionState === 'paused' || executionState === 'stopping' || executionState === 'stopped' ? 'warn' : 'pending') }
    ];
    workflowBar.innerHTML = steps.map(function (step) {
      return '<div class="workflow-step ' + step.state + '"><span>' + escapeHtml(step.label) + '</span></div>';
    }).join('');
  }

  function updateModeButtons(status) {
    if (!monitorModeBtn || !actionModeBtn || !status) return;
    var busy = !!status.busy;
    monitorModeBtn.className = 'secondary' + (status.monitor_mode ? ' active' : '');
    actionModeBtn.className = 'secondary' + (!status.monitor_mode ? ' active' : '');
    monitorModeBtn.disabled = busy;
    actionModeBtn.disabled = busy;
  }

  function updateRecordingAvailability() {
    var connected = !!(lastStatus && lastStatus.connected);
    var monitor = !!(lastStatus && lastStatus.monitor_mode);
    var busy = !!(lastStatus && lastStatus.busy);
    var executionState = (lastStatus && lastStatus.execution_state) || 'idle';
    var teleop = (lastStatus && lastStatus.teleop) || {};
    var teleopRunning = !!teleop.running;
    var paused = executionState === 'paused';
    var canPlay = canRunMotion() && !!selectedRecording();
    if (recordHint) {
      if (!monitor) {
        recordHint.textContent = '\u5F55\u5236\u53EA\u5728\u76D1\u89C6\u6A21\u5F0F\u5F00\u653E\uFF1B\u52A8\u4F5C\u6A21\u5F0F\u7528\u4E8E\u56DE\u653E\u548C\u516D\u8F74\u53D1\u9001\u3002';
      } else if (!connected) {
        recordHint.textContent = '\u76D1\u89C6\u6A21\u5F0F\u4E0B\u5148\u8FDE\u63A5\u4ECE\u81C2\uFF0C\u7136\u540E\u624B\u52A8\u62D6\u52A8\u5F55\u5236\u3002';
      } else {
        recordHint.textContent = '\u5F55\u5236\u671F\u95F4\u6309\u95F4\u9694\u8FDE\u7EED\u91C7\u6837\u5F53\u524D\u4ECE\u81C2\u59FF\u6001\uFF0C\u505C\u6B62\u540E\u53EF\u4FDD\u5B58\u4E3A\u6A21\u677F\u3002';
      }
    }
    if (recordStartBtn) recordStartBtn.disabled = busy || !monitor || !connected || recording;
    if (recordStopBtn) recordStopBtn.disabled = !recording;
    if (recordSaveBtn) recordSaveBtn.disabled = busy || !monitor || recording || recordedPoints.length < 2;
    if (playbackHint) {
      playbackHint.textContent = canRunMotion()
        ? '\u9009\u62E9\u5DF2\u4FDD\u5B58\u7684\u5F55\u5236\u6A21\u677F\u6216\u6587\u4EF6\u8FDB\u884C\u56DE\u653E\u3002'
        : '\u56DE\u653E\u9700\u8981\u52A8\u4F5C\u6A21\u5F0F\uFF0C\u5E76\u5148\u6309\u5F53\u524D\u5B9E\u673A\u4F4D\u7F6E\u521D\u59CB\u5316\u3002';
    }
    if (recordingRefreshBtn) recordingRefreshBtn.disabled = busy;
    if (recordingDeleteBtn) recordingDeleteBtn.disabled = busy || !selectedRecording();
    if (recordingRenameBtn) recordingRenameBtn.disabled = busy || !selectedRecording();
    if (recordingHomeBtn) recordingHomeBtn.disabled = !connected || monitor || !manualInitialized;
    if (recordingPauseBtn) recordingPauseBtn.disabled = !busy || paused;
    if (recordingResumeBtn) recordingResumeBtn.disabled = !paused;
    if (recordingPlayBtn) recordingPlayBtn.disabled = busy || !canPlay;
  }

  function updateTeleopAvailability() {
    var connected = !!(lastStatus && lastStatus.connected);
    var monitor = !!(lastStatus && lastStatus.monitor_mode);
    var busy = !!(lastStatus && lastStatus.busy);
    var executionState = (lastStatus && lastStatus.execution_state) || 'idle';
    var teleop = (lastStatus && lastStatus.teleop) || {};
    var running = !!teleop.running;
    var paused = !!teleop.paused || executionState === 'paused';
    var canUseTeleop = connected && !monitor;
    var calibrated = !!(teleop.calibration && teleop.calibration.calibrated);
    if (teleopHint) {
      if (monitor) {
        teleopHint.textContent = '主从遥操作只在动作模式下开放。';
      } else if (!connected) {
        teleopHint.textContent = '先连接从臂，再扫描主臂。';
      } else if (!calibrated) {
        teleopHint.textContent = '先把两臂摆成同一姿态，再点击“同步当前位置为校准”。';
      } else {
        teleopHint.textContent = '已保存主从校准，可以开始跟随；先小幅移动确认方向。';
      }
    }
    if (teleopMeta) {
      if (running) {
        teleopMeta.textContent = (paused ? '已暂停' : '跟随中') + ' / ' + (teleop.frames || 0) + ' frames';
      } else if (calibrated) {
        teleopMeta.textContent = '已校准 / ' + new Date(Number(teleop.calibration.created_ms || 0)).toLocaleString();
      } else if (teleop.last_error) {
        teleopMeta.textContent = '已停止 / ' + teleop.last_error;
      } else {
        teleopMeta.textContent = '未校准';
      }
    }
    if (leaderPortInput) leaderPortInput.disabled = running;
    if (leaderIdsInput) leaderIdsInput.disabled = running;
    if (teleopFreqInput) teleopFreqInput.disabled = running;
    if (teleopStepInput) teleopStepInput.disabled = running;
    if (teleopScanBtn) teleopScanBtn.disabled = busy || !canUseTeleop;
    if (teleopCalibrateBtn) teleopCalibrateBtn.disabled = busy || !canUseTeleop;
    if (teleopStartBtn) teleopStartBtn.disabled = busy || !canUseTeleop || !calibrated;
    if (teleopPauseBtn) teleopPauseBtn.disabled = !running || paused;
    if (teleopResumeBtn) teleopResumeBtn.disabled = !running || !paused;
    if (teleopStopBtn) teleopStopBtn.disabled = !running;
  }

  function setMode(mode) {
    addEvent('info', '\u5207\u6362\u6A21\u5F0F: ' + mode);
    stopRecording(false);
    api('POST', '/api/mode', { mode: mode }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        manualInitialized = false;
        autoSyncAttempted = false;
        recordedPoints = [];
        updateRecordCount();
        addEvent('ok', '\u5DF2\u5207\u6362\u5230 ' + (res.monitor_mode ? '\u76D1\u89C6\u6A21\u5F0F' : '\u52A8\u4F5C\u6A21\u5F0F'));
      } else {
        addEvent('error', '\u5207\u6362\u5931\u8D25: ' + (res.error || 'unknown'));
      }
      refreshStatus();
    });
  }

  function captureRecordingSample(quiet) {
    if (!lastStatus || !lastStatus.connected) {
      if (!quiet) addEvent('error', '\u4ECE\u81C2\u672A\u8FDE\u63A5\uFF0C\u65E0\u6CD5\u5F55\u5236');
      return;
    }
    api('POST', '/api/observation', {}).then(function (res) {
      if (!res || !res.ok || !res.observation) {
        if (!quiet) addEvent('error', '\u8BFB\u53D6\u59FF\u6001\u5931\u8D25: ' + ((res && res.error) || 'unknown'));
        return;
      }
      if (lastStatus) {
        lastStatus.last_observation = res.observation;
      }
      renderJoints(res.observation);
      var positions = positionsFromObservation(res.observation);
      if (!positions) {
        if (!quiet) addEvent('warn', '\u5F53\u524D\u59FF\u6001\u4E0D\u5B8C\u6574\uFF0C\u8DF3\u8FC7\u672C\u6B21\u91C7\u6837');
        return;
      }
      recordedPoints.push(positions);
      updateRecordCount();
      updateRecordingAvailability();
    });
  }

  function startRecording() {
    if (recording) return;
    if (!lastStatus || !lastStatus.monitor_mode) {
      addEvent('error', '\u5F55\u5236\u53EA\u80FD\u5728\u76D1\u89C6\u6A21\u5F0F\u4E0B\u8FDB\u884C');
      return;
    }
    if (!lastStatus.connected) {
      addEvent('error', '\u5148\u8FDE\u63A5\u4ECE\u81C2\u518D\u5F55\u5236');
      return;
    }
    recordedPoints = [];
    updateRecordCount();
    recording = true;
    var intervalMs = clamp(Number(recordIntervalInput.value || 250), 80, 3000);
    recordIntervalInput.value = intervalMs;
    captureRecordingSample(true);
    recordTimer = setInterval(function () {
      captureRecordingSample(true);
    }, intervalMs);
    updateRecordingAvailability();
    addEvent('ok', '\u5F00\u59CB\u65F6\u95F4\u6BB5\u5F55\u5236\uFF0C\u95F4\u9694 ' + intervalMs + 'ms');
  }

  function stopRecording(showEvent) {
    if (recordTimer) {
      clearInterval(recordTimer);
      recordTimer = null;
    }
    if (recording && showEvent !== false) {
      addEvent('warn', '\u5DF2\u505C\u6B62\u5F55\u5236\uFF0C\u5171 ' + recordedPoints.length + ' \u5E27');
    }
    recording = false;
    updateRecordingAvailability();
  }

  function saveRecording() {
    if (recordedPoints.length < 2) {
      addEvent('error', '\u5F55\u5236\u5E27\u6570\u4E0D\u8DB3\uFF0C\u81F3\u5C11 2 \u5E27');
      return;
    }
    var intervalMs = clamp(Number(recordIntervalInput.value || 250), 80, 3000);
    var requestedName = normalizeRecordingName(recordNameInput && recordNameInput.value);
    api('POST', '/api/recording/save', {
      name: requestedName,
      delay: intervalMs / 1000.0,
      points: recordedPoints
    }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        addEvent('ok', '\u5DF2\u4FDD\u5B58\u5F55\u5236: ' + res.template + ' / \u6587\u4EF6: ' + (res.file || '-') + ' (' + res.samples + ' \u5E27)');
        recordedPoints = [];
        updateRecordCount();
        if (recordNameInput && res.template) {
          recordNameInput.value = res.template;
        }
        if (res.file) {
          pendingRecordingSelection = 'file:' + res.file;
        } else if (res.template) {
          pendingRecordingSelection = 'template:' + res.template;
        }
        refreshRecordingsAndTemplates();
      } else {
        addEvent('error', '\u4FDD\u5B58\u5931\u8D25: ' + (res.error || 'unknown'));
      }
      updateRecordingAvailability();
    });
  }

  function loadRecordings(preferredValue) {
    return api('GET', '/api/recordings').then(function (payload) {
      if (!payload) return;
      recordings = payload.recordings || [];
      recordings.sort(function (a, b) {
        if (a.kind !== b.kind) return a.kind === 'file' ? -1 : 1;
        var timeDiff = Number(b.created_ms || 0) - Number(a.created_ms || 0);
        if (timeDiff) return timeDiff;
        return String(b.id || '').localeCompare(String(a.id || ''));
      });
      if (!recordingSelect) return;
      var selectedValue = preferredValue || pendingRecordingSelection || recordingSelect.value || '';
      if (!recordings.length) {
        recordingSelect.innerHTML = '<option value="">\u6CA1\u6709\u5DF2\u4FDD\u5B58\u5F55\u5236</option>';
      } else {
        recordingSelect.innerHTML = recordings.map(function (rec) {
          var label = (rec.kind === 'file' ? '\u52A8\u4F5C ' : '\u6A21\u677F ') +
            (rec.display_name || rec.name) + ' (' + rec.samples + ' \u5E27)';
          return '<option value="' + escapeHtml(rec.kind + ':' + rec.id) + '">' + escapeHtml(label) + '</option>';
        }).join('');
      }
      if (selectedValue) {
        for (var i = 0; i < recordingSelect.options.length; i++) {
          if (recordingSelect.options[i].value === selectedValue) {
            recordingSelect.value = selectedValue;
            pendingRecordingSelection = '';
            break;
          }
        }
      }
      updateRecordingMeta();
      renderTemplateLibrary();
      updateRecordingAvailability();
    });
  }

  function loadSelectedRecordingFile(callback) {
    var rec = selectedRecording();
    if (!rec) {
      addEvent('error', '\u5148\u9009\u62E9\u4E00\u4E2A\u5F55\u5236');
      return;
    }
    if (rec.kind === 'template') {
      if (callback) callback(rec.id);
      return;
    }
    api('POST', '/api/recording/load', { id: rec.id }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        addEvent('ok', '\u5DF2\u5BFC\u5165\u5F55\u5236\u6587\u4EF6\u4E3A\u6A21\u677F: ' + res.template);
        refreshRecordingsAndTemplates().then(function () {
          if (callback) callback(res.template);
        });
      } else {
        addEvent('error', '\u5BFC\u5165\u5F55\u5236\u5931\u8D25: ' + (res.error || 'unknown'));
      }
    });
  }

  function playSelectedRecording() {
    if (!canRunMotion()) {
      addEvent('error', '\u56DE\u653E\u524D\u9700\u8981\u5207\u5230\u52A8\u4F5C\u6A21\u5F0F\u5E76\u5B8C\u6210\u521D\u59CB\u5316');
      return;
    }
    loadSelectedRecordingFile(function (templateName) {
      runTemplate(templateName);
    });
  }

  function pausePlayback() {
    api('POST', '/api/pause').then(function (res) {
      if (!res) return;
      if (res.ok) {
        addEvent('warn', res.message || '\u5DF2\u6682\u505C');
      } else {
        addEvent('error', '\u6682\u505C\u5931\u8D25: ' + (res.error || 'unknown'));
      }
      refreshStatus();
    });
  }

  function resumePlayback() {
    api('POST', '/api/resume').then(function (res) {
      if (!res) return;
      if (res.ok) {
        addEvent('ok', res.message || '\u7EE7\u7EED\u56DE\u653E');
      } else {
        addEvent('error', '\u7EE7\u7EED\u5931\u8D25: ' + (res.error || 'unknown'));
      }
      refreshStatus();
    });
  }

  function goSafePointFromPlayback() {
    addEvent('warn', '正在请求慢速回安全点...');
    api('POST', '/api/safe-point').then(function (res) {
      if (!res) return;
      if (res.ok) {
        addEvent('ok', '已发送回安全点');
      } else {
        addEvent('error', '回安全点失败: ' + (res.error || 'unknown'));
      }
      refreshStatus();
    });
  }

  function teleopPayload() {
    var ids = parseIds(leaderIdsInput && leaderIdsInput.value);
    return {
      leader_port: (leaderPortInput && leaderPortInput.value) || '/dev/ttyACM1',
      leader_ids: ids.length ? ids : [1, 2, 3, 4, 5, 6],
      frequency_hz: clamp(Number((teleopFreqInput && teleopFreqInput.value) || 20), 5, 50),
      max_step_raw: clamp(Number((teleopStepInput && teleopStepInput.value) || 24), 2, 120)
    };
  }

  function scanLeaderArm() {
    var payload = teleopPayload();
    addEvent('info', '正在扫描主臂: ' + payload.leader_port);
    api('POST', '/api/teleop/scan', payload, 30000).then(function (res) {
      if (!res) return;
      if (res.ok) {
        addEvent('ok', '主臂扫描成功: ' + JSON.stringify(res.present_raw || {}));
      } else {
        addEvent('error', '主臂扫描失败，缺少 ID: ' + JSON.stringify(res.missing || []) + ' found=' + JSON.stringify(res.found || {}));
      }
      refreshStatus();
    });
  }

  function calibrateTeleop() {
    if (!lastStatus || lastStatus.monitor_mode || !lastStatus.connected) {
      addEvent('error', '先切到动作模式并连接从臂。');
      return;
    }
    if (!window.confirm('确认同步当前位置为主从校准？\n请先把主臂和从臂摆到你认为一致的物理姿态。')) {
      return;
    }
    var payload = teleopPayload();
    addEvent('warn', '正在保存主从当前位置校准...');
    api('POST', '/api/teleop/calibrate', payload, 30000).then(function (res) {
      if (!res) return;
      if (res.ok) {
        addEvent('ok', '主从校准已保存: ' + (res.file || 'config/teleop_calibration.json'));
      } else {
        addEvent('error', '主从校准失败: ' + (res.error || 'unknown'));
      }
      refreshStatus();
    });
  }

  function startTeleop() {
    if (!lastStatus || lastStatus.monitor_mode || !lastStatus.connected) {
      addEvent('error', '先切到动作模式并连接从臂。');
      return;
    }
    var payload = teleopPayload();
    addEvent('warn', '开始主从跟随：使用已保存校准，先小幅移动主臂确认方向。');
    api('POST', '/api/teleop/start', payload, 30000).then(function (res) {
      if (!res) return;
      if (res.ok) {
        addEvent('ok', '主从跟随已启动');
      } else {
        addEvent('error', '主从跟随启动失败: ' + (res.error || 'unknown'));
      }
      refreshStatus();
    });
  }

  function pauseTeleop() {
    api('POST', '/api/teleop/pause').then(function (res) {
      if (!res) return;
      if (res.ok) addEvent('warn', '主从跟随已暂停');
      else addEvent('error', '暂停跟随失败: ' + (res.error || 'unknown'));
      refreshStatus();
    });
  }

  function resumeTeleop() {
    api('POST', '/api/teleop/resume').then(function (res) {
      if (!res) return;
      if (res.ok) addEvent('ok', '主从跟随已继续');
      else addEvent('error', '继续跟随失败: ' + (res.error || 'unknown'));
      refreshStatus();
    });
  }

  function stopTeleop() {
    api('POST', '/api/teleop/stop').then(function (res) {
      if (!res) return;
      if (res.ok) addEvent('warn', '主从跟随已停止');
      else addEvent('error', '停止跟随失败: ' + (res.error || 'unknown'));
      refreshStatus();
    });
  }

  function deleteSelectedRecording() {
    var rec = selectedRecording();
    if (!rec) {
      addEvent('error', '\u5148\u9009\u62E9\u4E00\u4E2A\u5F55\u5236');
      return;
    }
    var label = (rec.kind === 'file' ? '\u52A8\u4F5C ' : '\u6A21\u677F ') + (rec.display_name || rec.name) + ' (' + rec.samples + ' \u5E27)';
    if (!window.confirm('\u5220\u9664\u6240\u9009\u5F55\u5236\uFF1F\n' + label)) {
      return;
    }
    api('POST', '/api/recording/delete', { kind: rec.kind, id: rec.id }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        pendingRecordingSelection = '';
        addEvent('warn', '\u5DF2\u5220\u9664\u5F55\u5236: ' + label + (res.trashed_file ? ' / trash: ' + res.trashed_file : ''));
        refreshRecordingsAndTemplates('');
      } else {
        addEvent('error', '\u5220\u9664\u5931\u8D25: ' + (res.error || 'unknown'));
      }
    });
  }

  function renderStatus(status) {
    if (!status) return;
    lastStatus = status;

    var obs = status.last_observation || {};
    var hwConn = !!(status.connected || obs.connected);
    var monitor = !!status.monitor_mode;
    var executionState = status.execution_state || 'idle';
    if (!hwConn || monitor) {
      manualInitialized = false;
      autoSyncAttempted = false;
    } else if (status.control_initialized) {
      manualInitialized = true;
    }

    hardwareBadge.className = 'hardware-badge ' + (hwConn ? 'connected' : 'disconnected');
    hardwareBadge.textContent = hwConn ? '\u2714 Hardware: connected' : '\u2718 Hardware: disconnected';

    modeBadge.style.background = '';
    if (monitor) {
      modeBadge.className = 'hardware-badge connected';
      modeBadge.textContent = '\u76D1\u89C6\u6A21\u5F0F';
      modeBadge.style.background = '#2a5298';
    } else {
      modeBadge.className = 'hardware-badge connected';
      modeBadge.textContent = '\u52A8\u4F5C\u6A21\u5F0F';
    }

    if (executionBadge) {
      executionBadge.className = 'hardware-badge ' + ((executionState === 'running' || executionState === 'connecting') ? 'connected' : (executionState === 'stopped' ? 'warn' : 'unknown'));
      executionBadge.textContent = executionState === 'connecting' ? '\u8FDE\u63A5\u4E2D' : (executionState === 'running' ? 'EXECUTING' : (executionState === 'stopped' ? 'STOPPED' : 'IDLE'));
    }

    if (manualModeHint) {
      if (monitor) {
        manualModeHint.textContent = '监视模式下不会写入舵机。';
      } else if (!hwConn) {
        manualModeHint.textContent = '\u5148\u8FDE\u63A5\u4ECE\u81C2\uFF1B\u8FDE\u63A5\u540E\u4F1A\u7528\u5B9E\u673A\u5F53\u524D\u4F4D\u7F6E\u521D\u59CB\u5316\u3002';
      } else if (!manualInitialized) {
        manualModeHint.textContent = '\u5DF2\u8FDE\u63A5\uFF0C\u5FC5\u987B\u5148\u540C\u6B65\u5B9E\u673A\u5F53\u524D\u4F4D\u7F6E\u624D\u80FD\u8FD0\u884C\u3002';
      } else {
        manualModeHint.textContent = '\u5DF2\u6309\u5B9E\u673A\u5F53\u524D\u4F4D\u7F6E\u521D\u59CB\u5316\uFF0C\u53EF\u4EE5\u5C0F\u6B65\u8FD0\u884C\u3002';
      }
    }

    var rows = [
      ['connected', status.connected],
      ['mode', monitor ? 'monitor' : 'action'],
      ['execution_state', executionState],
      ['busy', status.busy],
      ['control_initialized', status.control_initialized],
      ['port', status.port],
      ['backend', status.backend],
      ['last_template', status.last_template || '-'],
      ['last_waypoint', status.last_waypoint || '-'],
      ['last_error', status.last_error || '-']
    ];
    statusGrid.innerHTML = rows.map(function (row) {
      return '<div><dt>' + row[0] + '</dt><dd>' + escapeHtml(row[1]) + '</dd></div>';
    }).join('');
    if (compactStatusGrid) {
      compactStatusGrid.innerHTML = [
        ['mode', monitor ? '监视' : '动作'],
        ['hardware', hwConn ? '已连接' : '未连接'],
        ['execution', executionState === 'connecting' ? '连接中' : (executionState === 'running' ? '执行中' : (executionState === 'paused' ? '已暂停' : (executionState === 'stopping' ? '停止中' : (executionState === 'stopped' ? '已停止' : '空闲'))))],
        ['init', status.control_initialized ? '已初始化' : '未初始化']
      ].map(function (row) {
        return '<div><dt>' + row[0] + '</dt><dd>' + escapeHtml(row[1]) + '</dd></div>';
      }).join('');
    }
    lastAction.textContent = JSON.stringify(status.last_action || {}, null, 2);

    renderJoints(obs);
    if (hwConn && !obs.present_positions && !obs.raw_present) {
      api('POST', '/api/observation', {}).then(function (res) {
        if (res && res.ok && res.observation) {
          if (lastStatus) {
            lastStatus.last_observation = res.observation;
          }
          renderJoints(res.observation);
        }
      });
    }
    if (!monitor && hwConn && !manualInitialized && !autoSyncAttempted && countObservationAxes(obs) === JOINT_NAMES.length) {
      autoSyncAttempted = true;
      syncManualFromObservation(true);
    }
    updateModeButtons(status);
    renderWorkflow(status);
    updateMotionAvailability();
    updateRecordingAvailability();
    updateTeleopAvailability();
  }

  function refreshStatus() {
    return api('GET', '/api/status').then(function (status) {
      if (status) renderStatus(status);
    });
  }

  function renderTemplateLibrary() {
    if (!templateButtons) return;
    var templateRecords = recordings.filter(function (rec) {
      return rec.kind === 'template' && templates[rec.id];
    });
    var known = {};
    for (var i = 0; i < templateRecords.length; i++) {
      known[templateRecords[i].id] = true;
    }
    Object.keys(templates).filter(function (name) {
      return name.indexOf('record_') === 0 && !known[name];
    }).forEach(function (name) {
      templateRecords.push({
        kind: 'template',
        id: name,
        name: name,
        display_name: name,
        samples: (templates[name] || []).length
      });
    });
    templateRecords.sort(function (a, b) {
      return String(b.id || '').localeCompare(String(a.id || ''));
    });
    if (!templateRecords.length) {
      templateButtons.innerHTML = '<div class="template-empty">\u6682\u65E0\u5F55\u5236\u52A8\u4F5C</div>';
    } else {
      templateButtons.innerHTML = templateRecords.map(function (rec) {
        var label = rec.display_name || rec.name || rec.id;
        return '<div class="template-item">' +
          '<button class="template-btn" data-template="' + escapeHtml(rec.id) + '">' + escapeHtml(label) + '</button>' +
          '<button class="template-rename-btn secondary" data-rename-template="' + escapeHtml(rec.id) + '" data-current-name="' + escapeHtml(label) + '" title="\u91CD\u547D\u540D">\u6539</button>' +
          '<button class="template-delete-btn danger" data-delete-template="' + escapeHtml(rec.id) + '" title="\u5220\u9664">x</button>' +
          '</div>';
      }).join('');
    }
  }

  function loadTemplates() {
    return api('GET', '/api/templates').then(function (payload) {
      if (!payload) return;
      templates = payload.templates || {};
      waypoints = payload.waypoints || {};
      mapping = payload.mapping || {};
      CAL = payload.calibration || null;
      renderTemplateLibrary();
      renderManualControls();
      setManualPositions(manualState);
      updateMotionAvailability();
      updateRecordingAvailability();
    });
  }

  function refreshRecordingsAndTemplates(preferredValue) {
    return loadTemplates().then(function () {
      return loadRecordings(preferredValue);
    });
  }

  function runTemplate(name) {
    if (!canRunMotion()) {
      addEvent('error', '\u5C1A\u672A\u6309\u5F53\u524D\u5B9E\u673A\u4F4D\u7F6E\u521D\u59CB\u5316\uFF0C\u4E0D\u5141\u8BB8\u8FD0\u884C\u6A21\u677F');
      return;
    }
    var repeat = getRepeatCount();
    addEvent('info', '\u89C4\u5212\u6A21\u677F: ' + name + ' x ' + repeat);
    api('POST', '/api/action', { template: name, repeat: repeat }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        addEvent('ok', '\u89C4\u5212\u5B8C\u6210: ' + name + ' x ' + (res.repeat || repeat));
      } else {
        addEvent('error', '\u6A21\u677F\u5931\u8D25: ' + (res.error || 'unknown'));
      }
      refreshStatus();
    });
  }

  function deleteTemplateByName(name) {
    if (!name) return;
    if (!window.confirm('\u5220\u9664\u5F55\u5236\u52A8\u4F5C\uFF1F\n' + name)) {
      return;
    }
    api('POST', '/api/recording/delete', { kind: 'template', id: name }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        addEvent('warn', '\u5DF2\u5220\u9664\u5F55\u5236\u52A8\u4F5C: ' + name);
        refreshRecordingsAndTemplates('');
      } else {
        addEvent('error', '\u5220\u9664\u5931\u8D25: ' + (res.error || 'unknown'));
      }
    });
  }

  function renameRecording(kind, id, currentName) {
    var requested = window.prompt('\u65B0\u540D\u79F0', currentName || id || '');
    if (requested === null) return;
    var displayName = normalizeDisplayName(requested);
    if (!displayName) {
      addEvent('error', '\u540D\u79F0\u4E0D\u80FD\u4E3A\u7A7A');
      return;
    }
    api('POST', '/api/recording/rename', {
      kind: kind,
      id: id,
      name: displayName
    }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        pendingRecordingSelection = res.kind + ':' + res.new_id;
        addEvent('ok', '\u5DF2\u91CD\u547D\u540D: ' + displayName);
        refreshRecordingsAndTemplates(pendingRecordingSelection);
      } else {
        addEvent('error', '\u91CD\u547D\u540D\u5931\u8D25: ' + (res.error || 'unknown'));
      }
    });
  }

  function renameSelectedRecording() {
    var rec = selectedRecording();
    if (!rec) {
      addEvent('error', '\u5148\u9009\u62E9\u4E00\u4E2A\u5F55\u5236');
      return;
    }
    renameRecording(rec.kind, rec.id, rec.display_name || rec.name || rec.id);
  }

  connectBtn.onclick = function () {
    manualInitialized = false;
    autoSyncAttempted = false;
    updateMotionAvailability();
    connectBtn.disabled = true;
    connectBtn.textContent = '\u626B\u63CF\u4E2D\uFF08\u7EA6 20s\uFF09';
    addEvent('info', '正在连接并扫描 6 个舵机，请等待约 20 秒，期间不需要重复点击。');
    refreshStatus();
    api('POST', '/api/connect', null, 60000).then(function (res) {
      if (!res) {
        return;
      }
      if (res.ok) {
        addEvent('ok', '\u2714 连接成功! 发现舵机: ' + JSON.stringify(res.found || {}));
      } else {
        addEvent('error', '\u2718 \u8FDE\u63A5\u5931\u8D25: ' + (res.error || 'unknown'));
      }
      refreshStatus();
    }).then(function () {
      connectBtn.disabled = false;
      connectBtn.textContent = '\u8FDE\u63A5\u786C\u4EF6';
    });
  };

  document.getElementById('refreshBtn').onclick = function () {
    refreshStatus();
  };

  monitorModeBtn.onclick = function () {
    setMode('monitor');
  };

  actionModeBtn.onclick = function () {
    setMode('action');
  };

  document.getElementById('stopBtn').onclick = function () {
    api('POST', '/api/stop').then(function (res) {
      if (res) addEvent('warn', res.message || '\u5DF2\u8BF7\u6C42\u505C\u6B62');
      refreshStatus();
    });
  };

  templateButtons.onclick = function (event) {
    var target = event.target;
    if (target && target.getAttribute('data-delete-template')) {
      deleteTemplateByName(target.getAttribute('data-delete-template'));
    } else if (target && target.getAttribute('data-rename-template')) {
      var templateName = target.getAttribute('data-rename-template');
      renameRecording('template', templateName, target.getAttribute('data-current-name') || templateName);
    } else if (target && target.getAttribute('data-template')) {
      runTemplate(target.getAttribute('data-template'));
    }
  };

  manualControls.oninput = function (event) {
    var target = event.target;
    if (!target || (target.type !== 'range' && target.type !== 'number')) return;
    var row = target.parentNode;
    setManualValue(Number(row.getAttribute('data-axis-index')), target.value);
  };

  manualControls.onchange = manualControls.oninput;

  manualControls.onclick = function (event) {
    var target = event.target;
    var nudge = target ? target.getAttribute('data-nudge') : null;
    if (nudge === null) return;
    var row = target.parentNode;
    var index = Number(row.getAttribute('data-axis-index'));
    var current = displayFromPosition(index, manualState[index]);
    setManualValue(index, current + Number(nudge));
  };

  manualSendBtn.onclick = sendManualPositions;

  manualHomeBtn.onclick = function () {
    if (waypoints.home) {
      setManualPositions(waypoints.home);
      addEvent('info', '\u516D\u8F74\u76EE\u6807\u5DF2\u8BBE\u4E3A home\uFF0C\u5C1A\u672A\u53D1\u9001');
    }
  };

  manualSyncBtn.onclick = function () {
    syncManualFromObservation(false);
  };

  recordStartBtn.onclick = startRecording;
  recordStopBtn.onclick = function () {
    stopRecording(true);
  };
  recordSaveBtn.onclick = saveRecording;
  if (recordNameInput) {
    recordNameInput.oninput = function () {
      recordNameInput.value = normalizeRecordingName(recordNameInput.value) || recordNameInput.value.replace(/\s+/g, ' ').trim();
    };
  }
  recordingSelect.onchange = function () {
    updateRecordingMeta();
    updateRecordingAvailability();
  };
  recordingRefreshBtn.onclick = function () {
    refreshRecordingsAndTemplates();
  };
  if (recordingRenameBtn) recordingRenameBtn.onclick = renameSelectedRecording;
  recordingDeleteBtn.onclick = deleteSelectedRecording;
  if (recordingHomeBtn) recordingHomeBtn.onclick = goSafePointFromPlayback;
  if (recordingPauseBtn) recordingPauseBtn.onclick = pausePlayback;
  if (recordingResumeBtn) recordingResumeBtn.onclick = resumePlayback;
  recordingPlayBtn.onclick = playSelectedRecording;
  if (teleopScanBtn) teleopScanBtn.onclick = scanLeaderArm;
  if (teleopCalibrateBtn) teleopCalibrateBtn.onclick = calibrateTeleop;
  if (teleopStartBtn) teleopStartBtn.onclick = startTeleop;
  if (teleopPauseBtn) teleopPauseBtn.onclick = pauseTeleop;
  if (teleopResumeBtn) teleopResumeBtn.onclick = resumeTeleop;
  if (teleopStopBtn) teleopStopBtn.onclick = stopTeleop;

  refreshRecordingsAndTemplates().then(function () {
    refreshStatus();
  });
  setInterval(refreshStatus, 3000);
}());
