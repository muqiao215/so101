package com.so101.mes.model;

public enum TaskStatusCode {
  STARTED,
  STEP,
  DETECTION_TRIGGER,
  OK,
  BUSY,
  BAD_REQUEST,
  DETECTION_MISMATCH,
  EXECUTION_ERROR,
  UNKNOWN;

  public static TaskStatusCode from(String raw) {
    if (raw == null || raw.isBlank()) {
      return UNKNOWN;
    }
    try {
      return TaskStatusCode.valueOf(raw.trim().toUpperCase());
    } catch (IllegalArgumentException ignored) {
      return UNKNOWN;
    }
  }
}
