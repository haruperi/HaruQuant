/**
 * @file analytics.cpp
 * @brief Unified engine analytics compilation unit.
 */

#include "engine/engine.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <unordered_set>

namespace hqt::sim {

PortfolioState::PortfolioState(double initial_balance, std::string currency) {
    reset(initial_balance, currency);
}

void PortfolioState::reset(double initial_balance, const std::string& currency) {
    std::lock_guard<std::mutex> lock(mutex_);
    account_ = AccountInfoData{};
    account_.currency = currency;
    account_.balance = initial_balance;
    account_.credit = 0.0;
    account_.profit = 0.0;
    account_.equity = initial_balance;
    account_.margin = 0.0;
    account_.margin_free = initial_balance;
    account_.margin_level = 0.0;
    account_.commission_blocked = 0.0;
    total_realized_pnl_ = 0.0;
    strategy_symbol_positions_.clear();
    symbol_positions_.clear();
}

void PortfolioState::set_capital(double balance, double credit) {
    std::lock_guard<std::mutex> lock(mutex_);
    account_.balance = balance;
    account_.credit = credit;
    recompute_unlocked();
}

void PortfolioState::upsert_position(
    const std::string& strategy_id,
    const std::string& symbol,
    double net_volume,
    double margin,
    double unrealized_pnl) {
    if (strategy_id.empty() || symbol.empty()) {
        return;
    }

    std::lock_guard<std::mutex> lock(mutex_);
    PositionAggregate aggregate;
    aggregate.net_volume = net_volume;
    aggregate.long_volume = std::max(net_volume, 0.0);
    aggregate.short_volume = std::max(-net_volume, 0.0);
    aggregate.margin = std::max(margin, 0.0);
    aggregate.unrealized_pnl = unrealized_pnl;
    aggregate.realized_pnl = strategy_symbol_positions_[strategy_id][symbol].realized_pnl;
    strategy_symbol_positions_[strategy_id][symbol] = aggregate;
    recompute_unlocked();
}

void PortfolioState::clear_position(const std::string& strategy_id, const std::string& symbol) {
    if (strategy_id.empty() || symbol.empty()) {
        return;
    }

    std::lock_guard<std::mutex> lock(mutex_);
    const auto strategy_it = strategy_symbol_positions_.find(strategy_id);
    if (strategy_it == strategy_symbol_positions_.end()) {
        return;
    }
    strategy_it->second.erase(symbol);
    if (strategy_it->second.empty()) {
        strategy_symbol_positions_.erase(strategy_it);
    }
    recompute_unlocked();
}

void PortfolioState::apply_realized_pnl(
    const std::string& strategy_id,
    const std::string& symbol,
    double realized_pnl,
    double commission,
    double swap) {
    if (strategy_id.empty() || symbol.empty()) {
        return;
    }

    std::lock_guard<std::mutex> lock(mutex_);
    const double net_realized = realized_pnl - commission + swap;
    total_realized_pnl_ += net_realized;
    account_.balance += net_realized;
    strategy_symbol_positions_[strategy_id][symbol].realized_pnl += net_realized;
    recompute_unlocked();
}

AccountInfoData PortfolioState::account_snapshot() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return account_;
}

double PortfolioState::total_realized_pnl() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return total_realized_pnl_;
}

double PortfolioState::total_unrealized_pnl() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return account_.profit;
}

std::unordered_map<std::string, PositionAggregate> PortfolioState::positions_by_symbol() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return symbol_positions_;
}

std::unordered_map<std::string, PositionAggregate> PortfolioState::positions_by_strategy(
    const std::string& strategy_id) const {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto it = strategy_symbol_positions_.find(strategy_id);
    if (it == strategy_symbol_positions_.end()) {
        return {};
    }
    return it->second;
}

void PortfolioState::recompute_unlocked() {
    symbol_positions_.clear();

    double total_margin = 0.0;
    double total_unrealized = 0.0;

    for (const auto& [_, symbol_map] : strategy_symbol_positions_) {
        for (const auto& [symbol, aggregate] : symbol_map) {
            auto& target = symbol_positions_[symbol];
            target.net_volume += aggregate.net_volume;
            target.long_volume += aggregate.long_volume;
            target.short_volume += aggregate.short_volume;
            target.margin += aggregate.margin;
            target.realized_pnl += aggregate.realized_pnl;
            target.unrealized_pnl += aggregate.unrealized_pnl;
        }
    }

    for (const auto& [_, aggregate] : symbol_positions_) {
        total_margin += aggregate.margin;
        total_unrealized += aggregate.unrealized_pnl;
    }

    account_.profit = total_unrealized;
    account_.margin = total_margin;
    account_.equity = account_.balance + account_.credit + total_unrealized;
    account_.margin_free = account_.equity - total_margin;
    account_.margin_level = (total_margin > 0.0) ? ((account_.equity / total_margin) * 100.0) : 0.0;
}

