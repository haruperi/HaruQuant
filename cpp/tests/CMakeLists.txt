# Google Test framework
find_package(GTest REQUIRED)
include(GoogleTest)

# ZeroMQ
find_package(cppzmq CONFIG REQUIRED)

# Enable testing
enable_testing()

# Test executable
add_executable(hqt_tests
    test_simulator_state.cpp
    test_sim_data.cpp
    test_sim_calculators.cpp
    test_simulator_client_getters.cpp
    test_sim_order_send_market.cpp
    test_sim_pending_orders.cpp
    test_sim_backtest_single_symbol.cpp
    test_sim_position_monitor.cpp
    test_sim_pending_trigger_monitor.cpp
    test_sim_tick_models.cpp
    test_sim_trade_record.cpp
    test_sim_portfolio_engine.cpp
    test_sim_result_metrics.cpp
    test_data_structures.cpp
    test_utilities.cpp
    test_event_loop.cpp
    test_clock_service.cpp
    test_event_sequencer.cpp
    test_session_calendar.cpp
    test_trade.cpp
    test_currency_margin.cpp
    test_costs_engine.cpp
    test_zmq_wal.cpp
    test_logger.cpp
    test_connection_pool.cpp
    test_schema_validator.cpp
)

# Link against Google Test and our library
target_link_libraries(hqt_tests
    PRIVATE
    GTest::gtest
    GTest::gtest_main
    hqt_core
    cppzmq-static
)

# Include directories
target_include_directories(hqt_tests
    PRIVATE
    ${CMAKE_SOURCE_DIR}/cpp/include
)

# Set C++20 standard
target_compile_features(hqt_tests PRIVATE cxx_std_20)

# Discover tests
gtest_discover_tests(hqt_tests)

# Add test target
add_test(NAME AllTests COMMAND hqt_tests)
