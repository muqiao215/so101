package com.so101.mes.model;

public enum GateReasonCode {
  ESTOP_ACTIVE,
  WAITING_FOR_HARDWARE,
  STATUS_TIMEOUT,
  NOT_POWERED,
  UNCALIBRATED,
  CALIBRATION_INVALID,
  NOT_HOMED,
  MANUAL_LOCK,
  READY_FOR_MIN_MOTION,
  STATUS_FILE_INVALID,
  GATE_FILE_INVALID,
  HWS_002_PENDING,
  CAL_002_PENDING;

  public static GateReasonCode fromRuntime(
      String explicitReasonCode, String fallbackReason, boolean commandGateEnabled) {
    if (explicitReasonCode != null && !explicitReasonCode.isBlank()) {
      try {
        return GateReasonCode.valueOf(explicitReasonCode.trim());
      } catch (IllegalArgumentException ignored) {
      }
    }

    String reason = fallbackReason == null ? "" : fallbackReason.trim();
    if (reason.contains("HWS-002")) {
      return HWS_002_PENDING;
    }
    if (reason.contains("CAL-002") || reason.contains("校准")) {
      return CAL_002_PENDING;
    }
    return commandGateEnabled ? READY_FOR_MIN_MOTION : MANUAL_LOCK;
  }
}
