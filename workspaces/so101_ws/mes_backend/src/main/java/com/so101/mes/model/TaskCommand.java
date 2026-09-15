package com.so101.mes.model;

import java.util.Map;

public record TaskCommand(
    String requestId,
    String orderId,
    String actionTemplateId,
    Map<String, Object> params) {}
