#pragma once

#include "trading/account_info.hpp"
#include "trading/deal_info.hpp"
#include "trading/order_info.hpp"
#include "trading/position_info.hpp"

#include <cstdint>
#include <unordered_map>

namespace haruquant::core {

class BacktestSimulator {
public:
    explicit BacktestSimulator(const haruquant::AccountInfo& account_info);

private:
    haruquant::AccountInfo account_info_;
    std::unordered_map<std::uint64_t, haruquant::PositionInfo> positions_container_;
    std::unordered_map<std::uint64_t, haruquant::OrderInfo> orders_container_;
    std::unordered_map<std::uint64_t, haruquant::DealInfo> deals_container_;
};

}  // namespace haruquant::core
