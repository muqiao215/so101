package com.so101.mes.controller;

import com.so101.mes.model.TaskStatus;
import com.so101.mes.service.RosbridgeClientService;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/ros")
public class RosbridgeController {
  private final RosbridgeClientService rosbridge;

  public RosbridgeController(RosbridgeClientService rosbridge) {
    this.rosbridge = rosbridge;
  }

  @GetMapping("/health")
  public Map<String, Object> health() {
    return Map.of("connected", rosbridge.isConnected());
  }

  @PostMapping("/connect")
  public Map<String, Object> connect() {
    rosbridge.connect();
    return Map.of("ok", true);
  }

  @PostMapping("/status")
  public Map<String, Object> ingestStatus(@RequestBody TaskStatus status) {
    rosbridge.ingestTaskStatus(status);
    return Map.of("ok", true);
  }

  @PostMapping("/detections")
  public Map<String, Object> ingestDetections(@RequestBody Map<String, Object> payload) {
    rosbridge.ingestDetectionPayload(payload);
    return Map.of("ok", true);
  }
}
