package com.so101.mes.service.runtime;

import com.so101.mes.service.ProcessRunner;
import java.io.IOException;
import java.nio.file.Files;
import java.util.Map;

public final class SimulationRuntimeService {
  private static final String GAZEBO_SETUP = "/usr/share/gazebo/setup.bash";

  private final ProcessRunner runner;
  private final RuntimeStatusService runtimeStatusService;
  private final String rosSetup;

  public SimulationRuntimeService(
      ProcessRunner runner, RuntimeStatusService runtimeStatusService, String rosSetup) {
    this.runner = runner;
    this.runtimeStatusService = runtimeStatusService;
    this.rosSetup = rosSetup;
  }

  public RuntimeProcessSnapshot startSimulation() throws IOException {
    runtimeStatusService.ensureRuntimeDir();
    runtimeStatusService.ensureRosLogDir();
    Long livePid = runtimeStatusService.readLivePid(runtimeStatusService.simPidFile());
    if (livePid != null || runtimeStatusService.isTargetRuntimeRunning()) {
      return runtimeStatusService.getRuntimeSnapshot();
    }

    String command = runtimeStatusService.isRealHardwareTarget()
        ? realHardwareCommand()
        : simulationCommand();
    long pid =
        runner.spawnBash(
            command,
            runtimeStatusService.workspaceRoot(),
            Map.of("ROS_LOG_DIR", runtimeStatusService.rosLogDir().toString()),
            runtimeStatusService.simLogFile());
    runtimeStatusService.writePid(runtimeStatusService.simPidFile(), pid);
    return runtimeStatusService.getRuntimeSnapshot();
  }

  private String simulationCommand() {
    return "source '%s' && source '%s' && source '%s/install/setup.bash' && export ROS_LOG_DIR='%s' && exec ros2 launch so101_bringup sim_bringup.launch.py use_rviz:=false use_gzclient:=true use_mock_yolo:=false use_gazebo_color_detector:=true use_real_yolo:=false use_vision_target_projection:=true enable_rosbridge:=true"
        .formatted(
            GAZEBO_SETUP,
            rosSetup,
            runtimeStatusService.workspaceRoot(),
            runtimeStatusService.rosLogDir());
  }

  private String realHardwareCommand() {
    String port = System.getenv().getOrDefault("SO101_FOLLOWER_PORT", "/dev/ttyACM0");
    String maxRelativeTarget =
        System.getenv().getOrDefault("SO101_FOLLOWER_MAX_RELATIVE_TARGET_DEG", "2.0");
    String dryRun = System.getenv().getOrDefault("SO101_FOLLOWER_DRY_RUN", "true");
    return "source '%s' && source '%s/install/setup.bash' && export ROS_LOG_DIR='%s' && export PYTHONPATH='/home/muqiao/.local/lib/python3.10/site-packages:'\"${PYTHONPATH:-}\" && exec ros2 launch so101_bringup real_bringup.launch.py enable_rosbridge:=true command_execution_enabled:=true detection_trigger_enabled:=false enable_follower_adapter:=true follower_port:='%s' follower_max_relative_target_deg:='%s' follower_calibrate_on_connect:=false follower_dry_run:='%s'"
        .formatted(
            rosSetup,
            runtimeStatusService.workspaceRoot(),
            runtimeStatusService.rosLogDir(),
            port,
            maxRelativeTarget,
            dryRun);
  }

  public RuntimeProcessSnapshot openRviz() throws IOException {
    runtimeStatusService.ensureRuntimeDir();
    Long livePid = runtimeStatusService.readLivePid(runtimeStatusService.rvizPidFile());
    if (livePid != null || runner.hasProcess("rviz2 -d")) {
      return runtimeStatusService.getRuntimeSnapshot();
    }

    String rvizConfig =
        runtimeStatusService
            .workspaceRoot()
            .resolve("install/so101_description/share/so101_description/rviz/display.rviz")
            .toString();
    String command =
        "source '%s' && source '%s/install/setup.bash' && exec rviz2 -d '%s'"
            .formatted(rosSetup, runtimeStatusService.workspaceRoot(), rvizConfig);
    long pid =
        runner.spawnBash(
            command,
            runtimeStatusService.workspaceRoot(),
            Map.of(),
            runtimeStatusService.rvizLogFile());
    runtimeStatusService.writePid(runtimeStatusService.rvizPidFile(), pid);
    return runtimeStatusService.getRuntimeSnapshot();
  }

  public RuntimeProcessSnapshot stopSimulation() throws IOException, InterruptedException {
    Long simPid = runtimeStatusService.readLivePid(runtimeStatusService.simPidFile());
    Long rvizPid = runtimeStatusService.readLivePid(runtimeStatusService.rvizPidFile());
    if (rvizPid != null) {
      runner.terminate(rvizPid);
    }
    if (simPid != null) {
      runner.terminate(simPid);
    }

    runner.runBash(
        "pkill -f 'rviz2 -d' || true; pkill -f gzclient || true; pkill -f gzserver || true; pkill -f \"ros2 launch so101_bringup sim_bringup.launch.py\" || true; pkill -f \"ros2 launch so101_bringup real_bringup.launch.py\" || true; pkill -f rosbridge_websocket || true; pkill -f task_executor.py || true; pkill -f so101_follower_trajectory_adapter.py || true; pkill -f sim_color_detector_node.py || true; pkill -f vision_target_projector_node.py || true",
        runtimeStatusService.workspaceRoot());

    Files.deleteIfExists(runtimeStatusService.simPidFile());
    Files.deleteIfExists(runtimeStatusService.rvizPidFile());
    return runtimeStatusService.getRuntimeSnapshot();
  }
}
