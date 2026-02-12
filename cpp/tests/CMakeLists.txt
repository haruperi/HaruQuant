# Google Test framework
find_package(GTest REQUIRED)
include(GoogleTest)

# ZeroMQ
find_package(cppzmq CONFIG REQUIRED)

# Enable testing
enable_testing()

# Test executable
add_executable(hqt_tests
    test_data_structures.cpp
    test_utilities.cpp
    test_event_loop.cpp
    test_trade.cpp
    test_currency_margin.cpp
    test_costs_engine.cpp
    test_engine.cpp
    test_zmq_wal.cpp
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
