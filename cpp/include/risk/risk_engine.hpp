/**
 * @file risk_engine.hpp
 * @brief C++ risk primitives for parity migration from apps/risk.
 */

#pragma once

#include <unordered_map>
#include <string>
#include <vector>

namespace hqt::risk {

struct RiskLimits {
    double var_cap_frac{0.10};
    double es_cap_frac{0.15};
    double delta_var_cap_frac{0.02};
    double delta_es_cap_frac{0.03};
    double max_margin_used_frac{0.50};
    double min_pair_corr{0.20};
    double stressed_corr_floor{0.50};
    bool use_stressed_corr{true};
    double confidence_level{0.95};
    int time_horizon_days{1};
    int vol_lookback{20};
    int corr_lookback{60};
    double max_single_rc_frac{0.20};
    double rc_rebalance_tolerance{0.05};
};

struct CorrelationPreference {
    double target_corr{0.50};
    double penalty_strength{2.0};
    double min_budget_frac{0.30};
};

struct RegimeState {
    std::string name{"NORMAL"};
};

struct RiskDecision {
    bool allowed{true};
    std::string policy_code{"OK"};
    std::string reason{"ok"};
    double drawdown_frac{0.0};
    double projected_gross_exposure{0.0};
    double projected_net_exposure{0.0};
};

enum class RiskMode {
    Live = 0,
    Backtest = 1,
};

struct RiskGovernorConfig {
    double max_drawdown_frac{0.20};
    double max_gross_exposure{5.0};
    double max_net_exposure{2.0};
    double live_limit_multiplier{0.90};
    double backtest_limit_multiplier{1.10};
    double min_order_size{0.0};
    double max_order_size{100.0};
    double max_margin_utilization{0.80};
};

struct RiskAccountState {
    double equity{0.0};
    double peak_equity{0.0};
    double gross_exposure{0.0};
    double net_exposure{0.0};
};

class RiskRegimeDetector {
public:
    RiskRegimeDetector(
        double vol_spike_mult = 1.8,
        double corr_spike_level = 0.55,
        double dd_trigger_frac = 0.05,
        int lookback = 60,
        int vol_med_window = 20);

    [[nodiscard]] RegimeState detect(
        const std::vector<std::vector<double>>& returns_matrix,
        const std::vector<double>& equity_curve = {}) const;

private:
    double vol_spike_mult_{1.8};
    double corr_spike_level_{0.55};
    double dd_trigger_frac_{0.05};
    int lookback_{60};
    int vol_med_window_{20};
};

class RiskGovernor {
public:
    explicit RiskGovernor(RiskGovernorConfig config = {});

    [[nodiscard]] const RiskGovernorConfig& config() const noexcept;
    [[nodiscard]] double drawdown_frac(const RiskAccountState& state) const;
    [[nodiscard]] RiskDecision can_trade(
        const RiskAccountState& state,
        double candidate_gross_add = 0.0,
        double candidate_net_delta = 0.0) const;
    [[nodiscard]] RiskDecision can_trade_with_mode(
        const RiskAccountState& state,
        double candidate_size,
        double candidate_gross_add,
        double candidate_net_delta,
        double margin_required,
        double free_margin,
        RiskMode mode) const;

private:
    RiskGovernorConfig config_{};
};

struct PositionSizingConfig {
    double lot_size{0.1};
    double initial_balance{10000.0};
    double base_lot_size{0.1};
    double milestone_amount{3000.0};
    double lot_increment{0.2};
    double risk_percent{1.0};
    double kelly_fraction_limit{0.25};
    double fraction{2.0};
    double atr_multiplier{1.0};
};

class PositionSizer {
public:
    explicit PositionSizer(
        std::string method = "fixed_risk",
        PositionSizingConfig config = {});

    [[nodiscard]] double calculate_size(
        double account_balance,
        double entry_price,
        double stop_loss = 0.0,
        double contract_size = 100000.0,
        double atr = 0.0,
        double win_rate = 0.5,
        double avg_win = 100.0,
        double avg_loss = 50.0) const;

    [[nodiscard]] const std::string& method() const noexcept;
    [[nodiscard]] const PositionSizingConfig& config() const noexcept;

private:
    [[nodiscard]] double fixed_lot() const;
    [[nodiscard]] double milestone(double account_balance) const;
    [[nodiscard]] double fixed_risk(
        double account_balance,
        double entry_price,
        double stop_loss,
        double contract_size) const;
    [[nodiscard]] double kelly(
        double account_balance,
        double entry_price,
        double contract_size,
        double win_rate,
        double avg_win,
        double avg_loss) const;
    [[nodiscard]] double volatility(
        double account_balance,
        double atr,
        double contract_size) const;
    [[nodiscard]] double fixed_fractional(
        double account_balance,
        double entry_price,
        double contract_size) const;

    std::string method_;
    PositionSizingConfig config_{};
};

struct ExposureConstraints {
    double max_total_exposure{1.0};
    double max_symbol_exposure{1.0};
    std::unordered_map<std::string, double> max_strategy_exposure{};
    std::unordered_map<std::string, double> max_asset_exposure{};
};

class RiskBudgetAllocator {
public:
    explicit RiskBudgetAllocator(CorrelationPreference corr_pref = {});

    [[nodiscard]] const CorrelationPreference& corr_pref() const noexcept;
    [[nodiscard]] std::unordered_map<std::string, double> compute_target_lots(
        const std::unordered_map<std::string, double>& base_lots,
        const std::unordered_map<std::string, double>& budgets = {},
        const std::unordered_map<std::string, double>& corr_map = {}) const;
    [[nodiscard]] std::unordered_map<std::string, double> lots_to_deltas(
        const std::unordered_map<std::string, double>& current,
        const std::unordered_map<std::string, double>& target) const;
    [[nodiscard]] std::unordered_map<std::string, double> apply_exposure_constraints(
        const std::unordered_map<std::string, double>& target_allocations,
        const std::unordered_map<std::string, std::string>& symbol_to_strategy,
        const std::unordered_map<std::string, std::string>& symbol_to_asset,
        const ExposureConstraints& constraints) const;

private:
    [[nodiscard]] std::unordered_map<std::string, double> normalize_budgets(
        const std::unordered_map<std::string, double>& base_lots,
        const std::unordered_map<std::string, double>& budgets) const;
    [[nodiscard]] std::unordered_map<std::string, double> apply_correlation_penalty(
        const std::unordered_map<std::string, double>& budgets,
        const std::unordered_map<std::string, double>& corr_map) const;

    CorrelationPreference corr_pref_{};
};

[[nodiscard]] double validate_position_size(
    double size,
    double min_lot,
    double max_lot,
    double lot_step,
    double max_size = 0.0,
    bool allow_fractional = false);

}  // namespace hqt::risk
