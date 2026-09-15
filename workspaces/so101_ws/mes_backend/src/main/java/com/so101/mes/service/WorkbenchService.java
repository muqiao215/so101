package com.so101.mes.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.so101.mes.model.TaskCommand;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Stream;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.yaml.snakeyaml.DumperOptions;
import org.yaml.snakeyaml.Yaml;

@Service
public class WorkbenchService {
  private static final DateTimeFormatter TS = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss");
  private static final String LATEST_VISION_EPISODE_ID = "gzv011_status_heartbeat_smoke_20260427_010757";

  private final RosbridgeClientService rosbridge;
  private final Path workspaceRoot;
  private final ObjectMapper objectMapper = new ObjectMapper();

  public WorkbenchService(
      RosbridgeClientService rosbridge,
      @Value("${so101.workspace-root:/home/muqiao/dev/ros2/workspaces/so101_ws}") String workspaceRoot) {
    this.rosbridge = rosbridge;
    this.workspaceRoot = Path.of(workspaceRoot);
  }

  public Map<String, Object> previewPose(WorkbenchPreviewRequest request) {
    validatePreviewRequest(request);
    String requestId = "preview-" + UUID.randomUUID();
    Map<String, Object> previewPose =
        new LinkedHashMap<>(
            Map.of(
                "name", request.name(),
                "durationSec", request.durationSec(),
                "positions", request.positions()));
    rosbridge.publishTask(
        new TaskCommand(
            requestId,
            "preview",
            "preview_pose",
            Map.of("previewPose", previewPose)));
    return Map.of("ok", true, "requestId", requestId, "message", "preview pose published");
  }

  public Map<String, Object> saveExport(WorkbenchSaveRequest request) throws IOException {
    String stem = sanitizeStem(request.fileStem());
    String content = request.content() == null ? "" : request.content().trim();
    if (content.isBlank()) {
      throw new IllegalArgumentException("content must not be blank");
    }
    Path dir = workspaceRoot.resolve("docs/generated/fixed-action-workbench");
    Files.createDirectories(dir);
    Path path = dir.resolve(TS.format(LocalDateTime.now()) + "-" + stem + ".yaml");
    Files.writeString(path, content + System.lineSeparator());
    return Map.of("ok", true, "path", path.toString(), "bytes", Files.size(path));
  }

  public Map<String, Object> mergeIntoWaypoints(WorkbenchMergeRequest request) throws IOException {
    validateMergeRequest(request);
    Path waypointsPath = workspaceRoot.resolve("src/so101_bringup/config/waypoints.yaml");
    if (!Files.exists(waypointsPath)) {
      throw new IllegalArgumentException("waypoints.yaml not found");
    }

    Path backupDir = workspaceRoot.resolve("docs/generated/fixed-action-workbench/backups");
    Files.createDirectories(backupDir);
    Path backupPath = backupDir.resolve(TS.format(LocalDateTime.now()) + "-waypoints.yaml");
    Files.copy(waypointsPath, backupPath, StandardCopyOption.REPLACE_EXISTING);

    Yaml yaml = createYaml();
    Map<String, Object> doc =
        yaml.load(Files.readString(waypointsPath));
    if (doc == null) {
      doc = new LinkedHashMap<>();
    }

    Map<String, Object> waypoints = ensureMap(doc, "waypoints");
    for (WorkbenchPose pose : request.poses()) {
      waypoints.put(pose.name(), new ArrayList<>(pose.positions()));
    }

    Map<String, Object> templates = ensureMap(doc, "action_templates");
    Map<String, Object> template = new LinkedHashMap<>();
    template.put("detection_required", false);
    List<String> sequence = request.poses().stream().map(WorkbenchPose::name).toList();
    template.put("sequence", sequence);
    templates.put(request.templateName(), template);

    Files.writeString(waypointsPath, yaml.dump(doc));

    return Map.of(
        "ok", true,
        "path", waypointsPath.toString(),
        "backupPath", backupPath.toString(),
        "templateName", request.templateName(),
        "poseCount", request.poses().size());
  }

