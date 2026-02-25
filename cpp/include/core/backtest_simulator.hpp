#pragma once

#include "trading/account_info.hpp"
#include "trading/deal_info.hpp"
#include "trading/history_order_info.hpp"
#include "trading/order_info.hpp"
#include "trading/position_info.hpp"



#include <string>
#include <vector>


namespace haruquant::core {

class BacktestSimulator {
public:
    explicit BacktestSimulator();
    explicit BacktestSimulator(const haruquant::trading::AccountInfo& account);
    const haruquant::trading::AccountInfo& account_info() const { return account_; }
    double order_calc_profit(const std::string& action,
                             const std::string& symbol,
                             double lotsize,
                             double entry_price,
                             double exit_price) const;
    double order_calc_margin(const std::string& action,
                             const std::string& symbol,
                             double lotsize,
                             double entry_price) const;
    std::vector<haruquant::trading::OrderInfo> orders_get(const std::string& symbol = "",
                                                          const std::string& group = "",
                                                          long ticket = 0) const;
    long orders_total() const;
    std::vector<haruquant::trading::PositionInfo> positions_get(const std::string& symbol = "",
                                                                const std::string& group = "",
                                                                long ticket = 0) const;
    long positions_total() const;
    std::vector<haruquant::trading::HistoryOrderInfo> history_orders_get(long date_from,
                                                                         long date_to,
                                                                         const std::string& group = "",
                                                                         long ticket = 0) const;
    std::vector<haruquant::trading::HistoryOrderInfo> history_orders_get(long ticket) const;
    long history_orders_total(long date_from, long date_to) const;
    std::vector<haruquant::trading::DealInfo> history_deals_get(long date_from,
                                                                long date_to,
                                                                const std::string& group = "",
                                                                long ticket = 0) const;
    std::vector<haruquant::trading::DealInfo> history_deals_get(long ticket) const;
    long history_deals_total(long date_from, long date_to) const;

private:
    haruquant::trading::AccountInfo account_{};
};

}  // namespace haruquant::core
