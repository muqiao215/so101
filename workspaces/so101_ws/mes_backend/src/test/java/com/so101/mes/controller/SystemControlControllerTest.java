package com.so101.mes.controller;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.so101.mes.model.RealHardwareStatus;
import com.so101.mes.model.SystemStatus;
import com.so101.mes.service.SystemControlService;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(SystemControlController.class)
class SystemControlControllerTest {
  @Autowired private MockMvc mockMvc;

  @MockBean private SystemControlService systemControlService;

  @Test
  void shouldExposeSystemStatus() throws Exception {
    when(systemControlService.getStatus())
        .thenReturn(
            new SystemStatus(
                "simulation",
                true,
                true,
                true,
                true,
                true,
                123L,
                456L,
                789L,
                "/tmp/sim.log",
                "/tmp/rviz.log",
                "/tmp/browser.log",
                "http://127.0.0.1:9223",
                new RealHardwareStatus(
                    true,
                    "ros2_control",
                    "已上电",
                    false,
                    "安全待机",
                    "无",
                    false,
                    "2026-03-25 20:00:00",
                    "LOCKED",
                    "HWS_002_PENDING",
                    "安全基线未完成，继续锁执行",
                    "READY",
                    true,
                    List.of())));

    mockMvc
        .perform(get("/api/system/status"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.runtimeTarget").value("simulation"))
        .andExpect(jsonPath("$.simRunning").value(true))
        .andExpect(jsonPath("$.gazeboRunning").value(true))
        .andExpect(jsonPath("$.rvizRunning").value(true))
        .andExpect(jsonPath("$.browserRunning").value(true))
        .andExpect(jsonPath("$.rosbridgeConnected").value(true))
        .andExpect(jsonPath("$.simPid").value(123))
        .andExpect(jsonPath("$.rvizPid").value(456))
        .andExpect(jsonPath("$.browserPid").value(789))
        .andExpect(jsonPath("$.browserDebugUrl").value("http://127.0.0.1:9223"))
        .andExpect(jsonPath("$.realHardware.online").value(true))
        .andExpect(jsonPath("$.realHardware.controlInterface").value("ros2_control"))
        .andExpect(jsonPath("$.realHardware.powerState").value("已上电"))
        .andExpect(jsonPath("$.realHardware.gateReasonCode").value("HWS_002_PENDING"))
        .andExpect(jsonPath("$.realHardware.calibrationState").value("READY"));
  }

  @Test
  void shouldStartSimulation() throws Exception {
    when(systemControlService.startSimulation())
        .thenReturn(
            new SystemStatus(
                "simulation",
                true,
                true,
                false,
                false,
                false,
                1001L,
                null,
                null,
                "/tmp/sim.log",
                null,
                null,
                "http://127.0.0.1:9223",
                RealHardwareStatus.safeDefault()));

    mockMvc
        .perform(post("/api/system/start-sim"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true))
        .andExpect(jsonPath("$.status.simRunning").value(true))
        .andExpect(jsonPath("$.status.simPid").value(1001));
  }

  @Test
  void shouldOpenRviz() throws Exception {
    when(systemControlService.openRviz())
        .thenReturn(
            new SystemStatus(
                "simulation",
                true,
                true,
                true,
                true,
                false,
                1001L,
                2002L,
                null,
                "/tmp/sim.log",
                "/tmp/rviz.log",
                null,
                "http://127.0.0.1:9223",
                RealHardwareStatus.safeDefault()));

    mockMvc
        .perform(post("/api/system/open-rviz"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true))
        .andExpect(jsonPath("$.status.rvizRunning").value(true))
        .andExpect(jsonPath("$.status.rvizPid").value(2002));
  }

  @Test
  void shouldStopSimulationAndRviz() throws Exception {
    when(systemControlService.stopSimulation())
        .thenReturn(
            new SystemStatus(
                "simulation",
                false,
                false,
                false,
                false,
                false,
                null,
                null,
                null,
                "/tmp/sim.log",
                "/tmp/rviz.log",
                null,
                "http://127.0.0.1:9223",
                RealHardwareStatus.safeDefault()));

    mockMvc
        .perform(post("/api/system/stop-sim"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true))
        .andExpect(jsonPath("$.status.simRunning").value(false))
        .andExpect(jsonPath("$.status.rvizRunning").value(false));
  }

  @Test
  void shouldOpenCleanBrowser() throws Exception {
    when(systemControlService.openBrowser())
        .thenReturn(
            new SystemStatus(
                "simulation",
                false,
                false,
                false,
                false,
                true,
                null,
                null,
                3003L,
                "/tmp/sim.log",
                "/tmp/rviz.log",
                "/tmp/browser.log",
                "http://127.0.0.1:9223",
                RealHardwareStatus.safeDefault()));

    mockMvc
        .perform(post("/api/system/open-browser"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true))
        .andExpect(jsonPath("$.status.browserRunning").value(true))
        .andExpect(jsonPath("$.status.browserPid").value(3003))
        .andExpect(jsonPath("$.status.browserDebugUrl").value("http://127.0.0.1:9223"));
  }

  @Test
  void shouldStopCleanBrowser() throws Exception {
    when(systemControlService.stopBrowser())
        .thenReturn(
            new SystemStatus(
                "simulation",
                false,
                false,
                false,
                false,
                false,
                null,
                null,
                null,
                "/tmp/sim.log",
                "/tmp/rviz.log",
                "/tmp/browser.log",
                "http://127.0.0.1:9223",
                RealHardwareStatus.safeDefault()));

    mockMvc
        .perform(post("/api/system/stop-browser"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true))
        .andExpect(jsonPath("$.status.browserRunning").value(false));
  }

  @Test
  void shouldUpdateRuntimeTarget() throws Exception {
    when(systemControlService.setRuntimeTarget("real_hardware"))
        .thenReturn(
            new SystemStatus(
                "real_hardware",
                false,
                false,
                false,
                false,
                false,
                null,
                null,
                null,
                "/tmp/sim.log",
                null,
                null,
                "http://127.0.0.1:9223",
                RealHardwareStatus.safeDefault()));

    mockMvc
        .perform(
            post("/api/system/runtime-target")
                .contentType("application/json")
                .content("{\"runtimeTarget\":\"real_hardware\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.ok").value(true))
        .andExpect(jsonPath("$.status.runtimeTarget").value("real_hardware"));
  }
}
