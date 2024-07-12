cmake_minimum_required(VERSION 3.26.4 FATAL_ERROR)

project(foo VERSION 0.0.1 LANGUAGES C)

add_library(foo SHARED foo.c)
target_include_directories(foo PUBLIC "$<INSTALL_INTERFACE:include>")

include(GNUInstallDirs)
install(
  TARGETS foo
  DESTINATION ${CMAKE_INSTALL_LIBDIR}
  EXPORT ${PROJECT_NAME}-exports
)
install(
  FILES foo.h
  DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

include(CMakePackageConfigHelpers)
set(install_location "${CMAKE_INSTALL_LIBDIR}/cmake/${PROJECT_NAME}")
set(build_location "${PROJECT_BINARY_DIR}/${install_location}")
write_basic_package_version_file(
  "${build_location}/${PROJECT_NAME}-config-version.cmake"
  VERSION ${CMAKE_PROJECT_VERSION}
  COMPATIBILITY AnyNewerVersion)
configure_package_config_file("${CMAKE_CURRENT_LIST_DIR}/cmake/config.cmake.in"
                              "${build_location}/${PROJECT_NAME}-config.cmake"
                              INSTALL_DESTINATION "${install_location}")
install(DIRECTORY "${build_location}/" DESTINATION "${install_location}")
install(EXPORT ${PROJECT_NAME}-exports
        DESTINATION "${install_location}"
        FILE "${PROJECT_NAME}-targets.cmake"
        NAMESPACE ${PROJECT_NAME}::)
