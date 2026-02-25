#pragma once

#include "trading/account_info.hpp"
#include "trading/deal_info.hpp"
#include "trading/history_order_info.hpp"
#include "trading/order_info.hpp"
#include "trading/position_info.hpp"



#include <string>
#include <utility>
#include <vector>


namespace haruquant::core {

struct TradeRequest {
    long action{0};
    long magic{0};
    long order{0};
    std::string symbol{};
    double volume{0.0};
    long type{0};
    double price{0.0};
    double stoplimit{0.0};
    double sl{0.0};
    double tp{0.0};
    long deviation{0};
    long type_filling{0};
    long type_time{0};
    long expiration{0};
    std::string comment{};
    long position{0};
    long position_by{0};
};

struct TradeResult {
    long retcode{10013};
    long deal{0};
    long order{0};
    double volume{0.0};
    double price{0.0};
    double bid{0.0};
    double ask{0.0};
    std::string comment{};
    long retcode_external{0};
    TradeRequest request{};
};

class BacktestSimulator {
public:
    explicit BacktestSimulator();
    explicit BacktestSimulator(const haruquant::trading::AccountInfo& account);
    const haruquant::trading::AccountInfo& account_info() const { return account_; }
    TradeResult order_send(const TradeRequest& request);
    std::pair<int, std::string> last_error() const;
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
    void set_last_error(int code, std::string message);
    haruquant::trading::AccountInfo account_{};
    int last_error_code_{0};
    std::string last_error_message_{"No error"};
};

}  // namespace haruquant::core
