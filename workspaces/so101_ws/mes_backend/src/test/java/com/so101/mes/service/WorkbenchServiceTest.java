package com.so101.mes.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.so101.mes.model.TaskCommand;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.ArgumentCaptor;
import org.springframework.messaging.simp.SimpMessagingTemplate;

class WorkbenchServiceTest {
  @TempDir Path tempDir;

  @Test
  void shouldPublishPreviewPoseAsTaskCommand() throws Exception {
    var ws = org.mockito.Mockito.mock(SimpMessagingTemplate.class);
    var orders = new OrderService();
    var rosbridge = new RosbridgeClientService(new ObjectMapper(), ws, orders);
    var service = new WorkbenchService(rosbridge, tempDir.toString());

    Map<String, Object> result =
        service.previewPose(
            new WorkbenchService.WorkbenchPreviewRequest(
                "debug_pose_1",
                1.2,
                List.of(0.0, -0.2, 0.4, -0.2, 0.0, 0.2)));

    assertThat(result.get("ok")).isEqualTo(true);
    assertThat(result.get("requestId")).isNotNull();

    String payload =
        rosbridge.buildPublishStringMessage(
            "/mes_task_cmd",
            new TaskCommand(
                result.get("requestId").toString(),
                "preview",
                "preview_pose",
                Map.of(
                    "previewPose",
                    Map.of(
                        "name", "debug_pose_1",
                        "durationSec", 1.2,
                        "positions", List.of(0.0, -0.2, 0.4, -0.2, 0.0, 0.2)))));

    assertThat(payload).contains("\\\"actionTemplateId\\\":\\\"preview_pose\\\"");
    assertThat(payload).contains("\\\"previewPose\\\"");
  }

  @Test
  void shouldPersistWorkbenchExportUnderDocsGenerated() throws Exception {
    var ws = org.mockito.Mockito.mock(SimpMessagingTemplate.class);
    var orders = new OrderService();
    var rosbridge = new RosbridgeClientService(new ObjectMapper(), ws, orders);
    var service = new WorkbenchService(rosbridge, tempDir.toString());

    Map<String, Object> result =
        service.saveExport(
            new WorkbenchService.WorkbenchSaveRequest(
                "wave_debug",
                "waypoints:\n  wave_debug:\n  - 0.0\n"));

    Path saved = Path.of(result.get("path").toString());
    assertThat(saved).exists();
    assertThat(saved).isRegularFile();
    assertThat(saved.getFileName().toString()).matches(".*wave_debug.*\\.yaml");
    assertThat(Files.readString(saved)).contains("wave_debug");
  }

  @Test
  void shouldMergePosesIntoWaypointsYamlWithBackup() throws Exception {
    Path root = tempDir.resolve("ws");
    Path configDir = root.resolve("src/so101_bringup/config");
    Files.createDirectories(configDir);
    Path waypoints = configDir.resolve("waypoints.yaml");
    Files.writeString(
        waypoints,
        """
        joint_names:
        - shoulder_pan
        - shoulder_lift
        - elbow_flex
        - wrist_flex
        - wrist_roll
        - gripper
        waypoints:
          home:
          - 0.0
          - -0.2
          - 0.4
          - -0.2
          - 0.0
          - 0.2
        action_templates:
          pick_place_default:
            detection_required: false
            sequence:
            - home
        """);

    var ws = org.mockito.Mockito.mock(SimpMessagingTemplate.class);
    var orders = new OrderService();
    var rosbridge = new RosbridgeClientService(new ObjectMapper(), ws, orders);
    var service = new WorkbenchService(rosbridge, root.toString());

    Map<String, Object> result =
        service.mergeIntoWaypoints(
            new WorkbenchService.WorkbenchMergeRequest(
                "debug_sequence",
                List.of(
                    new WorkbenchService.WorkbenchPose(
                        "debug_pose_1",
                        1200,
                        List.of(0.0, -0.2, 0.4, -0.2, 0.0, 0.2)))));

    assertThat(result.get("ok")).isEqualTo(true);
    assertThat(result.get("backupPath")).isNotNull();
    String merged = Files.readString(waypoints);
    assertThat(merged).contains("debug_pose_1");
    assertThat(merged).contains("debug_sequence:");
  }

  @Test
  void shouldReadLatestVisionQualityArtifacts() throws Exception {
    Path root = tempDir.resolve("ws");
    Path dataset =
        root.resolve(
            "docs/generated/vision-episodes/gzv011_status_heartbeat_smoke_20260427_010757/dataset");
    Files.createDirectories(dataset.resolve("lerobot-candidate-exec-actions"));
    Files.createDirectories(dataset.resolve("lerobot-native-exec-actions-uvrun"));
    Files.createDirectories(root.resolve("docs/generated/yolo-smoke/gzv011-train-infer"));
    Files.writeString(
        dataset.resolve("dataset-index.json"),
        """
        {"source_episode_id":"gzv011_status_heartbeat_smoke_20260427_010757","sample_count":9}
        """);
    Files.writeString(
        dataset.resolve("lerobot-candidate-exec-actions/manifest.json"),
        """
        {"schema":"so101_lerobot_candidate_exec_actions_v1","train_sample_count":8,"rejected_sample_count":1}
        """);
    Files.writeString(
        dataset.resolve("lerobot-native-exec-actions-uvrun/native-export-report.json"),
        """
        {"status":"done","sample_count":8,"features":{"action":{"shape":[6]}}}
        """);
    Files.writeString(
        root.resolve("docs/generated/yolo-smoke/gzv011-train-infer/yolo-smoke-report.json"),
        """
        {"status":"done","weights":{"best":"/tmp/best.pt"},"predict":{"result_count":1}}
        """);

    var ws = org.mockito.Mockito.mock(SimpMessagingTemplate.class);
    var orders = new OrderService();
    var rosbridge = new RosbridgeClientService(new ObjectMapper(), ws, orders);
    var service = new WorkbenchService(rosbridge, root.toString());

    Map<String, Object> result = service.latestVisionQuality();

    assertThat(result.get("ok")).isEqualTo(true);
    assertThat(result.get("episodeId")).isEqualTo("gzv011_status_heartbeat_smoke_20260427_010757");
    assertThat(((Map<?, ?>) result.get("candidateManifest")).get("train_sample_count")).isEqualTo(8);
    assertThat(((Map<?, ?>) result.get("nativeLeRobot")).get("status")).isEqualTo("done");
    assertThat(((Map<?, ?>) result.get("yoloSmoke")).get("status")).isEqualTo("done");
  }
}
