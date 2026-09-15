package com.so101.mes.service.realhardware;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.so101.mes.model.GateReasonCode;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

public final class RuntimeRealHardwareReader {
  private final ObjectMapper objectMapper;

  public RuntimeRealHardwareReader(ObjectMapper objectMapper) {
    this.objectMapper = objectMapper;
  }

  public RuntimeReadResult read(
      Path realHardwareStatusFile, Path realHardwareCommandGateFile, Path realHardwareCalibrationFile) {
    if (!Files.exists(realHardwareStatusFile)) {
      return new RuntimeReadResult(true, false, null, defaultGate(), emptyCalibration());
    }

    try {
      RuntimeStatusFilePayload payload =
          objectMapper.readValue(realHardwareStatusFile.toFile(), RuntimeStatusFilePayload.class);
      return new RuntimeReadResult(
          false,
          false,
          new RuntimeRealHardwareSnapshot(
              Boolean.TRUE.equals(payload.online()),
              normalizeText(payload.controlInterface(), ""),
              normalizeText(payload.powerState(), "未上电"),
              Boolean.TRUE.equals(payload.estopActive()),
              normalizeText(payload.mode(), ""),
              normalizeText(payload.lastError(), ""),
              Boolean.TRUE.equals(payload.allowExecute()),
              normalizeText(payload.updatedAt(), "")),
          readGate(realHardwareCommandGateFile),
          readCalibration(realHardwareCalibrationFile));
    } catch (Exception e) {
      return new RuntimeReadResult(false, true, null, defaultGate(), emptyCalibration());
    }
  }

  private CommandGateSnapshot readGate(Path realHardwareCommandGateFile) {
    if (!Files.exists(realHardwareCommandGateFile)) {
      return defaultGate();
    }

    try {
      RuntimeCommandGatePayload payload =
          objectMapper.readValue(realHardwareCommandGateFile.toFile(), RuntimeCommandGatePayload.class);
      boolean enabled = Boolean.TRUE.equals(payload.commandExecutionEnabled());
      return new CommandGateSnapshot(
          enabled,
          GateReasonCode.fromRuntime(payload.reasonCode(), payload.reason(), enabled),
          normalizeText(payload.reason(), "默认保护态，需人工确认后放行"));
    } catch (Exception e) {
      return new CommandGateSnapshot(false, GateReasonCode.GATE_FILE_INVALID, "命令门控文件解析失败");
    }
  }

  private CalibrationFileSnapshot readCalibration(Path realHardwareCalibrationFile) {
    if (!Files.exists(realHardwareCalibrationFile)) {
      return emptyCalibration();
    }

    try {
      RuntimeCalibrationPayload payload =
          objectMapper.readValue(realHardwareCalibrationFile.toFile(), RuntimeCalibrationPayload.class);
      return new CalibrationFileSnapshot(
          Boolean.TRUE.equals(payload.calibrated()),
          Boolean.TRUE.equals(payload.homed()),
          payload.poses());
    } catch (Exception e) {
      return emptyCalibration();
    }
  }

  private CommandGateSnapshot defaultGate() {
    return new CommandGateSnapshot(false, GateReasonCode.MANUAL_LOCK, "默认保护态，需人工确认后放行");
  }

  private CalibrationFileSnapshot emptyCalibration() {
    return new CalibrationFileSnapshot(false, false, null);
  }

  private String normalizeText(String value, String fallback) {
    if (value == null || value.isBlank()) {
      return fallback;
    }
    return value.trim();
  }

  private record RuntimeStatusFilePayload(
      Boolean online,
      String controlInterface,
      String powerState,
      Boolean estopActive,
      String mode,
      String lastError,
      Boolean allowExecute,
      String updatedAt) {}

  private record RuntimeCommandGatePayload(
      Boolean commandExecutionEnabled,
      String reasonCode,
      String reason,
      String source,
      String updatedAt) {}

  private record RuntimeCalibrationPayload(
      String schemaVersion,
      Boolean calibrated,
      Boolean homed,
      String profileName,
      String updatedAt,
      Map<String, CalibrationPoseSnapshot> poses) {}

  public record RuntimeReadResult(
      boolean statusMissing,
      boolean statusInvalid,
      RuntimeRealHardwareSnapshot snapshot,
      CommandGateSnapshot gate,
      CalibrationFileSnapshot calibration) {}

  public record RuntimeRealHardwareSnapshot(
      boolean online,
      String controlInterface,
      String powerState,
      boolean estopActive,
      String mode,
      String lastError,
      boolean allowExecute,
      String updatedAt) {}

  public record CommandGateSnapshot(
      boolean commandExecutionEnabled, GateReasonCode reasonCode, String reason) {}

  public record CalibrationFileSnapshot(
      boolean calibrated, boolean homed, Map<String, CalibrationPoseSnapshot> poses) {}

  public record CalibrationPoseSnapshot(List<Double> joints, Double value) {}
}
