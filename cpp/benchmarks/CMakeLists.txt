# Google Benchmark framework
find_package(benchmark REQUIRED)

# Benchmark executable for EventLoop
add_executable(bench_event_loop
    bench_event_loop.cpp
)

# Link against Google Benchmark
target_link_libraries(bench_event_loop
    PRIVATE
    benchmark::benchmark
)

# Include directories
target_include_directories(bench_event_loop
    PRIVATE
    ${CMAKE_SOURCE_DIR}/cpp/include
)

# Set C++20 standard
target_compile_features(bench_event_loop PRIVATE cxx_std_20)

# Enable optimizations for benchmarks
if(MSVC)
    target_compile_options(bench_event_loop PRIVATE /O2)
else()
    target_compile_options(bench_event_loop PRIVATE -O3)
endif()
