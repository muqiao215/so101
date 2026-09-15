package com.so101.mes.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.so101.mes.model.SystemStatus;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class SystemControlServiceStatusContractTest {
  @TempDir java.nio.file.Path tempDir;

  @Test
  void returns_protective_stop_when_estop_is_active() throws Exception {
    SystemControlService service =
        TestSystemControlFactory.withRuntimeFiles(
            tempDir,
            """
            {"online":true,"powerState":"已上电","estopActive":true,"allowExecute":true,"updatedAt":"2026-04-02T10:00:00+08:00"}
            """);

    SystemStatus status = service.getStatus();

    assertEquals("PROTECTIVE_STOP", status.realHardware().safetyState());
    assertFalse(status.realHardware().allowExecute());
    assertEquals("ESTOP_ACTIVE", status.realHardware().gateReasonCode());
  }

  private static final class TestSystemControlFactory {
    private static SystemControlService withRuntimeFiles(Path workspaceRoot, String statusJson)
        throws Exception {
      Path runtimeDir = workspaceRoot.resolve(".vscode/.runtime");
      Files.createDirectories(runtimeDir);
      Files.writeString(runtimeDir.resolve("real_hardware_status.json"), statusJson);
      Files.writeString(
          runtimeDir.resolve("real_hardware_command_gate.json"),
          """
          {
            "commandExecutionEnabled": true,
            "reasonCode": "READY_FOR_MIN_MOTION",
            "reason": "已人工放行",
            "source": "contract-test",
            "updatedAt": "2026-04-02T10:00:01+08:00"
          }
          """);
      Files.writeString(
          runtimeDir.resolve("real_hardware_calibration.json"),
          """
          {
            "schemaVersion": "1.0",
            "profileName": "so101-default",
            "calibrated": true,
            "homed": true,
            "updatedAt": "2026-04-02T10:00:02+08:00",
            "poses": {
              "home": { "joints": [0, 0, 0, 0, 0, 0] },
              "pick": { "joints": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6] },
              "place": { "joints": [0.6, 0.5, 0.4, 0.3, 0.2, 0.1] },
              "gripper_open": { "value": 0.0 },
              "gripper_close": { "value": 1.0 }
            }
          }
          """);

      RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);
      ProcessRunner runner = new FakeProcessRunner();
      return new SystemControlService(
          runner,
          rosbridge,
          new ObjectMapper(),
          workspaceRoot.toString(),
          "/opt/ros/humble/setup.bash",
          Clock.fixed(Instant.parse("2026-04-02T02:00:05Z"), ZoneOffset.UTC));
    }
  }

  private static final class FakeProcessRunner implements ProcessRunner {
    private final Map<String, Boolean> processes = new HashMap<>();

    @Override
    public long spawnBash(String command, Path workdir, Map<String, String> env, Path logFile) {
      throw new UnsupportedOperationException("not needed in status contract tests");
    }

    @Override
    public int runBash(String command, Path workdir) {
      return 0;
    }

    @Override
    public boolean hasProcess(String pattern) {
      return processes.getOrDefault(pattern, false);
    }

    @Override
    public boolean isPortListening(int port) {
      return false;
    }

    @Override
    public boolean isAlive(long pid) {
      return false;
    }

    @Override
    public void terminate(long pid) {}
  }
}
