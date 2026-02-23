# Google Test framework
find_package(GTest REQUIRED)
include(GoogleTest)

# ZeroMQ
find_package(cppzmq CONFIG REQUIRED)

# Enable testing
enable_testing()

# Test executable
file(GLOB TEST_SOURCES CONFIGURE_DEPENDS "test_*.cpp")
add_executable(haruquant_tests ${TEST_SOURCES})

# Link against Google Test and our library
target_link_libraries(haruquant_tests
    PRIVATE
    GTest::gtest
    GTest::gtest_main
    haruquant_core
    cppzmq-static
)

# Include directories
target_include_directories(haruquant_tests
    PRIVATE
    ${CMAKE_SOURCE_DIR}/cpp/include
)

# Set C++20 standard
target_compile_features(haruquant_tests PRIVATE cxx_std_20)

# Discover tests
gtest_discover_tests(haruquant_tests)

# Add test target
add_test(NAME AllTests COMMAND haruquant_tests)