PositionBook::PositionBook(PositionMode mode)
    : mode_(mode) {}

void PositionBook::set_mode(PositionMode mode) {
    std::lock_guard<std::mutex> lock(mutex_);
    mode_ = mode;
}

PositionMode PositionBook::mode() const noexcept {
    return mode_;
}

void PositionBook::reset() {
    std::lock_guard<std::mutex> lock(mutex_);
    net_positions_.clear();
    hedged_legs_.clear();
    next_leg_id_ = 1;
    account_ = AccountInfoData{};
}

void PositionBook::apply_fill(const FillEvent& fill) {
    if (fill.symbol.empty() || fill.volume <= 0.0 || fill.price <= 0.0) {
        return;
    }
    std::lock_guard<std::mutex> lock(mutex_);
    if (mode_ == PositionMode::Netting) {
        apply_fill_netting_unlocked(fill);
    } else {
        apply_fill_hedging_unlocked(fill);
    }
    account_.balance -= fill.commission;
    account_.balance += fill.swap;
}

void PositionBook::apply_account_snapshot(const AccountInfoData& account) {
    std::lock_guard<std::mutex> lock(mutex_);
    account_ = account;
}

std::unordered_map<std::string, PositionAggregate> PositionBook::snapshot_positions() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return snapshot_positions_unlocked();
}

AccountInfoData PositionBook::snapshot_account() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return account_;
}

std::vector<PositionLeg> PositionBook::legs_for_symbol(const std::string& symbol) const {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto it = hedged_legs_.find(symbol);
    if (it == hedged_legs_.end()) {
        return {};
    }
    return it->second;
}

ReconciliationReport PositionBook::reconcile_with_broker(
    const std::unordered_map<std::string, PositionAggregate>& broker_positions,
    const AccountInfoData& broker_account,
    const std::string& trigger) const {
    std::lock_guard<std::mutex> lock(mutex_);
    ReconciliationReport report;
    report.trigger = trigger;

    const auto local_positions = snapshot_positions_unlocked();
    std::unordered_set<std::string> symbols;
    symbols.reserve(local_positions.size() + broker_positions.size());
    for (const auto& [symbol, _] : local_positions) {
        symbols.insert(symbol);
    }
    for (const auto& [symbol, _] : broker_positions) {
        symbols.insert(symbol);
    }

    for (const auto& symbol : symbols) {
        const auto local_it = local_positions.find(symbol);
        const auto broker_it = broker_positions.find(symbol);
        const PositionAggregate local = (local_it != local_positions.end()) ? local_it->second : PositionAggregate{};
        const PositionAggregate broker = (broker_it != broker_positions.end()) ? broker_it->second : PositionAggregate{};

        if (!almost_equal(local.net_volume, broker.net_volume)) {
            ++report.position_mismatch_count;
            report.issues.push_back("position.net_volume mismatch symbol=" + symbol);
        }
        if (!almost_equal(local.long_volume, broker.long_volume)) {
            ++report.position_mismatch_count;
            report.issues.push_back("position.long_volume mismatch symbol=" + symbol);
        }
        if (!almost_equal(local.short_volume, broker.short_volume)) {
            ++report.position_mismatch_count;
            report.issues.push_back("position.short_volume mismatch symbol=" + symbol);
        }
    }

    if (!almost_equal(account_.balance, broker_account.balance)) {
        ++report.account_mismatch_count;
        report.issues.push_back("account.balance mismatch");
    }
    if (!almost_equal(account_.equity, broker_account.equity)) {
        ++report.account_mismatch_count;
        report.issues.push_back("account.equity mismatch");
    }
    if (!almost_equal(account_.margin, broker_account.margin)) {
        ++report.account_mismatch_count;
        report.issues.push_back("account.margin mismatch");
    }

    report.ok = (report.position_mismatch_count == 0 && report.account_mismatch_count == 0);
    return report;
}

ReconciliationReport PositionBook::periodic_reconcile(
    const std::unordered_map<std::string, PositionAggregate>& broker_positions,
    const AccountInfoData& broker_account) const {
    return reconcile_with_broker(broker_positions, broker_account, "periodic");
}

ReconciliationReport PositionBook::reconnect_reconcile(
    const std::unordered_map<std::string, PositionAggregate>& broker_positions,
    const AccountInfoData& broker_account) const {
    return reconcile_with_broker(broker_positions, broker_account, "reconnect");
}

