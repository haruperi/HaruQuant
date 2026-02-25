#pragma once

#include "trading/account_info.hpp"



#include <string>


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

private:
    haruquant::trading::AccountInfo account_{};
};

}  // namespace haruquant::core
