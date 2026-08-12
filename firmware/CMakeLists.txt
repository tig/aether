# ESP-IDF project root. Configure with idf.py from an ESP-IDF environment.
# Minimal hello-metal: identity on UART, optional LED via hal_board.

cmake_minimum_required(VERSION 3.16)

# esprec on-device component (sibling checkout: tig/esprec next to this GCU).
get_filename_component(_ESPREC_COMP
  "${CMAKE_CURRENT_LIST_DIR}/../../esprec/component" ABSOLUTE)
if(EXISTS "${_ESPREC_COMP}/esprec/CMakeLists.txt")
  set(EXTRA_COMPONENT_DIRS "${_ESPREC_COMP}")
else()
  message(WARNING "esprec component not found at ${_ESPREC_COMP} — shot capture needs sibling tig/esprec")
endif()

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(gcu_c)
