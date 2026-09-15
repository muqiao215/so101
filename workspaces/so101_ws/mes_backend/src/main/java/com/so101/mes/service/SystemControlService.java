package com.so101.mes.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.so101.mes.model.SystemStatus;
import com.so101.mes.service.realhardware.CalibrationAssessmentService;
import com.so101.mes.service.realhardware.RuntimeRealHardwareReader;
import com.so101.mes.service.realhardware.SafetyPolicyService;
import com.so101.mes.service.runtime.BrowserRuntimeService;
import com.so101.mes.service.runtime.RuntimeStatusService;
import com.so101.mes.service.runtime.RuntimeTargetService;
import com.so101.mes.service.runtime.SimulationRuntimeService;
import java.io.IOException;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class SystemControlService {
  private final RuntimeStatusService runtimeStatusService;
  private final SimulationRuntimeService simulationRuntimeService;
  private final BrowserRuntimeService browserRuntimeService;
  private final RuntimeTargetService runtimeTargetService;

  @Autowired
  public SystemControlService(
      ProcessRunner runner,
      RosbridgeClientService rosbridge,
      ObjectMapper objectMapper,
      @Value("${so101.workspace-root:/home/muqiao/dev/ros2/workspaces/so101_ws}") String workspaceRoot,
      @Value("${so101.ros-setup:/opt/ros/humble/setup.bash}") String rosSetup) {
    this(runner, rosbridge, objectMapper, workspaceRoot, rosSetup, Clock.systemDefaultZone());
  }

  SystemControlService(
      ProcessRunner runner,
      RosbridgeClientService rosbridge,
      ObjectMapper objectMapper,
      String workspaceRoot,
      String rosSetup,
      Clock clock) {
    RuntimeTargetService runtimeTargetService =
        new RuntimeTargetService(
            objectMapper, Path.of(workspaceRoot).resolve(".vscode/.runtime/runtime_target.json"));
    RuntimeStatusService runtimeStatusService =
        new RuntimeStatusService(
            runner,
            rosbridge,
            Path.of(workspaceRoot),
            runtimeTargetService,
            new RuntimeRealHardwareReader(objectMapper),
            new CalibrationAssessmentService(),
            new SafetyPolicyService(clock, Duration.ofSeconds(15)));
    this.runtimeTargetService = runtimeTargetService;
    this.runtimeStatusService = runtimeStatusService;
    this.simulationRuntimeService =
        new SimulationRuntimeService(runner, runtimeStatusService, rosSetup);
    this.browserRuntimeService = new BrowserRuntimeService(runner, runtimeStatusService);
  }

  public SystemStatus getStatus() {
    return runtimeStatusService.getStatus();
  }

  public SystemStatus setRuntimeTarget(String runtimeTarget) throws IOException {
    runtimeTargetService.setRuntimeTarget(runtimeTarget);
    return runtimeStatusService.getStatus();
  }

  public SystemStatus startSimulation() throws IOException {
    simulationRuntimeService.startSimulation();
    return runtimeStatusService.getStatus();
  }

  public SystemStatus openRviz() throws IOException {
    simulationRuntimeService.openRviz();
    return runtimeStatusService.getStatus();
  }

  public SystemStatus openBrowser() throws IOException {
    browserRuntimeService.openBrowser();
    return runtimeStatusService.getStatus();
  }

  public SystemStatus stopSimulation() throws IOException, InterruptedException {
    simulationRuntimeService.stopSimulation();
    return runtimeStatusService.getStatus();
  }

  public SystemStatus stopBrowser() throws IOException, InterruptedException {
    browserRuntimeService.stopBrowser();
    return runtimeStatusService.getStatus();
  }
}
