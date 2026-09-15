package com.so101.mes.service.realhardware;

import com.so101.mes.model.GateReasonCode;
import com.so101.mes.model.SafetyCheckItem;
import java.time.Clock;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;

public final class SafetyPolicyService {
  private final Clock clock;
  private final Duration statusTimeout;

  public SafetyPolicyService(Clock clock, Duration statusTimeout) {
    this.clock = clock;
    this.statusTimeout = statusTimeout;
  }

  public SafetyAssessment assess(
      RuntimeRealHardwareReader.RuntimeRealHardwareSnapshot payload,
      CalibrationAssessmentService.CalibrationAssessment calibration,
      RuntimeRealHardwareReader.CommandGateSnapshot gate) {
    boolean online = payload.online();
    boolean estopActive = payload.estopActive();
    boolean powered = "已上电".equals(payload.powerState());
    boolean stale = isStatusStale(payload.updatedAt());
    boolean commandGateEnabled = gate != null && gate.commandExecutionEnabled();

    GateReasonCode gateReasonCode;
    String gateReasonLabel;
    String safetyState;
    if (estopActive) {
      gateReasonCode = GateReasonCode.ESTOP_ACTIVE;
      gateReasonLabel = "急停触发，保持保护态";
      safetyState = "PROTECTIVE_STOP";
    } else if (!online) {
      gateReasonCode = GateReasonCode.WAITING_FOR_HARDWARE;
      gateReasonLabel = "真机尚未接入";
      safetyState = "LOCKED";
    } else if (stale) {
      gateReasonCode = GateReasonCode.STATUS_TIMEOUT;
      gateReasonLabel = "状态超时，保持保护态";
      safetyState = "PROTECTIVE_STOP";
    } else if (!powered) {
      gateReasonCode = GateReasonCode.NOT_POWERED;
      gateReasonLabel = "真机已接入，但尚未上电";
      safetyState = "LOCKED";
    } else if ("UNCALIBRATED".equals(calibration.calibrationState())) {
      gateReasonCode = GateReasonCode.UNCALIBRATED;
      gateReasonLabel = "尚未完成真机校准";
      safetyState = "LOCKED";
    } else if ("INVALID".equals(calibration.calibrationState())) {
      gateReasonCode = GateReasonCode.CALIBRATION_INVALID;
      gateReasonLabel = "校准配置无效，保持保护态";
      safetyState = "PROTECTIVE_STOP";
    } else if (!calibration.homed()) {
      gateReasonCode = GateReasonCode.NOT_HOMED;
      gateReasonLabel = "尚未完成安全回中";
      safetyState = "LOCKED";
    } else if (!commandGateEnabled) {
      gateReasonCode = gate.reasonCode();
      gateReasonLabel = normalizeText(gate.reason(), "默认保护态，需人工确认后放行");
      safetyState = "LOCKED";
    } else {
      gateReasonCode = GateReasonCode.READY_FOR_MIN_MOTION;
      gateReasonLabel = "已满足最小动作验证前提";
      safetyState = "READY";
    }

    boolean allowExecute =
        "READY".equals(safetyState)
            && payload.allowExecute()
            && commandGateEnabled
            && online
            && !estopActive;
    return new SafetyAssessment(
        allowExecute,
        safetyState,
        gateReasonCode,
        gateReasonLabel,
        defaultChecks(
            online,
            !stale,
            powered,
            !estopActive,
            calibration.valid(),
            calibration.homed(),
            commandGateEnabled,
            gateReasonLabel));
  }

  private boolean isStatusStale(String updatedAt) {
    if (updatedAt == null || updatedAt.isBlank()) {
      return true;
    }

    OffsetDateTime ts = parseOffsetDateTime(updatedAt.trim());
    if (ts == null) {
      return true;
    }
    Duration age = Duration.between(ts.toInstant(), clock.instant());
    return age.compareTo(statusTimeout) > 0;
  }

  private OffsetDateTime parseOffsetDateTime(String text) {
    try {
      return OffsetDateTime.parse(text, DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss Z"));
    } catch (DateTimeParseException ignored) {
    }
    try {
      return OffsetDateTime.parse(text);
    } catch (DateTimeParseException ignored) {
    }
    return null;
  }

  private List<SafetyCheckItem> defaultChecks(
      boolean online,
      boolean fresh,
      boolean powered,
      boolean estopClear,
      boolean calibrated,
      boolean homed,
      boolean gateEnabled,
      String gateDetail) {
    List<SafetyCheckItem> checks = new ArrayList<>();
    checks.add(new SafetyCheckItem("driver_online", "驱动在线", online, online ? "真机状态源已接入" : "等待真机目录接入"));
    checks.add(new SafetyCheckItem("status_fresh", "状态新鲜", fresh, fresh ? "最近状态仍在有效窗口内" : "状态超时或未刷新"));
    checks.add(new SafetyCheckItem("power_on", "已上电", powered, powered ? "当前已上电" : "当前未上电"));
    checks.add(new SafetyCheckItem("estop_clear", "急停正常", estopClear, estopClear ? "急停未触发" : "急停已触发"));
    checks.add(new SafetyCheckItem("calibrated", "已完成校准", calibrated, calibrated ? "关键姿态配置已就绪" : "尚未完成校准"));
    checks.add(new SafetyCheckItem("homed", "已安全回中", homed, homed ? "当前已完成安全回中" : "尚未完成安全回中"));
    checks.add(new SafetyCheckItem("gate_enabled", "系统已放行", gateEnabled, gateDetail));
    return List.copyOf(checks);
  }

  private String normalizeText(String value, String fallback) {
    if (value == null || value.isBlank()) {
      return fallback;
    }
    return value.trim();
  }

  public record SafetyAssessment(
      boolean allowExecute,
      String safetyState,
      GateReasonCode gateReasonCode,
      String gateReasonLabel,
      List<SafetyCheckItem> checks) {}
}
