cmake_minimum_required(VERSION 3.26.4 FATAL_ERROR)

project(
  ${SKBUILD_PROJECT_NAME}
  VERSION 0.0.1
  LANGUAGES C
)

find_package(bar REQUIRED)

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)

python_add_library(pylibbar MODULE pylibbar/pylibbar.c WITH_SOABI)
target_link_libraries(pylibbar PRIVATE bar::bar)

install(TARGETS pylibbar DESTINATION pylibbar)
