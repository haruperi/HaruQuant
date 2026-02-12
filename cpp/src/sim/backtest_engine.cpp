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

        apply_exit_signal(symbol, bar.exit_signal);
        apply_entry_signal(symbol, volume, bar.entry_signal, bid, ask);

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
    double ask) {
    if (entry_signal != 1 && entry_signal != -1) {
        return;
    }

    TradeRequest request;
    request.action = 1;  // TRADE_ACTION_DEAL
    request.type = (entry_signal == 1) ? 0 : 1;  // BUY / SELL
    request.symbol = symbol;
    request.volume = volume;
    request.price = (entry_signal == 1) ? ask : bid;

    (void)client_.order_send(request);
}

}  // namespace hqt::sim
