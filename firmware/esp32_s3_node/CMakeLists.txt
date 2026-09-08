cmake_minimum_required(VERSION 3.16)
if(DEFINED ENV{IDF_PATH})
  include($ENV{IDF_PATH}/tools/cmake/project.cmake)
  project(tank_sensor_node)
else()
  project(tank_core_tests LANGUAGES CXX)
  enable_testing()
  add_library(tank_core
    main/core/src/sector.cpp
    main/core/src/temporal_validator.cpp
    main/core/src/indicator_manager.cpp)
  target_sources(tank_core PRIVATE main/core/src/tf02_frame_parser.cpp)
  target_include_directories(tank_core PUBLIC main/core/include)
  target_compile_features(tank_core PUBLIC cxx_std_17)
  target_compile_options(tank_core PRIVATE -Wall -Wextra -Werror)
  add_executable(tank_core_tests test/core_tests.cpp)
  target_link_libraries(tank_core_tests PRIVATE tank_core)
  add_test(NAME tank_core_tests COMMAND tank_core_tests)
endif()
