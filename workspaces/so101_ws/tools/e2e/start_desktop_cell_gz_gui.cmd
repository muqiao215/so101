@echo off
setlocal

REM Launch the SO101 Blender desktop cell in Gazebo Classic GUI from Windows.
REM This must run from an interactive Windows session so WSLg can create the GUI window.
wsl.exe -d Ubuntu-22.04 --cd /home/muqiao/dev/ros2/workspaces/so101_ws bash -lc "source /opt/ros/humble/setup.bash; source install/setup.bash; ros2 launch so101_gazebo desktop_cell_classic.launch.py"

endlocal
