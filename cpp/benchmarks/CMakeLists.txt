find_package(benchmark CONFIG REQUIRED)

add_executable(hqt_benchmarks
    bench_hello.cpp
)

target_link_libraries(hqt_benchmarks PRIVATE
    hqt_core
    benchmark::benchmark
    benchmark::benchmark_main
)
