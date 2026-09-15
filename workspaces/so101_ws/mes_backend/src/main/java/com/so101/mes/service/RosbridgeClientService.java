package com.so101.mes.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.so101.mes.model.TaskCommand;
import com.so101.mes.model.TaskStatus;
import jakarta.annotation.PostConstruct;
import java.net.URI;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicLong;
import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

@Service
public class RosbridgeClientService {
  private static final Logger log = LoggerFactory.getLogger(RosbridgeClientService.class);
  private static final String STD_MSGS_STRING_TYPE = "std_msgs/msg/String";
  private static final String SENSOR_MSGS_JOINT_STATE_TYPE = "sensor_msgs/msg/JointState";
  private static final long JOINT_DEBUG_FORWARD_INTERVAL_MS = 200L;

  private final ObjectMapper objectMapper;
  private final SimpMessagingTemplate ws;
  private final OrderService orders;
  private final AtomicBoolean connected = new AtomicBoolean(false);
  private final AtomicBoolean connecting = new AtomicBoolean(false);
  private final AtomicLong lastLeaderJointDebugForwardedMs = new AtomicLong(0L);
  private final AtomicLong lastGazeboJointDebugForwardedMs = new AtomicLong(0L);
  private final ConcurrentLinkedQueue<String> pendingMessages = new ConcurrentLinkedQueue<>();
  private WebSocketClient client;

  @Value("${rosbridge.url:ws://127.0.0.1:9090}")
  private String rosbridgeUrl = "ws://127.0.0.1:9090";

  @Value("${rosbridge.cmd-topic:/mes_task_cmd}")
  private String cmdTopic = "/mes_task_cmd";

  @Value("${rosbridge.status-topic:/mes_task_status}")
  private String statusTopic = "/mes_task_status";

  @Value("${rosbridge.detection-topic:/detections}")
  private String detectionTopic = "/detections";

  @Value("${rosbridge.vision-target-topic:/vision/targets}")
  private String visionTargetTopic = "/vision/targets";

  @Value("${rosbridge.leader-status-topic:/leader/status}")
  private String leaderStatusTopic = "/leader/status";

  @Value("${rosbridge.leader-gazebo-status-topic:/leader/gazebo_bridge/status}")
  private String leaderGazeboStatusTopic = "/leader/gazebo_bridge/status";

  @Value("${rosbridge.leader-joint-states-topic:/leader/joint_states}")
  private String leaderJointStatesTopic = "/leader/joint_states";

  @Value("${rosbridge.gazebo-joint-states-topic:/joint_states}")
  private String gazeboJointStatesTopic = "/joint_states";

  @Value("${rosbridge.real-follower-status-topic:/real_follower/status}")
  private String realFollowerStatusTopic = "/real_follower/status";

  public RosbridgeClientService(ObjectMapper objectMapper, SimpMessagingTemplate ws, OrderService orders) {
    this.objectMapper = objectMapper;
    this.ws = ws;
    this.orders = orders;
  }

  @PostConstruct
  public void autoConnect() {
    connect();
  }

  public synchronized void connect() {
    if (client != null && client.isOpen()) {
      return;
    }
    if (connecting.get()) {
      return;
    }
    connecting.set(true);
    client = new WebSocketClient(URI.create(rosbridgeUrl)) {
      @Override
      public void onOpen(ServerHandshake handshakedata) {
        connecting.set(false);
        connected.set(true);
        log.info("Connected rosbridge: {}", rosbridgeUrl);
        try {
          send(buildSubscribeMessage(statusTopic));
          send(buildSubscribeMessage(detectionTopic));
          send(buildSubscribeMessage(visionTargetTopic));
          send(buildSubscribeMessage(leaderStatusTopic));
          send(buildSubscribeMessage(leaderGazeboStatusTopic));
          send(buildSubscribeMessage(leaderJointStatesTopic, SENSOR_MSGS_JOINT_STATE_TYPE));
          send(buildSubscribeMessage(gazeboJointStatesTopic, SENSOR_MSGS_JOINT_STATE_TYPE));
          send(buildSubscribeMessage(realFollowerStatusTopic));
          flushPendingMessages();
        } catch (Exception e) {
          log.error("Failed to initialize rosbridge subscription", e);
        }
      }

      @Override
      public void onMessage(String message) {
        handleRosbridgeMessage(message);
      }

      @Override
      public void onClose(int code, String reason, boolean remote) {
        connecting.set(false);
        connected.set(false);
        log.warn("Rosbridge closed: code={}, reason={}", code, reason);
      }

      @Override
      public void onError(Exception ex) {
        connecting.set(false);
        connected.set(false);
        log.error("Rosbridge error", ex);
      }
    };
    client.connect();
  }

