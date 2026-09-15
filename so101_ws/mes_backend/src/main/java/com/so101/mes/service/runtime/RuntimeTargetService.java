package com.so101.mes.service.runtime;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

public final class RuntimeTargetService {
  public static final String SIMULATION = "simulation";
  public static final String REAL_HARDWARE = "real_hardware";
  public static final String REAL_LEADER_TO_GAZEBO = "real_leader_to_gazebo";

  private final ObjectMapper objectMapper;
  private final Path runtimeTargetFile;

  public RuntimeTargetService(ObjectMapper objectMapper, Path runtimeTargetFile) {
    this.objectMapper = objectMapper;
    this.runtimeTargetFile = runtimeTargetFile;
  }

  public String getRuntimeTarget() {
    try {
      if (!Files.exists(runtimeTargetFile)) {
        return SIMULATION;
      }
      JsonNode root = objectMapper.readTree(runtimeTargetFile.toFile());
      return sanitizeRuntimeTarget(root.path("runtimeTarget").asText(null));
    } catch (Exception ignored) {
      return SIMULATION;
    }
  }

  public String setRuntimeTarget(String runtimeTarget) throws IOException {
    String normalized = requireRuntimeTarget(runtimeTarget);
    Files.createDirectories(runtimeTargetFile.getParent());
    objectMapper
        .writerWithDefaultPrettyPrinter()
        .writeValue(runtimeTargetFile.toFile(), Map.of("runtimeTarget", normalized));
    return normalized;
  }

  public String requireRuntimeTarget(String runtimeTarget) {
    String normalized = normalizeRuntimeTarget(runtimeTarget);
    if (SIMULATION.equals(normalized)
        || REAL_HARDWARE.equals(normalized)
        || REAL_LEADER_TO_GAZEBO.equals(normalized)) {
      return normalized;
    }
    throw new IllegalArgumentException(
        "runtimeTarget must be one of: simulation, real_hardware, real_leader_to_gazebo");
  }

  private String sanitizeRuntimeTarget(String runtimeTarget) {
    String normalized = normalizeRuntimeTarget(runtimeTarget);
    if (SIMULATION.equals(normalized)
        || REAL_HARDWARE.equals(normalized)
        || REAL_LEADER_TO_GAZEBO.equals(normalized)) {
      return normalized;
    }
    return SIMULATION;
  }

  private String normalizeRuntimeTarget(String runtimeTarget) {
    if (runtimeTarget == null) {
      return SIMULATION;
    }
    String normalized = runtimeTarget.trim().toLowerCase();
    if (normalized.isEmpty()) {
      return SIMULATION;
    }
    return normalized;
  }
}
