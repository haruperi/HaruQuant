/**
 * @file analytics.cpp
 * @brief Unified engine analytics compilation unit.
 */

#include "engine/engine.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <condition_variable>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <numeric>
#include <random>
#include <sstream>
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

    const std::size_t total_mismatches = report.position_mismatch_count + report.account_mismatch_count;
    report.ok = (total_mismatches == 0);
    if (total_mismatches == 0) {
        report.severity = "none";
        report.requires_manual_resolution = false;
        report.block_new_orders = false;
    } else if (total_mismatches <= 2) {
        report.severity = "minor";
        report.requires_manual_resolution = false;
        report.block_new_orders = false;
    } else {
        report.severity = "major";
        report.requires_manual_resolution = true;
        report.block_new_orders = true;
    }
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

EscalationDecision PositionBook::evaluate_reconciliation(
    const ReconciliationReport& report,
    ReconcilePolicy policy,
    std::size_t major_threshold) const {
    EscalationDecision decision;
    decision.policy = (policy == ReconcilePolicy::Manual) ? "manual" : "auto";

    const std::size_t total_mismatches = report.position_mismatch_count + report.account_mismatch_count;
    const bool major = total_mismatches >= major_threshold;

    if (policy == ReconcilePolicy::Manual) {
        decision.allow_new_orders = report.ok;
        decision.requires_manual_resolution = !report.ok;
        decision.escalate_alert = !report.ok;
        decision.reason = report.ok ? "manual_policy_clean" : "manual_policy_requires_operator";
        return decision;
    }

    if (report.ok) {
        decision.allow_new_orders = true;
        decision.requires_manual_resolution = false;
        decision.escalate_alert = false;
        decision.reason = "auto_policy_clean";
        return decision;
    }

    if (major) {
        decision.allow_new_orders = false;
        decision.requires_manual_resolution = true;
        decision.escalate_alert = true;
        decision.reason = "auto_policy_major_mismatch_blocked";
    } else {
        decision.allow_new_orders = true;
        decision.requires_manual_resolution = false;
        decision.escalate_alert = true;
        decision.reason = "auto_policy_minor_mismatch_alerted";
    }
    return decision;
}