bool PositionBook::almost_equal(double lhs, double rhs, double eps) noexcept {
    return std::abs(lhs - rhs) <= eps;
}

void PositionBook::apply_fill_netting_unlocked(const FillEvent& fill) {
    auto& agg = net_positions_[fill.symbol];
    const double delta = fill.is_buy ? fill.volume : -fill.volume;
    const double current = agg.net_volume;

    if (almost_equal(current, 0.0)) {
        agg.net_volume = delta;
    } else if ((current > 0.0 && delta > 0.0) || (current < 0.0 && delta < 0.0)) {
        agg.net_volume = current + delta;
    } else if (std::abs(delta) < std::abs(current)) {
        agg.net_volume = current + delta;
    } else if (almost_equal(std::abs(delta), std::abs(current))) {
        agg.net_volume = 0.0;
    } else {
        agg.net_volume = current + delta;
    }
    agg.long_volume = std::max(agg.net_volume, 0.0);
    agg.short_volume = std::max(-agg.net_volume, 0.0);
}

void PositionBook::apply_fill_hedging_unlocked(const FillEvent& fill) {
    auto& legs = hedged_legs_[fill.symbol];
    PositionLeg leg;
    leg.leg_id = next_leg_id_++;
    leg.is_buy = fill.is_buy;
    leg.volume = fill.volume;
    leg.price = fill.price;
    leg.time_msc = fill.time_msc;
    legs.push_back(leg);
}

std::unordered_map<std::string, PositionAggregate> PositionBook::snapshot_positions_unlocked() const {
    if (mode_ == PositionMode::Netting) {
        return net_positions_;
    }

    std::unordered_map<std::string, PositionAggregate> out;
    out.reserve(hedged_legs_.size());
    for (const auto& [symbol, legs] : hedged_legs_) {
        auto& agg = out[symbol];
        for (const auto& leg : legs) {
            if (leg.is_buy) {
                agg.long_volume += leg.volume;
                agg.net_volume += leg.volume;
            } else {
                agg.short_volume += leg.volume;
                agg.net_volume -= leg.volume;
            }
        }
    }
    return out;
}

std::vector<ModelTick> TickModel::generate_m1_ohlc(
    const std::vector<TickModelBar>& bars,
    double point,
    double spread_default_points) {
    std::vector<ModelTick> out;
    out.reserve(bars.size() * 4);

    for (const auto& bar : bars) {
        const double spread_points = (bar.spread_points >= 0.0) ? bar.spread_points : spread_default_points;
        const bool bullish = bar.close >= bar.open;

        const double p0 = bar.open;
        const double p1 = bullish ? bar.low : bar.high;
        const double p2 = bullish ? bar.high : bar.low;
        const double p3 = bar.close;
        const double prices[4]{p0, p1, p2, p3};

        for (int i = 0; i < 4; ++i) {
            const double bid = prices[i];
            out.push_back(ModelTick{
                bar.time_msc + i,
                bid,
                bid + (spread_points * point),
                bid,
            });
        }
    }

    return out;
}

std::vector<ModelTick> TickModel::generate_synthetic_ticks(
    const std::vector<TickModelBar>& bars,
    double point,
    double spread_default_points,
    int support_points) {
    std::vector<ModelTick> out;
    const int clamped_support = std::max(0, support_points);

    for (const auto& bar : bars) {
        const double spread_points = (bar.spread_points >= 0.0) ? bar.spread_points : spread_default_points;
        const bool bullish = bar.close >= bar.open;

        const double p0 = bar.open;
        const double p1 = bullish ? bar.low : bar.high;
        const double p2 = bullish ? bar.high : bar.low;
        const double p3 = bar.close;

        const std::vector<double> s01 = support_point_split(p0, p1, clamped_support);
        const std::vector<double> s12 = support_point_split(p1, p2, clamped_support);
        const std::vector<double> s23 = support_point_split(p2, p3, clamped_support);

        int64_t offset = 0;
        const auto append_prices = [&](const std::vector<double>& prices, bool skip_first) {
            const std::size_t begin = skip_first ? 1U : 0U;
            for (std::size_t i = begin; i < prices.size(); ++i) {
                const double bid = prices[i];
                out.push_back(ModelTick{
                    bar.time_msc + offset,
                    bid,
                    bid + (spread_points * point),
                    bid,
                });
                ++offset;
            }
        };

        append_prices(s01, false);
        append_prices(s12, true);
        append_prices(s23, true);
    }

    return out;
}

std::vector<ModelTick> TickModel::passthrough_real_ticks(const std::vector<ModelTick>& ticks) {
    return ticks;
}

