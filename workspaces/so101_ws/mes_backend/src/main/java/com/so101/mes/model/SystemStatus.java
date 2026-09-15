package com.so101.mes.model;

public record SystemStatus(
    String runtimeTarget,
    boolean simRunning,
    boolean gazeboRunning,
    boolean rvizRunning,
    boolean rosbridgeConnected,
    boolean browserRunning,
    Long simPid,
    Long rvizPid,
    Long browserPid,
    String simLog,
    String rvizLog,
    String browserLog,
    String browserDebugUrl,
    RealHardwareStatus realHardware) {}
