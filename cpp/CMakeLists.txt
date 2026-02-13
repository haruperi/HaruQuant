# HQT Core C++ Library
add_library(hqt_core STATIC
    src/util/logger.cpp
    src/usage/logger_usage.cpp
    src/hello.cpp
    src/trading/trade.cpp
    src/sim/simulator_state.cpp
    src/sim/sim_data.cpp
    src/sim/calculators.cpp
    src/sim/account_monitor.cpp
    src/sim/trade_gateway.cpp
    src/sim/simulator_client.cpp
    src/sim/backtest_engine.cpp
    src/sim/tick_model.cpp
    src/sim/trade_record.cpp
    src/sim/portfolio_engine.cpp
    src/sim/result_metrics.cpp
)

target_include_directories(hqt_core PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_compile_features(hqt_core PUBLIC cxx_std_20)

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