bool PositionBook::write_incident_report(
    const std::string& path,
    const ReconciliationReport& report,
    const EscalationDecision& decision) const {
    if (path.empty()) {
        return false;
    }

    std::filesystem::path p(path);
    std::error_code ec;
    if (p.has_parent_path()) {
        std::filesystem::create_directories(p.parent_path(), ec);
        if (ec) {
            return false;
        }
    }

    std::ofstream out(path, std::ios::out | std::ios::trunc);
    if (!out.is_open()) {
        return false;
    }

    auto esc = [](const std::string& s) {
        std::string r;
        r.reserve(s.size());
        for (char c : s) {
            if (c == '"' || c == '\\') {
                r.push_back('\\');
            }
            r.push_back(c);
        }
        return r;
    };

    out << "{\n";
    out << "  \"trigger\": \"" << esc(report.trigger) << "\",\n";
    out << "  \"ok\": " << (report.ok ? "true" : "false") << ",\n";
    out << "  \"severity\": \"" << esc(report.severity) << "\",\n";
    out << "  \"position_mismatch_count\": " << report.position_mismatch_count << ",\n";
    out << "  \"account_mismatch_count\": " << report.account_mismatch_count << ",\n";
    out << "  \"requires_manual_resolution\": " << (report.requires_manual_resolution ? "true" : "false") << ",\n";
    out << "  \"block_new_orders\": " << (report.block_new_orders ? "true" : "false") << ",\n";
    out << "  \"decision\": {\n";
    out << "    \"allow_new_orders\": " << (decision.allow_new_orders ? "true" : "false") << ",\n";
    out << "    \"requires_manual_resolution\": " << (decision.requires_manual_resolution ? "true" : "false") << ",\n";
    out << "    \"escalate_alert\": " << (decision.escalate_alert ? "true" : "false") << ",\n";
    out << "    \"policy\": \"" << esc(decision.policy) << "\",\n";
    out << "    \"reason\": \"" << esc(decision.reason) << "\"\n";
    out << "  },\n";
    out << "  \"issues\": [\n";
    for (std::size_t i = 0; i < report.issues.size(); ++i) {
        out << "    \"" << esc(report.issues[i]) << "\"";
        if (i + 1 < report.issues.size()) {
            out << ",";
        }
        out << "\n";
    }
    out << "  ]\n";
    out << "}\n";
    out.close();
    return out.good();
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

VectorizedBacktestEngine::VectorizedBacktestEngine(SimulatorClient& client)
    : client_(client) {}

void VectorizedBacktestEngine::run(
    const std::string& symbol,
    double volume,
    const std::vector<BacktestBarStep>& bars) {
    processed_bars_ = 0U;
    total_trades_ = 0U;
    account_snapshot_ = client_.account_info();

    if (bars.empty() || volume <= 0.0) {
        return;
    }
    const auto* symbol_info = client_.symbol_info(symbol);
    if (symbol_info == nullptr) {
        return;
    }

    const double normalized_volume = normalize_volume(volume, *symbol_info);
    if (normalized_volume <= 0.0) {
        return;
    }

    AccountMonitor account_monitor;
    for (const auto& bar : bars) {
        ++processed_bars_;

        const double spread_points =
            (bar.spread_points >= 0.0) ? bar.spread_points : static_cast<double>(symbol_info->spread);
        const double bid = bar.close;
        const double ask = bar.close + (spread_points * symbol_info->point);

        SymbolTickData tick;
        tick.time = bar.time_msc / 1000;
        tick.time_msc = bar.time_msc;
        tick.bid = bid;
        tick.ask = ask;
        tick.last = bar.close;
        client_.set_symbol_tick(symbol, tick);

        const PositionTotals totals = account_monitor.monitor_positions(client_, symbol, bid, ask);
        account_snapshot_ = account_monitor.monitor_account(client_.account_info(), totals);

        if (bar.exit_signal != 0) {
            const auto positions = client_.positions_get(std::nullopt, symbol);
            for (const auto& pos : positions) {
                const bool is_buy = (pos.type == 0U);
                if ((bar.exit_signal == 1 && is_buy) || (bar.exit_signal == -1 && !is_buy)) {
                    const auto result = client_.close_position(pos.ticket);
                    if (result.retcode == 10009 || result.retcode == 10010) {
                        ++total_trades_;
                    }
                }
            }
        }

        if (bar.entry_signal == 1 || bar.entry_signal == -1) {
            TradeRequest request;
            request.action = 1;
            request.type = (bar.entry_signal == 1) ? 0 : 1;
            request.symbol = symbol;
            request.volume = normalized_volume;
            request.price = (bar.entry_signal == 1) ? ask : bid;
            request.sl = bar.sl;
            request.tp = bar.tp;

            (void)client_.order_send(request);
        }
    }
}

const AccountInfoData& VectorizedBacktestEngine::account_snapshot() const noexcept {
    return account_snapshot_;
}

std::size_t VectorizedBacktestEngine::processed_bars() const noexcept {
    return processed_bars_;
}

std::size_t VectorizedBacktestEngine::total_trades() const noexcept {
    return total_trades_;
}

double VectorizedBacktestEngine::normalize_volume(double requested, const SymbolInfoData& symbol_info) {
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

namespace {

std::string fnv1a64_hex(std::string_view payload) {
    std::uint64_t hash = 1469598103934665603ULL;
    for (const unsigned char c : payload) {
        hash ^= static_cast<std::uint64_t>(c);
        hash *= 1099511628211ULL;
    }
    std::ostringstream os;
    os << std::hex << std::setw(16) << std::setfill('0') << hash;
    return os.str();
}

double safe_mean(const std::vector<double>& values) {
    if (values.empty()) {
        return 0.0;
    }
    const double sum = std::accumulate(values.begin(), values.end(), 0.0);
    return sum / static_cast<double>(values.size());
}

double safe_stddev(const std::vector<double>& values, double mean) {
    if (values.empty()) {
        return 0.0;
    }
    double acc = 0.0;
    for (const double v : values) {
        const double d = v - mean;
        acc += d * d;
    }
    return std::sqrt(acc / static_cast<double>(values.size()));
}

double safe_corr(const std::vector<double>& a, const std::vector<double>& b) {
    if (a.size() != b.size() || a.size() < 2U) {
        return 0.0;
    }

    const double mean_a = safe_mean(a);
    const double mean_b = safe_mean(b);
    const double std_a = safe_stddev(a, mean_a);
    const double std_b = safe_stddev(b, mean_b);
    if (std_a <= 0.0 || std_b <= 0.0) {
        return 0.0;
    }

    double cov = 0.0;
    for (std::size_t i = 0; i < a.size(); ++i) {
        cov += (a[i] - mean_a) * (b[i] - mean_b);
    }
    cov /= static_cast<double>(a.size());
    return cov / (std_a * std_b);
}

long double binomial_prob(std::size_t n, std::size_t k) {
    if (k > n) {
        return 0.0L;
    }
    const std::size_t kk = std::min(k, n - k);
    long double comb = 1.0L;
    for (std::size_t i = 1; i <= kk; ++i) {
        comb *= static_cast<long double>(n - kk + i);
        comb /= static_cast<long double>(i);
    }
    long double p = comb;
    for (std::size_t i = 0; i < n; ++i) {
        p *= 0.5L;
    }
    return p;
}

}  // namespace

std::string ReplayCertifier::fingerprint(const std::vector<ReplayTradeEvent>& events) {
    struct CanonicalRow {
        std::size_t idx{0};
        ReplayTradeEvent event{};
    };

    std::vector<CanonicalRow> rows;
    rows.reserve(events.size());
    for (std::size_t i = 0; i < events.size(); ++i) {
        rows.push_back(CanonicalRow{i, events[i]});
    }

    std::sort(rows.begin(), rows.end(), [](const CanonicalRow& lhs, const CanonicalRow& rhs) {
        if (lhs.event.time_msc != rhs.event.time_msc) {
            return lhs.event.time_msc < rhs.event.time_msc;
        }
        if (lhs.event.symbol != rhs.event.symbol) {
            return lhs.event.symbol < rhs.event.symbol;
        }
        if (lhs.event.side != rhs.event.side) {
            return lhs.event.side < rhs.event.side;
        }
        if (lhs.event.ticket != rhs.event.ticket) {
            return lhs.event.ticket < rhs.event.ticket;
        }
        return lhs.idx < rhs.idx;
    });

    std::ostringstream payload;
    payload << std::fixed << std::setprecision(10);
    for (const auto& row : rows) {
        payload << row.event.time_msc << '|'
                << row.event.symbol << '|'
                << row.event.side << '|'
                << row.event.price << '|'
                << row.event.volume << '|'
                << row.event.ticket << ';';
    }
    return fnv1a64_hex(payload.str());
}

ReplayCertificationResult ReplayCertifier::compare(
    const std::vector<ReplayTradeEvent>& baseline,
    const std::vector<ReplayTradeEvent>& candidate) {
    ReplayCertificationResult out;
    out.baseline_fingerprint = fingerprint(baseline);
    out.candidate_fingerprint = fingerprint(candidate);
    out.consistent = (out.baseline_fingerprint == out.candidate_fingerprint);
    if (out.consistent) {
        out.message = "Replay consistent: " + out.baseline_fingerprint;
    } else {
        out.message = "Replay mismatch: baseline=" + out.baseline_fingerprint +
            " candidate=" + out.candidate_fingerprint;
    }
    return out;
}

std::vector<WfoWindow> WfoWfmOrchestrator::build_windows(std::size_t total_bars, const WfoSpec& spec) {
    std::vector<WfoWindow> windows;
    if (spec.train_bars == 0 || spec.test_bars == 0 || total_bars < (spec.train_bars + spec.test_bars)) {
        return windows;
    }

    const std::size_t step = (spec.step_bars > 0) ? spec.step_bars : spec.test_bars;
    if (step == 0) {
        return windows;
    }

    std::size_t start = 0;
    while ((start + spec.train_bars + spec.test_bars) <= total_bars) {
        WfoWindow w;
        w.train_start = start;
        w.train_end = start + spec.train_bars;
        w.test_start = w.train_end;
        w.test_end = w.test_start + spec.test_bars;
        windows.push_back(w);
        start += step;
    }
    return windows;
}

std::vector<WfoWindowResult> WfoWfmOrchestrator::run_wfo(
    std::size_t total_bars,
    const WfoSpec& spec,
    const std::function<double(const WfoWindow&, bool)>& evaluator) {
    std::vector<WfoWindowResult> out;
    if (!evaluator) {
        return out;
    }
    const auto windows = build_windows(total_bars, spec);
    out.reserve(windows.size());
    for (const auto& w : windows) {
        WfoWindowResult result;
        result.window = w;
        result.train_score = evaluator(w, true);
        result.test_score = evaluator(w, false);
        out.push_back(result);
    }
    return out;
}

WfoSummary WfoWfmOrchestrator::summarize(const std::vector<WfoWindowResult>& results) {
    WfoSummary out;
    out.num_windows = results.size();
    if (results.empty()) {
        return out;
    }

    std::vector<double> train;
    std::vector<double> test;
    train.reserve(results.size());
    test.reserve(results.size());
    for (const auto& r : results) {
        train.push_back(r.train_score);
        test.push_back(r.test_score);
    }

    out.avg_train_score = safe_mean(train);
    out.avg_test_score = safe_mean(test);
    out.std_train_score = safe_stddev(train, out.avg_train_score);
    out.std_test_score = safe_stddev(test, out.avg_test_score);
    out.train_test_correlation = safe_corr(train, test);
    out.overfitting_ratio = (std::abs(out.avg_train_score) > 1e-12)
        ? (out.avg_test_score / out.avg_train_score)
        : 0.0;
    return out;
}

std::vector<WfmCellResult> WfoWfmOrchestrator::run_wfm(
    std::size_t total_bars,
    const std::vector<WfoSpec>& matrix_specs,
    const std::function<double(const WfoWindow&, bool)>& evaluator) {
    std::vector<WfmCellResult> out;
    out.reserve(matrix_specs.size());
    for (const auto& spec : matrix_specs) {
        WfmCellResult cell;
        cell.spec = spec;
        const auto results = run_wfo(total_bars, spec, evaluator);
        cell.summary = summarize(results);
        out.push_back(cell);
    }
    return out;
}

EdgeDetectorReport EdgeDetector::from_wfo(const std::vector<WfoWindowResult>& results, double alpha) {
    EdgeDetectorReport out;
    out.windows = results.size();
    if (results.empty()) {
        out.verdict = "INSUFFICIENT_DATA";
        return out;
    }

    std::vector<double> test_scores;
    test_scores.reserve(results.size());
    for (const auto& r : results) {
        test_scores.push_back(r.test_score);
    }
    out.mean_test_score = safe_mean(test_scores);

    std::size_t positives = 0;
    for (const auto s : test_scores) {
        if (s > 0.0) {
            ++positives;
        }
    }

    long double p = 0.0L;
    for (std::size_t k = positives; k <= test_scores.size(); ++k) {
        p += binomial_prob(test_scores.size(), k);
    }
    out.p_value = static_cast<double>(std::min<long double>(1.0L, p));
    out.skill_confirmed = (out.mean_test_score > 0.0) && (out.p_value < alpha);

    if (results.size() < 3U) {
        out.verdict = "INSUFFICIENT_DATA";
    } else if (out.skill_confirmed) {
        out.verdict = "EDGE_CONFIRMED";
    } else if (out.mean_test_score > 0.0) {
        out.verdict = "POTENTIAL_EDGE";
    } else {
        out.verdict = "NO_EDGE";
    }
    return out;
}

void ExperimentRegistry::upsert(const ExperimentRecord& record) {
    if (record.experiment_id.empty()) {
        return;
    }
    records_[record.experiment_id] = record;
}

std::vector<ExperimentRecord> ExperimentRegistry::all() const {
    std::vector<ExperimentRecord> out;
    out.reserve(records_.size());
    for (const auto& [_, record] : records_) {
        out.push_back(record);
    }
    std::sort(out.begin(), out.end(), [](const ExperimentRecord& lhs, const ExperimentRecord& rhs) {
        return lhs.experiment_id < rhs.experiment_id;
    });
    return out;
}

std::vector<ExperimentRecord> ExperimentRegistry::query(
    std::optional<std::string_view> strategy,
    std::optional<std::string_view> symbol,
    std::optional<int64_t> period_start_msc,
    std::optional<int64_t> period_end_msc) const {
    std::vector<ExperimentRecord> out;
    for (const auto& [_, record] : records_) {
        if (strategy.has_value() && record.strategy != *strategy) {
            continue;
        }
        if (symbol.has_value() && record.symbol != *symbol) {
            continue;
        }
        if (period_start_msc.has_value() && record.period_end_msc < *period_start_msc) {
            continue;
        }
        if (period_end_msc.has_value() && record.period_start_msc > *period_end_msc) {
            continue;
        }
        out.push_back(record);
    }
    std::sort(out.begin(), out.end(), [](const ExperimentRecord& lhs, const ExperimentRecord& rhs) {
        return lhs.period_start_msc < rhs.period_start_msc;
    });
    return out;
}

SymbolClassification SymbolClassifier::classify(std::string_view symbol, double annualized_volatility) {
    SymbolClassification out;

    const std::string s(symbol);
    if (s.find("BTC") != std::string::npos || s.find("ETH") != std::string::npos) {
        out.asset_class = "crypto";
    } else if (s.find("XAU") != std::string::npos || s.find("XAG") != std::string::npos) {
        out.asset_class = "metal";
    } else if (s.find("SPX") != std::string::npos || s.find("NAS") != std::string::npos || s.find("DAX") != std::string::npos) {
        out.asset_class = "index";
    } else if (s.find("USD") != std::string::npos ||
        s.find("EUR") != std::string::npos ||
        s.find("JPY") != std::string::npos ||
        s.find("GBP") != std::string::npos ||
        s.find("AUD") != std::string::npos ||
        s.find("CAD") != std::string::npos ||
        s.find("CHF") != std::string::npos ||
        s.find("NZD") != std::string::npos) {
        out.asset_class = "fx";
    }

    if (annualized_volatility < 0.10) {
        out.volatility_regime = "low";
    } else if (annualized_volatility < 0.25) {
        out.volatility_regime = "normal";
    } else if (annualized_volatility < 0.40) {
        out.volatility_regime = "high";
    } else {
        out.volatility_regime = "extreme";
    }

    return out;
}

SeasonalAnalysis SeasonalPatternAnalyzer::analyze(
    const std::vector<int64_t>& timestamps_msc,
    const std::vector<double>& returns,
    const std::unordered_set<int64_t>& holiday_days_epoch) {
    SeasonalAnalysis out;
    if (timestamps_msc.size() != returns.size() || timestamps_msc.empty()) {
        return out;
    }

    struct Agg {
        std::size_t count{0};
        double sum{0.0};
    };

    std::array<Agg, 7> dow{};
    std::array<Agg, 2> holiday{};

    for (std::size_t i = 0; i < timestamps_msc.size(); ++i) {
        const int64_t ts_sec = timestamps_msc[i] / 1000;
        const int day_index = static_cast<int>(((ts_sec / 86400) + 4) % 7);  // epoch Thursday offset
        const int safe_day = (day_index < 0) ? (day_index + 7) : day_index;
        dow[static_cast<std::size_t>(safe_day)].count += 1U;
        dow[static_cast<std::size_t>(safe_day)].sum += returns[i];

        const int64_t epoch_day = ts_sec / 86400;
        const bool is_holiday = (holiday_days_epoch.find(epoch_day) != holiday_days_epoch.end());
        const std::size_t idx = is_holiday ? 1U : 0U;
        holiday[idx].count += 1U;
        holiday[idx].sum += returns[i];
    }

    out.day_of_week.reserve(7);
    for (std::size_t i = 0; i < dow.size(); ++i) {
        SeasonalBucket b;
        b.key = static_cast<int>(i);
        b.count = dow[i].count;
        b.mean_return = (dow[i].count > 0U) ? (dow[i].sum / static_cast<double>(dow[i].count)) : 0.0;
        out.day_of_week.push_back(b);
    }

    out.holiday_vs_non_holiday.reserve(2);
    for (std::size_t i = 0; i < holiday.size(); ++i) {
        SeasonalBucket b;
        b.key = static_cast<int>(i);  // 0=non-holiday, 1=holiday
        b.count = holiday[i].count;
        b.mean_return = (holiday[i].count > 0U)
            ? (holiday[i].sum / static_cast<double>(holiday[i].count))
            : 0.0;
        out.holiday_vs_non_holiday.push_back(b);
    }

    return out;
}

namespace {

using ParamMap = std::unordered_map<std::string, double>;

std::vector<std::pair<std::string, std::vector<double>>> canonical_dimensions(
    const OptimizationParamSpace& space) {
    std::vector<std::pair<std::string, std::vector<double>>> dims;
    dims.reserve(space.size());
    for (const auto& [key, values] : space) {
        if (key.empty() || values.empty()) {
            continue;
        }
        dims.push_back({key, values});
    }
    std::sort(dims.begin(), dims.end(), [](const auto& lhs, const auto& rhs) {
        return lhs.first < rhs.first;
    });
    return dims;
}

void rank_trials(std::vector<OptimizationTrial>& trials) {
    std::sort(trials.begin(), trials.end(), [](const OptimizationTrial& lhs, const OptimizationTrial& rhs) {
        if (lhs.score != rhs.score) {
            return lhs.score > rhs.score;
        }
        return lhs.iteration < rhs.iteration;
    });
}

ParamMap random_candidate(
    const std::vector<std::pair<std::string, std::vector<double>>>& dims,
    std::mt19937_64& rng) {
    ParamMap out;
    out.reserve(dims.size());
    for (const auto& [name, values] : dims) {
        std::uniform_int_distribution<std::size_t> pick(0U, values.size() - 1U);
        out[name] = values[pick(rng)];
    }
    return out;
}

std::size_t nearest_index(const std::vector<double>& values, double v) {
    std::size_t best = 0U;
    double best_dist = std::numeric_limits<double>::max();
    for (std::size_t i = 0; i < values.size(); ++i) {
        const double d = std::abs(values[i] - v);
        if (d < best_dist) {
            best_dist = d;
            best = i;
        }
    }
    return best;
}

OptimizationTrial evaluate_trial(
    const ParamMap& params,
    std::size_t iteration,
    std::size_t generation,
    const std::function<double(const ParamMap&)>& evaluator) {
    OptimizationTrial t;
    t.params = params;
    t.score = evaluator(params);
    t.iteration = iteration;
    t.generation = generation;
    return t;
}

}  // namespace

std::vector<OptimizationTrial> GridSearchRunner::run(
    const OptimizationParamSpace& space,
    const std::function<double(const std::unordered_map<std::string, double>&)>& evaluator,
    std::size_t max_evals) {
    std::vector<OptimizationTrial> trials;
    if (!evaluator) {
        return trials;
    }

    const auto dims = canonical_dimensions(space);
    if (dims.empty()) {
        return trials;
    }

    ParamMap current;
    current.reserve(dims.size());
    std::size_t emitted = 0U;

    std::function<void(std::size_t)> walk = [&](std::size_t idx) {
        if (max_evals > 0U && emitted >= max_evals) {
            return;
        }
        if (idx == dims.size()) {
            trials.push_back(evaluate_trial(current, emitted, 0U, evaluator));
            ++emitted;
            return;
        }
        const auto& [name, values] = dims[idx];
        for (const double v : values) {
            current[name] = v;
            walk(idx + 1U);
            if (max_evals > 0U && emitted >= max_evals) {
                return;
            }
        }
    };

    walk(0U);
    rank_trials(trials);
    return trials;
}

std::vector<OptimizationTrial> RandomSearchRunner::run(
    const OptimizationParamSpace& space,
    std::size_t samples,
    std::uint64_t seed,
    const std::function<double(const std::unordered_map<std::string, double>&)>& evaluator) {
    std::vector<OptimizationTrial> trials;
    if (!evaluator || samples == 0U) {
        return trials;
    }

    const auto dims = canonical_dimensions(space);
    if (dims.empty()) {
        return trials;
    }

    std::mt19937_64 rng(seed);
    trials.reserve(samples);
    for (std::size_t i = 0; i < samples; ++i) {
        const ParamMap params = random_candidate(dims, rng);
        trials.push_back(evaluate_trial(params, i, 0U, evaluator));
    }
    rank_trials(trials);
    return trials;
}

std::vector<OptimizationTrial> GeneticSearchRunner::run(
    const OptimizationParamSpace& space,
    std::size_t population_size,
    std::size_t generations,
    std::uint64_t seed,
    const std::function<double(const std::unordered_map<std::string, double>&)>& evaluator,
    double mutation_rate) {
    std::vector<OptimizationTrial> all_trials;
    if (!evaluator || population_size == 0U || generations == 0U) {
        return all_trials;
    }

    const auto dims = canonical_dimensions(space);
    if (dims.empty()) {
        return all_trials;
    }

    std::mt19937_64 rng(seed);
    std::uniform_real_distribution<double> unit(0.0, 1.0);
    std::vector<ParamMap> population;
    population.reserve(population_size);
    for (std::size_t i = 0; i < population_size; ++i) {
        population.push_back(random_candidate(dims, rng));
    }

    std::size_t iteration = 0U;
    for (std::size_t gen = 0; gen < generations; ++gen) {
        std::vector<OptimizationTrial> ranked;
        ranked.reserve(population.size());
        for (const auto& p : population) {
            ranked.push_back(evaluate_trial(p, iteration++, gen, evaluator));
        }
        rank_trials(ranked);
        all_trials.insert(all_trials.end(), ranked.begin(), ranked.end());

        const std::size_t elite_count = std::max<std::size_t>(1U, population_size / 4U);
        std::vector<ParamMap> next;
        next.reserve(population_size);
        for (std::size_t i = 0; i < elite_count && i < ranked.size(); ++i) {
            next.push_back(ranked[i].params);
        }

        std::uniform_int_distribution<std::size_t> elite_pick(0U, next.size() - 1U);
        while (next.size() < population_size) {
            const ParamMap& a = next[elite_pick(rng)];
            const ParamMap& b = next[elite_pick(rng)];
            ParamMap child;
            child.reserve(dims.size());
            for (const auto& [name, values] : dims) {
                const double base = (unit(rng) < 0.5) ? a.at(name) : b.at(name);
                double v = base;
                if (unit(rng) < mutation_rate) {
                    std::uniform_int_distribution<std::size_t> pick(0U, values.size() - 1U);
                    v = values[pick(rng)];
                }
                child[name] = v;
            }
            next.push_back(std::move(child));
        }
        population = std::move(next);
    }

    rank_trials(all_trials);
    return all_trials;
}

std::vector<OptimizationTrial> BayesianSearchRunner::run(
    const OptimizationParamSpace& space,
    std::size_t iterations,
    std::uint64_t seed,
    const std::function<double(const std::unordered_map<std::string, double>&)>& evaluator,
    std::size_t random_warmup,
    double exploration_weight) {
    std::vector<OptimizationTrial> trials;
    if (!evaluator || iterations == 0U) {
        return trials;
    }

    const auto dims = canonical_dimensions(space);
    if (dims.empty()) {
        return trials;
    }

    std::mt19937_64 rng(seed);
    std::uniform_real_distribution<double> unit(0.0, 1.0);
    trials.reserve(iterations);

    const std::size_t warmup = std::min(random_warmup, iterations);
    for (std::size_t i = 0; i < warmup; ++i) {
        trials.push_back(evaluate_trial(random_candidate(dims, rng), i, 0U, evaluator));
    }

    for (std::size_t i = warmup; i < iterations; ++i) {
        const auto best_it = std::max_element(
            trials.begin(),
            trials.end(),
            [](const OptimizationTrial& lhs, const OptimizationTrial& rhs) { return lhs.score < rhs.score; });

        ParamMap candidate = best_it->params;
        for (const auto& [name, values] : dims) {
            const std::size_t current_idx = nearest_index(values, candidate[name]);
            std::size_t target_idx = current_idx;

            const bool explore = unit(rng) < std::clamp(exploration_weight, 0.0, 1.0);
            if (explore) {
                std::uniform_int_distribution<std::size_t> pick(0U, values.size() - 1U);
                target_idx = pick(rng);
            } else {
                if (current_idx == 0U) {
                    target_idx = std::min<std::size_t>(1U, values.size() - 1U);
                } else if (current_idx + 1U >= values.size()) {
                    target_idx = current_idx - 1U;
                } else {
                    target_idx = (unit(rng) < 0.5) ? (current_idx - 1U) : (current_idx + 1U);
                }
            }
            candidate[name] = values[target_idx];
        }

        trials.push_back(evaluate_trial(candidate, i, 0U, evaluator));
    }

    rank_trials(trials);
    return trials;
}

DistributedOptimizationResult DistributedOptimizationRunner::run(
    const std::vector<std::unordered_map<std::string, double>>& params_list,
    const std::function<double(const std::unordered_map<std::string, double>&)>& evaluator,
    OptimizationWorkerPolicy policy) {
    DistributedOptimizationResult out;
    out.health.submitted = params_list.size();
    if (!evaluator || params_list.empty()) {
        return out;
    }

    const std::size_t total = params_list.size();
    const std::size_t worker_count = std::max<std::size_t>(
        1U,
        std::min<std::size_t>(
            (policy.max_workers > 0U) ? policy.max_workers : 1U,
            total));
    const auto timeout_ms = std::max<int64_t>(1, policy.task_timeout_ms);
    const auto heartbeat_ms = std::max<int64_t>(1, policy.heartbeat_ms);

    std::vector<std::size_t> attempts(total, 0U);
    std::vector<bool> settled(total, false);
    std::queue<std::size_t> pending;
    for (std::size_t i = 0; i < total; ++i) {
        pending.push(i);
    }

    std::mutex mutex;
    std::condition_variable cv;
    std::vector<OptimizationTrial> trials;
    trials.reserve(total);

    std::atomic<std::size_t> settled_count{0U};
    std::atomic<std::size_t> completed_count{0U};
    std::atomic<std::size_t> failed_count{0U};
    std::atomic<std::size_t> restarted_count{0U};
    std::atomic<std::size_t> timeout_restarts{0U};
    std::atomic<bool> stop{false};

    auto worker = [&]() {
        while (!stop.load()) {
            std::size_t idx = std::numeric_limits<std::size_t>::max();
            {
                std::unique_lock<std::mutex> lock(mutex);
                cv.wait_for(lock, std::chrono::milliseconds(heartbeat_ms), [&]() {
                    return stop.load() || !pending.empty();
                });
                if (stop.load()) {
                    break;
                }
                if (pending.empty()) {
                    continue;
                }
                idx = pending.front();
                pending.pop();
            }

            const auto started = std::chrono::steady_clock::now();
            bool ok = false;
            double score = 0.0;
            try {
                score = evaluator(params_list[idx]);
                ok = true;
            } catch (...) {
                ok = false;
            }
            const auto ended = std::chrono::steady_clock::now();
            const auto elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(ended - started).count();
            const bool timed_out = elapsed_ms > timeout_ms;

            std::lock_guard<std::mutex> lock(mutex);
            if (settled[idx]) {
                continue;
            }

            if (ok && !timed_out) {
                OptimizationTrial t;
                t.params = params_list[idx];
                t.score = score;
                t.iteration = completed_count.fetch_add(1U);
                t.generation = attempts[idx];
                trials.push_back(std::move(t));
                settled[idx] = true;
                settled_count.fetch_add(1U);
                continue;
            }

            if (timed_out) {
                timeout_restarts.fetch_add(1U);
            }

            if (attempts[idx] < policy.max_restarts) {
                attempts[idx] += 1U;
                restarted_count.fetch_add(1U);
                pending.push(idx);
                cv.notify_one();
            } else {
                settled[idx] = true;
                settled_count.fetch_add(1U);
                failed_count.fetch_add(1U);
            }
        }
    };

    std::vector<std::thread> workers;
    workers.reserve(worker_count);
    for (std::size_t i = 0; i < worker_count; ++i) {
        workers.emplace_back(worker);
    }

    while (settled_count.load() < total) {
        std::this_thread::sleep_for(std::chrono::milliseconds(heartbeat_ms));
    }
    stop.store(true);
    cv.notify_all();
    for (auto& t : workers) {
        if (t.joinable()) {
            t.join();
        }
    }

    rank_trials(trials);
    out.trials = std::move(trials);
    out.health.completed = completed_count.load();
    out.health.failed = failed_count.load();
    out.health.restarted = restarted_count.load();
    out.health.timeout_restarts = timeout_restarts.load();
    return out;
}

}  // namespace hqt::sim
