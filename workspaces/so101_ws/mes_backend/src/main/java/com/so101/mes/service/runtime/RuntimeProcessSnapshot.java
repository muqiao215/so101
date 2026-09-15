package com.so101.mes.service.runtime;

public record RuntimeProcessSnapshot(
    boolean simRunning,
    boolean gazeboRunning,
    boolean rvizRunning,
    boolean browserRunning,
    Long simPid,
    Long rvizPid,
    Long browserPid,
    String simLog,
    String rvizLog,
    String browserLog,
    String browserDebugUrl) {}
