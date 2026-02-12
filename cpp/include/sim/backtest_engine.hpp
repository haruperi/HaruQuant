/**
 * @file backtest_engine.hpp
 * @brief Minimal single-symbol trading_timeframe backtest loop.
 */

#pragma once

#include "sim/simulator_client.hpp"
#include "sim/simulator_state.hpp"

#include <cstddef>
#include <cstdint>
#include <functional>
#include <string>
#include <vector>

namespace hqt::sim {

/**
 * @brief Single trading bar step with precomputed signals.
 */
struct BacktestBarStep {
    int64_t time_msc{0};
    double close{0.0};
    double spread_points{-1.0};
    int entry_signal{0};  // 1=buy, -1=sell, 0=none
    int exit_signal{0};   // 1=close buys, -1=close sells, 0=none
};

/**
 * @brief Callback invoked once per processed bar.
 */
using BarProcessedCallback = std::function<void(std::size_t, const BacktestBarStep&, const SimulatorState&)>;

/**
 * @brief Minimal engine that reproduces trading_timeframe signal flow.
 */
class BacktestEngine {
public:
    explicit BacktestEngine(SimulatorClient& client);

    void set_on_bar_processed(BarProcessedCallback callback);

    void run_trading_timeframe(
        const std::string& symbol,
        double volume,
        const std::vector<BacktestBarStep>& bars);

    [[nodiscard]] const SimulatorState& state() const noexcept;

private:
    void apply_exit_signal(const std::string& symbol, int exit_signal);
    void apply_entry_signal(const std::string& symbol, double volume, int entry_signal, double bid, double ask);

    SimulatorClient& client_;
    SimulatorState state_{};
    BarProcessedCallback on_bar_processed_{};
};

}  // namespace hqt::sim

