# Google Test framework
find_package(GTest REQUIRED)
include(GoogleTest)

# ZeroMQ
find_package(cppzmq CONFIG REQUIRED)

# Enable testing
enable_testing()

# Test executable
file(GLOB TEST_SOURCES CONFIGURE_DEPENDS "test_*.cpp")
add_executable(hqt_tests ${TEST_SOURCES})

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