  public Map<String, Object> latestVisionQuality() throws IOException {
    Path episodeRoot =
        findLatestVisionEpisodeRoot()
            .orElse(workspaceRoot.resolve("docs/generated/vision-episodes").resolve(LATEST_VISION_EPISODE_ID));
    Path datasetRoot = episodeRoot.resolve("dataset");
    Path yoloSmokeReport =
        findLatestYoloSmokeReport()
            .orElse(workspaceRoot.resolve("docs/generated/yolo-smoke/gzv011-train-infer/yolo-smoke-report.json"));
    Map<String, Object> response = new LinkedHashMap<>();
    response.put("ok", true);
    response.put("episodeId", episodeRoot.getFileName().toString());
    response.put("episodeRoot", episodeRoot.toString());
    response.put("datasetIndex", readJsonIfExists(datasetRoot.resolve("dataset-index.json")));
    response.put("candidateManifest", readJsonIfExists(datasetRoot.resolve("lerobot-candidate-exec-actions/manifest.json")));
    response.put("nativeLeRobot", readJsonIfExists(datasetRoot.resolve("lerobot-native-exec-actions-uvrun/native-export-report.json")));
    response.put("yoloSmoke", readJsonIfExists(yoloSmokeReport));
    response.put(
        "paths",
        Map.of(
            "datasetIndex", datasetRoot.resolve("dataset-index.json").toString(),
            "candidateManifest", datasetRoot.resolve("lerobot-candidate-exec-actions/manifest.json").toString(),
            "nativeLeRobot", datasetRoot.resolve("lerobot-native-exec-actions-uvrun/native-export-report.json").toString(),
            "yoloSmoke", yoloSmokeReport.toString()));
    response.put(
        "available",
        Map.of(
            "datasetIndex", Files.exists(datasetRoot.resolve("dataset-index.json")),
            "candidateManifest", Files.exists(datasetRoot.resolve("lerobot-candidate-exec-actions/manifest.json")),
            "nativeLeRobot", Files.exists(datasetRoot.resolve("lerobot-native-exec-actions-uvrun/native-export-report.json")),
            "yoloSmoke", Files.exists(yoloSmokeReport)));
    return response;
  }

  private Optional<Path> findLatestVisionEpisodeRoot() throws IOException {
    Path root = workspaceRoot.resolve("docs/generated/vision-episodes");
    if (!Files.isDirectory(root)) {
      return Optional.empty();
    }
    try (Stream<Path> entries = Files.list(root)) {
      return entries
          .filter(Files::isDirectory)
          .filter(path -> Files.exists(path.resolve("dataset/dataset-index.json")))
          .max(Comparator.comparing(path -> path.toFile().lastModified()));
    }
  }

  private Optional<Path> findLatestYoloSmokeReport() throws IOException {
    Path root = workspaceRoot.resolve("docs/generated/yolo-smoke");
    if (!Files.isDirectory(root)) {
      return Optional.empty();
    }
    try (Stream<Path> entries = Files.list(root)) {
      return entries
          .map(path -> path.resolve("yolo-smoke-report.json"))
          .filter(Files::exists)
          .max(Comparator.comparing(path -> path.toFile().lastModified()));
    }
  }

  private Map<String, Object> readJsonIfExists(Path path) throws IOException {
    if (!Files.exists(path)) {
      return Map.of();
    }
    return objectMapper.readValue(Files.readString(path), new TypeReference<>() {});
  }

  private void validatePreviewRequest(WorkbenchPreviewRequest request) {
    if (request == null) {
      throw new IllegalArgumentException("request is required");
    }
    if (request.positions() == null || request.positions().size() != 6) {
      throw new IllegalArgumentException("positions must contain exactly 6 values");
    }
    if (request.durationSec() == null || request.durationSec() <= 0) {
      throw new IllegalArgumentException("durationSec must be > 0");
    }
  }

  private void validateMergeRequest(WorkbenchMergeRequest request) {
    if (request == null || request.poses() == null || request.poses().isEmpty()) {
      throw new IllegalArgumentException("poses must not be empty");
    }
    if (request.templateName() == null || request.templateName().isBlank()) {
      throw new IllegalArgumentException("templateName must not be blank");
    }
    for (WorkbenchPose pose : request.poses()) {
      if (pose.name() == null || pose.name().isBlank()) {
        throw new IllegalArgumentException("pose name must not be blank");
      }
      if (pose.positions() == null || pose.positions().size() != 6) {
        throw new IllegalArgumentException("each pose must contain exactly 6 positions");
      }
    }
  }

  @SuppressWarnings("unchecked")
  private Map<String, Object> ensureMap(Map<String, Object> doc, String key) {
    Object raw = doc.get(key);
    if (raw instanceof Map<?, ?> map) {
      return (Map<String, Object>) map;
    }
    Map<String, Object> created = new LinkedHashMap<>();
    doc.put(key, created);
    return created;
  }

  private Yaml createYaml() {
    DumperOptions options = new DumperOptions();
    options.setDefaultFlowStyle(DumperOptions.FlowStyle.BLOCK);
    options.setPrettyFlow(true);
    options.setIndent(2);
    return new Yaml(options);
  }

  private String sanitizeStem(String fileStem) {
    String raw = fileStem == null ? "workbench-export" : fileStem.trim();
    String sanitized = raw.replaceAll("[^a-zA-Z0-9._-]+", "-").replaceAll("-{2,}", "-");
    sanitized = sanitized.replaceAll("^-+", "").replaceAll("-+$", "");
    return sanitized.isBlank() ? "workbench-export" : sanitized;
  }

  public record WorkbenchPreviewRequest(String name, Double durationSec, List<Double> positions) {}

  public record WorkbenchSaveRequest(String fileStem, String content) {}

  public record WorkbenchPose(String name, Integer durationMs, List<Double> positions) {}

  public record WorkbenchMergeRequest(String templateName, List<WorkbenchPose> poses) {}
}
