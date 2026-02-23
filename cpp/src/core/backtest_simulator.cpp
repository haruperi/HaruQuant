#include "core/backtest_simulator.hpp"
#include "util/logger.hpp"

namespace haruquant::core {

BacktestSimulator::BacktestSimulator(const haruquant::AccountInfo& account_info)
    : account_info_{account_info},
      positions_container_{},
      orders_container_{},
      deals_container_{} {
    haruquant::util::info("Backtest Simulator successfully initialised");
}

}  // namespace haruquant::core
