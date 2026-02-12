#include "sim/backtest_engine.hpp"

#include <optional>
#include <utility>

namespace hqt::sim {

BacktestEngine::BacktestEngine(SimulatorClient& client)
    : client_(client) {}

void BacktestEngine::set_on_bar_processed(BarProcessedCallback callback) {
    on_bar_processed_ = std::move(callback);
}

void BacktestEngine::run_trading_timeframe(
    const std::string& symbol,
    double volume,
    const std::vector<BacktestBarStep>& bars) {
    state_.reset();
    state_.running = true;
    close_reasons_.clear();
    account_snapshot_ = client_.account_info();

    const SymbolInfoData* info = client_.symbol_info(symbol);
    if (info == nullptr || volume <= 0.0) {
        state_.running = false;
        return;
    }

    for (std::size_t idx = 0; idx < bars.size(); ++idx) {
        const BacktestBarStep& bar = bars[idx];
        state_.current_bar_index = idx;
        state_.current_time_us = bar.time_msc * 1000;

        const double spread_points = (bar.spread_points >= 0.0) ? bar.spread_points : static_cast<double>(info->spread);
        const double bid = bar.close;
        const double ask = bar.close + (spread_points * info->point);

        SymbolTickData tick;
        tick.time = bar.time_msc / 1000;
        tick.time_msc = bar.time_msc;
        tick.bid = bid;
        tick.ask = ask;
        tick.last = bar.close;
        client_.set_symbol_tick(symbol, tick);

        monitor_positions_and_account(symbol, bid, ask);
        apply_exit_signal(symbol, bar.exit_signal);
        apply_entry_signal(symbol, volume, bar.entry_signal, bid, ask, bar.sl, bar.tp);

        ++state_.processed_events;
        if (on_bar_processed_) {
            on_bar_processed_(idx, bar, state_);
        }
    }

    state_.running = false;
}

const SimulatorState& BacktestEngine::state() const noexcept {
    return state_;
}

const AccountInfoData& BacktestEngine::account_snapshot() const noexcept {
    return account_snapshot_;
}

std::optional<AutoCloseReason> BacktestEngine::close_reason(uint64_t ticket) const {
    const auto it = close_reasons_.find(ticket);
    if (it == close_reasons_.end()) {
        return std::nullopt;
    }
    return it->second;
}

void BacktestEngine::monitor_positions_and_account(const std::string& symbol, double bid, double ask) {
    const auto positions = client_.positions_get(std::nullopt, symbol);
    for (const auto& pos : positions) {
        const bool is_buy = (pos.type == 0U);
        const double current_price = is_buy ? bid : ask;
        const bool sl_hit = (pos.sl > 0.0) &&
            (is_buy ? (current_price <= pos.sl) : (current_price >= pos.sl));
        const bool tp_hit = (pos.tp > 0.0) &&
            (is_buy ? (current_price >= pos.tp) : (current_price <= pos.tp));

        if (sl_hit || tp_hit) {
            const TradeResult result = client_.close_position(pos.ticket);
            if (result.retcode == 10009 || result.retcode == 10010) {
                close_reasons_[pos.ticket] = tp_hit ? AutoCloseReason::TakeProfit : AutoCloseReason::StopLoss;
            }
        }
    }

    const PositionTotals totals = account_monitor_.monitor_positions(client_, symbol, bid, ask);
    account_snapshot_ = account_monitor_.monitor_account(client_.account_info(), totals);
}

void BacktestEngine::apply_exit_signal(const std::string& symbol, int exit_signal) {
    if (exit_signal == 0) {
        return;
    }

    const auto positions = client_.positions_get(std::nullopt, symbol);
    for (const auto& pos : positions) {
        const bool is_buy = (pos.type == 0U);
        if ((exit_signal == 1 && is_buy) || (exit_signal == -1 && !is_buy)) {
            (void)client_.close_position(pos.ticket);
        }
    }
}

void BacktestEngine::apply_entry_signal(
    const std::string& symbol,
    double volume,
    int entry_signal,
    double bid,
    double ask,
    double sl,
    double tp) {
    if (entry_signal != 1 && entry_signal != -1) {
        return;
    }

    TradeRequest request;
    request.action = 1;  // TRADE_ACTION_DEAL
    request.type = (entry_signal == 1) ? 0 : 1;  // BUY / SELL
    request.symbol = symbol;
    request.volume = volume;
    request.price = (entry_signal == 1) ? ask : bid;
    request.sl = sl;
    request.tp = tp;

    (void)client_.order_send(request);
}

}  // namespace hqt::sim
