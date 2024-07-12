cmake_minimum_required(VERSION 3.26.4 FATAL_ERROR)

project(
  ${SKBUILD_PROJECT_NAME}
  VERSION 0.0.1
  LANGUAGES C
)

find_package(example REQUIRED)

find_package(
  Python
  COMPONENTS Interpreter Development.Module
  REQUIRED)

python_add_library(pylibexample2 MODULE pylibexample2/pylibexample2.c WITH_SOABI)
target_link_libraries(pylibexample2 PRIVATE example::example)

install(TARGETS pylibexample2 DESTINATION pylibexample2)
