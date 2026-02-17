# HQT Core C++ Library
find_package(spdlog CONFIG REQUIRED)

add_library(hqt_core STATIC
    src/engine/engine.cpp
    src/engine/models.cpp
    src/engine/trading.cpp
    src/engine/analytics.cpp
    src/engine/infrastructure.cpp
    src/engine/error.cpp
    src/engine/logger.cpp
    src/engine/usage.cpp
    src/hello.cpp
    src/trading/trade.cpp
)

target_include_directories(hqt_core PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_compile_features(hqt_core PUBLIC cxx_std_20)
target_link_libraries(hqt_core PRIVATE spdlog::spdlog)

# MSVC-specific flags
if(MSVC)
    target_compile_options(hqt_core PRIVATE /W4 /utf-8)
else()
    target_compile_options(hqt_core PRIVATE -Wall -Wextra -Wpedantic)
endif()

# Tests
if(HQT_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Benchmarks
if(HQT_BUILD_BENCHMARKS)
    add_subdirectory(benchmarks)
endif()
