cmake_minimum_required(VERSION 3.16)
project(gcu_c_host C)

set(CMAKE_C_STANDARD 11)
enable_testing()

add_library(gcu_core
  ../src/defaults.c
  ../src/domain.c
  ../src/ecu_client.c
)
target_include_directories(gcu_core PUBLIC ../include)

add_executable(test_defaults test_defaults.c)
target_link_libraries(test_defaults gcu_core)
add_test(NAME defaults COMMAND test_defaults)

add_executable(test_time test_time.c)
target_link_libraries(test_time gcu_core)
add_test(NAME time64 COMMAND test_time)

add_executable(test_ecu_client test_ecu_client.c)
target_link_libraries(test_ecu_client gcu_core)
add_test(NAME ecu_client COMMAND test_ecu_client)

# TCP bench against software V-ECU (invoked from pytest, not default ctest).
add_executable(ecu_tcp_bench ecu_tcp_bench.c)
target_link_libraries(ecu_tcp_bench gcu_core)
if(WIN32)
  target_link_libraries(ecu_tcp_bench ws2_32)
endif()

# Convenience: cmake --build build/host --target host_test runs ctest.
# Do not name this target "test" — CMake reserves that name when enable_testing() is on.
add_custom_target(host_test
  COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure
  DEPENDS test_defaults test_time test_ecu_client
  WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
)
