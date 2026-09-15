package com.so101.mes.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.so101.mes.service.WorkbenchService;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(WorkbenchController.class)
class WorkbenchControllerTest {
  @Autowired private MockMvc mockMvc;

  @MockBean private WorkbenchService workbenchService;

  @Test
  void shouldPreviewPose() throws Exception {
    when(workbenchService.previewPose(any()))
        .thenReturn(Map.of("ok", true, "requestId", "preview-001", "message", "preview pose published"));

    mockMvc
        .perform(
            post("/api/workbench/preview")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {
                      "name":"debug_pose_1",
                      "durationSec":1.2,
                      "positions":[0.0,-0.2,0.4,-0.2,0.0,0.2]
                    }
                    """))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true))
        .andExpect(jsonPath("$.requestId").value("preview-001"));
  }

  @Test
  void shouldSaveWorkbenchExport() throws Exception {
    when(workbenchService.saveExport(any()))
        .thenReturn(
            Map.of(
                "ok", true,
                "path", Path.of("/tmp/workbench/export.yaml").toString(),
                "bytes", 42));

    mockMvc
        .perform(
            post("/api/workbench/save")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {
                      "fileStem":"wave_debug",
                      "content":"waypoints:\\n  wave_debug:\\n  - 0.0"
                    }
                    """))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true))
        .andExpect(jsonPath("$.path").value("/tmp/workbench/export.yaml"))
        .andExpect(jsonPath("$.bytes").value(42));
  }

  @Test
  void shouldMergeWorkbenchIntoWaypointsYaml() throws Exception {
    when(workbenchService.mergeIntoWaypoints(any()))
        .thenReturn(
            Map.of(
                "ok", true,
                "path", "/tmp/workbench/waypoints.yaml",
                "backupPath", "/tmp/workbench/backup.yaml",
                "templateName", "debug_sequence"));

    mockMvc
        .perform(
            post("/api/workbench/merge-waypoints")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {
                      "templateName":"debug_sequence",
                      "poses":[
                        {"name":"debug_pose_1","durationMs":1200,"positions":[0.0,-0.2,0.4,-0.2,0.0,0.2]}
                      ]
                    }
                    """))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true))
        .andExpect(jsonPath("$.templateName").value("debug_sequence"))
        .andExpect(jsonPath("$.backupPath").value("/tmp/workbench/backup.yaml"));
  }

  @Test
  void shouldReturnLatestVisionQuality() throws Exception {
    when(workbenchService.latestVisionQuality())
        .thenReturn(
            Map.of(
                "ok", true,
                "episodeId", "gzv011_status_heartbeat_smoke_20260427_010757",
                "yoloSmoke", Map.of("status", "done")));

    mockMvc
        .perform(get("/api/workbench/vision/latest-quality"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true))
        .andExpect(jsonPath("$.episodeId").value("gzv011_status_heartbeat_smoke_20260427_010757"))
        .andExpect(jsonPath("$.yoloSmoke.status").value("done"));
  }
}
