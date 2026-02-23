#pragma once

#include "trading/account_info.hpp"
#include "trading/deal_info.hpp"
#include "trading/order_info.hpp"
#include "trading/position_info.hpp"
#include "trading/trade.hpp"
#include "core/state.hpp"

#include <cstdint>
#include <string>
#include <unordered_map>

namespace haruquant::core {

class BacktestSimulator {
public:
    explicit BacktestSimulator();

private:

};

}  // namespace haruquant::core
