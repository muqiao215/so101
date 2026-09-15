cmake_minimum_required(VERSION 3.8)
project(yolov8_detector)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/yolov8_detector_node.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