std::vector<double> TickModel::support_point_split(
    double start,
    double end,
    int support_points) {
    std::vector<double> out;
    const int points = std::max(0, support_points);
    out.reserve(static_cast<std::size_t>(points + 2));
    out.push_back(start);

    const double step = (end - start) / static_cast<double>(points + 1);
    for (int i = 1; i <= points; ++i) {
        out.push_back(start + (step * static_cast<double>(i)));
    }
    out.push_back(end);
    return out;
}

namespace {

double population_stddev(const std::vector<double>& values, double mean) {
    if (values.empty()) {
        return 0.0;
    }
    double accum = 0.0;
    for (const double v : values) {
        const double d = v - mean;
        accum += d * d;
    }
    return std::sqrt(accum / static_cast<double>(values.size()));
}

}  // namespace

ResultMetricsSummary ResultMetrics::from_trades(
    const std::vector<TradeRecord>& trades,
    double initial_balance,
    double final_balance) {
    ResultMetricsSummary out;
    out.initial_balance = initial_balance;
    out.final_balance = final_balance;
    out.total_return = out.final_balance - out.initial_balance;
    out.total_return_pct = (out.initial_balance > 0.0)
        ? ((out.total_return / out.initial_balance) * 100.0)
        : 0.0;

    if (trades.empty()) {
        return out;
    }

    out.total_trades = trades.size();
    std::vector<double> trade_returns;
    trade_returns.reserve(trades.size());

    std::vector<double> equity_curve;
    equity_curve.reserve(trades.size() + 1);
    equity_curve.push_back(initial_balance);
    double running_balance = initial_balance;

    for (const auto& t : trades) {
        if (t.profit_loss > 0.0) {
            ++out.winning_trades;
            out.gross_profit += t.profit_loss;
        } else if (t.profit_loss < 0.0) {
            ++out.losing_trades;
            out.gross_loss += -t.profit_loss;
        } else {
            ++out.breakeven_trades;
        }

        if (initial_balance > 0.0) {
            trade_returns.push_back(t.profit_loss / initial_balance);
        } else {
            trade_returns.push_back(0.0);
        }

        running_balance += t.profit_loss;
        equity_curve.push_back(running_balance);
    }

    out.win_rate = (out.total_trades > 0)
        ? (static_cast<double>(out.winning_trades) / static_cast<double>(out.total_trades) * 100.0)
        : 0.0;

    if (out.gross_loss > 0.0) {
        out.profit_factor = out.gross_profit / out.gross_loss;
    } else {
        out.profit_factor = std::numeric_limits<double>::infinity();
    }

    double peak = equity_curve.front();
    for (const double equity : equity_curve) {
        if (equity > peak) {
            peak = equity;
        }
        const double dd_abs = peak - equity;
        const double dd_pct = (peak > 0.0) ? ((dd_abs / peak) * 100.0) : 0.0;
        if (dd_abs > out.max_drawdown) {
            out.max_drawdown = dd_abs;
        }
        if (dd_pct > out.max_drawdown_pct) {
            out.max_drawdown_pct = dd_pct;
        }
    }

    if (trade_returns.size() > 1U) {
        double mean = 0.0;
        for (const double r : trade_returns) {
            mean += r;
        }
        mean /= static_cast<double>(trade_returns.size());

        const double stdev = population_stddev(trade_returns, mean);
        out.sharpe_ratio = (stdev > 0.0)
            ? ((mean / stdev) * std::sqrt(252.0))
            : 0.0;
    }

    return out;
}

std::unordered_map<std::string, double> PortfolioAllocator::equal_weight(
    const std::vector<std::string>& symbols,
    double max_total_exposure) {
    if (symbols.empty() || max_total_exposure <= 0.0) {
        return {};
    }
    const double w = max_total_exposure / static_cast<double>(symbols.size());
    std::unordered_map<std::string, double> out;
    out.reserve(symbols.size());
    for (const auto& symbol : symbols) {
        out[symbol] = w;
    }
    return out;
}

std::unordered_map<std::string, double> PortfolioAllocator::risk_parity(
    const std::unordered_map<std::string, double>& symbol_volatility,
    double max_total_exposure) {
    if (symbol_volatility.empty() || max_total_exposure <= 0.0) {
        return {};
    }

    std::unordered_map<std::string, double> inverse_vol;
    inverse_vol.reserve(symbol_volatility.size());
    double total_inverse = 0.0;
    for (const auto& [symbol, vol] : symbol_volatility) {
        const double inv = vol > 0.0 ? (1.0 / vol) : 0.0;
        inverse_vol[symbol] = inv;
        total_inverse += inv;
    }

    if (total_inverse <= 0.0) {
        std::vector<std::string> symbols;
        symbols.reserve(symbol_volatility.size());
        for (const auto& [symbol, _] : symbol_volatility) {
            symbols.push_back(symbol);
        }
        return equal_weight(symbols, max_total_exposure);
    }

    std::unordered_map<std::string, double> out;
    out.reserve(inverse_vol.size());
    for (const auto& [symbol, inv] : inverse_vol) {
        out[symbol] = (inv / total_inverse) * max_total_exposure;
    }
    return out;
}

