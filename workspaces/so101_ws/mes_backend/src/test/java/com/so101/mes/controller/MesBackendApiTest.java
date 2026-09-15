package com.so101.mes.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest(properties = "rosbridge.url=ws://127.0.0.1:1")
@AutoConfigureMockMvc
class MesBackendApiTest {
  @Autowired private MockMvc mockMvc;
  @Autowired private ObjectMapper objectMapper;

  @Test
  void orderShouldStayPendingAfterDispatchUntilRosStatusArrives() throws Exception {
    String orderId = "order-" + UUID.randomUUID();

    mockMvc
        .perform(
            post("/api/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {"orderId":"%s","actionTemplateId":"pick_place_red"}
                    """
                        .formatted(orderId)))
        .andExpect(status().isCreated())
        .andExpect(jsonPath("$.state").value("PENDING"));

    mockMvc
        .perform(
            post("/api/orders/%s/dispatch".formatted(orderId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("{}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true))
        .andExpect(jsonPath("$.requestId").exists());

    mockMvc
        .perform(get("/api/orders/%s".formatted(orderId)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.state").value("PENDING"))
        .andExpect(jsonPath("$.lastStatusCode").value("DISPATCHED"));
  }

  @Test
  void rosStatusApiShouldDriveOrderStateMachine() throws Exception {
    String orderId = "order-" + UUID.randomUUID();

    mockMvc
        .perform(
            post("/api/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {"orderId":"%s","actionTemplateId":"pick_place_blue"}
                    """
                        .formatted(orderId)))
        .andExpect(status().isCreated());

    mockMvc
        .perform(
            post("/api/orders/%s/dispatch".formatted(orderId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("{}"))
        .andExpect(status().isOk());

    String requestId =
        objectMapper.readValue(
                mockMvc
            .perform(get("/api/orders/%s".formatted(orderId)))
            .andExpect(status().isOk())
            .andReturn()
            .getResponse()
            .getContentAsString(),
                java.util.Map.class)
            .get("lastRequestId")
            .toString();

    mockMvc
        .perform(
            post("/api/ros/status")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {"requestId":"%s","state":"执行中","code":"STARTED","message":"template=pick_place_blue","ts":1}
                    """
                        .formatted(requestId)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true));

    mockMvc
        .perform(get("/api/orders/%s".formatted(orderId)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.state").value("RUNNING"))
        .andExpect(jsonPath("$.lastStatusCode").value("STARTED"));

    mockMvc
        .perform(
            post("/api/ros/status")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {"requestId":"%s","state":"完成","code":"OK","message":"Task completed","ts":2}
                    """
                        .formatted(requestId)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true));

    mockMvc
        .perform(get("/api/orders/%s".formatted(orderId)))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.state").value("DONE"))
        .andExpect(jsonPath("$.message").value("Task completed"))
        .andExpect(jsonPath("$.lastRequestId").value(requestId))
        .andExpect(jsonPath("$.lastStatusCode").value("OK"));
  }

  @Test
  void rosDetectionsApiShouldAcceptDemoPayload() throws Exception {
    mockMvc
        .perform(
            post("/api/ros/detections")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {"count":1,"detections":[{"category":"red","confidence":0.95}]}
                    """))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true));
  }

  @Test
  void workbenchPreviewApiShouldAcceptPosePayload() throws Exception {
    mockMvc
        .perform(
            post("/api/workbench/preview")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {"name":"debug_pose_1","durationSec":1.2,"positions":[0.0,-0.2,0.4,-0.2,0.0,0.2]}
                    """))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true))
        .andExpect(jsonPath("$.requestId").exists());
  }

  @Test
  void workbenchSaveApiShouldPersistExportSnippet() throws Exception {
    mockMvc
        .perform(
            post("/api/workbench/save")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    """
                    {"fileStem":"debug-sequence","content":"waypoints:\\n  demo:\\n  - 0.0\\n"}
                    """))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true))
        .andExpect(jsonPath("$.path").exists())
        .andExpect(jsonPath("$.bytes").isNumber());
  }
}
