#include "sim/trade_record.hpp"

#include <cmath>

namespace hqt::sim {

void TradeRecordTracker::reset() {
    open_.clear();
    completed_.clear();
}

bool TradeRecordTracker::has_open(uint64_t ticket) const {
    return open_.find(ticket) != open_.end();
}

void TradeRecordTracker::on_open(
    uint64_t ticket,
    const std::string& symbol,
    bool is_buy,
    double volume,
    double open_price,
    double sl,
    double tp,
    int64_t open_time_msc,
    double initial_risk_usd) {
    if (ticket == 0 || has_open(ticket)) {
        return;
    }

    OpenTradeState state;
    state.record.ticket = ticket;
    state.record.symbol = symbol;
    state.record.is_buy = is_buy;
    state.record.volume = volume;
    state.record.open_price = open_price;
    state.record.stop_loss = sl;
    state.record.take_profit = tp;
    state.record.open_time_msc = open_time_msc;
    state.record.initial_risk_usd = initial_risk_usd;
    open_[ticket] = state;
}

void TradeRecordTracker::on_update(uint64_t ticket, double profit_usd) {
    const auto it = open_.find(ticket);
    if (it == open_.end()) {
        return;
    }

    OpenTradeState& state = it->second;
    state.record.bars_in_trade += 1;
    if (profit_usd > state.mfe_usd) {
        state.mfe_usd = profit_usd;
    }
    if (profit_usd < state.mae_usd) {
        state.mae_usd = profit_usd;
    }
}

bool TradeRecordTracker::on_close(
    uint64_t ticket,
    int64_t close_time_msc,
    double close_price,
    double profit_loss_usd) {
    const auto it = open_.find(ticket);
    if (it == open_.end()) {
        return false;
    }

    TradeRecord record = it->second.record;
    record.close_time_msc = close_time_msc;
    record.close_price = close_price;
    record.time_in_trade_seconds = static_cast<double>(record.close_time_msc - record.open_time_msc) / 1000.0;
    record.profit_loss = profit_loss_usd;
    record.mfe_usd = it->second.mfe_usd;
    record.mae_usd = std::abs(it->second.mae_usd);
    if (record.initial_risk_usd > 0.0) {
        record.r_multiple = record.profit_loss / record.initial_risk_usd;
    }

    completed_.push_back(record);
    open_.erase(it);
    return true;
}

const std::vector<TradeRecord>& TradeRecordTracker::completed_trades() const noexcept {
    return completed_;
}

}  // namespace hqt::sim

