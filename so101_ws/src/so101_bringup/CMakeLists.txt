cmake_minimum_required(VERSION 3.8)
project(so101_bringup)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch config scripts
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/action_template_mapping.py
  scripts/task_executor.py
  scripts/mock_yolo_node.py
  scripts/sync_action_template_mapping.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
