# Google Benchmark framework
find_package(benchmark REQUIRED)

# Benchmark executable for EventLoop (legacy; build only if dependency exists).
if(EXISTS "${CMAKE_SOURCE_DIR}/cpp/include/engine/event_loop.hpp")
    add_executable(bench_event_loop
        bench_event_loop.cpp
    )

    target_link_libraries(bench_event_loop
        PRIVATE
        benchmark::benchmark
    )

    target_include_directories(bench_event_loop
        PRIVATE
        ${CMAKE_SOURCE_DIR}/cpp/include
    )

    target_compile_features(bench_event_loop PRIVATE cxx_std_20)

    if(MSVC)
        target_compile_options(bench_event_loop PRIVATE /O2)
    else()
        target_compile_options(bench_event_loop PRIVATE -O3)
    endif()
endif()
