package com.so101.mes.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.so101.mes.model.OrderState;
import com.so101.mes.model.TaskCommand;
import com.so101.mes.model.TaskStatus;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.messaging.simp.SimpMessagingTemplate;

class RosbridgeClientServiceTest {
  private final ObjectMapper objectMapper = new ObjectMapper();

  private SimpMessagingTemplate ws;
  private OrderService orders;
  private RosbridgeClientService service;

  @BeforeEach
  void setUp() {
    ws = org.mockito.Mockito.mock(SimpMessagingTemplate.class);
    orders = new OrderService();
    service = new RosbridgeClientService(objectMapper, ws, orders);
  }

  @Test
  void shouldBroadcastAndSyncOrderStateForStdMsgsStringPayload() {
    orders.create("order-001", "pick_place_red");
    orders.bindRequest("req-001", "order-001");

    service.handleRosbridgeMessage(
        """
        {"op":"publish","topic":"/mes_task_status","msg":{"data":"{\\"requestId\\":\\"req-001\\",\\"state\\":\\"完成\\",\\"code\\":\\"OK\\",\\"message\\":\\"Task completed\\",\\"ts\\":1772188888123}"}}
        """);

    ArgumentCaptor<TaskStatus> captor = ArgumentCaptor.forClass(TaskStatus.class);
    verify(ws).convertAndSend(org.mockito.ArgumentMatchers.eq("/topic/task-status"), captor.capture());

    TaskStatus status = captor.getValue();
    assertThat(status.requestId()).isEqualTo("req-001");
    assertThat(status.state()).isEqualTo("完成");
    assertThat(status.code()).isEqualTo("OK");
    assertThat(orders.get("order-001").state()).isEqualTo(OrderState.DONE);
    assertThat(orders.get("order-001").message()).isEqualTo("Task completed");
    assertThat(orders.get("order-001").lastRequestId()).isEqualTo("req-001");
    assertThat(orders.get("order-001").lastStatusCode()).isEqualTo("OK");
  }

  @Test
  void shouldBroadcastRawPayloadWhenTaskStatusCannotBeDecoded() {
    service.handleRosbridgeMessage(
        """
        {"op":"publish","topic":"/mes_task_status","msg":{"raw":"not-a-task-status"}}
        """);

    verify(ws)
        .convertAndSend(
            "/topic/task-status",
            java.util.Map.of("raw", "not-a-task-status"));
  }

  @Test
  void shouldBroadcastDecodedDetectionsPayload() {
    service.handleRosbridgeMessage(
        """
        {"op":"publish","topic":"/detections","msg":{"data":"{\\"detections\\":[{\\"category\\":\\"red\\",\\"confidence\\":0.95}],\\"count\\":1}"}}
        """);

    ArgumentCaptor<Object> payloadCaptor = ArgumentCaptor.forClass(Object.class);
    verify(ws).convertAndSend(org.mockito.ArgumentMatchers.eq("/topic/detections"), payloadCaptor.capture());
    assertThat(payloadCaptor.getValue()).isInstanceOf(java.util.Map.class);
    assertThat(((java.util.Map<?, ?>) payloadCaptor.getValue()).get("count")).isEqualTo(1);
  }

  @Test
  void shouldBroadcastDecodedVisionTargetsPayload() {
    service.handleRosbridgeMessage(
        """
        {"op":"publish","topic":"/vision/targets","msg":{"data":"{\\"targets\\":[{\\"category\\":\\"red\\",\\"world_xyz\\":[0.25,0.18,0.8]}],\\"count\\":1}"}}
        """);

    ArgumentCaptor<Object> payloadCaptor = ArgumentCaptor.forClass(Object.class);
    verify(ws).convertAndSend(org.mockito.ArgumentMatchers.eq("/topic/vision-targets"), payloadCaptor.capture());
    assertThat(payloadCaptor.getValue()).isInstanceOf(java.util.Map.class);
    assertThat(((java.util.Map<?, ?>) payloadCaptor.getValue()).get("count")).isEqualTo(1);
  }