  public synchronized void disconnect() {
    if (client != null) {
      client.close();
    }
    connecting.set(false);
  }

  public boolean isConnected() {
    return connected.get();
  }

  public void publishTask(TaskCommand cmd) {
    sendRawJson(buildPublishStringMessage(cmdTopic, cmd));
  }

  public void ingestTaskStatus(TaskStatus status) {
    if (status == null) {
      return;
    }
    ws.convertAndSend("/topic/task-status", status);
    orders.applyTaskStatus(status);
  }

  public void ingestDetectionPayload(Object payload) {
    if (payload == null) {
      return;
    }
    ws.convertAndSend("/topic/detections", payload);
  }

  void handleRosbridgeMessage(String message) {
    try {
      Map<?, ?> msg = objectMapper.readValue(message, Map.class);
      if (!"publish".equals(msg.get("op"))) {
        return;
      }
      Object topic = msg.get("topic");
      if (statusTopic.equals(topic)) {
        handleStatusPayload(msg.get("msg"));
        return;
      }
      if (detectionTopic.equals(topic)) {
        handleDetectionPayload(msg.get("msg"));
        return;
      }
      if (visionTargetTopic.equals(topic)) {
        handleVisionTargetPayload(msg.get("msg"));
        return;
      }
      if (leaderStatusTopic.equals(topic)) {
        handleLeaderStatusPayload(msg.get("msg"));
        return;
      }
      if (leaderGazeboStatusTopic.equals(topic)) {
        handleLeaderGazeboStatusPayload(msg.get("msg"));
        return;
      }
      if (leaderJointStatesTopic.equals(topic)) {
        handleLeaderJointStatePayload(msg.get("msg"));
        return;
      }
      if (gazeboJointStatesTopic.equals(topic)) {
        handleGazeboJointStatePayload(msg.get("msg"));
        return;
      }
      if (realFollowerStatusTopic.equals(topic)) {
        handleRealFollowerStatusPayload(msg.get("msg"));
      }
    } catch (Exception e) {
      log.warn("Failed to parse rosbridge message", e);
    }
  }

  private void handleStatusPayload(Object payload) {
    TaskStatus status = decodeStatusPayload(payload);
    if (status != null) {
      ingestTaskStatus(status);
      return;
    }
    ws.convertAndSend("/topic/task-status", payload);
  }

  private void handleDetectionPayload(Object payload) {
    Object decoded = decodeGenericPayload(payload);
    ingestDetectionPayload(decoded);
  }

  private void handleVisionTargetPayload(Object payload) {
    Object decoded = decodeGenericPayload(payload);
    ws.convertAndSend("/topic/vision-targets", decoded);
  }

  private void handleLeaderStatusPayload(Object payload) {
    Object decoded = decodeGenericPayload(payload);
    ws.convertAndSend("/topic/leader-status", decoded);
  }

  private void handleLeaderGazeboStatusPayload(Object payload) {
    Object decoded = decodeGenericPayload(payload);
    ws.convertAndSend("/topic/leader-gazebo-status", decoded);
  }

  private void handleLeaderJointStatePayload(Object payload) {
    if (shouldForwardJointDebug(lastLeaderJointDebugForwardedMs)) {
      ws.convertAndSend("/topic/leader-joint-states", payload);
    }
  }

