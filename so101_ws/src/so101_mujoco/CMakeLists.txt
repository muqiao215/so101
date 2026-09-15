cmake_minimum_required(VERSION 3.8)
project(so101_mujoco)

find_package(ament_cmake REQUIRED)

install(DIRECTORY models scripts launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
