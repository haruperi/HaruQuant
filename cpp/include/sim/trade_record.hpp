/**
 * @file trade_record.hpp
 * @brief Trade lifecycle tracker (MAE/MFE/bars/time/R).
 */

#pragma once

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace hqt::sim {

struct TradeRecord {
    uint64_t ticket{0};
    std::string symbol{};
    bool is_buy{true};
    double volume{0.0};
    double open_price{0.0};
    double close_price{0.0};
    double stop_loss{0.0};
    double take_profit{0.0};

    int64_t open_time_msc{0};
    int64_t close_time_msc{0};
    double time_in_trade_seconds{0.0};
    int bars_in_trade{0};

    double initial_risk_usd{0.0};
    double profit_loss{0.0};
    double mae_usd{0.0};
    double mfe_usd{0.0};
    double r_multiple{0.0};
};

class TradeRecordTracker {
public:
    void reset();

    bool has_open(uint64_t ticket) const;
    void on_open(
        uint64_t ticket,
        const std::string& symbol,
        bool is_buy,
        double volume,
        double open_price,
        double sl,
        double tp,
        int64_t open_time_msc,
        double initial_risk_usd);
    void on_update(uint64_t ticket, double profit_usd);
    bool on_close(
        uint64_t ticket,
        int64_t close_time_msc,
        double close_price,
        double profit_loss_usd);

    [[nodiscard]] const std::vector<TradeRecord>& completed_trades() const noexcept;

private:
    struct OpenTradeState {
        TradeRecord record;
        double mfe_usd{0.0};
        double mae_usd{0.0};
    };

    std::unordered_map<uint64_t, OpenTradeState> open_;
    std::vector<TradeRecord> completed_;
};

}  // namespace hqt::sim