  private void handleGazeboJointStatePayload(Object payload) {
    if (shouldForwardJointDebug(lastGazeboJointDebugForwardedMs)) {
      ws.convertAndSend("/topic/gazebo-joint-states", payload);
    }
  }

  private void handleRealFollowerStatusPayload(Object payload) {
    Object decoded = decodeGenericPayload(payload);
    ws.convertAndSend("/topic/real-follower-status", decoded);
  }

  private boolean shouldForwardJointDebug(AtomicLong lastForwardedMs) {
    long nowMs = System.currentTimeMillis();
    long previousMs = lastForwardedMs.get();
    if (nowMs - previousMs < JOINT_DEBUG_FORWARD_INTERVAL_MS) {
      return false;
    }
    return lastForwardedMs.compareAndSet(previousMs, nowMs);
  }

  private TaskStatus decodeStatusPayload(Object payload) {
    try {
      if (payload instanceof String s) {
        return validateStatus(objectMapper.readValue(s, TaskStatus.class));
      }

      // rosbridge std_msgs/String payload shape: {"data":"{\"requestId\":...}"}
      if (payload instanceof Map<?, ?> map && map.get("data") instanceof String data) {
        return validateStatus(objectMapper.readValue(data, TaskStatus.class));
      }

      if (payload instanceof Map<?, ?> map) {
        if (!map.containsKey("requestId") && !map.containsKey("state")) {
          return null;
        }
        return validateStatus(objectMapper.convertValue(map, TaskStatus.class));
      }
    } catch (Exception e) {
      log.warn("Failed to decode task status payload: {}", payload, e);
    }
    return null;
  }

  private Object decodeGenericPayload(Object payload) {
    try {
      if (payload instanceof String s) {
        return objectMapper.readValue(s, Object.class);
      }
      if (payload instanceof Map<?, ?> map && map.get("data") instanceof String data) {
        return objectMapper.readValue(data, Object.class);
      }
    } catch (Exception e) {
      log.warn("Failed to decode generic payload: {}", payload, e);
    }
    return payload;
  }

  private TaskStatus validateStatus(TaskStatus status) {
    if (status == null) {
      return null;
    }
    if (status.requestId() == null || status.requestId().isBlank()) {
      return null;
    }
    if (status.state() == null || status.state().isBlank()) {
      return null;
    }
    return status;
  }

  private void sendJson(Object payload) {
    try {
      sendRawJson(objectMapper.writeValueAsString(payload));
    } catch (Exception e) {
      throw new RuntimeException("Failed to send rosbridge message", e);
    }
  }

  private void sendRawJson(String json) {
    if (client == null || !client.isOpen()) {
      pendingMessages.offer(json);
      connect();
      log.warn("Rosbridge not open yet. Message queued.");
      return;
    }
    client.send(json);
  }

  private void flushPendingMessages() {
    String payload;
    while ((payload = pendingMessages.poll()) != null) {
      client.send(payload);
    }
  }

  String buildSubscribeMessage(String topic) {
    return buildSubscribeMessage(topic, STD_MSGS_STRING_TYPE);
  }

  String buildSubscribeMessage(String topic, String type) {
    try {
      return objectMapper.writeValueAsString(
          Map.of(
              "op", "subscribe",
              "topic", topic,
              "type", type));
    } catch (Exception e) {
      throw new RuntimeException("Failed to build rosbridge subscribe payload", e);
    }
  }

  String buildPublishStringMessage(String topic, Object payload) {
    try {
      return objectMapper.writeValueAsString(
          Map.of(
              "op", "publish",
              "topic", topic,
              "msg", Map.of("data", objectToJson(payload))));
    } catch (Exception e) {
      throw new RuntimeException("Failed to build rosbridge publish payload", e);
    }
  }

  private String objectToJson(Object o) {
    try {
      return objectMapper.writeValueAsString(o);
    } catch (Exception e) {
      throw new RuntimeException(e);
    }
  }
}
