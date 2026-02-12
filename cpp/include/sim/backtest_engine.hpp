/**
 * @file backtest_engine.hpp
 * @brief Minimal single-symbol trading_timeframe backtest loop.
 */

#pragma once

#include "sim/account_monitor.hpp"
#include "sim/simulator_client.hpp"
#include "sim/simulator_state.hpp"
#include "sim/tick_model.hpp"
#include "sim/trade_record.hpp"

#include <cstddef>
#include <cstdint>
#include <functional>
#include <optional>
#include <string>
#include <unordered_map>
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
    double sl{0.0};
    double tp{0.0};
};

enum class AutoCloseReason {
    StopLoss = 1,
    TakeProfit = 2,
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
    void run_trading_timeframe_with_ticks(
        const std::string& symbol,
        double volume,
        const std::vector<BacktestBarStep>& bars,
        const std::vector<ModelTick>& ticks);

    [[nodiscard]] const SimulatorState& state() const noexcept;
    [[nodiscard]] const AccountInfoData& account_snapshot() const noexcept;
    [[nodiscard]] std::optional<AutoCloseReason> close_reason(uint64_t ticket) const;
    [[nodiscard]] const std::vector<TradeRecord>& completed_trades() const noexcept;

private:
    void ensure_trade_record_for_position(const TradeRecordData& pos, int64_t now_msc);
    void close_position_and_track(const TradeRecordData& pos, int64_t now_msc, double close_price);
    double lookup_deal_profit_or_fallback(uint64_t deal_ticket, const TradeRecordData& pos, double close_price) const;
    void monitor_pending_orders(const std::string& symbol, double bid, double ask, int64_t current_time_msc);
    void monitor_positions_and_account(const std::string& symbol, double bid, double ask);
    static bool should_trigger_order(const TradeRecordData& order, double bid, double ask);
    void apply_exit_signal(const std::string& symbol, int exit_signal);
    void apply_entry_signal(
        const std::string& symbol,
        double volume,
        int entry_signal,
        double bid,
        double ask,
        double sl,
        double tp);

    SimulatorClient& client_;
    SimulatorState state_{};
    AccountMonitor account_monitor_{};
    TradeRecordTracker trade_record_tracker_{};
    AccountInfoData account_snapshot_{};
    std::unordered_map<uint64_t, AutoCloseReason> close_reasons_{};
    BarProcessedCallback on_bar_processed_{};
};

}  // namespace hqt::sim
