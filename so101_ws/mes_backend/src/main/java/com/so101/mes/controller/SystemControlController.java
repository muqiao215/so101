package com.so101.mes.controller;

import com.so101.mes.model.RuntimeTargetUpdateRequest;
import com.so101.mes.model.SystemStatus;
import com.so101.mes.service.SystemControlService;
import java.io.IOException;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/system")
public class SystemControlController {
  private final SystemControlService systemControlService;

  public SystemControlController(SystemControlService systemControlService) {
    this.systemControlService = systemControlService;
  }

  @GetMapping("/status")
  public SystemStatus status() {
    return systemControlService.getStatus();
  }

  @PostMapping("/start-sim")
  public Map<String, Object> startSimulation() throws IOException {
    return Map.of("ok", true, "status", systemControlService.startSimulation());
  }

  @PostMapping("/open-rviz")
  public Map<String, Object> openRviz() throws IOException {
    return Map.of("ok", true, "status", systemControlService.openRviz());
  }

  @PostMapping("/open-browser")
  public Map<String, Object> openBrowser() throws IOException {
    return Map.of("ok", true, "status", systemControlService.openBrowser());
  }

  @PostMapping("/runtime-target")
  public Map<String, Object> updateRuntimeTarget(@RequestBody RuntimeTargetUpdateRequest request)
      throws IOException {
    try {
      return Map.of("ok", true, "status", systemControlService.setRuntimeTarget(request.runtimeTarget()));
    } catch (IllegalArgumentException error) {
      throw new ResponseStatusException(HttpStatus.BAD_REQUEST, error.getMessage(), error);
    }
  }

  @PostMapping("/stop-sim")
  public Map<String, Object> stopSimulation() throws IOException, InterruptedException {
    return Map.of("ok", true, "status", systemControlService.stopSimulation());
  }

  @PostMapping("/stop-browser")
  public Map<String, Object> stopBrowser() throws IOException, InterruptedException {
    return Map.of("ok", true, "status", systemControlService.stopBrowser());
  }
}
