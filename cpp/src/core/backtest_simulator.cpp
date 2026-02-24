#include "core/backtest_simulator.hpp"

#include "util/logger.hpp"

namespace haruquant::core {

BacktestSimulator::BacktestSimulator() {
    haruquant::util::info("Backtest Simulator successfully initialised");
}

BacktestSimulator::BacktestSimulator(const haruquant::trading::AccountInfo& account) : account_(account) {
    haruquant::util::info("Backtest Simulator successfully initialised with account");
}

}  // namespace haruquant::core
