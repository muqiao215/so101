package com.so101.mes.controller;

import com.so101.mes.model.OrderRecord;
import com.so101.mes.model.TaskCommand;
import com.so101.mes.service.OrderService;
import com.so101.mes.service.RosbridgeClientService;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/orders")
public class OrderController {
  private final OrderService orderService;
  private final RosbridgeClientService rosbridge;

  public OrderController(OrderService orderService, RosbridgeClientService rosbridge) {
    this.orderService = orderService;
    this.rosbridge = rosbridge;
  }

  @GetMapping
  public java.util.List<OrderRecord> listOrders() {
    return orderService.list();
  }

  @GetMapping("/{orderId}")
  public OrderRecord getOrder(@PathVariable String orderId) {
    return orderService.get(orderId);
  }

  @PostMapping
  @ResponseStatus(HttpStatus.CREATED)
  public OrderRecord createOrder(@RequestBody Map<String, Object> req) {
    String orderId = String.valueOf(req.getOrDefault("orderId", UUID.randomUUID().toString()));
    String actionTemplateId = String.valueOf(req.getOrDefault("actionTemplateId", "pick_place_default"));
    return orderService.create(orderId, actionTemplateId);
  }

  @PostMapping("/{orderId}/dispatch")
  public Map<String, Object> dispatch(@PathVariable String orderId, @RequestBody(required = false) Map<String, Object> req) {
    OrderRecord order = orderService.get(orderId);
    if (order == null) {
      return Map.of("ok", false, "error", "ORDER_NOT_FOUND");
    }
    String requestId = "req-" + System.currentTimeMillis();
    TaskCommand cmd =
        new TaskCommand(
            requestId,
            order.orderId(),
            order.actionTemplateId(),
            req == null ? Map.of() : req);
    rosbridge.publishTask(cmd);
    orderService.markDispatched(orderId, requestId, "Dispatched to ROS2");
    return Map.of("ok", true, "requestId", requestId);
  }
}
