# SO101 Workspace Agent Rules

This file defines project-local execution and tracking rules for `so101_ws`.
It is the source of truth for task status tracking in this project.

## 1. Scope

- Current scope is **single-PC runnable first**.
- No real arm is required at this stage.
- Hardware communication tasks are allowed to remain `blocked` with clear reasons.

## 2. Tracking Files (must keep in sync)

- Master task board: `docs/任务清单.md`
- Progress journal: `docs/进度日志.md`

When any code is changed for this project, update both files in the same session.

## 3. Task ID and Status Rules

Each task must have:
- `Task ID` (immutable, e.g. `R2C-001`)
- `Owner` (default: `muqiao`)
- `Status` in this set only:
  - `not_started`
  - `in_progress`
  - `blocked`
  - `done`
- `Evidence` (command output, log file, screenshot path, or commit hash)
- `Done Criteria` (objective acceptance conditions)

Do not mark `done` without evidence.

## 4. Update Frequency

- Update `docs/任务清单.md` after every meaningful implementation chunk.
- Append one new entry to `docs/进度日志.md` at least once per day while active.
- If blocked for more than 1 day, add:
  - blocker description
  - impact
  - fallback path

## 5. Single-PC Priority Execution Order

1. `ros2_control` simulation control chain
2. Gazebo + MoveIt2 planning and execution chain
3. Real YOLOv8 ROS2 detector (camera + detection topic)
4. MES backend integration stabilization
5. Vue production frontend
6. End-to-end local demo and reproducibility scripts

## 6. Professional Clarification (important)

- `ros2_control` mock (`mock_components/GenericSystem`) is **virtual hardware backend**, not Gazebo physics simulation.
- Gazebo simulation and `ros2_control` mock can both be used on one PC, but they solve different layers:
  - mock: control interface and controller pipeline verification
  - Gazebo: kinematics/dynamics scene behavior verification

## 7. Definition of Done (project-level)

Project can be considered locally complete when all are true:
- One-command bringup runs on one PC.
- End-to-end path works:
  `MES command -> ROS2 task executor -> trajectory execution -> status feedback -> UI update`.
- Gazebo + MoveIt2 can generate and execute pick-place trajectory.
- YOLOv8 detector publishes real detection results (not mock) to `/detections`.
- Vue frontend is buildable and demonstrates order lifecycle + status stream.
