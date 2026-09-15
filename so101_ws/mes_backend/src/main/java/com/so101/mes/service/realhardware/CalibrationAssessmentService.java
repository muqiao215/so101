package com.so101.mes.service.realhardware;

import java.util.Map;

public final class CalibrationAssessmentService {
  public CalibrationAssessment assess(RuntimeRealHardwareReader.CalibrationFileSnapshot calibration) {
    if (calibration == null || !calibration.calibrated()) {
      return CalibrationAssessment.uncalibrated();
    }

    Map<String, RuntimeRealHardwareReader.CalibrationPoseSnapshot> poses = calibration.poses();
    if (poses == null) {
      return CalibrationAssessment.invalid();
    }
    if (!hasJointPose(poses, "home") || !hasJointPose(poses, "pick") || !hasJointPose(poses, "place")) {
      return CalibrationAssessment.invalid();
    }
    if (!hasGripperPose(poses, "gripper_open") || !hasGripperPose(poses, "gripper_close")) {
      return CalibrationAssessment.invalid();
    }
    if (!calibration.homed()) {
      return CalibrationAssessment.calibratedNotHomed();
    }
    return CalibrationAssessment.ready();
  }

  private boolean hasJointPose(
      Map<String, RuntimeRealHardwareReader.CalibrationPoseSnapshot> poses, String key) {
    RuntimeRealHardwareReader.CalibrationPoseSnapshot pose = poses.get(key);
    return pose != null && pose.joints() != null && pose.joints().size() == 6;
  }

  private boolean hasGripperPose(
      Map<String, RuntimeRealHardwareReader.CalibrationPoseSnapshot> poses, String key) {
    RuntimeRealHardwareReader.CalibrationPoseSnapshot pose = poses.get(key);
    return pose != null && pose.value() != null;
  }

  public record CalibrationAssessment(String calibrationState, boolean valid, boolean homed) {
    public static CalibrationAssessment uncalibrated() {
      return new CalibrationAssessment("UNCALIBRATED", false, false);
    }

    public static CalibrationAssessment invalid() {
      return new CalibrationAssessment("INVALID", false, false);
    }

    public static CalibrationAssessment calibratedNotHomed() {
      return new CalibrationAssessment("CALIBRATED_NOT_HOMED", true, false);
    }

    public static CalibrationAssessment ready() {
      return new CalibrationAssessment("READY", true, true);
    }
  }
}
