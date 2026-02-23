/**
FILE: benchmarks\bench_hello.cpp

PURPOSE:
Defines bench_hello.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in bench_hello.cpp.
- File-local helpers supporting the main public or internal entry points.

DATA FLOW:
Callers provide requests or data -> this file applies core logic -> outputs state changes or results.

DEPENDENCIES:
- Internal modules: Neighboring headers under cpp/include and shared utility components.
- External systems: Standard C++ library and optional third-party libs linked by CMake.

DESIGN NOTES:
- Keep behavior deterministic for backtest and unit-test reliability.
- Prefer explicit validation and retcode-based failure signaling.
- Preserve low coupling between domains through typed interfaces.
*/
#include <benchmark/benchmark.h>
#include <hqt/hello.hpp>

static void BM_Hello(benchmark::State& state) {
    for (auto _ : state) {
        auto result = hqt::hello();
        benchmark::DoNotOptimize(result);
    }
}
BENCHMARK(BM_Hello);

