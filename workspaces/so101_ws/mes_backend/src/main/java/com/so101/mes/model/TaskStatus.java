package com.so101.mes.model;

public record TaskStatus(
    String requestId,
    String state,
    String code,
    String message,
    long ts) {}