  @Test
  void shouldBroadcastLeaderDebugStatusPayloads() {
    service.handleRosbridgeMessage(
        """
        {"op":"publish","topic":"/leader/status","msg":{"data":"{\\"state\\":\\"READY\\",\\"connected\\":true,\\"hz\\":30.0}"}}
        """);
    service.handleRosbridgeMessage(
        """
        {"op":"publish","topic":"/leader/gazebo_bridge/status","msg":{"data":"{\\"state\\":\\"COMMANDING\\",\\"last_reasons\\":[] }"}}
        """);

    ArgumentCaptor<Object> payloadCaptor = ArgumentCaptor.forClass(Object.class);
    verify(ws)
        .convertAndSend(
            org.mockito.ArgumentMatchers.eq("/topic/leader-status"),
            payloadCaptor.capture());
    assertThat(payloadCaptor.getValue()).isInstanceOf(java.util.Map.class);
    assertThat(((java.util.Map<?, ?>) payloadCaptor.getValue()).get("state")).isEqualTo("READY");

    verify(ws)
        .convertAndSend(
            org.mockito.ArgumentMatchers.eq("/topic/leader-gazebo-status"),
            org.mockito.ArgumentMatchers.any(Object.class));
  }

  @Test
  void shouldBroadcastRealFollowerStatusPayload() {
    service.handleRosbridgeMessage(
        """
        {"op":"publish","topic":"/real_follower/status","msg":{"data":"{\\"software_ready\\":true,\\"hardware_bus_ready\\":false,\\"dry_run\\":true,\\"sent_command_count\\":1}"}}
        """);

    ArgumentCaptor<Object> payloadCaptor = ArgumentCaptor.forClass(Object.class);
    verify(ws)
        .convertAndSend(
            org.mockito.ArgumentMatchers.eq("/topic/real-follower-status"),
            payloadCaptor.capture());
    assertThat(payloadCaptor.getValue()).isInstanceOf(java.util.Map.class);
    assertThat(((java.util.Map<?, ?>) payloadCaptor.getValue()).get("software_ready")).isEqualTo(true);
    assertThat(((java.util.Map<?, ?>) payloadCaptor.getValue()).get("hardware_bus_ready")).isEqualTo(false);
  }

  @Test
  void shouldBroadcastLeaderAndGazeboJointStatesForDebug() {
    service.handleRosbridgeMessage(
        """
        {"op":"publish","topic":"/leader/joint_states","msg":{"name":["shoulder_pan"],"position":[0.12]}}
        """);
    service.handleRosbridgeMessage(
        """
        {"op":"publish","topic":"/joint_states","msg":{"name":["shoulder_pan"],"position":[0.11]}}
        """);

    verify(ws)
        .convertAndSend(
            org.mockito.ArgumentMatchers.eq("/topic/leader-joint-states"),
            org.mockito.ArgumentMatchers.any(Object.class));
    verify(ws)
        .convertAndSend(
            org.mockito.ArgumentMatchers.eq("/topic/gazebo-joint-states"),
            org.mockito.ArgumentMatchers.any(Object.class));
  }

  @Test
  void shouldBuildSubscribeMessageWithExplicitStringType() {
    String payload = service.buildSubscribeMessage("/mes_task_status");

    assertThat(payload).contains("\"op\":\"subscribe\"");
    assertThat(payload).contains("\"topic\":\"/mes_task_status\"");
    assertThat(payload).contains("\"type\":\"std_msgs/msg/String\"");
  }

  @Test
  void shouldBuildSubscribeMessageWithExplicitJointStateType() {
    String payload = service.buildSubscribeMessage("/leader/joint_states", "sensor_msgs/msg/JointState");

    assertThat(payload).contains("\"op\":\"subscribe\"");
    assertThat(payload).contains("\"topic\":\"/leader/joint_states\"");
    assertThat(payload).contains("\"type\":\"sensor_msgs/msg/JointState\"");
  }

  @Test
  void shouldBuildPublishMessageAsStdMsgsStringObject() {
    String payload =
        service.buildPublishStringMessage(
            "/mes_task_cmd",
            new TaskCommand("req-001", "order-001", "pick_place_red", java.util.Map.of("priority", 1)));

    assertThat(payload).contains("\"op\":\"publish\"");
    assertThat(payload).contains("\"topic\":\"/mes_task_cmd\"");
    assertThat(payload).contains("\"msg\":{\"data\":\"{\\\"requestId\\\":\\\"req-001\\\"");
    assertThat(payload).contains("\\\"orderId\\\":\\\"order-001\\\"");
    assertThat(payload).contains("\\\"actionTemplateId\\\":\\\"pick_place_red\\\"");
  }
}
