#include "engine/engine.hpp"
#include "util/logger.hpp"

#include <cmath>
#include <optional>
#include <string>
#include <utility>

namespace hqt::sim {

BacktestEngine::BacktestEngine(SimulatorClient& client)
    : client_(client) {}

void BacktestEngine::set_on_bar_processed(BarProcessedCallback callback) {
    on_bar_processed_ = std::move(callback);
}

void BacktestEngine::set_on_tick_processed(TickProcessedCallback callback) {
    on_tick_processed_ = std::move(callback);
}

void BacktestEngine::set_on_trade_event(TradeEventCallback callback) {
    on_trade_event_ = std::move(callback);
}

void BacktestEngine::run_trading_timeframe(
    const std::string& symbol,
    double volume,
    const std::vector<BacktestBarStep>& bars) {
    state_.reset();
    state_.running = true;
    close_reasons_.clear();
    trade_record_tracker_.reset();
    account_snapshot_ = client_.account_info();

    const SymbolInfoData* info = client_.symbol_info(symbol);
    if (info == nullptr || volume <= 0.0) {
        util::warning("BacktestEngine::run_trading_timeframe invalid start state "
                      "symbol=" + symbol + " volume=" + std::to_string(volume));
        state_.running = false;
        return;
    }

    util::info("BacktestEngine::run_trading_timeframe start symbol=" + symbol +
               " bars=" + std::to_string(bars.size()));

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

        if (on_tick_processed_) {
            on_tick_processed_(ModelTick{bar.time_msc, bid, ask, bar.close}, state_);
        }

        monitor_pending_orders(symbol, bid, ask, bar.time_msc);
        monitor_positions_and_account(symbol, bid, ask);
        apply_exit_signal(symbol, bar.exit_signal);
        apply_entry_signal(symbol, volume, bar.entry_signal, bid, ask, bar.sl, bar.tp);

        ++state_.processed_events;
        if (on_bar_processed_) {
            on_bar_processed_(idx, bar, state_);
        }
    }

    state_.running = false;
    util::info("BacktestEngine::run_trading_timeframe finish processed_events=" +
               std::to_string(state_.processed_events));
}

