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
  var operatorBadge = document.getElementById('operatorBadge');
  var loginGate = document.getElementById('loginGate');
  var loginAdminTab = document.getElementById('loginAdminTab');
  var loginEmployeeTab = document.getElementById('loginEmployeeTab');
  var loginNameLabel = document.getElementById('loginNameLabel');
  var loginNameInput = document.getElementById('loginNameInput');
  var loginPasswordField = document.getElementById('loginPasswordField');
  var loginPasswordInput = document.getElementById('loginPasswordInput');
  var loginEnterBtn = document.getElementById('loginEnterBtn');
  var loginRecordsPanel = document.getElementById('loginRecordsPanel');
  var loginRecordsList = document.getElementById('loginRecordsList');
  var loginRecordsRefreshBtn = document.getElementById('loginRecordsRefreshBtn');
  var loginRecordsClearBtn = document.getElementById('loginRecordsClearBtn');
  var loginRecordsToggleBtn = document.getElementById('loginRecordsToggleBtn');
  var loginRecordsBody = document.getElementById('loginRecordsBody');
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
  var gripperCalArmSelect = document.getElementById('gripperCalArmSelect');
  var followerGripperMinBtn = document.getElementById('followerGripperMinBtn');
  var followerGripperCloseTestBtn = document.getElementById('followerGripperCloseTestBtn');
  var teleopHealthBtn = document.getElementById('teleopHealthBtn');
  var teleopStartBtn = document.getElementById('teleopStartBtn');
  var teleopPauseBtn = document.getElementById('teleopPauseBtn');
  var teleopResumeBtn = document.getElementById('teleopResumeBtn');
  var teleopStopBtn = document.getElementById('teleopStopBtn');
  var productActionSelect = document.getElementById('productActionSelect');
  var productActionRepeatInput = document.getElementById('productActionRepeatInput');
  var productActionMeta = document.getElementById('productActionMeta');
  var visionInspectBtn = document.getElementById('visionInspectBtn');
  var visionResult = document.getElementById('visionResult');
  var visionSnapshot = document.getElementById('visionSnapshot');
  var productActionRefreshBtn = document.getElementById('productActionRefreshBtn');
  var productActionRunBtn = document.getElementById('productActionRunBtn');
  var productActionAdminPanel = document.getElementById('productActionAdminPanel');
  var productActionNameInput = document.getElementById('productActionNameInput');
  var productActionSourceSelect = document.getElementById('productActionSourceSelect');
  var productActionStatusSelect = document.getElementById('productActionStatusSelect');
  var productActionNoteInput = document.getElementById('productActionNoteInput');
  var productActionSaveBtn = document.getElementById('productActionSaveBtn');
  var productActionAdminList = document.getElementById('productActionAdminList');
  var businessRunLogPanel = document.getElementById('businessRunLogPanel');
  var businessRunLogList = document.getElementById('businessRunLogList');
  var businessRunToggleBtn = document.getElementById('businessRunToggleBtn');
  var eventsToggleBtn = document.getElementById('eventsToggleBtn');
  var maintenancePanels = document.querySelectorAll ? document.querySelectorAll('.maintenance-panel') : [];

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
  var pendingSavePayload = null;
  var teleopAlignmentArmed = false;
  var followerGripperMinArmed = false;
  var gripperMinCalibrationArm = 'follower';
  var loginRole = 'admin';
  var loginSession = null;
  var productActions = [];
  var businessRunLog = [];
  var editingProductActionId = '';
  var visionInspecting = false;
  var pendingDeleteRecordingKey = '';
  var pendingDeleteTemplateName = '';
  var eventsExpanded = false;
  var businessRunExpanded = false;
  var loginRecordsExpanded = false;
  var eventItems = [];

  function addEvent(type, text) {
    eventItems.unshift({ type: type, text: text, time: new Date().toLocaleTimeString() });
    while (eventItems.length > 20) eventItems.pop();
    renderEvents();
  }

  function renderEvents() {
    if (!eventBox) return;
    var rows = eventItems.slice(0, eventsExpanded ? 20 : 5);
    if (!rows.length) {
      eventBox.innerHTML = '<div class="template-empty">暂无执行结果</div>';
    } else {
      eventBox.innerHTML = rows.map(function (row) {
        return '<div class="event ' + escapeHtml(row.type) + '">' +
          '<strong>' + escapeHtml(row.time) + '</strong><span>' + escapeHtml(row.text) + '</span>' +
          '</div>';
      }).join('');
    }
    if (eventsToggleBtn) {
      eventsToggleBtn.textContent = eventsExpanded ? '收起' : '展开';
      eventsToggleBtn.disabled = eventItems.length <= 5;
    }
  }

  function setCollapsible(element, button, expanded) {
    if (element) element.className = element.className.replace(/\s*\bhidden\b/g, '') + (expanded ? '' : ' hidden');
    if (button) button.textContent = expanded ? '收起' : '展开';
  }

  function api(method, url, body, timeoutMs) {
    var controller = window.AbortController ? new AbortController() : null;
    var didAbort = false;
    var timeout = timeoutMs ? setTimeout(function () {
      didAbort = true;
      if (controller) controller.abort();
    }, timeoutMs) : null;
    var headers = { 'Content-Type': 'application/json' };
    if (loginSession && loginSession.token) {
      headers['X-Session-Token'] = loginSession.token;
    }
    return fetch(url, {
      method: method,
      headers: headers,
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

  function setElementVisible(element, visible) {
    if (!element) return;
    var className = element.className || '';
    var hasHidden = /\bhidden\b/.test(className);
    if (visible && hasHidden) {
      element.className = className.replace(/\s*\bhidden\b/g, '');
    } else if (!visible && !hasHidden) {
      element.className = className + ' hidden';
    }
  }

  function setLoginRole(role) {
    loginRole = role === 'employee' ? 'employee' : 'admin';
    if (loginAdminTab) loginAdminTab.className = loginRole === 'admin' ? 'active' : 'secondary';
    if (loginEmployeeTab) loginEmployeeTab.className = loginRole === 'employee' ? 'active' : 'secondary';
    if (loginNameLabel) loginNameLabel.textContent = loginRole === 'admin' ? '管理员账号' : '员工姓名';
    if (loginNameInput) {
      loginNameInput.placeholder = loginRole === 'admin' ? 'admin' : '例如 张三';
      loginNameInput.autocomplete = loginRole === 'admin' ? 'username' : 'name';
    }
    if (loginPasswordField) {
      loginPasswordField.className = 'login-field' + (loginRole === 'admin' ? '' : ' hidden');
    }
    if (loginPasswordInput) {
      loginPasswordInput.value = '';
    }
  }

  function updateOperatorUi() {
    var roleLabel = loginSession && loginSession.role === 'employee' ? '员工' : '管理员';
    var name = loginSession ? loginSession.operator : '未登录';
    if (operatorBadge) {
      operatorBadge.className = 'hardware-badge ' + (loginSession ? 'connected' : 'unknown');
      operatorBadge.textContent = loginSession ? (roleLabel + ': ' + name) : '未登录';
    }
    var isAdmin = !!(loginSession && loginSession.role === 'admin');
    setElementVisible(loginRecordsPanel, isAdmin);
    setElementVisible(productActionAdminPanel, isAdmin);
    setElementVisible(businessRunLogPanel, isAdmin);
    for (var i = 0; i < maintenancePanels.length; i++) {
      setElementVisible(maintenancePanels[i], isAdmin);
    }
    if (isAdmin) {
      loadLoginRecords();
    }
    if (loginSession) {
      loadProductActions();
    }
  }

  function renderLoginRecords(records) {
    if (!loginRecordsList) return;
    setCollapsible(loginRecordsBody, loginRecordsToggleBtn, loginRecordsExpanded);
    records = records || [];
    if (!records.length) {
      loginRecordsList.innerHTML = '<div class="template-empty">暂无登录记录</div>';
      return;
    }
    loginRecordsList.innerHTML = records.map(function (rec) {
      var role = rec.role === 'employee' ? '员工' : '管理员';
      return '<div class="login-record">' +
        '<span>' + escapeHtml(rec.time || '-') + '</span>' +
        '<span class="role">' + escapeHtml(role) + '</span>' +
        '<span>' + escapeHtml(rec.operator || '-') + '</span>' +
        '</div>';
    }).join('');
  }

  function loadLoginRecords() {
    return api('GET', '/api/login-records').then(function (res) {
      if (!res || !res.ok) return;
      renderLoginRecords(res.records || []);
    });
  }

  function submitLogin() {
    var operatorName = normalizeDisplayName(loginNameInput && loginNameInput.value);
    var password = loginPasswordInput ? loginPasswordInput.value : '';
    api('POST', '/api/login', {
      role: loginRole,
      operator: operatorName,
      password: password
    }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        loginSession = res.session || { role: loginRole, operator: operatorName || (loginRole === 'admin' ? '管理员' : '员工') };
        if (loginGate) loginGate.className = 'login-gate hidden';
        updateOperatorUi();
        addEvent('ok', '已登录: ' + (loginSession.role === 'employee' ? '员工 ' : '管理员 ') + loginSession.operator);
      } else {
        addEvent('error', '登录失败: ' + (res.error || 'unknown'));
      }
    });
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

  function canPlayRecording() {
    if (!lastStatus) return false;
    if (lastStatus.monitor_mode) return false;
    if (lastStatus.busy) return false;
    if (lastStatus.dry_run) return true;
    return !!lastStatus.connected;
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

  function getProductActionRepeatCount() {
    var repeat = clamp(parseInt((productActionRepeatInput && productActionRepeatInput.value) || '1', 10) || 1, 1, 20);
    if (productActionRepeatInput) productActionRepeatInput.value = repeat;
    return repeat;
  }

  function currentOperatorName() {
    return loginSession ? loginSession.operator : '';
  }

  function productActionStatusLabel(status) {
    if (status === 'released') return '已发布';
    if (status === 'disabled') return '停用';
    return '草稿';
  }

  function productActionSourceRecords() {
    var records = recordings.filter(function (rec) {
      return rec.kind === 'template' && templates[rec.id];
    });
    var known = {};
    for (var i = 0; i < records.length; i++) {
      known[records[i].id] = true;
    }
    Object.keys(templates).filter(function (name) {
      return name.indexOf('record_') === 0 && !known[name];
    }).forEach(function (name) {
      records.push({
        kind: 'template',
        id: name,
        name: name,
        display_name: name,
        samples: (templates[name] || []).length
      });
    });
    records.sort(function (a, b) {
      return String(b.id || '').localeCompare(String(a.id || ''));
    });
    return records;
  }

  function productActionById(id) {
    for (var i = 0; i < productActions.length; i++) {
      if (String(productActions[i].id || '') === String(id || '')) return productActions[i];
    }
    return null;
  }

  function selectedProductAction() {
    if (!productActionSelect) return null;
    return productActionById(productActionSelect.value);
  }

  function updateProductActionMeta() {
    if (!productActionMeta) return;
    var action = selectedProductAction();
    if (!action) {
      productActionMeta.textContent = '未选择产品动作';
      return;
    }
    var parts = [
      productActionStatusLabel(action.status),
      action.source_template || '-',
      action.execution_template ? ('执行 ' + action.execution_template) : '未补帧',
      action.updated_at || '-'
    ];
    if (action.optimization && action.optimization.execution_samples) {
      parts.splice(3, 0, '补帧 ' + action.optimization.source_samples + '->' + action.optimization.execution_samples);
    }
    productActionMeta.textContent = parts.join(' / ');
  }

  function updateProductActionAvailability() {
    var action = selectedProductAction();
    var busy = !!(lastStatus && lastStatus.busy);
    if (productActionRunBtn) productActionRunBtn.disabled = busy || !action || !canPlayRecording();
    if (visionInspectBtn) visionInspectBtn.disabled = busy || visionInspecting || !loginSession;
    if (productActionRefreshBtn) productActionRefreshBtn.disabled = busy;
    if (productActionSaveBtn) productActionSaveBtn.disabled = busy;
  }

  function visionZoneLabel(zone) {
    if (zone === 'raw_zone') return '原料区';
    if (zone === 'process_zone') return '加工区';
    if (zone === 'finished_zone') return '成品区';
    return '未识别';
  }

  function renderVisionResult(payload) {
    if (!visionResult) return;
    if (!payload || !payload.ok) {
      visionResult.textContent = '视觉识别失败: ' + ((payload && payload.error) || 'unknown');
      return;
    }
    var selected = payload.selected || null;
    var parts = [];
    if (selected) {
      parts.push('识别: ' + visionZoneLabel(selected.zone));
      parts.push((selected.color_label || selected.color || '-') + ' / 置信度 ' + selected.confidence);
      parts.push('中心 ' + (selected.center_px || []).join(','));
    } else {
      parts.push('未识别到稳定沙包');
    }
    if (payload.recommended_action_name) {
      parts.push('已选动作: ' + payload.recommended_action_name);
    } else {
      parts.push('未匹配到已发布动作');
    }
    visionResult.textContent = parts.join(' / ');
    if (visionSnapshot && payload.annotated_image_url) {
      visionSnapshot.src = payload.annotated_image_url;
      visionSnapshot.className = 'vision-snapshot';
    }
  }

  function selectProductActionById(id) {
    if (!productActionSelect || !id) return false;
    for (var i = 0; i < productActionSelect.options.length; i++) {
      if (productActionSelect.options[i].value === id) {
        productActionSelect.value = id;
        updateProductActionMeta();
        updateProductActionAvailability();
        return true;
      }
    }
    return false;
  }

  function inspectVision() {
    if (visionInspecting) return;
    visionInspecting = true;
    if (visionResult) visionResult.textContent = '正在拍照识别...';
    updateProductActionAvailability();
    api('POST', '/api/vision/inspect', {}, 10000).then(function (res) {
      if (!res) return;
      renderVisionResult(res);
      if (res.ok && res.recommended_action_id) {
        if (selectProductActionById(res.recommended_action_id)) {
          addEvent('ok', '视觉识别已选择动作: ' + (res.recommended_action_name || res.recommended_action_id));
        } else {
          addEvent('warn', '视觉识别有推荐动作，但当前列表中不可选: ' + res.recommended_action_id);
        }
      } else if (res.ok) {
        addEvent('warn', '视觉识别完成，但没有匹配到已发布动作');
      } else {
        addEvent('error', '视觉识别失败: ' + (res.error || 'unknown'));
      }
    }).then(function () {
      visionInspecting = false;
      updateProductActionAvailability();
    });
  }

  function renderProductActionSourceOptions() {
    if (!productActionSourceSelect) return;
    var records = productActionSourceRecords();
    if (!records.length) {
      productActionSourceSelect.innerHTML = '<option value="">暂无可发布录制</option>';
      return;
    }
    var selected = productActionSourceSelect.value || '';
    productActionSourceSelect.innerHTML = records.map(function (rec) {
      var label = (rec.display_name || rec.name || rec.id) + ' (' + rec.samples + ' 帧)';
      return '<option value="' + escapeHtml(rec.id) + '">' + escapeHtml(label) + '</option>';
    }).join('');
    if (selected) {
      for (var i = 0; i < productActionSourceSelect.options.length; i++) {
        if (productActionSourceSelect.options[i].value === selected) {
          productActionSourceSelect.value = selected;
          break;
        }
      }
    }
  }

  function renderBusinessRunLog() {
    if (!businessRunLogList) return;
    setCollapsible(businessRunLogList, businessRunToggleBtn, businessRunExpanded);
    var rows = businessRunLog.slice(0, businessRunExpanded ? 30 : 5);
    if (!rows.length) {
      businessRunLogList.innerHTML = '<div class="template-empty">暂无业务执行记录</div>';
      return;
    }
    businessRunLogList.innerHTML = rows.map(function (row) {
      var result = row.result === 'ok' ? '成功' : (row.result === 'stopped' ? '停止' : '失败');
      var cls = row.result === 'ok' ? 'released' : (row.result === 'stopped' ? 'draft' : 'disabled');
      return '<div class="business-run-row">' +
        '<span>' + escapeHtml(row.time || '-') + '</span>' +
        '<span>' + escapeHtml(row.operator || '-') + '</span>' +
        '<strong>' + escapeHtml(row.action_name || row.action_id || '-') + '</strong>' +
        '<span>' + escapeHtml('x ' + (row.repeat || 1)) + '</span>' +
        '<span class="status-pill ' + cls + '">' + escapeHtml(result) + '</span>' +
        '<span>' + escapeHtml(row.error || '') + '</span>' +
        '</div>';
    }).join('');
  }

  function renderProductActions() {
    renderProductActionSourceOptions();
    if (productActionSelect) {
      var released = productActions.filter(function (action) {
        return action.status === 'released';
      });
      var selected = productActionSelect.value || '';
      if (!released.length) {
        productActionSelect.innerHTML = '<option value="">暂无已发布产品动作</option>';
      } else {
        productActionSelect.innerHTML = released.map(function (action) {
          var label = (action.name || action.id) + ' / ' + (action.source_template || '-');
          return '<option value="' + escapeHtml(action.id) + '">' + escapeHtml(label) + '</option>';
        }).join('');
        var stillExists = false;
        for (var i = 0; i < productActionSelect.options.length; i++) {
          if (productActionSelect.options[i].value === selected) {
            stillExists = true;
            break;
          }
        }
        if (stillExists) productActionSelect.value = selected;
      }
      updateProductActionMeta();
    }
    if (productActionAdminList) {
      if (!productActions.length) {
        productActionAdminList.innerHTML = '<div class="template-empty">暂无产品动作。先录制并保存动作，再在这里发布。</div>';
      } else {
        productActionAdminList.innerHTML = productActions.map(function (action) {
          var status = action.status || 'draft';
          var opt = action.optimization || {};
          var optimizationText = opt.execution_samples ? (' / 补帧 ' + opt.source_samples + '->' + opt.execution_samples + ' / ' + Number(opt.frame_delay_sec || 0).toFixed(2) + 's') : '';
          var testTemplate = action.execution_template || action.source_template || '';
          return '<div class="product-action-card">' +
            '<div class="product-action-main">' +
              '<strong>' + escapeHtml(action.name || action.id) + '</strong>' +
              '<span class="status-pill ' + escapeHtml(status) + '">' + escapeHtml(productActionStatusLabel(status)) + '</span>' +
              '<span>来源: ' + escapeHtml(action.source_template || '-') + '</span>' +
              '<span>执行: ' + escapeHtml(action.execution_template || '-') + escapeHtml(optimizationText) + '</span>' +
              '<span>更新: ' + escapeHtml(action.updated_by || '-') + ' / ' + escapeHtml(action.updated_at || '-') + '</span>' +
              '<small>' + escapeHtml(action.note || '') + '</small>' +
            '</div>' +
            '<div class="product-action-actions">' +
              '<button class="secondary" data-product-fill="' + escapeHtml(action.id) + '">填入</button>' +
              '<button class="secondary" data-product-test="' + escapeHtml(testTemplate) + '">试运行</button>' +
              '<button data-product-status="released" data-product-id="' + escapeHtml(action.id) + '">发布</button>' +
              '<button class="secondary" data-product-status="draft" data-product-id="' + escapeHtml(action.id) + '">草稿</button>' +
              '<button class="danger" data-product-status="disabled" data-product-id="' + escapeHtml(action.id) + '">停用</button>' +
            '</div>' +
            '</div>';
        }).join('');
      }
    }
    renderBusinessRunLog();
    updateProductActionAvailability();
  }

  function loadProductActions() {
    return api('GET', '/api/product-actions').then(function (res) {
      if (!res || !res.ok) return;
      productActions = res.actions || [];
      businessRunLog = res.run_log || [];
      renderProductActions();
    });
  }

  function fillProductActionForm(action) {
    if (!action) return;
    editingProductActionId = action.id || '';
    if (productActionNameInput) productActionNameInput.value = action.name || '';
    if (productActionStatusSelect) productActionStatusSelect.value = action.status || 'draft';
    if (productActionNoteInput) productActionNoteInput.value = action.note || '';
    renderProductActionSourceOptions();
    if (productActionSourceSelect && action.source_template) productActionSourceSelect.value = action.source_template;
  }

  function saveProductAction() {
    var name = normalizeDisplayName(productActionNameInput && productActionNameInput.value);
    var template = (productActionSourceSelect && productActionSourceSelect.value) || '';
    if (!name) {
      addEvent('error', '产品动作名不能为空');
      return;
    }
    if (!template) {
      addEvent('error', '先选择一个已保存录制作为来源');
      return;
    }
    api('POST', '/api/product-action/save', {
      id: editingProductActionId,
      name: name,
      template: template,
      status: (productActionStatusSelect && productActionStatusSelect.value) || 'draft',
      note: normalizeDisplayName(productActionNoteInput && productActionNoteInput.value),
      operator: currentOperatorName()
    }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        editingProductActionId = '';
        addEvent('ok', '产品动作已保存: ' + (res.action && res.action.name ? res.action.name : name));
        loadProductActions();
      } else {
        addEvent('error', '保存产品动作失败: ' + (res.error || 'unknown'));
      }
    });
  }

  function changeProductActionStatus(id, status) {
    api('POST', '/api/product-action/status', {
      id: id,
      status: status,
      operator: currentOperatorName()
    }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        addEvent('ok', '产品动作状态已更新: ' + productActionStatusLabel(status));
        loadProductActions();
      } else {
        addEvent('error', '状态更新失败: ' + (res.error || 'unknown'));
      }
    });
  }

  function runProductAction(id) {
    var action = productActionById(id);
    if (!action) {
      addEvent('error', '先选择一个产品动作');
      return;
    }
    if (!canPlayRecording()) {
      addEvent('error', '产品动作需要动作模式、已连接从臂，且当前没有其他动作');
      return;
    }
    var repeat = getProductActionRepeatCount();
    addEvent('info', '执行产品动作: ' + (action.name || action.id) + ' x ' + repeat);
    api('POST', '/api/product-action/run', {
      id: action.id,
      repeat: repeat,
      operator: currentOperatorName()
    }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        addEvent('ok', '产品动作已执行: ' + (action.name || action.id));
      } else {
        addEvent('error', '产品动作执行失败: ' + (res.error || 'unknown'));
      }
      refreshStatus();
      loadProductActions();
    });
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
    updateTemplateButtonsDisabled(monitor || busy || !canPlayRecording());
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
    var canPlay = canPlayRecording() && !!selectedRecording();
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
      playbackHint.textContent = canPlayRecording()
        ? '\u9009\u62E9\u5DF2\u4FDD\u5B58\u7684\u5F55\u5236\u6A21\u677F\u6216\u6587\u4EF6\u8FDB\u884C\u56DE\u653E\u3002'
        : '\u56DE\u653E\u9700\u8981\u52A8\u4F5C\u6A21\u5F0F\u3001\u5DF2\u8FDE\u63A5\u4ECE\u81C2\uFF0C\u4E14\u5F53\u524D\u6CA1\u6709\u5176\u4ED6\u52A8\u4F5C\u3002';
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
    var calibrationSource = (teleop.calibration && teleop.calibration.source) || '';
    var midpointCalibrated = calibrated && calibrationSource === 'motor_midpoint_calibration';
    if (teleopHint) {
      if (monitor) {
        teleopHint.textContent = '主从遥操作只在动作模式下开放。';
      } else if (!connected) {
        teleopHint.textContent = '先连接从臂，再扫描主臂。';
      } else if (!calibrated) {
        teleopHint.textContent = '未读取到主从校准文件，请检查主臂和从臂校准 JSON。';
      } else if (midpointCalibrated) {
        teleopHint.textContent = '已使用主臂/从臂中位校准，可以开始跟随；先小幅移动确认方向。';
      } else {
        teleopHint.textContent = '已保存主从校准，可以开始跟随；先小幅移动确认方向。';
      }
    }
    if (teleopMeta) {
      if (running) {
        var gripperDebug = teleop.last_gripper_debug || {};
        var gripperText = gripperDebug.goal_raw !== undefined
          ? (' / G 主 ' + gripperDebug.leader_now_raw + ' 从始 ' + gripperDebug.follower_start_raw + ' 实 ' + gripperDebug.follower_present_raw + ' 目 ' + gripperDebug.goal_raw + (gripperDebug.hold_active ? ' 保持' : ''))
          : '';
        teleopMeta.textContent = (paused ? '已暂停' : '跟随中') + ' / ' + (teleop.frames || 0) + ' frames' + gripperText;
      } else if (midpointCalibrated) {
        teleopMeta.textContent = '已校准 / 中位校准 / ' + new Date(Number(teleop.calibration.created_ms || 0)).toLocaleString();
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
    if (teleopCalibrateBtn) {
      teleopCalibrateBtn.disabled = busy || !canUseTeleop;
      teleopCalibrateBtn.textContent = teleopAlignmentArmed ? '保存当前位置对齐' : '手动重设对齐';
    }
    if (followerGripperMinBtn) {
      followerGripperMinBtn.disabled = busy || !canUseTeleop;
      followerGripperMinBtn.textContent = followerGripperMinArmed ? '保存夹爪闭合端' : '夹爪闭合端';
    }
    if (gripperCalArmSelect) gripperCalArmSelect.disabled = busy || followerGripperMinArmed;
    if (followerGripperCloseTestBtn) followerGripperCloseTestBtn.disabled = busy || !canUseTeleop;
    if (teleopHealthBtn) teleopHealthBtn.disabled = busy;
    if (teleopStartBtn) teleopStartBtn.disabled = busy || !canUseTeleop || !calibrated;
    if (teleopPauseBtn) teleopPauseBtn.disabled = !running || paused;
    if (teleopResumeBtn) teleopResumeBtn.disabled = !running || !paused;
    if (teleopStopBtn) teleopStopBtn.disabled = !running;
  }

  function setMode(mode) {
    addEvent('info', '\u5207\u6362\u6A21\u5F0F: ' + mode);
    teleopAlignmentArmed = false;
    followerGripperMinArmed = false;
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
    var wasRecording = recording;
    recording = false;
    updateRecordingAvailability();
    if (showEvent === false) return;
    if (wasRecording) {
      addEvent('warn', '\u5DF2\u505C\u6B62\u5F55\u5236\uFF0C\u5171 ' + recordedPoints.length + ' \u5E27');
    }
    if (recordedPoints.length >= 2) {
      var intervalMs = clamp(Number(recordIntervalInput.value || 250), 80, 3000);
      promptSaveRecording(recordedPoints, intervalMs / 1000.0, recordedPoints.length);
    } else if (recordedPoints.length > 0) {
      addEvent('warn', '\u5F55\u5236\u53EA\u6709 ' + recordedPoints.length + ' \u5E27\uFF0C\u5C11\u4E8E 2 \u5E27\uFF0C\u5DF2\u81EA\u52A8\u4E22\u5F03');
      recordedPoints = [];
      updateRecordCount();
    }
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
      renderProductActions();
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
    if (!canPlayRecording()) {
      addEvent('error', '\u56DE\u653E\u9700\u8981\u52A8\u4F5C\u6A21\u5F0F\u3001\u5DF2\u8FDE\u63A5\u4ECE\u81C2\uFF0C\u4E14\u5F53\u524D\u6CA1\u6709\u5176\u4ED6\u52A8\u4F5C');
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
      frequency_hz: clamp(Number((teleopFreqInput && teleopFreqInput.value) || 12), 5, 50),
      max_step_raw: clamp(Number((teleopStepInput && teleopStepInput.value) || 12), 2, 120)
    };
  }

  function selectedGripperCalibrationArm() {
    return gripperCalArmSelect && gripperCalArmSelect.value === 'leader' ? 'leader' : 'follower';
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

  function showCalibrationHealth(health, sourceLabel) {
    if (!health) {
      addEvent('warn', '校准体检：未返回结果。');
      return;
    }
    if (health.ok) {
      addEvent('ok', '校准体检（' + (sourceLabel || '') + '）：' + (health.summary || '正常'));
      return;
    }
    addEvent('error', '校准体检（' + (sourceLabel || '') + '）：' + (health.summary || '发现问题'));
    var warnings = health.warnings || [];
    for (var i = 0; i < warnings.length; i++) {
      addEvent('warn', '  · ' + warnings[i].message);
    }
  }

  function checkSavedCalibration() {
    api('GET', '/api/teleop/calibration-health').then(function (res) {
      if (!res) return;
      if (res.ok) {
        showCalibrationHealth(res.health, '当前已保存校准');
      } else {
        addEvent('error', '校准体检失败: ' + (res.error || 'unknown'));
      }
    });
  }

  function calibrateTeleop() {
    if (!lastStatus || lastStatus.monitor_mode || !lastStatus.connected) {
      addEvent('error', '先切到动作模式并连接从臂。');
      return;
    }
    followerGripperMinArmed = false;
    if (!teleopAlignmentArmed) {
      if (!window.confirm('准备手动重设主从对齐？\n系统会先释放从臂力矩，然后你手动把主臂和从臂摆成同一姿态。摆好后再点“保存当前位置对齐”。')) {
        return;
      }
      addEvent('warn', '正在释放从臂力矩，准备手动摆臂对齐...');
      api('POST', '/api/teleop/prepare-calibration', {}, 10000).then(function (res) {
        if (!res) return;
        if (res.ok) {
          teleopAlignmentArmed = true;
          addEvent('ok', '从臂力矩已释放。现在手动摆成同一姿态，然后点击“保存当前位置对齐”。');
        } else {
          addEvent('error', '释放力矩失败: ' + (res.error || 'unknown'));
        }
        refreshStatus();
      });
      return;
    }
    if (!window.confirm('确认保存当前主臂和从臂姿态为新的主从对齐？')) {
      return;
    }
    var payload = teleopPayload();
    addEvent('warn', '正在保存主从当前位置校准...');
    api('POST', '/api/teleop/calibrate', payload, 30000).then(function (res) {
      if (!res) return;
      if (res.ok) {
        teleopAlignmentArmed = false;
        addEvent('ok', '主从校准已保存: ' + (res.file || 'config/teleop_calibration.json'));
        showCalibrationHealth(res.calibration && res.calibration.health, '新保存的校准');
      } else {
        addEvent('error', '主从校准失败: ' + (res.error || 'unknown'));
      }
      refreshStatus();
    });
  }

  function calibrateFollowerGripperMin() {
    if (!lastStatus || lastStatus.monitor_mode || !lastStatus.connected) {
      addEvent('error', '先切到动作模式并连接从臂。');
      return;
    }
    teleopAlignmentArmed = false;
    if (!followerGripperMinArmed) {
      gripperMinCalibrationArm = selectedGripperCalibrationArm();
      var armLabel = gripperMinCalibrationArm === 'leader' ? '主臂' : '从臂';
      if (!window.confirm('准备校准' + armLabel + '夹爪闭合端？\n系统只释放' + armLabel + '夹爪力矩。释放后，请手动把' + armLabel + '夹爪推到完全闭合端，再点“保存夹爪闭合端”。')) {
        return;
      }
      var preparePayload = teleopPayload();
      preparePayload.arm = gripperMinCalibrationArm;
      addEvent('warn', '正在释放' + armLabel + '夹爪力矩...');
      api('POST', '/api/gripper/prepare-min', preparePayload, 10000).then(function (res) {
        if (!res) return;
        if (res.ok) {
          followerGripperMinArmed = true;
          addEvent('ok', armLabel + '夹爪力矩已释放。请手动推到闭合端，然后点击“保存夹爪闭合端”。');
        } else {
          addEvent('error', '释放夹爪失败: ' + (res.error || 'unknown'));
        }
        updateTeleopAvailability();
        refreshStatus();
      });
      return;
    }
    var saveArmLabel = gripperMinCalibrationArm === 'leader' ? '主臂' : '从臂';
    if (!window.confirm('确认把当前' + saveArmLabel + '夹爪位置保存为闭合端 range_min？\n保存前会自动备份对应校准文件。')) {
      return;
    }
    var savePayload = teleopPayload();
    savePayload.arm = gripperMinCalibrationArm;
    addEvent('warn', '正在保存' + saveArmLabel + '夹爪闭合端...');
    api('POST', '/api/gripper/save-min', savePayload, 10000).then(function (res) {
      if (!res) return;
      if (res.ok) {
        followerGripperMinArmed = false;
        addEvent('ok', saveArmLabel + '夹爪闭合端已保存: ' + res.old_range_min + ' -> ' + res.new_range_min);
        loadTemplates();
      } else {
        addEvent('error', '保存夹爪闭合端失败: ' + (res.error || 'unknown'));
      }
      updateTeleopAvailability();
      refreshStatus();
    });
  }

  function testFollowerGripperClose() {
    if (!lastStatus || lastStatus.monitor_mode || !lastStatus.connected) {
      addEvent('error', '先切到动作模式并连接从臂。');
      return;
    }
    if (!window.confirm('直接测试从臂夹爪闭合？\n系统会连续 3 秒向 ID 6 发送闭合端 raw，不经过动作模板。')) {
      return;
    }
    addEvent('warn', '正在直接测试从臂夹爪闭合...');
    api('POST', '/api/follower-gripper/close-test', { duration: 3.0 }, 10000).then(function (res) {
      if (!res) return;
      if (res.ok) {
        var diff = Math.abs(Number(res.final_raw) - Number(res.target_raw));
        var type = diff <= 80 ? 'ok' : 'error';
        var sync = res.limit_sync || {};
        var before = sync.before || {};
        var after = sync.after || {};
        var limitText = '';
        if (before.min_angle_limit !== undefined || after.min_angle_limit !== undefined) {
          limitText = ' / limit ' +
            (before.min_angle_limit !== undefined ? before.min_angle_limit : '-') + '-' +
            (before.max_angle_limit !== undefined ? before.max_angle_limit : '-') + ' -> ' +
            (after.min_angle_limit !== undefined ? after.min_angle_limit : '-') + '-' +
            (after.max_angle_limit !== undefined ? after.max_angle_limit : '-');
        }
        addEvent(type, '夹爪闭合测试: start=' + res.start_raw + ' target=' + res.target_raw + ' final=' + res.final_raw + ' error=' + res.error_raw + limitText);
      } else {
        addEvent('error', '夹爪闭合测试失败: ' + (res.error || 'unknown'));
      }
      refreshStatus();
    });
  }

  function startTeleop() {
    if (!lastStatus || lastStatus.monitor_mode || !lastStatus.connected) {
      addEvent('error', '先切到动作模式并连接从臂。');
      return;
    }
    teleopAlignmentArmed = false;
    followerGripperMinArmed = false;
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
      if (res.ok) {
        addEvent('warn', '主从跟随已停止');
        var samples = res.recorded_samples || 0;
        var points = res.recorded_points || [];
        var delay = res.recorded_delay || 0.25;
        if (samples >= 2 && points.length >= 2) {
          promptSaveRecording(points, delay, samples);
        } else if (samples > 0) {
          addEvent('warn', '主从录制只有 ' + samples + ' 帧，少于 2 帧，已自动丢弃');
        }
      } else {
        addEvent('error', '停止跟随失败: ' + (res.error || 'unknown'));
      }
      refreshStatus();
    });
  }

  function promptSaveRecording(points, delay, samples) {
    var dialog = document.getElementById('savePromptDialog');
    var meta = document.getElementById('savePromptMeta');
    var nameInput = document.getElementById('savePromptName');
    if (!dialog || !meta || !nameInput) {
      addEvent('warn', '录制了 ' + samples + ' 帧（' + (delay * samples).toFixed(1) + ' 秒）但保存对话框不可用');
      return;
    }
    var defaultName = 'teleop_' + formatTimestamp(new Date());
    meta.textContent = '本次主从跟随录制了 ' + samples + ' 帧，间隔 ' + (delay * 1000).toFixed(0) + 'ms，总时长约 ' + (delay * samples).toFixed(1) + ' 秒';
    nameInput.value = defaultName;
    pendingSavePayload = { points: points, delay: delay, samples: samples };
    if (typeof dialog.showModal === 'function') {
      dialog.showModal();
      setTimeout(function () { nameInput.focus(); nameInput.select(); }, 30);
    } else {
      addEvent('warn', '当前浏览器不支持 <dialog>，请改用 Chrome / Edge');
    }
  }

  function commitSaveRecording() {
    var dialog = document.getElementById('savePromptDialog');
    var nameInput = document.getElementById('savePromptName');
    if (!pendingSavePayload) {
      if (dialog) dialog.close();
      return;
    }
    var requestedName = normalizeRecordingName(nameInput && nameInput.value) || '';
    var payload = pendingSavePayload;
    pendingSavePayload = null;
    if (dialog) dialog.close();
    addEvent('warn', '正在保存录制: ' + (requestedName || '默认时间戳名'));
    api('POST', '/api/recording/save', {
      name: requestedName,
      delay: payload.delay,
      points: payload.points
    }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        pendingRecordingSelection = res.file ? 'file:' + res.file : 'template:' + res.template;
        addEvent('ok', '已保存录制: ' + res.template + ' / 文件: ' + (res.file || '-') + ' (' + res.samples + ' 帧)');
        if (recordedPoints === payload.points || (payload.points && recordedPoints.length === payload.points.length)) {
          recordedPoints = [];
          updateRecordCount();
        }
        if (recordNameInput && res.template) {
          recordNameInput.value = res.template;
        }
        refreshRecordingsAndTemplates();
      } else {
        addEvent('error', '保存失败: ' + (res.error || 'unknown'));
      }
    });
  }

  function discardSaveRecording() {
    var dialog = document.getElementById('savePromptDialog');
    var payload = pendingSavePayload;
    pendingSavePayload = null;
    if (payload && recordedPoints === payload.points) {
      recordedPoints = [];
      updateRecordCount();
    }
    addEvent('warn', '已丢弃本次录制（' + (payload ? payload.samples : 0) + ' 帧）');
    if (dialog) dialog.close();
  }

  function cancelSaveRecording() {
    var dialog = document.getElementById('savePromptDialog');
    addEvent('warn', '已取消保存选择，' + (pendingSavePayload ? pendingSavePayload.samples : 0) + ' 帧暂存于本会话');
    if (dialog) dialog.close();
  }

  function formatTimestamp(d) {
    function pad(n) { return n < 10 ? '0' + n : '' + n; }
    return d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) + '_' + pad(d.getHours()) + pad(d.getMinutes()) + pad(d.getSeconds());
  }

  function deleteSelectedRecording() {
    var rec = selectedRecording();
    if (!rec) {
      addEvent('error', '\u5148\u9009\u62E9\u4E00\u4E2A\u5F55\u5236');
      return;
    }
    var label = (rec.kind === 'file' ? '\u52A8\u4F5C ' : '\u6A21\u677F ') + (rec.display_name || rec.name) + ' (' + rec.samples + ' \u5E27)';
    var key = rec.kind + ':' + rec.id;
    if (pendingDeleteRecordingKey !== key) {
      pendingDeleteRecordingKey = key;
      if (recordingDeleteBtn) recordingDeleteBtn.textContent = '确认删除';
      addEvent('warn', '再次点击“确认删除”才会删除: ' + label);
      return;
    }
    pendingDeleteRecordingKey = '';
    if (recordingDeleteBtn) recordingDeleteBtn.textContent = '删除所选';
    api('POST', '/api/recording/delete', { kind: rec.kind, id: rec.id }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        pendingRecordingSelection = '';
        pendingDeleteRecordingKey = '';
        if (recordingDeleteBtn) recordingDeleteBtn.textContent = '删除所选';
        addEvent('warn', '\u5DF2\u5220\u9664\u5F55\u5236: ' + label + (res.trashed_file ? ' / trash: ' + res.trashed_file : ''));
        refreshRecordingsAndTemplates('');
      } else {
        pendingDeleteRecordingKey = '';
        if (recordingDeleteBtn) recordingDeleteBtn.textContent = '删除所选';
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
    updateProductActionAvailability();
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
    var pendingStillExists = false;
    for (var pendingIndex = 0; pendingIndex < templateRecords.length; pendingIndex++) {
      if (templateRecords[pendingIndex].id === pendingDeleteTemplateName) pendingStillExists = true;
    }
    if (!pendingStillExists) pendingDeleteTemplateName = '';
    if (!templateRecords.length) {
      templateButtons.innerHTML = '<div class="template-empty">\u6682\u65E0\u5F55\u5236\u52A8\u4F5C</div>';
    } else {
      templateButtons.innerHTML = templateRecords.map(function (rec) {
        var label = rec.display_name || rec.name || rec.id;
        var deleteLabel = pendingDeleteTemplateName === rec.id ? '确认' : 'x';
        return '<div class="template-item">' +
          '<button class="template-btn" data-template="' + escapeHtml(rec.id) + '">' + escapeHtml(label) + '</button>' +
          '<button class="template-rename-btn secondary" data-rename-template="' + escapeHtml(rec.id) + '" data-current-name="' + escapeHtml(label) + '" title="\u91CD\u547D\u540D">\u6539</button>' +
          '<button class="template-delete-btn danger" data-delete-template="' + escapeHtml(rec.id) + '" title="\u5220\u9664">' + deleteLabel + '</button>' +
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
      renderProductActions();
    });
  }

  function refreshRecordingsAndTemplates(preferredValue) {
    return loadTemplates().then(function () {
      return loadRecordings(preferredValue);
    }).then(function () {
      return loadProductActions();
    });
  }

  function runTemplate(name) {
    if (!canPlayRecording()) {
      addEvent('error', '\u56DE\u653E\u9700\u8981\u52A8\u4F5C\u6A21\u5F0F\u3001\u5DF2\u8FDE\u63A5\u4ECE\u81C2\uFF0C\u4E14\u5F53\u524D\u6CA1\u6709\u5176\u4ED6\u52A8\u4F5C');
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
    if (pendingDeleteTemplateName !== name) {
      pendingDeleteTemplateName = name;
      renderTemplateLibrary();
      addEvent('warn', '再次点击“确认”才会删除录制动作: ' + name);
      return;
    }
    pendingDeleteTemplateName = '';
    api('POST', '/api/recording/delete', { kind: 'template', id: name }).then(function (res) {
      if (!res) return;
      if (res.ok) {
        pendingDeleteTemplateName = '';
        addEvent('warn', '\u5DF2\u5220\u9664\u5F55\u5236\u52A8\u4F5C: ' + name);
        refreshRecordingsAndTemplates('');
      } else {
        pendingDeleteTemplateName = '';
        renderTemplateLibrary();
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

  if (loginAdminTab) loginAdminTab.onclick = function () {
    setLoginRole('admin');
  };

  if (loginEmployeeTab) loginEmployeeTab.onclick = function () {
    setLoginRole('employee');
  };

  if (loginEnterBtn) loginEnterBtn.onclick = submitLogin;

  if (loginNameInput) {
    loginNameInput.onkeydown = function (event) {
      if (event.key === 'Enter') {
        submitLogin();
      }
    };
  }

  if (loginPasswordInput) {
    loginPasswordInput.onkeydown = function (event) {
      if (event.key === 'Enter') {
        submitLogin();
      }
    };
  }

  if (loginRecordsRefreshBtn) loginRecordsRefreshBtn.onclick = loadLoginRecords;
  if (eventsToggleBtn) eventsToggleBtn.onclick = function () {
    eventsExpanded = !eventsExpanded;
    renderEvents();
  };
  if (businessRunToggleBtn) businessRunToggleBtn.onclick = function () {
    businessRunExpanded = !businessRunExpanded;
    renderBusinessRunLog();
  };
  if (loginRecordsToggleBtn) loginRecordsToggleBtn.onclick = function () {
    loginRecordsExpanded = !loginRecordsExpanded;
    setCollapsible(loginRecordsBody, loginRecordsToggleBtn, loginRecordsExpanded);
    if (loginRecordsExpanded) loadLoginRecords();
  };

  if (loginRecordsClearBtn) loginRecordsClearBtn.onclick = function () {
    if (!window.confirm('清空所有登录记录？')) return;
    api('POST', '/api/login-records/clear', {}).then(function (res) {
      if (!res) return;
      if (res.ok) {
        renderLoginRecords([]);
        addEvent('warn', '登录记录已清空');
      } else {
        addEvent('error', '清空登录记录失败: ' + (res.error || 'unknown'));
      }
    });
  };

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
    pendingDeleteRecordingKey = '';
    if (recordingDeleteBtn) recordingDeleteBtn.textContent = '删除所选';
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
  if (productActionRefreshBtn) productActionRefreshBtn.onclick = loadProductActions;
  if (productActionSelect) productActionSelect.onchange = updateProductActionMeta;
  if (visionInspectBtn) visionInspectBtn.onclick = inspectVision;
  if (productActionRunBtn) productActionRunBtn.onclick = function () {
    var action = selectedProductAction();
    runProductAction(action && action.id);
  };
  if (productActionSaveBtn) productActionSaveBtn.onclick = saveProductAction;
  if (productActionAdminList) {
    productActionAdminList.onclick = function (event) {
      var target = event.target;
      if (!target) return;
      var fillId = target.getAttribute('data-product-fill');
      var testTemplate = target.getAttribute('data-product-test');
      var status = target.getAttribute('data-product-status');
      var id = target.getAttribute('data-product-id');
      if (fillId) {
        fillProductActionForm(productActionById(fillId));
      } else if (testTemplate) {
        runTemplate(testTemplate);
      } else if (status && id) {
        changeProductActionStatus(id, status);
      }
    };
  }
  if (teleopScanBtn) teleopScanBtn.onclick = scanLeaderArm;
  if (teleopCalibrateBtn) teleopCalibrateBtn.onclick = calibrateTeleop;
  if (followerGripperMinBtn) followerGripperMinBtn.onclick = calibrateFollowerGripperMin;
  if (followerGripperCloseTestBtn) followerGripperCloseTestBtn.onclick = testFollowerGripperClose;
  if (teleopHealthBtn) teleopHealthBtn.onclick = checkSavedCalibration;
  if (teleopStartBtn) teleopStartBtn.onclick = startTeleop;
  if (teleopPauseBtn) teleopPauseBtn.onclick = pauseTeleop;
  if (teleopResumeBtn) teleopResumeBtn.onclick = resumeTeleop;
  if (teleopStopBtn) teleopStopBtn.onclick = stopTeleop;

  var savePromptDialog = document.getElementById('savePromptDialog');
  var savePromptSaveBtn = document.getElementById('savePromptSaveBtn');
  var savePromptDiscardBtn = document.getElementById('savePromptDiscardBtn');
  var savePromptCancelBtn = document.getElementById('savePromptCancelBtn');
  if (savePromptSaveBtn) savePromptSaveBtn.onclick = commitSaveRecording;
  if (savePromptDiscardBtn) savePromptDiscardBtn.onclick = discardSaveRecording;
  if (savePromptCancelBtn) savePromptCancelBtn.onclick = cancelSaveRecording;
  if (savePromptDialog) {
    savePromptDialog.addEventListener('cancel', function (ev) {
      if (pendingSavePayload) {
        ev.preventDefault();
        cancelSaveRecording();
      }
    });
  }

  refreshRecordingsAndTemplates().then(function () {
    refreshStatus();
  });
  setLoginRole('admin');
  updateOperatorUi();
  setInterval(refreshStatus, 3000);
}());
