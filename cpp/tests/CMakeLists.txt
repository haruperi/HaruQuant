find_package(GTest CONFIG REQUIRED)

add_executable(hqt_tests
    test_hello.cpp
)

target_link_libraries(hqt_tests PRIVATE
    hqt_core
    GTest::gtest
    GTest::gtest_main
)

include(GoogleTest)
gtest_discover_tests(hqt_tests)
