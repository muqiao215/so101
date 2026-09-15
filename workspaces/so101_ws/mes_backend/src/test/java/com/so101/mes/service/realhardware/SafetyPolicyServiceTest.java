package com.so101.mes.service.realhardware;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

import com.so101.mes.model.GateReasonCode;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;

class SafetyPolicyServiceTest {
  private final SafetyPolicyService policy =
      new SafetyPolicyService(
          Clock.fixed(Instant.parse("2026-04-02T02:00:05Z"), ZoneOffset.UTC),
          java.time.Duration.ofSeconds(15));

  @Test
  void uncalibrated_and_not_homed_forces_locked_state() {
    var payload =
        new RuntimeRealHardwareReader.RuntimeRealHardwareSnapshot(
            true,
            "已接入",
            "已上电",
            false,
            "保护待机",
            "无",
            true,
            "2026-04-02T10:00:00+08:00");
    var calibration = CalibrationAssessmentService.CalibrationAssessment.uncalibrated();
    var gate =
        new RuntimeRealHardwareReader.CommandGateSnapshot(
            false, GateReasonCode.CAL_002_PENDING, "未校准禁止执行");

    var result = policy.assess(payload, calibration, gate);

    assertEquals("LOCKED", result.safetyState());
    assertFalse(result.allowExecute());
    assertEquals(GateReasonCode.UNCALIBRATED, result.gateReasonCode());
  }
}
