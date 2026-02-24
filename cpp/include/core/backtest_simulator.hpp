#pragma once

#include "trading/deal_info.hpp"
#include "trading/order_info.hpp"
#include "trading/position_info.hpp"
#include "trading/account_info.hpp"
#include "trading/trade.hpp"
#include "core/state.hpp"

#include <cstdint>
#include <string>
#include <unordered_map>

namespace haruquant::core {

class BacktestSimulator {
public:
    explicit BacktestSimulator();
    explicit BacktestSimulator(const haruquant::trading::AccountInfo& account);
    const haruquant::trading::AccountInfo& account_info() const { return account_; }

private:
    haruquant::trading::AccountInfo account_{};
};

}  // namespace haruquant::core
