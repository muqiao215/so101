package com.so101.mes.service.runtime;

import com.so101.mes.model.GateReasonCode;
import com.so101.mes.model.RealHardwareStatus;
import com.so101.mes.model.SafetyCheckItem;
import com.so101.mes.model.SystemStatus;
import com.so101.mes.service.ProcessRunner;
import com.so101.mes.service.RosbridgeClientService;
import com.so101.mes.service.realhardware.CalibrationAssessmentService;
import com.so101.mes.service.realhardware.RuntimeRealHardwareReader;
import com.so101.mes.service.realhardware.SafetyPolicyService;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public final class RuntimeStatusService {
  private final ProcessRunner runner;
  private final RosbridgeClientService rosbridge;
  private final Path workspaceRoot;
  private final Path runtimeDir;
  private final Path simPidFile;
  private final Path rvizPidFile;
  private final Path browserPidFile;
  private final Path simLogFile;
  private final Path rvizLogFile;
  private final Path browserLogFile;
  private final Path rosLogDir;
  private final String browserDebugUrl;
  private final Path realHardwareStatusFile;
  private final Path realHardwareCommandGateFile;
  private final Path realHardwareCalibrationFile;
  private final RuntimeTargetService runtimeTargetService;
  private final RuntimeRealHardwareReader realHardwareReader;
  private final CalibrationAssessmentService calibrationAssessmentService;
  private final SafetyPolicyService safetyPolicyService;

  public RuntimeStatusService(
      ProcessRunner runner,
      RosbridgeClientService rosbridge,
      Path workspaceRoot,
      RuntimeTargetService runtimeTargetService,
      RuntimeRealHardwareReader realHardwareReader,
      CalibrationAssessmentService calibrationAssessmentService,
      SafetyPolicyService safetyPolicyService) {
    this.runner = runner;
    this.rosbridge = rosbridge;
    this.workspaceRoot = workspaceRoot;
    this.runtimeDir = workspaceRoot.resolve(".vscode/.runtime");
    this.simPidFile = runtimeDir.resolve("gui_sim.pid");
    this.rvizPidFile = runtimeDir.resolve("gui_rviz.pid");
    this.browserPidFile = runtimeDir.resolve("gui_browser.pid");
    this.simLogFile = runtimeDir.resolve("gui_sim.log");
    this.rvizLogFile = runtimeDir.resolve("gui_rviz.log");
    this.browserLogFile = runtimeDir.resolve("gui_browser.log");
    this.rosLogDir = runtimeDir.resolve("ros_logs_gui_api");
    this.browserDebugUrl = "http://127.0.0.1:9223";
    this.realHardwareStatusFile = runtimeDir.resolve("real_hardware_status.json");
    this.realHardwareCommandGateFile = runtimeDir.resolve("real_hardware_command_gate.json");
    this.realHardwareCalibrationFile = runtimeDir.resolve("real_hardware_calibration.json");
    this.runtimeTargetService = runtimeTargetService;
    this.realHardwareReader = realHardwareReader;
    this.calibrationAssessmentService = calibrationAssessmentService;
    this.safetyPolicyService = safetyPolicyService;
  }

  public SystemStatus getStatus() {
    RuntimeProcessSnapshot runtime = getRuntimeSnapshot();
    return new SystemStatus(
        runtimeTargetService.getRuntimeTarget(),
        runtime.simRunning(),
        runtime.gazeboRunning(),
        runtime.rvizRunning(),
        rosbridge.isConnected(),
        runtime.browserRunning(),
        runtime.simPid(),
        runtime.rvizPid(),
        runtime.browserPid(),
        runtime.simLog(),
        runtime.rvizLog(),
        runtime.browserLog(),
        runtime.browserDebugUrl(),
        readRealHardwareStatus());
  }

  RuntimeProcessSnapshot getRuntimeSnapshot() {
    Long simPid = readLivePid(simPidFile);
    Long rvizPid = readLivePid(rvizPidFile);
    Long browserPid = readLivePid(browserPidFile);
    boolean realHardwareRuntimeRunning = isRealHardwareRuntimeRunning();
    boolean simRunning = simPid != null || isSimulationRunning() || realHardwareRuntimeRunning;
    boolean gazeboRunning =
        (!isRealHardwareTarget() && simPid != null)
            || isSimulationRunning()
            || runner.hasProcess("gzserver");
    boolean rvizRunning = rvizPid != null || runner.hasProcess("rviz2 -d");
    boolean browserRunning = browserPid != null || runner.isPortListening(9223);
    return new RuntimeProcessSnapshot(
        simRunning,
        gazeboRunning,
        rvizRunning,
        browserRunning,
        simPid,
        rvizPid,
        browserPid,
        simLogFile.toString(),
        rvizLogFile.toString(),
        browserLogFile.toString(),
        browserDebugUrl);
  }

  Path workspaceRoot() {
    return workspaceRoot;
  }

  Path rosLogDir() {
    return rosLogDir;
  }

  Path simPidFile() {
    return simPidFile;
  }

  Path rvizPidFile() {
    return rvizPidFile;
  }

  Path browserPidFile() {
    return browserPidFile;
  }

  Path simLogFile() {
    return simLogFile;
  }

  Path rvizLogFile() {
    return rvizLogFile;
  }

  Path browserLogFile() {
    return browserLogFile;
  }

  void ensureRuntimeDir() throws IOException {
    Files.createDirectories(runtimeDir);
  }

  void ensureRosLogDir() throws IOException {
    Files.createDirectories(rosLogDir);
  }

  Long readLivePid(Path pidFile) {
    try {
      if (!Files.exists(pidFile)) {
        return null;
      }
      long pid = Long.parseLong(Files.readString(pidFile).trim());
      if (!runner.isAlive(pid)) {
        Files.deleteIfExists(pidFile);
        return null;
      }
      return pid;
    } catch (Exception e) {
      try {
        Files.deleteIfExists(pidFile);
      } catch (IOException ignored) {
      }
      return null;
    }
  }

  boolean isSimulationRunning() {
    return runner.hasProcess("sim_bringup.launch.py") || runner.hasProcess("gzserver");
  }

  boolean isRealHardwareRuntimeRunning() {
    return runner.hasProcess("real_bringup.launch.py")
        || runner.hasProcess("so101_follower_trajectory_adapter.py");
  }

  boolean isTargetRuntimeRunning() {
    return isRealHardwareTarget() ? isRealHardwareRuntimeRunning() : isSimulationRunning();
  }

  boolean isRealHardwareTarget() {
    return "real_hardware".equals(runtimeTargetService.getRuntimeTarget());
  }

  void writePid(Path pidFile, long pid) throws IOException {
    Files.createDirectories(pidFile.getParent());
    Files.writeString(pidFile, pid + System.lineSeparator());
  }

  void waitForPortState(int port, boolean expected, int attempts, long sleepMillis) {
    for (int i = 0; i < attempts; i++) {
      if (runner.isPortListening(port) == expected) {
        return;
      }
      try {
        Thread.sleep(sleepMillis);
      } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        return;
      }
    }
  }

  private RealHardwareStatus readRealHardwareStatus() {
    RuntimeRealHardwareReader.RuntimeReadResult readResult =
        realHardwareReader.read(
            realHardwareStatusFile, realHardwareCommandGateFile, realHardwareCalibrationFile);
    if (readResult.statusMissing()) {
      return RealHardwareStatus.safeDefault();
    }
    if (readResult.statusInvalid()) {
      return invalidRealHardwareStatus();
    }

    RuntimeRealHardwareReader.RuntimeRealHardwareSnapshot payload = readResult.snapshot();
    CalibrationAssessmentService.CalibrationAssessment calibrationAssessment =
        calibrationAssessmentService.assess(readResult.calibration());
    SafetyPolicyService.SafetyAssessment safety =
        safetyPolicyService.assess(payload, calibrationAssessment, readResult.gate());
    return new RealHardwareStatus(
        payload.online(),
        normalizeText(payload.controlInterface(), payload.online() ? "已接入" : "待接入"),
        normalizeText(payload.powerState(), "未上电"),
        payload.estopActive(),
        normalizeText(payload.mode(), safety.allowExecute() ? "最小动作验证" : "安全待机"),
        normalizeText(payload.lastError(), "无"),
        safety.allowExecute(),
        normalizeText(payload.updatedAt(), ""),
        safety.safetyState(),
        safety.gateReasonCode().name(),
        safety.gateReasonLabel(),
        calibrationAssessment.calibrationState(),
        calibrationAssessment.homed(),
        safety.checks());
  }

  private RealHardwareStatus invalidRealHardwareStatus() {
    return new RealHardwareStatus(
        false,
        "状态文件异常",
        "未上电",
        false,
        "安全待机",
        "真机状态文件解析失败",
        false,
        "",
        "PROTECTIVE_STOP",
        GateReasonCode.STATUS_FILE_INVALID.name(),
        "真机状态文件解析失败",
        "UNCALIBRATED",
        false,
        List.of(
            new SafetyCheckItem("driver_online", "驱动在线", false, "状态文件异常"),
            new SafetyCheckItem("status_fresh", "状态新鲜", false, "状态文件异常"),
            new SafetyCheckItem("power_on", "已上电", false, "当前未上电"),
            new SafetyCheckItem("estop_clear", "急停正常", true, "急停未触发"),
            new SafetyCheckItem("calibrated", "已完成校准", false, "尚未完成校准"),
            new SafetyCheckItem("homed", "已安全回中", false, "尚未完成安全回中"),
            new SafetyCheckItem("gate_enabled", "系统已放行", false, "状态文件异常")));
  }

  private String normalizeText(String value, String fallback) {
    if (value == null || value.isBlank()) {
      return fallback;
    }
    return value.trim();
  }
}