std::unordered_map<std::string, double> PortfolioAllocator::custom(
    const std::unordered_map<std::string, double>& raw_weights,
    double max_total_exposure,
    bool normalize) {
    if (raw_weights.empty() || max_total_exposure <= 0.0) {
        return {};
    }

    std::unordered_map<std::string, double> out;
    out.reserve(raw_weights.size());
    for (const auto& [symbol, weight] : raw_weights) {
        out[symbol] = std::max(0.0, weight);
    }

    if (!normalize) {
        return out;
    }

    double sum = 0.0;
    for (const auto& [_, weight] : out) {
        sum += weight;
    }
    if (sum <= 0.0) {
        return out;
    }
    for (auto& [_, weight] : out) {
        weight = (weight / sum) * max_total_exposure;
    }
    return out;
}

std::unordered_map<std::string, double> PortfolioAllocator::apply_exposure_constraints(
    const std::unordered_map<std::string, double>& target_allocations,
    const std::unordered_map<std::string, std::string>& symbol_to_strategy,
    const std::unordered_map<std::string, std::string>& symbol_to_asset,
    const ExposureConstraints& constraints) {
    std::unordered_map<std::string, double> out;
    out.reserve(target_allocations.size());

    std::unordered_map<std::string, double> strategy_exposure;
    std::unordered_map<std::string, double> asset_exposure;
    double total = 0.0;

    for (const auto& [symbol, raw] : target_allocations) {
        double allocation = std::max(0.0, raw);
        allocation = std::min(allocation, std::max(0.0, constraints.max_symbol_exposure));

        const auto strategy_it = symbol_to_strategy.find(symbol);
        if (strategy_it != symbol_to_strategy.end()) {
            const auto limit_it = constraints.max_strategy_exposure.find(strategy_it->second);
            if (limit_it != constraints.max_strategy_exposure.end()) {
                const double used = strategy_exposure[strategy_it->second];
                allocation = std::min(allocation, std::max(0.0, limit_it->second - used));
            }
        }

        const auto asset_it = symbol_to_asset.find(symbol);
        if (asset_it != symbol_to_asset.end()) {
            const auto limit_it = constraints.max_asset_exposure.find(asset_it->second);
            if (limit_it != constraints.max_asset_exposure.end()) {
                const double used = asset_exposure[asset_it->second];
                allocation = std::min(allocation, std::max(0.0, limit_it->second - used));
            }
        }

        out[symbol] = allocation;
        total += allocation;
        if (strategy_it != symbol_to_strategy.end()) {
            strategy_exposure[strategy_it->second] += allocation;
        }
        if (asset_it != symbol_to_asset.end()) {
            asset_exposure[asset_it->second] += allocation;
        }
    }

    if (total > constraints.max_total_exposure && total > 0.0) {
        const double scale = constraints.max_total_exposure / total;
        for (auto& [_, allocation] : out) {
            allocation *= scale;
        }
    }

    return out;
}

RebalanceController::RebalanceController(RebalancePolicy policy)
    : policy_(policy) {}

bool RebalanceController::should_rebalance(
    int64_t now_msc,
    const std::unordered_map<std::string, double>& current_allocations,
    const std::unordered_map<std::string, double>& target_allocations) const {
    if (policy_.schedule_interval_msc > 0 &&
        (last_rebalance_msc_ == 0 || (now_msc - last_rebalance_msc_) >= policy_.schedule_interval_msc)) {
        return true;
    }

    if (policy_.drift_threshold > 0.0) {
        for (const auto& [symbol, target] : target_allocations) {
            const auto it = current_allocations.find(symbol);
            const double current = (it == current_allocations.end()) ? 0.0 : it->second;
            if (std::abs(current - target) >= policy_.drift_threshold) {
                return true;
            }
        }
    }

    return false;
}

void RebalanceController::mark_rebalanced(int64_t now_msc) {
    last_rebalance_msc_ = now_msc;
}

int64_t RebalanceController::last_rebalance_msc() const noexcept {
    return last_rebalance_msc_;
}

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
