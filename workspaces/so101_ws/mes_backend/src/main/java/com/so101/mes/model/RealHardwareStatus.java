package com.so101.mes.model;

import java.util.List;

public record RealHardwareStatus(
    boolean online,
    String controlInterface,
    String powerState,
    boolean estopActive,
    String mode,
    String lastError,
    boolean allowExecute,
    String updatedAt,
    String safetyState,
    String gateReasonCode,
    String gateReasonLabel,
    String calibrationState,
    boolean homed,
    List<SafetyCheckItem> safetyChecks) {
  public static RealHardwareStatus safeDefault() {
    return new RealHardwareStatus(
        false,
        "待接入",
        "未上电",
        false,
        "安全待机",
        "待接入真机状态源",
        false,
        "",
        "LOCKED",
        GateReasonCode.WAITING_FOR_HARDWARE.name(),
        "待接入真机",
        "UNCALIBRATED",
        false,
        List.of(
            new SafetyCheckItem("driver_online", "驱动在线", false, "真机状态源未接入"),
            new SafetyCheckItem("status_fresh", "状态新鲜", false, "等待状态刷新"),
            new SafetyCheckItem("power_on", "已上电", false, "当前未上电"),
            new SafetyCheckItem("estop_clear", "急停正常", true, "当前未检测到急停"),
            new SafetyCheckItem("calibrated", "已完成校准", false, "尚未加载校准配置"),
            new SafetyCheckItem("homed", "已安全回中", false, "尚未完成回中"),
            new SafetyCheckItem("gate_enabled", "系统已放行", false, "默认保护态，需人工确认后放行")));
  }
}
