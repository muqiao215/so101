package com.so101.mes.model;

public record OrderRecord(
    String orderId,
    String actionTemplateId,
    OrderState state,
    long updatedAt,
    String message,
    String lastRequestId,
    String lastStatusCode) {}
