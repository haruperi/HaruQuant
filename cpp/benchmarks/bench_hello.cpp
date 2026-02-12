#include <benchmark/benchmark.h>
#include <hqt/hello.hpp>

static void BM_Hello(benchmark::State& state) {
    for (auto _ : state) {
        auto result = hqt::hello();
        benchmark::DoNotOptimize(result);
    }
}
BENCHMARK(BM_Hello);