void BacktestEngine::run_trading_timeframe_with_ticks(
    const std::string& symbol,
    double volume,
    const std::vector<BacktestBarStep>& bars,
    const std::vector<ModelTick>& ticks) {
    state_.reset();
    state_.running = true;
    close_reasons_.clear();
    trade_record_tracker_.reset();
    account_snapshot_ = client_.account_info();

    if (client_.symbol_info(symbol) == nullptr || volume <= 0.0 || bars.empty() || ticks.empty()) {
        util::warning("BacktestEngine::run_trading_timeframe_with_ticks invalid start state "
                      "symbol=" + symbol +
                      " volume=" + std::to_string(volume) +
                      " bars=" + std::to_string(bars.size()) +
                      " ticks=" + std::to_string(ticks.size()));
        state_.running = false;
        return;
    }

    util::info("BacktestEngine::run_trading_timeframe_with_ticks start symbol=" + symbol +
               " bars=" + std::to_string(bars.size()) +
               " ticks=" + std::to_string(ticks.size()));

    std::size_t next_bar_idx = 0;
    for (const auto& tick_model : ticks) {
        state_.current_time_us = tick_model.time_msc * 1000;

        SymbolTickData tick;
        tick.time = tick_model.time_msc / 1000;
        tick.time_msc = tick_model.time_msc;
        tick.bid = tick_model.bid;
        tick.ask = tick_model.ask;
        tick.last = tick_model.last;
        client_.set_symbol_tick(symbol, tick);

        if (on_tick_processed_) {
            on_tick_processed_(tick_model, state_);
        }

        monitor_pending_orders(symbol, tick.bid, tick.ask, tick.time_msc);
        monitor_positions_and_account(symbol, tick.bid, tick.ask);

        while (next_bar_idx < bars.size() && tick.time_msc >= bars[next_bar_idx].time_msc) {
            const BacktestBarStep& bar = bars[next_bar_idx];
            state_.current_bar_index = next_bar_idx;
            state_.current_time_us = bar.time_msc * 1000;

            apply_exit_signal(symbol, bar.exit_signal);
            apply_entry_signal(symbol, volume, bar.entry_signal, tick.bid, tick.ask, bar.sl, bar.tp);

            ++state_.processed_events;
            if (on_bar_processed_) {
                on_bar_processed_(next_bar_idx, bar, state_);
            }
            ++next_bar_idx;
        }
    }

    state_.running = false;
    util::info("BacktestEngine::run_trading_timeframe_with_ticks finish processed_events=" +
               std::to_string(state_.processed_events));
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

const std::vector<TradeRecord>& BacktestEngine::completed_trades() const noexcept {
    return trade_record_tracker_.completed_trades();
}

void BacktestEngine::ensure_trade_record_for_position(const TradeRecordData& pos, int64_t now_msc) {
    if (trade_record_tracker_.has_open(pos.ticket)) {
        return;
    }

    const bool is_buy = (pos.type == 0U);
    const int action = is_buy ? 0 : 1;
    double initial_risk_usd = 0.0;
    if (pos.sl > 0.0) {
        initial_risk_usd = std::abs(client_.order_calc_profit(
            action,
            pos.symbol,
            pos.volume,
            pos.price_open,
            pos.sl));
    }

    trade_record_tracker_.on_open(
        pos.ticket,
        pos.symbol,
        is_buy,
        pos.volume,
        pos.price_open,
        pos.sl,
        pos.tp,
        now_msc,
        initial_risk_usd);
}

void BacktestEngine::close_position_and_track(const TradeRecordData& pos, int64_t now_msc, double close_price) {
    const TradeResult result = client_.close_position(pos.ticket);
    if (!(result.retcode == 10009 || result.retcode == 10010)) {
        util::warning("BacktestEngine::close_position_and_track failed ticket=" +
                      std::to_string(pos.ticket) + " retcode=" + std::to_string(result.retcode));
        return;
    }

    const double pnl = lookup_deal_profit_or_fallback(result.deal, pos, close_price);
    (void)trade_record_tracker_.on_close(pos.ticket, now_msc, close_price, pnl);

    if (on_trade_event_) {
        BacktestTradeEvent evt;
        evt.event_type = "close";
        evt.trade = pos;
        evt.trade.time_msc = now_msc;
        evt.trade.price_current = close_price;
        evt.trade.profit = pnl;
        on_trade_event_(evt, state_);
    }
}

double BacktestEngine::lookup_deal_profit_or_fallback(
    uint64_t deal_ticket,
    const TradeRecordData& pos,
    double close_price) const {
    if (deal_ticket > 0) {
        const auto deals = client_.history_deals_get(deal_ticket);
        if (!deals.empty()) {
            return deals.front().profit;
        }
    }

    const bool is_buy = (pos.type == 0U);
    const int action = is_buy ? 0 : 1;
    return client_.order_calc_profit(action, pos.symbol, pos.volume, pos.price_open, close_price);
}

void BacktestEngine::monitor_pending_orders(
    const std::string& symbol,
    double bid,
    double ask,
    int64_t current_time_msc) {
    const auto orders = client_.orders_get(std::nullopt, symbol);
    for (const auto& order : orders) {
        const bool expires = (order.type_time == 2U || order.type_time == 3U) &&
            (order.expiration > 0) &&
            ((current_time_msc / 1000) >= order.expiration);

        if (expires) {
            TradeRequest remove;
            remove.action = 8;  // TRADE_ACTION_REMOVE
            remove.order = order.ticket;
            const TradeResult result = client_.order_send(remove);
            if (result.retcode == 10009 || result.retcode == 10010) {
                client_.set_history_order_state(order.ticket, 6U);  // ORDER_STATE_EXPIRED
                client_.set_history_order_done_time(order.ticket, current_time_msc / 1000, current_time_msc);
            }
            continue;
        }

        if (!should_trigger_order(order, bid, ask)) {
            continue;
        }

        TradeRequest deal;
        deal.action = 1;  // TRADE_ACTION_DEAL
        deal.symbol = symbol;
        deal.volume = order.volume;
        deal.sl = order.sl;
        deal.tp = order.tp;
        deal.comment = order.comment;

        if (order.type == 2U || order.type == 4U || order.type == 6U) {
            deal.type = 0;      // ORDER_TYPE_BUY
            deal.price = ask;
        } else if (order.type == 3U || order.type == 5U || order.type == 7U) {
            deal.type = 1;      // ORDER_TYPE_SELL
            deal.price = bid;
        } else {
            continue;
        }

        const TradeResult fill = client_.order_send(deal);
        if (!(fill.retcode == 10009 || fill.retcode == 10010)) {
            continue;
        }

        if (fill.order > 0) {
            const auto opened = client_.positions_get(fill.order);
            if (!opened.empty()) {
                ensure_trade_record_for_position(opened.front(), current_time_msc);
            }
        }

        TradeRequest remove;
        remove.action = 8;  // TRADE_ACTION_REMOVE
        remove.order = order.ticket;
        const TradeResult removed = client_.order_send(remove);
        if (removed.retcode == 10009 || removed.retcode == 10010) {
            client_.set_history_order_state(order.ticket, 4U);  // ORDER_STATE_FILLED
            client_.set_history_order_done_time(order.ticket, current_time_msc / 1000, current_time_msc);
        }
    }
}

void BacktestEngine::monitor_positions_and_account(const std::string& symbol, double bid, double ask) {
    const auto positions = client_.positions_get(std::nullopt, symbol);
    for (const auto& pos : positions) {
        const bool is_buy = (pos.type == 0U);
        const double current_price = is_buy ? bid : ask;
        ensure_trade_record_for_position(pos, state_.current_time_us / 1000);
        const double pnl = client_.order_calc_profit(
            is_buy ? 0 : 1,
            symbol,
            pos.volume,
            pos.price_open,
            current_price);
        trade_record_tracker_.on_update(pos.ticket, pnl);

        const bool sl_hit = (pos.sl > 0.0) &&
            (is_buy ? (current_price <= pos.sl) : (current_price >= pos.sl));
        const bool tp_hit = (pos.tp > 0.0) &&
            (is_buy ? (current_price >= pos.tp) : (current_price <= pos.tp));

        if (sl_hit || tp_hit) {
            close_position_and_track(pos, state_.current_time_us / 1000, current_price);
            close_reasons_[pos.ticket] = tp_hit ? AutoCloseReason::TakeProfit : AutoCloseReason::StopLoss;
        }
    }

    const PositionTotals totals = account_monitor_.monitor_positions(client_, symbol, bid, ask);
    account_snapshot_ = account_monitor_.monitor_account(client_.account_info(), totals);
}

bool BacktestEngine::should_trigger_order(const TradeRecordData& order, double bid, double ask) {
    switch (order.type) {
        case 2U: return ask <= order.price_open;  // BUY_LIMIT
        case 3U: return bid >= order.price_open;  // SELL_LIMIT
        case 4U: return ask >= order.price_open;  // BUY_STOP
        case 5U: return bid <= order.price_open;  // SELL_STOP
        case 6U: return ask >= order.price_open;  // BUY_STOP_LIMIT
        case 7U: return bid <= order.price_open;  // SELL_STOP_LIMIT
        default: return false;
    }
}

void BacktestEngine::apply_exit_signal(const std::string& symbol, int exit_signal) {
    if (exit_signal == 0) {
        return;
    }

    const auto positions = client_.positions_get(std::nullopt, symbol);
    const auto* tick = client_.symbol_info_tick(symbol);
    if (tick == nullptr) {
        return;
    }

    for (const auto& pos : positions) {
        const bool is_buy = (pos.type == 0U);
        if ((exit_signal == 1 && is_buy) || (exit_signal == -1 && !is_buy)) {
            const double close_price = is_buy ? tick->bid : tick->ask;
            util::debug("BacktestEngine::apply_exit_signal closing ticket=" + std::to_string(pos.ticket));
            close_position_and_track(pos, state_.current_time_us / 1000, close_price);
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

    const TradeResult result = client_.order_send(request);
    if (!(result.retcode == 10009 || result.retcode == 10010) || result.order == 0) {
        util::warning("BacktestEngine::apply_entry_signal order_send failed retcode=" +
                      std::to_string(result.retcode));
        return;
    }

    const auto opened = client_.positions_get(result.order);
    if (opened.empty()) {
        util::warning("BacktestEngine::apply_entry_signal no opened position for order=" +
                      std::to_string(result.order));
        return;
    }
    util::debug("BacktestEngine::apply_entry_signal opened order=" + std::to_string(result.order));
    ensure_trade_record_for_position(opened.front(), state_.current_time_us / 1000);
    if (on_trade_event_) {
        BacktestTradeEvent evt;
        evt.event_type = "open";
        evt.trade = opened.front();
        evt.trade.time_msc = state_.current_time_us / 1000;
        on_trade_event_(evt, state_);
    }
}

}  // namespace hqt::sim

namespace hqt::engine {

Engine::Engine(hqt::sim::SimulatorClient& client)
    : impl_(client) {}

void Engine::run_trading_timeframe(
    const std::string& symbol,
    double volume,
    const std::vector<hqt::sim::BacktestBarStep>& bars) {
    impl_.run_trading_timeframe(symbol, volume, bars);
}

void Engine::run_trading_timeframe_with_ticks(
    const std::string& symbol,
    double volume,
    const std::vector<hqt::sim::BacktestBarStep>& bars,
    const std::vector<hqt::sim::ModelTick>& ticks) {
    impl_.run_trading_timeframe_with_ticks(symbol, volume, bars, ticks);
}

const hqt::sim::SimulatorState& Engine::state() const noexcept {
    return impl_.state();
}

const hqt::sim::AccountInfoData& Engine::account_snapshot() const noexcept {
    return impl_.account_snapshot();
}

const std::vector<hqt::sim::TradeRecord>& Engine::completed_trades() const noexcept {
    return impl_.completed_trades();
}

}  // namespace hqt::engine
