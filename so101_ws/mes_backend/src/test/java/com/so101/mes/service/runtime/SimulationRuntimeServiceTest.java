package com.so101.mes.service.runtime;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.so101.mes.service.ProcessRunner;
import com.so101.mes.service.RosbridgeClientService;
import com.so101.mes.service.realhardware.CalibrationAssessmentService;
import com.so101.mes.service.realhardware.RuntimeRealHardwareReader;
import com.so101.mes.service.realhardware.SafetyPolicyService;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class SimulationRuntimeServiceTest {
  @TempDir Path tempDir;

  @Test
  void start_simulation_is_idempotent_when_pid_or_process_exists() throws Exception {
    ProcessRunner runner = org.mockito.Mockito.mock(ProcessRunner.class);
    RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);
    when(runner.hasProcess("gzserver")).thenReturn(true);

    RuntimeStatusService runtimeStatusService =
        new RuntimeStatusService(
            runner,
            rosbridge,
            tempDir,
            new RuntimeTargetService(new ObjectMapper(), tempDir.resolve(".vscode/.runtime/runtime_target.json")),
            new RuntimeRealHardwareReader(new ObjectMapper()),
            new CalibrationAssessmentService(),
            new SafetyPolicyService(
                Clock.fixed(Instant.parse("2026-04-02T02:00:05Z"), ZoneOffset.UTC),
                Duration.ofSeconds(15)));
    SimulationRuntimeService simulationRuntimeService =
        new SimulationRuntimeService(runner, runtimeStatusService, "/opt/ros/humble/setup.bash");

    RuntimeProcessSnapshot status = simulationRuntimeService.startSimulation();

    verify(runner, never()).spawnBash(any(), any(), anyMap(), any());
    assertThat(status.simRunning()).isTrue();
    assertThat(status.gazeboRunning()).isTrue();
  }
}
