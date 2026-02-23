/**
FILE: src\engine\risk_engine.cpp

PURPOSE:
Defines risk_engine.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in risk_engine.cpp.
- File-local helpers supporting the main public or internal entry points.

DATA FLOW:
Callers provide requests or data -> this file applies core logic -> outputs state changes or results.

DEPENDENCIES:
- Internal modules: Neighboring headers under cpp/include and shared utility components.
- External systems: Standard C++ library and optional third-party libs linked by CMake.

DESIGN NOTES:
- Keep behavior deterministic for backtest and unit-test reliability.
- Prefer explicit validation and retcode-based failure signaling.
- Preserve low coupling between domains through typed interfaces.
*/
#include "risk/risk_engine.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <unordered_set>

namespace haruquant::risk {

namespace {

double safe_stddev(const std::vector<double>& values) {
    if (values.size() < 2) {
        return 0.0;
    }
    const double mean = std::accumulate(values.begin(), values.end(), 0.0) /
        static_cast<double>(values.size());
    double accum = 0.0;
    for (const double value : values) {
        const double d = value - mean;
        accum += d * d;
    }
    return std::sqrt(accum / static_cast<double>(values.size()));
}

std::vector<double> rolling_stddevs(
    const std::vector<double>& values,
    int window) {
    std::vector<double> out;
    if (window <= 1 || static_cast<int>(values.size()) < window) {
        return out;
    }

    out.reserve(values.size() - static_cast<std::size_t>(window) + 1U);
    for (std::size_t i = 0; i + static_cast<std::size_t>(window) <= values.size(); ++i) {
        std::vector<double> slice(
            values.begin() + static_cast<std::ptrdiff_t>(i),
            values.begin() + static_cast<std::ptrdiff_t>(i + window));
        out.push_back(safe_stddev(slice));
    }
    return out;
}

double median(std::vector<double> values) {
    if (values.empty()) {
        return 0.0;
    }
    std::sort(values.begin(), values.end());
    const std::size_t mid = values.size() / 2U;
    if ((values.size() % 2U) == 0U) {
        return (values[mid - 1U] + values[mid]) / 2.0;
    }
    return values[mid];
}

double mode_multiplier(const RiskGovernorConfig& config, RiskMode mode) {
    if (mode == RiskMode::Live) {
        return std::max(0.0, config.live_limit_multiplier);
    }
    return std::max(0.0, config.backtest_limit_multiplier);
}

}  // namespace

IntradayRiskMonitor::IntradayRiskMonitor(IntradayRiskConfig config)
    : config_(config) {}

const IntradayRiskConfig& IntradayRiskMonitor::config() const noexcept {
    return config_;
}

IntradayRiskSnapshot IntradayRiskMonitor::evaluate(
    const std::vector<double>& equity_curve,
    const std::vector<double>& returns_window) const {
    return evaluate_with_hmm(equity_curve, returns_window, -1.0);
}

IntradayRiskSnapshot IntradayRiskMonitor::evaluate_with_hmm(
    const std::vector<double>& equity_curve,
    const std::vector<double>& returns_window,
    double hmm_stress_probability) const {
    IntradayRiskSnapshot out{};

    if (!equity_curve.empty()) {
        double peak = -std::numeric_limits<double>::infinity();
        for (const double v : equity_curve) {
            peak = std::max(peak, v);
        }
        if (peak > 0.0) {
            out.drawdown_frac = std::max(0.0, (peak - equity_curve.back()) / peak);
        }
    }

    if (!returns_window.empty()) {
        const int w = std::max(2, config_.volatility_window);
        if (static_cast<int>(returns_window.size()) >= w) {
            const std::size_t start = returns_window.size() - static_cast<std::size_t>(w);
            std::vector<double> tail(
                returns_window.begin() + static_cast<std::ptrdiff_t>(start),
                returns_window.end());
            out.volatility_now = safe_stddev(tail);
        } else {
            out.volatility_now = safe_stddev(returns_window);
        }

        if (static_cast<int>(returns_window.size()) > w) {
            std::vector<double> baseline(
                returns_window.begin(),
                returns_window.end() - static_cast<std::ptrdiff_t>(w));
            out.volatility_baseline = safe_stddev(baseline);
        } else {
            out.volatility_baseline = safe_stddev(returns_window);
        }

        if (out.volatility_baseline > 0.0) {
            out.volatility_spike = (
                out.volatility_now > (config_.volatility_spike_mult * out.volatility_baseline));
        }
    }

    const bool hmm_signal = (
        config_.use_hmm_proxy &&
        hmm_stress_probability >= 0.0 &&
        hmm_stress_probability >= config_.hmm_stress_probability_threshold);
    out.used_hmm_proxy = hmm_signal;
    out.hmm_stress_probability = hmm_stress_probability;
    out.drawdown_breached = out.drawdown_frac >= config_.protective_drawdown_frac;

    const bool halt_drawdown = out.drawdown_frac >= config_.halt_drawdown_frac;
    const bool halt_vol = (
        out.volatility_baseline > 0.0 &&
        out.volatility_now > (config_.halt_volatility_spike_mult * out.volatility_baseline));

    if (halt_drawdown || halt_vol || hmm_signal) {
        out.state = RiskState::Halt;
        if (hmm_signal) {
            out.reason = "HMM_STRESS_HALT";
        } else if (halt_drawdown) {
            out.reason = "DRAWDOWN_HALT";
        } else {
            out.reason = "VOLATILITY_HALT";
        }
        return out;
    }

    if (out.drawdown_breached || out.volatility_spike) {
        out.state = RiskState::Protective;
        out.reason = out.drawdown_breached ? "DRAWDOWN_PROTECTIVE" : "VOLATILITY_PROTECTIVE";
        return out;
    }

    out.state = RiskState::Normal;
    out.reason = "ok";
    return out;
}

void CircuitBreaker::trip_global(const std::string& reason) {
    global_halt_ = true;
    global_reason_ = reason;
}

void CircuitBreaker::reset_global() {
    global_halt_ = false;
    global_reason_.clear();
}

void CircuitBreaker::trip_strategy(const std::string& strategy_id, const std::string& reason) {
    strategy_halts_[strategy_id] = reason;
}

void CircuitBreaker::reset_strategy(const std::string& strategy_id) {
    strategy_halts_.erase(strategy_id);
}

bool CircuitBreaker::is_global_halt() const noexcept {
    return global_halt_;
}

bool CircuitBreaker::is_strategy_halted(const std::string& strategy_id) const {
    return strategy_halts_.find(strategy_id) != strategy_halts_.end();
}

std::size_t CircuitBreaker::strategy_halt_count() const noexcept {
    return strategy_halts_.size();
}

CircuitBreakerDecision CircuitBreaker::can_trade(const std::string& strategy_id) const {
    if (global_halt_) {
        return CircuitBreakerDecision{
            false,
            true,
            is_strategy_halted(strategy_id),
            "GLOBAL_CIRCUIT_BREAKER",
            global_reason_.empty() ? "global_halt" : global_reason_};
    }
    if (is_strategy_halted(strategy_id)) {
        const auto it = strategy_halts_.find(strategy_id);
        return CircuitBreakerDecision{
            false,
            false,
            true,
            "STRATEGY_CIRCUIT_BREAKER",
            it != strategy_halts_.end() ? it->second : "strategy_halt"};
    }
    return CircuitBreakerDecision{true, false, false, "OK", "ok"};
}

void KillSwitchController::set_reduce_only(const std::string& reason) {
    state_ = SafeModeState::ReduceOnly;
    last_reason_ = reason;
    last_source_ = "system";
}

void KillSwitchController::clear_reduce_only() {
    if (state_ == SafeModeState::ReduceOnly) {
        transition_to_normal_if_possible();
    }
}

void KillSwitchController::trigger_global_kill_switch(const std::string& reason) {
    breaker_.trip_global(reason);
    state_ = SafeModeState::Halt;
    last_reason_ = reason;
    last_source_ = "system";
}

void KillSwitchController::clear_global_kill_switch() {
    breaker_.reset_global();
    transition_to_normal_if_possible();
}

void KillSwitchController::trigger_strategy_kill_switch(
    const std::string& strategy_id,
    const std::string& reason) {
    breaker_.trip_strategy(strategy_id, reason);
    if (state_ == SafeModeState::Normal) {
        state_ = SafeModeState::ReduceOnly;
    }
    last_reason_ = reason;
    last_source_ = "system";
}

void KillSwitchController::clear_strategy_kill_switch(const std::string& strategy_id) {
    breaker_.reset_strategy(strategy_id);
    transition_to_normal_if_possible();
}

void KillSwitchController::request_emergency_shutdown(
    const std::string& source,
    const std::string& reason) {
    emergency_shutdown_ = true;
    state_ = SafeModeState::EmergencyShutdown;
    last_source_ = source.empty() ? "unknown" : source;
    last_reason_ = reason;
    breaker_.trip_global(reason.empty() ? "emergency_shutdown" : reason);
}

void KillSwitchController::clear_emergency_shutdown() {
    emergency_shutdown_ = false;
    breaker_.reset_global();
    transition_to_normal_if_possible();
}

SafeModeState KillSwitchController::state() const noexcept {
    return state_;
}

KillSwitchDecision KillSwitchController::can_trade(const std::string& strategy_id) const {
    if (emergency_shutdown_ || state_ == SafeModeState::EmergencyShutdown) {
        return KillSwitchDecision{
            false,
            SafeModeState::EmergencyShutdown,
            true,
            true,
            "EMERGENCY_SHUTDOWN",
            last_reason_.empty() ? "emergency_shutdown" : last_reason_,
            last_source_};
    }

    if (state_ == SafeModeState::ReduceOnly) {
        const bool strategy_halt = breaker_.is_strategy_halted(strategy_id);
        return KillSwitchDecision{
            false,
            SafeModeState::ReduceOnly,
            breaker_.is_global_halt(),
            strategy_halt,
            "REDUCE_ONLY",
            "reduce_only_mode_no_new_trades",
            last_source_};
    }

    if (state_ == SafeModeState::Halt) {
        return KillSwitchDecision{
            false,
            SafeModeState::Halt,
            breaker_.is_global_halt(),
            breaker_.is_strategy_halted(strategy_id),
            "SAFE_MODE_HALT",
            last_reason_.empty() ? "halt" : last_reason_,
            last_source_};
    }

    const auto cb = breaker_.can_trade(strategy_id);
    if (!cb.allowed) {
        return KillSwitchDecision{
            false,
            SafeModeState::Halt,
            cb.global_halt,
            cb.strategy_halt,
            cb.policy_code,
            cb.reason,
            last_source_};
    }

    return KillSwitchDecision{
        true,
        SafeModeState::Normal,
        false,
        false,
        "OK",
        "ok",
        last_source_};
}

KillSwitchSnapshot KillSwitchController::state_snapshot() const {
    return KillSwitchSnapshot{
        state_,
        breaker_.is_global_halt(),
        breaker_.strategy_halt_count(),
        emergency_shutdown_,
        last_reason_,
        last_source_};
}

void KillSwitchController::transition_to_normal_if_possible() {
    if (emergency_shutdown_) {
        state_ = SafeModeState::EmergencyShutdown;
        return;
    }
    if (breaker_.is_global_halt()) {
        state_ = SafeModeState::Halt;
        return;
    }
    if (breaker_.strategy_halt_count() > 0) {
        state_ = SafeModeState::ReduceOnly;
        return;
    }
    state_ = SafeModeState::Normal;
}

RiskGovernor::RiskGovernor(RiskGovernorConfig config)
    : config_(config) {}

const RiskGovernorConfig& RiskGovernor::config() const noexcept {
    return config_;
}

double RiskGovernor::drawdown_frac(const RiskAccountState& state) const {
    if (state.peak_equity <= 0.0) {
        return 0.0;
    }
    return std::max(0.0, (state.peak_equity - state.equity) / state.peak_equity);
}

RiskDecision RiskGovernor::can_trade(
    const RiskAccountState& state,
    double candidate_gross_add,
    double candidate_net_delta) const {
    const double dd = drawdown_frac(state);
    if (dd > config_.max_drawdown_frac) {
        return RiskDecision{
            false,
            "MAX_DRAWDOWN",
            "max_drawdown_exceeded",
            dd,
            std::max(0.0, state.gross_exposure + std::max(0.0, candidate_gross_add)),
            std::abs(state.net_exposure + candidate_net_delta)};
    }

    const double projected_gross =
        std::max(0.0, state.gross_exposure + std::max(0.0, candidate_gross_add));
    if (projected_gross > config_.max_gross_exposure) {
        return RiskDecision{
            false,
            "MAX_GROSS_EXPOSURE",
            "max_gross_exposure_exceeded",
            dd,
            projected_gross,
            std::abs(state.net_exposure + candidate_net_delta)};
    }

    const double projected_net = std::abs(state.net_exposure + candidate_net_delta);
    if (projected_net > config_.max_net_exposure) {
        return RiskDecision{
            false,
            "MAX_NET_EXPOSURE",
            "max_net_exposure_exceeded",
            dd,
            projected_gross,
            projected_net};
    }

    return RiskDecision{true, "OK", "ok", dd, projected_gross, projected_net};
}

RiskDecision RiskGovernor::can_trade_with_mode(
    const RiskAccountState& state,
    double candidate_size,
    double candidate_gross_add,
    double candidate_net_delta,
    double margin_required,
    double free_margin,
    RiskMode mode) const {
    if (std::abs(candidate_size) < config_.min_order_size ||
        std::abs(candidate_size) > config_.max_order_size) {
        return RiskDecision{
            false,
            "SIZE_INVALID",
            "candidate_size_out_of_bounds",
            drawdown_frac(state),
            std::max(0.0, state.gross_exposure + std::max(0.0, candidate_gross_add)),
            std::abs(state.net_exposure + candidate_net_delta)};
    }

    if (margin_required > 0.0 && free_margin >= 0.0) {
        const double margin_cap = free_margin * std::max(0.0, config_.max_margin_utilization);
        if (margin_required > margin_cap) {
            return RiskDecision{
                false,
                "INSUFFICIENT_MARGIN",
                "margin_required_exceeds_cap",
                drawdown_frac(state),
                std::max(0.0, state.gross_exposure + std::max(0.0, candidate_gross_add)),
                std::abs(state.net_exposure + candidate_net_delta)};
        }
    }

    const double mult = mode_multiplier(config_, mode);
    const double dd_limit = config_.max_drawdown_frac * mult;
    const double gross_limit = config_.max_gross_exposure * mult;
    const double net_limit = config_.max_net_exposure * mult;

    const double dd = drawdown_frac(state);
    const double projected_gross =
        std::max(0.0, state.gross_exposure + std::max(0.0, candidate_gross_add));
    const double projected_net = std::abs(state.net_exposure + candidate_net_delta);

    if (dd > dd_limit) {
        return RiskDecision{
            false,
            "MAX_DRAWDOWN",
            "max_drawdown_exceeded",
            dd,
            projected_gross,
            projected_net};
    }
    if (projected_gross > gross_limit) {
        return RiskDecision{
            false,
            "MAX_GROSS_EXPOSURE",
            "max_gross_exposure_exceeded",
            dd,
            projected_gross,
            projected_net};
    }
    if (projected_net > net_limit) {
        return RiskDecision{
            false,
            "MAX_NET_EXPOSURE",
            "max_net_exposure_exceeded",
            dd,
            projected_gross,
            projected_net};
    }

    return RiskDecision{true, "OK", "ok", dd, projected_gross, projected_net};
}

RiskRegimeDetector::RiskRegimeDetector(
    double vol_spike_mult,
    double corr_spike_level,
    double dd_trigger_frac,
    int lookback,
    int vol_med_window)
    : vol_spike_mult_(vol_spike_mult),
      corr_spike_level_(corr_spike_level),
      dd_trigger_frac_(dd_trigger_frac),
      lookback_(lookback),
      vol_med_window_(vol_med_window) {}

RegimeState RiskRegimeDetector::detect(
    const std::vector<std::vector<double>>& returns_matrix,
    const std::vector<double>& equity_curve) const {
    int flags = 0;

    const std::size_t rows = returns_matrix.size();
    const std::size_t cols = rows > 0 ? returns_matrix.front().size() : 0U;

    // 1) Vol spike on equal-weight proxy.
    if (rows >= static_cast<std::size_t>(std::max(lookback_, 2)) && cols > 0U) {
        const std::size_t start = rows - static_cast<std::size_t>(lookback_);
        std::vector<double> port_returns;
        port_returns.reserve(static_cast<std::size_t>(lookback_));
        for (std::size_t i = start; i < rows; ++i) {
            const auto& row = returns_matrix[i];
            if (row.empty()) {
                continue;
            }
            const double sum = std::accumulate(row.begin(), row.end(), 0.0);
            port_returns.push_back(sum / static_cast<double>(row.size()));
        }
        const double vol_now = safe_stddev(port_returns);
        const auto rolling = rolling_stddevs(port_returns, std::max(vol_med_window_, 2));
        const double vol_med = median(rolling);
        if (vol_med > 0.0 && vol_now > (vol_spike_mult_ * vol_med)) {
            ++flags;
        }
    }

    // 2) Correlation spike (avg off-diagonal).
    if (rows >= static_cast<std::size_t>(std::max(lookback_, 5)) && cols >= 2U) {
        const std::size_t start = rows - static_cast<std::size_t>(lookback_);
        double off_diag_sum = 0.0;
        std::size_t off_diag_count = 0U;

        for (std::size_t i = 0; i < cols; ++i) {
            std::vector<double> xi;
            xi.reserve(static_cast<std::size_t>(lookback_));
            for (std::size_t r = start; r < rows; ++r) {
                xi.push_back(returns_matrix[r][i]);
            }
            const double sxi = safe_stddev(xi);

            for (std::size_t j = i + 1U; j < cols; ++j) {
                std::vector<double> xj;
                xj.reserve(static_cast<std::size_t>(lookback_));
                for (std::size_t r = start; r < rows; ++r) {
                    xj.push_back(returns_matrix[r][j]);
                }
                const double sxj = safe_stddev(xj);
                if (sxi <= 0.0 || sxj <= 0.0) {
                    continue;
                }
                const double mi = std::accumulate(xi.begin(), xi.end(), 0.0) /
                    static_cast<double>(xi.size());
                const double mj = std::accumulate(xj.begin(), xj.end(), 0.0) /
                    static_cast<double>(xj.size());
                double cov = 0.0;
                for (std::size_t k = 0; k < xi.size(); ++k) {
                    cov += (xi[k] - mi) * (xj[k] - mj);
                }
                cov /= static_cast<double>(xi.size());
                off_diag_sum += (cov / (sxi * sxj));
                ++off_diag_count;
            }
        }

        if (off_diag_count > 0U) {
            const double avg_off = off_diag_sum / static_cast<double>(off_diag_count);
            if (avg_off >= corr_spike_level_) {
                ++flags;
            }
        }
    }

    // 3) Drawdown trigger.
    if (equity_curve.size() >= 10U) {
        double peak = -std::numeric_limits<double>::infinity();
        for (const double value : equity_curve) {
            peak = std::max(peak, value);
        }
        const double current = equity_curve.back();
        if (peak > 0.0) {
            const double dd = (peak - current) / peak;
            if (dd >= dd_trigger_frac_) {
                ++flags;
            }
        }
    }

    return RegimeState{flags >= 2 ? "STRESS" : "NORMAL"};
}

PositionSizer::PositionSizer(std::string method, PositionSizingConfig config)
    : method_(std::move(method)),
      config_(config) {}

double PositionSizer::calculate_size(
    double account_balance,
    double entry_price,
    double stop_loss,
    double contract_size,
    double atr,
    double win_rate,
    double avg_win,
    double avg_loss) const {
    if (method_ == "fixed_lot") {
        return fixed_lot();
    }
    if (method_ == "milestone") {
        return milestone(account_balance);
    }
    if (method_ == "fixed_risk") {
        return fixed_risk(account_balance, entry_price, stop_loss, contract_size);
    }
    if (method_ == "kelly") {
        return kelly(account_balance, entry_price, contract_size, win_rate, avg_win, avg_loss);
    }
    if (method_ == "volatility") {
        return volatility(account_balance, atr, contract_size);
    }
    if (method_ == "fixed_fractional") {
        return fixed_fractional(account_balance, entry_price, contract_size);
    }
    throw std::invalid_argument("Unknown sizing method: " + method_);
}

const std::string& PositionSizer::method() const noexcept {
    return method_;
}

const PositionSizingConfig& PositionSizer::config() const noexcept {
    return config_;
}

double PositionSizer::fixed_lot() const {
    return config_.lot_size;
}

double PositionSizer::milestone(double account_balance) const {
    if (config_.milestone_amount <= 0.0) {
        return config_.base_lot_size;
    }
    const double profit = std::max(0.0, account_balance - config_.initial_balance);
    const double milestones = std::floor(profit / config_.milestone_amount);
    return config_.base_lot_size + (milestones * config_.lot_increment);
}

double PositionSizer::fixed_risk(
    double account_balance,
    double entry_price,
    double stop_loss,
    double contract_size) const {
    if (account_balance <= 0.0 || contract_size <= 0.0 || stop_loss <= 0.0) {
        return 0.1;
    }
    const double risk_amount = account_balance * (config_.risk_percent / 100.0);
    const double stop_distance = std::abs(entry_price - stop_loss);
    if (stop_distance <= 0.0) {
        return 0.1;
    }
    return risk_amount / (stop_distance * contract_size);
}

double PositionSizer::kelly(
    double account_balance,
    double entry_price,
    double contract_size,
    double win_rate,
    double avg_win,
    double avg_loss) const {
    if (entry_price <= 0.0 || contract_size <= 0.0 || avg_win <= 0.0) {
        return 0.01;
    }
    const double loss = std::abs(avg_loss);
    double kelly_fraction = ((win_rate * avg_win) - ((1.0 - win_rate) * loss)) / avg_win;
    kelly_fraction = std::max(0.0, std::min(kelly_fraction, config_.kelly_fraction_limit));
    return (account_balance * kelly_fraction) / (entry_price * contract_size);
}

double PositionSizer::volatility(
    double account_balance,
    double atr,
    double contract_size) const {
    if (atr <= 0.0 || contract_size <= 0.0) {
        return 0.1;
    }
    const double risk_amount = account_balance * (config_.risk_percent / 100.0);
    const double adjusted_atr = atr * std::max(config_.atr_multiplier, 0.0001);
    return risk_amount / (adjusted_atr * contract_size);
}

double PositionSizer::fixed_fractional(
    double account_balance,
    double entry_price,
    double contract_size) const {
    if (entry_price <= 0.0 || contract_size <= 0.0 || account_balance <= 0.0) {
        return 0.01;
    }
    const double position_value = account_balance * (config_.fraction / 100.0);
    return position_value / (entry_price * contract_size);
}

RiskBudgetAllocator::RiskBudgetAllocator(CorrelationPreference corr_pref)
    : corr_pref_(corr_pref) {}

const CorrelationPreference& RiskBudgetAllocator::corr_pref() const noexcept {
    return corr_pref_;
}

std::unordered_map<std::string, double> RiskBudgetAllocator::normalize_budgets(
    const std::unordered_map<std::string, double>& base_lots,
    const std::unordered_map<std::string, double>& budgets) const {
    std::unordered_map<std::string, double> out;
    if (base_lots.empty()) {
        return out;
    }

    out.reserve(base_lots.size());
    if (budgets.empty()) {
        const double w = 1.0 / static_cast<double>(base_lots.size());
        for (const auto& [symbol, _] : base_lots) {
            out[symbol] = w;
        }
        return out;
    }

    double sum = 0.0;
    for (const auto& [symbol, _] : base_lots) {
        const auto it = budgets.find(symbol);
        const double value = (it == budgets.end()) ? 0.0 : std::max(0.0, it->second);
        out[symbol] = value;
        sum += value;
    }

    if (sum <= 0.0) {
        const double w = 1.0 / static_cast<double>(base_lots.size());
        for (auto& [_, value] : out) {
            value = w;
        }
        return out;
    }

    for (auto& [_, value] : out) {
        value /= sum;
    }
    return out;
}

std::unordered_map<std::string, double> RiskBudgetAllocator::apply_correlation_penalty(
    const std::unordered_map<std::string, double>& budgets,
    const std::unordered_map<std::string, double>& corr_map) const {
    if (budgets.empty() || corr_map.empty()) {
        return budgets;
    }

    std::unordered_map<std::string, double> adjusted;
    adjusted.reserve(budgets.size());

    for (const auto& [symbol, budget] : budgets) {
        const auto it = corr_map.find(symbol);
        const double corr = (it == corr_map.end()) ? 0.0 : std::abs(it->second);
        if (corr <= corr_pref_.target_corr) {
            adjusted[symbol] = budget;
            continue;
        }
        const double penalty = std::exp(-corr_pref_.penalty_strength * (corr - corr_pref_.target_corr));
        adjusted[symbol] = std::max(budget * penalty, corr_pref_.min_budget_frac * budget);
    }

    double sum = 0.0;
    for (const auto& [_, value] : adjusted) {
        sum += value;
    }
    if (sum <= 0.0) {
        return budgets;
    }
    for (auto& [_, value] : adjusted) {
        value /= sum;
    }
    return adjusted;
}

std::unordered_map<std::string, double> RiskBudgetAllocator::compute_target_lots(
    const std::unordered_map<std::string, double>& base_lots,
    const std::unordered_map<std::string, double>& budgets,
    const std::unordered_map<std::string, double>& corr_map) const {
    if (base_lots.empty()) {
        return {};
    }

    auto norm = normalize_budgets(base_lots, budgets);
    norm = apply_correlation_penalty(norm, corr_map);

    double total_abs_base = 0.0;
    for (const auto& [_, lots] : base_lots) {
        total_abs_base += std::abs(lots);
    }
    if (total_abs_base <= 0.0) {
        total_abs_base = static_cast<double>(base_lots.size());
    }

    std::unordered_map<std::string, double> target;
    target.reserve(base_lots.size());
    for (const auto& [symbol, base] : base_lots) {
        const double sign = (base < 0.0) ? -1.0 : 1.0;
        const double budget = norm.count(symbol) ? norm[symbol] : 0.0;
        target[symbol] = sign * (total_abs_base * budget);
    }
    return target;
}

std::unordered_map<std::string, double> RiskBudgetAllocator::lots_to_deltas(
    const std::unordered_map<std::string, double>& current,
    const std::unordered_map<std::string, double>& target) const {
    std::unordered_set<std::string> keys;
    keys.reserve(current.size() + target.size());
    for (const auto& [symbol, _] : current) {
        keys.insert(symbol);
    }
    for (const auto& [symbol, _] : target) {
        keys.insert(symbol);
    }

    std::unordered_map<std::string, double> out;
    out.reserve(keys.size());
    for (const auto& symbol : keys) {
        const double c = current.count(symbol) ? current.at(symbol) : 0.0;
        const double t = target.count(symbol) ? target.at(symbol) : 0.0;
        out[symbol] = t - c;
    }
    return out;
}

std::unordered_map<std::string, double> RiskBudgetAllocator::apply_exposure_constraints(
    const std::unordered_map<std::string, double>& target_allocations,
    const std::unordered_map<std::string, std::string>& symbol_to_strategy,
    const std::unordered_map<std::string, std::string>& symbol_to_asset,
    const ExposureConstraints& constraints) const {
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

double validate_position_size(
    double size,
    double min_lot,
    double max_lot,
    double lot_step,
    double max_size,
    bool allow_fractional) {
    double effective_max = max_lot;
    if (max_size > 0.0) {
        effective_max = std::min(effective_max, max_size);
    }
    if (!allow_fractional && lot_step > 0.0) {
        size = std::round(size / lot_step) * lot_step;
    }
    size = std::max(min_lot, std::min(size, effective_max));
    return size;
}

}  // namespace haruquant::risk

