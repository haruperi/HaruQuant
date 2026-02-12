#include "sim/portfolio_engine.hpp"

#include <algorithm>
#include <limits>
#include <cmath>

namespace hqt::sim {

PortfolioEngine::PortfolioEngine(SimulatorClient& client)
    : client_(client) {}

void PortfolioEngine::run_equal_weight(
    const std::vector<PortfolioSymbolInput>& inputs,
    double base_volume) {
    if (inputs.empty()) {
        effective_allocations_.clear();
        return;
    }

    const double w = 1.0 / static_cast<double>(inputs.size());
    std::unordered_map<std::string, double> allocations;
    for (const auto& input : inputs) {
        allocations[input.symbol] = w;
    }
    run_with_allocations(inputs, base_volume, allocations);
}

void PortfolioEngine::run_with_allocations(
    const std::vector<PortfolioSymbolInput>& inputs,
    double base_volume,
    const std::unordered_map<std::string, double>& allocations) {
    effective_allocations_.clear();
    if (inputs.empty() || base_volume <= 0.0) {
        return;
    }

    std::vector<std::size_t> indices(inputs.size(), 0U);
    for (const auto& input : inputs) {
        const auto it = allocations.find(input.symbol);
        effective_allocations_[input.symbol] = (it != allocations.end()) ? it->second : 0.0;
    }

    while (true) {
        int64_t next_time = std::numeric_limits<int64_t>::max();
        bool has_next = false;
        for (std::size_t i = 0; i < inputs.size(); ++i) {
            if (indices[i] >= inputs[i].bars.size()) {
                continue;
            }
            next_time = std::min(next_time, inputs[i].bars[indices[i]].time_msc);
            has_next = true;
        }
        if (!has_next) {
            break;
        }

        for (std::size_t i = 0; i < inputs.size(); ++i) {
            if (indices[i] >= inputs[i].bars.size()) {
                continue;
            }
            const auto& bar = inputs[i].bars[indices[i]];
            if (bar.time_msc != next_time) {
                continue;
            }
            process_bar(inputs[i].symbol, bar, base_volume);
            ++indices[i];
        }
    }
}

const std::unordered_map<std::string, double>& PortfolioEngine::effective_allocations() const noexcept {
    return effective_allocations_;
}

double PortfolioEngine::normalize_volume(double requested, const SymbolInfoData& symbol_info) {
    if (requested <= 0.0) {
        return 0.0;
    }

    const double vol_min = symbol_info.volume_min > 0.0 ? symbol_info.volume_min : 0.01;
    const double vol_step = symbol_info.volume_step > 0.0 ? symbol_info.volume_step : 0.01;
    const double vol_max = symbol_info.volume_max > 0.0 ? symbol_info.volume_max : requested;

    double vol = requested;
    const double steps = std::round((vol - vol_min) / vol_step);
    vol = vol_min + (steps * vol_step);
    vol = std::max(vol, vol_min);
    vol = std::min(vol, vol_max);
    return vol;
}

void PortfolioEngine::process_bar(const std::string& symbol, const BacktestBarStep& bar, double base_volume) {
    const auto* symbol_info = client_.symbol_info(symbol);
    if (symbol_info == nullptr) {
        return;
    }

    const double spread_points = (bar.spread_points >= 0.0) ? bar.spread_points : static_cast<double>(symbol_info->spread);
    const double bid = bar.close;
    const double ask = bar.close + (spread_points * symbol_info->point);

    SymbolTickData tick;
    tick.time = bar.time_msc / 1000;
    tick.time_msc = bar.time_msc;
    tick.bid = bid;
    tick.ask = ask;
    tick.last = bar.close;
    client_.set_symbol_tick(symbol, tick);

    if (bar.exit_signal != 0) {
        const auto positions = client_.positions_get(std::nullopt, symbol);
        for (const auto& pos : positions) {
            const bool is_buy = (pos.type == 0U);
            if ((bar.exit_signal == 1 && is_buy) || (bar.exit_signal == -1 && !is_buy)) {
                (void)client_.close_position(pos.ticket);
            }
        }
    }

    if (bar.entry_signal != 1 && bar.entry_signal != -1) {
        return;
    }

    const double alloc = effective_allocations_.count(symbol) > 0 ? effective_allocations_[symbol] : 0.0;
    const double requested = base_volume * alloc;
    const double volume = normalize_volume(requested, *symbol_info);
    if (volume <= 0.0) {
        return;
    }

    TradeRequest request;
    request.action = 1;  // TRADE_ACTION_DEAL
    request.type = (bar.entry_signal == 1) ? 0 : 1;
    request.symbol = symbol;
    request.volume = volume;
    request.price = (bar.entry_signal == 1) ? ask : bid;
    request.sl = bar.sl;
    request.tp = bar.tp;
    (void)client_.order_send(request);
}

}  // namespace hqt::sim
