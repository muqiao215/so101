import math


JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
BODY_JOINT_NAMES = JOINT_NAMES[:-1]
STS_MAX_RESOLUTION = 4095


def _bounded(raw, cal):
    return min(float(cal["range_max"]), max(float(cal["range_min"]), float(raw)))


def raw_to_lerobot_normalized(raw_by_id, calibration):
    """Official current LeRobot SO101 units.

    Body joints use RANGE_M100_100. Gripper uses RANGE_0_100.
    """
    values = []
    for name in JOINT_NAMES:
        cal = calibration[name]
        raw = _bounded(raw_by_id[int(cal["id"])], cal)
        low = float(cal["range_min"])
        high = float(cal["range_max"])
        if high == low:
            raise ValueError("invalid calibration range for %s" % name)
        if name == "gripper":
            value = (raw - low) / (high - low) * 100.0
            if int(cal.get("drive_mode", 0)):
                value = 100.0 - value
        else:
            value = ((raw - low) / (high - low) * 200.0) - 100.0
            if int(cal.get("drive_mode", 0)):
                value = -value
        values.append(value)
    return values


def raw_to_lerobot_degrees(raw_by_id, calibration):
    """Official LeRobot compatibility units when SO101FollowerConfig.use_degrees=True.

    Body joints are degrees around the calibrated range midpoint. Gripper remains 0..100.
    """
    values = []
    for name in JOINT_NAMES:
        cal = calibration[name]
        raw = _bounded(raw_by_id[int(cal["id"])], cal)
        low = float(cal["range_min"])
        high = float(cal["range_max"])
        if high == low:
            raise ValueError("invalid calibration range for %s" % name)
        if name == "gripper":
            value = (raw - low) / (high - low) * 100.0
            if int(cal.get("drive_mode", 0)):
                value = 100.0 - value
        else:
            mid = (low + high) / 2.0
            value = (raw - mid) * 360.0 / float(STS_MAX_RESOLUTION)
        values.append(value)
    return values


def apply_urdf_map(source_values, joint_map, clamp_enabled=True):
    source_by_name = {name: float(source_values[idx]) for idx, name in enumerate(JOINT_NAMES)}
    target_names = list(joint_map["joint_order"])
    mapping = joint_map.get("mapping", {})
    limits = joint_map.get("limits", {})
    target_values = []
    clamped = []
    for target in target_names:
        cfg = mapping.get(target, {})
        source = str(cfg.get("source", target))
        sign = float(cfg.get("sign", 1.0))
        scale = float(cfg.get("scale", 1.0))
        offset = float(cfg.get("offset", 0.0))
        if source not in source_by_name:
            raise KeyError("source joint %r for target %r not found" % (source, target))
        value = sign * scale * source_by_name[source] + offset
        if clamp_enabled and target in limits:
            low, high = limits[target]
            clamped_value = min(max(value, float(low)), float(high))
            if abs(clamped_value - value) > 1e-9:
                clamped.append(target)
            value = clamped_value
        target_values.append(float(value))
    return target_names, target_values, clamped


def format_values(values):
    return "[" + ", ".join("%+.3f" % float(v) for v in values) + "]"


def rad_per_official_unit(name, calibration):
    if name == "gripper":
        raise ValueError("gripper has no radian-per-normalized-body-unit scale")
    span = float(calibration[name]["range_max"]) - float(calibration[name]["range_min"])
    return span * math.pi / (float(STS_MAX_RESOLUTION) * 100.0)
