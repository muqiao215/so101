package com.so101.mes.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.so101.mes.model.OrderState;
import com.so101.mes.model.TaskStatus;
import org.junit.jupiter.api.Test;

class OrderServiceTest {
  private final OrderService orders = new OrderService();

  @Test
  void markDispatchedShouldKeepOrderPendingUntilRosStatusArrives() {
    orders.create("order-001", "pick_place_red");

    var record = orders.markDispatched("order-001", "req-001", "Dispatched to ROS2");

    assertThat(record.state()).isEqualTo(OrderState.PENDING);
    assertThat(record.lastRequestId()).isEqualTo("req-001");
    assertThat(record.lastStatusCode()).isEqualTo("DISPATCHED");
  }

  @Test
  void applyTaskStatusShouldMapExecutionAndCompletionCodes() {
    orders.create("order-001", "pick_place_red");
    orders.markDispatched("order-001", "req-001", "Dispatched to ROS2");

    orders.applyTaskStatus(new TaskStatus("req-001", "执行中", "STARTED", "template=pick_place_red", 1L));
    assertThat(orders.get("order-001").state()).isEqualTo(OrderState.RUNNING);
    assertThat(orders.get("order-001").lastStatusCode()).isEqualTo("STARTED");

    orders.applyTaskStatus(new TaskStatus("req-001", "完成", "OK", "Task completed", 2L));
    assertThat(orders.get("order-001").state()).isEqualTo(OrderState.DONE);
    assertThat(orders.get("order-001").lastStatusCode()).isEqualTo("OK");
  }

  @Test
  void applyTaskStatusShouldMapRosErrorCodesToErrorState() {
    orders.create("order-001", "pick_place_blue");
    orders.markDispatched("order-001", "req-002", "Dispatched to ROS2");

    orders.applyTaskStatus(new TaskStatus("req-002", "异常", "DETECTION_MISMATCH", "Expected blue, got red", 3L));

    assertThat(orders.get("order-001").state()).isEqualTo(OrderState.ERROR);
    assertThat(orders.get("order-001").message()).contains("Expected blue, got red");
    assertThat(orders.get("order-001").lastStatusCode()).isEqualTo("DETECTION_MISMATCH");
  }
}
