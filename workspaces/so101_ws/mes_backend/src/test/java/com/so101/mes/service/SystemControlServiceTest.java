package com.so101.mes.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.so101.mes.model.RealHardwareStatus;
import com.so101.mes.model.SystemStatus;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class SystemControlServiceTest {
  @TempDir Path tempDir;

  @Test
  void shouldStartSimWritePidAndExposeStatus() throws Exception {
    FakeProcessRunner runner = new FakeProcessRunner();
    runner.nextPid = 4321L;
    RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);
    org.mockito.Mockito.when(rosbridge.isConnected()).thenReturn(true);

    SystemControlService service =
        new SystemControlService(
            runner, rosbridge, new ObjectMapper(), tempDir.toString(), "/opt/ros/humble/setup.bash");

    SystemStatus status = service.startSimulation();

    assertThat(status.runtimeTarget()).isEqualTo("simulation");
    assertThat(status.simRunning()).isTrue();
    assertThat(status.gazeboRunning()).isTrue();
    assertThat(status.browserRunning()).isFalse();
    assertThat(status.simPid()).isEqualTo(4321L);
    assertThat(status.realHardware()).isEqualTo(RealHardwareStatus.safeDefault());
    assertThat(Files.readString(tempDir.resolve(".vscode/.runtime/gui_sim.pid")).trim()).isEqualTo("4321");
    assertThat(runner.lastSpawnCommand).contains("ros2 launch so101_bringup sim_bringup.launch.py");
    assertThat(runner.lastSpawnCommand).contains("source '/usr/share/gazebo/setup.bash'");
    assertThat(runner.lastSpawnCommand).contains("use_gzclient:=true");
    assertThat(runner.lastSpawnCommand).contains("use_gazebo_color_detector:=true");
    assertThat(runner.lastSpawnCommand).contains("use_real_yolo:=false");
    assertThat(runner.lastSpawnCommand).contains("use_vision_target_projection:=true");
    assertThat(runner.lastEnv).containsKey("ROS_LOG_DIR");
  }

  @Test
  void shouldPersistExplicitRuntimeTarget() throws Exception {
    FakeProcessRunner runner = new FakeProcessRunner();
    RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);

    SystemControlService service =
        new SystemControlService(
            runner, rosbridge, new ObjectMapper(), tempDir.toString(), "/opt/ros/humble/setup.bash");

    SystemStatus status = service.setRuntimeTarget("real_hardware");

    assertThat(status.runtimeTarget()).isEqualTo("real_hardware");
    assertThat(Files.readString(tempDir.resolve(".vscode/.runtime/runtime_target.json")))
        .contains("\"runtimeTarget\" : \"real_hardware\"");
  }

  @Test
  void shouldPersistRealLeaderToGazeboRuntimeTarget() throws Exception {
    FakeProcessRunner runner = new FakeProcessRunner();
    RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);

    SystemControlService service =
        new SystemControlService(
            runner, rosbridge, new ObjectMapper(), tempDir.toString(), "/opt/ros/humble/setup.bash");

    SystemStatus status = service.setRuntimeTarget("real_leader_to_gazebo");

    assertThat(status.runtimeTarget()).isEqualTo("real_leader_to_gazebo");
    assertThat(Files.readString(tempDir.resolve(".vscode/.runtime/runtime_target.json")))
        .contains("\"runtimeTarget\" : \"real_leader_to_gazebo\"");
  }

  @Test
  void shouldStartRealHardwareRuntimeWhenTargetIsRealHardware() throws Exception {
    FakeProcessRunner runner = new FakeProcessRunner();
    runner.nextPid = 2468L;
    RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);

    SystemControlService service =
        new SystemControlService(
            runner, rosbridge, new ObjectMapper(), tempDir.toString(), "/opt/ros/humble/setup.bash");

    service.setRuntimeTarget("real_hardware");
    SystemStatus status = service.startSimulation();

    assertThat(status.runtimeTarget()).isEqualTo("real_hardware");
    assertThat(status.simRunning()).isTrue();
    assertThat(status.gazeboRunning()).isFalse();
    assertThat(status.simPid()).isEqualTo(2468L);
    assertThat(runner.lastSpawnCommand).contains("ros2 launch so101_bringup real_bringup.launch.py");
    assertThat(runner.lastSpawnCommand).contains("enable_follower_adapter:=true");
    assertThat(runner.lastSpawnCommand).contains("follower_port:='/dev/ttyACM0'");
    assertThat(runner.lastSpawnCommand).contains("follower_dry_run:='true'");
    assertThat(runner.lastSpawnCommand).doesNotContain("sim_bringup.launch.py");
    assertThat(runner.lastSpawnCommand).doesNotContain("gzclient");
  }

  @Test
  void shouldOpenRvizWritePidAndExposeStatus() throws Exception {
    FakeProcessRunner runner = new FakeProcessRunner();
    runner.nextPid = 999L;
    RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);

    SystemControlService service =
        new SystemControlService(
            runner, rosbridge, new ObjectMapper(), tempDir.toString(), "/opt/ros/humble/setup.bash");

    SystemStatus status = service.openRviz();

    assertThat(status.rvizRunning()).isTrue();
    assertThat(status.browserRunning()).isFalse();
    assertThat(status.rvizPid()).isEqualTo(999L);
    assertThat(Files.readString(tempDir.resolve(".vscode/.runtime/gui_rviz.pid")).trim()).isEqualTo("999");
    assertThat(runner.lastSpawnCommand).contains("rviz2 -d");
  }

  @Test
  void shouldStopSimulationAndRvizAndClearPidFiles() throws Exception {
    FakeProcessRunner runner = new FakeProcessRunner();
    runner.alive.put(111L, true);
    runner.alive.put(222L, true);
    RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);

    Path runtimeDir = tempDir.resolve(".vscode/.runtime");
    Files.createDirectories(runtimeDir);
    Files.writeString(runtimeDir.resolve("gui_sim.pid"), "111\n");
    Files.writeString(runtimeDir.resolve("gui_rviz.pid"), "222\n");

    SystemControlService service =
        new SystemControlService(
            runner, rosbridge, new ObjectMapper(), tempDir.toString(), "/opt/ros/humble/setup.bash");

    SystemStatus status = service.stopSimulation();

    assertThat(status.simRunning()).isFalse();
    assertThat(status.rvizRunning()).isFalse();
    assertThat(status.browserRunning()).isFalse();
    assertThat(Files.exists(runtimeDir.resolve("gui_sim.pid"))).isFalse();
    assertThat(Files.exists(runtimeDir.resolve("gui_rviz.pid"))).isFalse();
    assertThat(runner.terminatedPids).containsExactlyInAnyOrder(111L, 222L);
    assertThat(runner.lastRunCommand).contains("pkill -f 'rviz2 -d'");
    assertThat(runner.lastRunCommand).contains("pkill -f gzclient");
  }

  @Test
  void shouldReportExternallyStartedSimulationAndRviz() {
    FakeProcessRunner runner = new FakeProcessRunner();
    runner.processes.put("sim_bringup.launch.py", true);
    runner.processes.put("gzserver", true);
    runner.processes.put("rviz2 -d", true);
    RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);

    SystemControlService service =
        new SystemControlService(
            runner, rosbridge, new ObjectMapper(), tempDir.toString(), "/opt/ros/humble/setup.bash");

    SystemStatus status = service.getStatus();

    assertThat(status.simRunning()).isTrue();
    assertThat(status.gazeboRunning()).isTrue();
    assertThat(status.rvizRunning()).isTrue();
    assertThat(status.browserRunning()).isFalse();
    assertThat(status.simPid()).isNull();
    assertThat(status.rvizPid()).isNull();
  }

  @Test
  void shouldNotSpawnSecondSimulationWhenExternalOneAlreadyRunning() throws Exception {
    FakeProcessRunner runner = new FakeProcessRunner();
    runner.processes.put("sim_bringup.launch.py", true);
    runner.processes.put("gzserver", true);
    RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);

    SystemControlService service =
        new SystemControlService(
            runner, rosbridge, new ObjectMapper(), tempDir.toString(), "/opt/ros/humble/setup.bash");

    SystemStatus status = service.startSimulation();

    assertThat(status.simRunning()).isTrue();
    assertThat(runner.lastSpawnCommand).isEmpty();
  }

  @Test
  void shouldOpenCleanBrowserAndExposeCdpUrl() throws Exception {
    FakeProcessRunner runner = new FakeProcessRunner();
    runner.nextPid = 3333L;
    RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);

    SystemControlService service =
        new SystemControlService(
            runner, rosbridge, new ObjectMapper(), tempDir.toString(), "/opt/ros/humble/setup.bash");

    SystemStatus status = service.openBrowser();

    assertThat(status.browserRunning()).isTrue();
    assertThat(status.browserPid()).isEqualTo(3333L);
    assertThat(status.browserDebugUrl()).isEqualTo("http://127.0.0.1:9223");
    assertThat(status.browserLog()).contains("gui_browser.log");
    assertThat(Files.readString(tempDir.resolve(".vscode/.runtime/gui_browser.pid")).trim()).isEqualTo("3333");
    assertThat(runner.lastSpawnCommand).contains("start_clean_cdp_browser.sh");
  }

  @Test
  void shouldStopCleanBrowser() throws Exception {
    FakeProcessRunner runner = new FakeProcessRunner();
    runner.alive.put(3333L, true);
    RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);

    Path runtimeDir = tempDir.resolve(".vscode/.runtime");
    Files.createDirectories(runtimeDir);
    Files.writeString(runtimeDir.resolve("gui_browser.pid"), "3333\n");

    SystemControlService service =
        new SystemControlService(
            runner, rosbridge, new ObjectMapper(), tempDir.toString(), "/opt/ros/humble/setup.bash");

    SystemStatus status = service.stopBrowser();

    assertThat(status.browserRunning()).isFalse();
    assertThat(Files.exists(runtimeDir.resolve("gui_browser.pid"))).isFalse();
    assertThat(runner.terminatedPids).contains(3333L);
    assertThat(runner.lastRunCommand).contains("stop_clean_cdp_browser.sh");
  }

  @Test
  void shouldReadRealHardwareStatusFileWhenPresent() throws Exception {
    FakeProcessRunner runner = new FakeProcessRunner();
    RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);

    Path runtimeDir = tempDir.resolve(".vscode/.runtime");
    Files.createDirectories(runtimeDir);
    Files.writeString(
        runtimeDir.resolve("real_hardware_status.json"),
        """
        {
          "online": true,
          "controlInterface": "ros2_control /dev/ttyACM0",
          "powerState": "已上电",
          "estopActive": false,
          "mode": "手动低速",
          "lastError": "",
          "allowExecute": true,
          "updatedAt": "2026-03-25 20:10:00 +0000"
        }
        """);
    Files.writeString(
        runtimeDir.resolve("real_hardware_command_gate.json"),
        """
        {
          "commandExecutionEnabled": true,
          "reasonCode": "READY_FOR_MIN_MOTION",
          "reason": "已人工放行",
          "source": "test",
          "updatedAt": "2026-03-25 20:10:01 +0000"
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
          "updatedAt": "2026-03-25 20:10:02",
          "poses": {
            "home": { "joints": [0, 0, 0, 0, 0, 0] },
            "pick": { "joints": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6] },
            "place": { "joints": [0.6, 0.5, 0.4, 0.3, 0.2, 0.1] },
            "gripper_open": { "value": 0.0 },
            "gripper_close": { "value": 1.0 }
          }
        }
        """);

    SystemControlService service =
        new SystemControlService(
            runner,
            rosbridge,
            new ObjectMapper(),
            tempDir.toString(),
            "/opt/ros/humble/setup.bash",
            Clock.fixed(Instant.parse("2026-03-25T20:10:05Z"), ZoneOffset.UTC));

    SystemStatus status = service.getStatus();

    assertThat(status.realHardware().online()).isTrue();
    assertThat(status.realHardware().controlInterface()).isEqualTo("ros2_control /dev/ttyACM0");
    assertThat(status.realHardware().powerState()).isEqualTo("已上电");
    assertThat(status.realHardware().mode()).isEqualTo("手动低速");
    assertThat(status.realHardware().allowExecute()).isTrue();
    assertThat(status.realHardware().calibrationState()).isEqualTo("READY");
    assertThat(status.realHardware().homed()).isTrue();
    assertThat(status.realHardware().safetyState()).isEqualTo("READY");
    assertThat(status.realHardware().gateReasonCode()).isEqualTo("READY_FOR_MIN_MOTION");
  }

  @Test
  void shouldForceSafeLockWhenCommandGateIsDisabled() throws Exception {
    FakeProcessRunner runner = new FakeProcessRunner();
    RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);

    Path runtimeDir = tempDir.resolve(".vscode/.runtime");
    Files.createDirectories(runtimeDir);
    Files.writeString(
        runtimeDir.resolve("real_hardware_status.json"),
        """
        {
          "online": true,
          "controlInterface": "adapter bridge",
          "powerState": "已上电",
          "estopActive": false,
          "mode": "最小动作验证",
          "lastError": "",
          "allowExecute": true,
          "updatedAt": "2026-03-25 20:12:00 +0000"
        }
        """);
    Files.writeString(
        runtimeDir.resolve("real_hardware_command_gate.json"),
        """
        {
          "commandExecutionEnabled": false,
          "reasonCode": "HWS_002_PENDING",
          "reason": "HWS-002 未通过",
          "source": "contract-test",
          "updatedAt": "2026-03-25 20:12:01 +0000"
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
          "updatedAt": "2026-03-25 20:12:02",
          "poses": {
            "home": { "joints": [0, 0, 0, 0, 0, 0] },
            "pick": { "joints": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6] },
            "place": { "joints": [0.6, 0.5, 0.4, 0.3, 0.2, 0.1] },
            "gripper_open": { "value": 0.0 },
            "gripper_close": { "value": 1.0 }
          }
        }
        """);

    SystemControlService service =
        new SystemControlService(
            runner,
            rosbridge,
            new ObjectMapper(),
            tempDir.toString(),
            "/opt/ros/humble/setup.bash",
            Clock.fixed(Instant.parse("2026-03-25T20:12:05Z"), ZoneOffset.UTC));

    SystemStatus status = service.getStatus();

    assertThat(status.realHardware().online()).isTrue();
    assertThat(status.realHardware().allowExecute()).isFalse();
    assertThat(status.realHardware().mode()).isEqualTo("最小动作验证");
    assertThat(status.realHardware().safetyState()).isEqualTo("LOCKED");
    assertThat(status.realHardware().gateReasonCode()).isEqualTo("HWS_002_PENDING");
  }

  @Test
  void shouldForceSafeLockWhenCalibrationIsMissing() throws Exception {
    FakeProcessRunner runner = new FakeProcessRunner();
    RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);

    Path runtimeDir = tempDir.resolve(".vscode/.runtime");
    Files.createDirectories(runtimeDir);
    Files.writeString(
        runtimeDir.resolve("real_hardware_status.json"),
        """
        {
          "online": true,
          "controlInterface": "adapter bridge",
          "powerState": "已上电",
          "estopActive": false,
          "mode": "保护待机",
          "lastError": "",
          "allowExecute": true,
          "updatedAt": "2026-03-25 20:15:00 +0000"
        }
        """);
    Files.writeString(
        runtimeDir.resolve("real_hardware_command_gate.json"),
        """
        {
          "commandExecutionEnabled": true,
          "reasonCode": "READY_FOR_MIN_MOTION",
          "reason": "已人工放行",
          "source": "contract-test",
          "updatedAt": "2026-03-25 20:15:01 +0000"
        }
        """);

    SystemControlService service =
        new SystemControlService(
            runner,
            rosbridge,
            new ObjectMapper(),
            tempDir.toString(),
            "/opt/ros/humble/setup.bash",
            Clock.fixed(Instant.parse("2026-03-25T20:15:05Z"), ZoneOffset.UTC));

    SystemStatus status = service.getStatus();

    assertThat(status.realHardware().allowExecute()).isFalse();
    assertThat(status.realHardware().calibrationState()).isEqualTo("UNCALIBRATED");
    assertThat(status.realHardware().gateReasonCode()).isEqualTo("UNCALIBRATED");
    assertThat(status.realHardware().safetyState()).isEqualTo("LOCKED");
  }

  @Test
  void shouldForceProtectiveStopWhenStatusIsStale() throws Exception {
    FakeProcessRunner runner = new FakeProcessRunner();
    RosbridgeClientService rosbridge = org.mockito.Mockito.mock(RosbridgeClientService.class);

    Path runtimeDir = tempDir.resolve(".vscode/.runtime");
    Files.createDirectories(runtimeDir);
    Files.writeString(
        runtimeDir.resolve("real_hardware_status.json"),
        """
        {
          "online": true,
          "controlInterface": "adapter bridge",
          "powerState": "已上电",
          "estopActive": false,
          "mode": "保护待机",
          "lastError": "",
          "allowExecute": true,
          "updatedAt": "2026-03-25 20:15:00 +0000"
        }
        """);
    Files.writeString(
        runtimeDir.resolve("real_hardware_command_gate.json"),
        """
        {
          "commandExecutionEnabled": true,
          "reasonCode": "READY_FOR_MIN_MOTION",
          "reason": "已人工放行",
          "source": "contract-test",
          "updatedAt": "2026-03-25 20:15:01 +0000"
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
          "updatedAt": "2026-03-25 20:15:02 +0000",
          "poses": {
            "home": { "joints": [0, 0, 0, 0, 0, 0] },
            "pick": { "joints": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6] },
            "place": { "joints": [0.6, 0.5, 0.4, 0.3, 0.2, 0.1] },
            "gripper_open": { "value": 0.0 },
            "gripper_close": { "value": 1.0 }
          }
        }
        """);

    SystemControlService service =
        new SystemControlService(
            runner,
            rosbridge,
            new ObjectMapper(),
            tempDir.toString(),
            "/opt/ros/humble/setup.bash",
            Clock.fixed(Instant.parse("2026-03-25T20:16:00Z"), ZoneOffset.UTC));

    SystemStatus status = service.getStatus();

    assertThat(status.realHardware().allowExecute()).isFalse();
    assertThat(status.realHardware().gateReasonCode()).isEqualTo("STATUS_TIMEOUT");
    assertThat(status.realHardware().safetyState()).isEqualTo("PROTECTIVE_STOP");
  }

  private static final class FakeProcessRunner implements ProcessRunner {
    long nextPid = 1L;
    String lastSpawnCommand = "";
    String lastRunCommand = "";
    Map<String, String> lastEnv = Map.of();
    Map<Long, Boolean> alive = new HashMap<>();
    Map<String, Boolean> processes = new HashMap<>();
    Map<Integer, Boolean> listeningPorts = new HashMap<>();
    java.util.List<Long> terminatedPids = new java.util.ArrayList<>();

    @Override
    public long spawnBash(String command, Path workdir, Map<String, String> env, Path logFile) {
      lastSpawnCommand = command;
      lastEnv = Map.copyOf(env);
      alive.put(nextPid, true);
      return nextPid;
    }

    @Override
    public int runBash(String command, Path workdir) {
      lastRunCommand = command;
      return 0;
    }

    @Override
    public boolean hasProcess(String pattern) {
      return processes.getOrDefault(pattern, false);
    }

    @Override
    public boolean isPortListening(int port) {
      return listeningPorts.getOrDefault(port, false);
    }

    @Override
    public boolean isAlive(long pid) {
      return alive.getOrDefault(pid, false);
    }

    @Override
    public void terminate(long pid) {
      terminatedPids.add(pid);
      alive.put(pid, false);
    }
  }
}
