package com.so101.mes.service;

import com.so101.mes.model.OrderRecord;
import com.so101.mes.model.OrderState;
import com.so101.mes.model.TaskStatus;
import com.so101.mes.model.TaskStatusCode;
import java.util.ArrayList;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Service;

@Service
public class OrderService {
  private final Map<String, OrderRecord> orders = new ConcurrentHashMap<>();
  private final Map<String, String> requestToOrder = new ConcurrentHashMap<>();

  public OrderRecord create(String orderId, String actionTemplateId) {
    OrderRecord record =
        new OrderRecord(
            orderId,
            actionTemplateId,
            OrderState.PENDING,
            System.currentTimeMillis(),
            "",
            "",
            "");
    orders.put(orderId, record);
    return record;
  }

  public OrderRecord get(String orderId) {
    return orders.get(orderId);
  }

  public java.util.List<OrderRecord> list() {
    return new ArrayList<>(orders.values());
  }

  public OrderRecord updateState(String orderId, OrderState state, String message) {
    OrderRecord old = orders.get(orderId);
    if (old == null) {
      return null;
    }
    OrderRecord now =
        new OrderRecord(
            orderId,
            old.actionTemplateId(),
            state,
            System.currentTimeMillis(),
            message,
            old.lastRequestId(),
            old.lastStatusCode());
    orders.put(orderId, now);
    return now;
  }

  public void bindRequest(String requestId, String orderId) {
    if (requestId == null || orderId == null || requestId.isBlank() || orderId.isBlank()) {
      return;
    }
    requestToOrder.put(requestId, orderId);
  }

  public OrderRecord updateStateByRequestId(String requestId, OrderState state, String message) {
    String orderId = requestToOrder.get(requestId);
    if (orderId == null) {
      return null;
    }
    return updateState(orderId, state, message);
  }

  public OrderRecord markDispatched(String orderId, String requestId, String message) {
    OrderRecord old = orders.get(orderId);
    if (old == null) {
      return null;
    }
    OrderRecord now =
        new OrderRecord(
            orderId,
            old.actionTemplateId(),
            OrderState.PENDING,
            System.currentTimeMillis(),
            message,
            requestId,
            "DISPATCHED");
    orders.put(orderId, now);
    bindRequest(requestId, orderId);
    return now;
  }

  public OrderRecord applyTaskStatus(TaskStatus status) {
    if (status == null || status.requestId() == null || status.requestId().isBlank()) {
      return null;
    }

    String orderId = requestToOrder.get(status.requestId());
    if (orderId == null) {
      return null;
    }

    OrderRecord old = orders.get(orderId);
    if (old == null) {
      return null;
    }

    TaskStatusCode code = TaskStatusCode.from(status.code());
    OrderState nextState = mapCodeToState(code, status.state(), old.state());
    OrderRecord now =
        new OrderRecord(
            orderId,
            old.actionTemplateId(),
            nextState,
            System.currentTimeMillis(),
            status.message(),
            status.requestId(),
            code.name());
    orders.put(orderId, now);
    return now;
  }

  private OrderState mapCodeToState(TaskStatusCode code, String rosState, OrderState currentState) {
    return switch (code) {
      case STARTED, STEP, DETECTION_TRIGGER -> OrderState.RUNNING;
      case OK -> OrderState.DONE;
      case BUSY, BAD_REQUEST, DETECTION_MISMATCH, EXECUTION_ERROR -> OrderState.ERROR;
      case UNKNOWN -> mapRosStateFallback(rosState, currentState);
    };
  }

  private OrderState mapRosStateFallback(String rosState, OrderState currentState) {
    if (rosState == null || rosState.isBlank()) {
      return currentState;
    }
    return switch (rosState) {
      case "待执行" -> OrderState.PENDING;
      case "执行中" -> OrderState.RUNNING;
      case "完成" -> OrderState.DONE;
      case "异常" -> OrderState.ERROR;
      default -> currentState;
    };
  }
}
