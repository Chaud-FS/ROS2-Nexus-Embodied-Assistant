cmake_minimum_required(VERSION 3.8)
project(nexus_description)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)

# Install all launch / urdf / config / world resources
install(DIRECTORY launch urdf config worlds rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
