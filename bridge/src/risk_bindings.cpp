/**
 * @file risk_bindings.cpp
 * @brief Nanobind bindings for C++ risk primitives under hqt_engine._risk.
 */

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/unordered_map.h>
#include <nanobind/stl/vector.h>

#include "risk/risk_engine.hpp"

namespace nb = nanobind;
using namespace hqt::risk;

void register_risk_bindings(nb::module_& m) {
    nb::class_<RiskLimits>(m, "RiskLimits")
        .def(nb::init<>())
        .def_rw("var_cap_frac", &RiskLimits::var_cap_frac)
        .def_rw("es_cap_frac", &RiskLimits::es_cap_frac)
        .def_rw("delta_var_cap_frac", &RiskLimits::delta_var_cap_frac)
        .def_rw("delta_es_cap_frac", &RiskLimits::delta_es_cap_frac)
        .def_rw("max_margin_used_frac", &RiskLimits::max_margin_used_frac)
        .def_rw("min_pair_corr", &RiskLimits::min_pair_corr)
        .def_rw("stressed_corr_floor", &RiskLimits::stressed_corr_floor)
        .def_rw("use_stressed_corr", &RiskLimits::use_stressed_corr)
        .def_rw("confidence_level", &RiskLimits::confidence_level)
        .def_rw("time_horizon_days", &RiskLimits::time_horizon_days)
        .def_rw("vol_lookback", &RiskLimits::vol_lookback)
        .def_rw("corr_lookback", &RiskLimits::corr_lookback)
        .def_rw("max_single_rc_frac", &RiskLimits::max_single_rc_frac)
        .def_rw("rc_rebalance_tolerance", &RiskLimits::rc_rebalance_tolerance);

    nb::class_<CorrelationPreference>(m, "CorrelationPreference")
        .def(nb::init<>())
        .def_rw("target_corr", &CorrelationPreference::target_corr)
        .def_rw("penalty_strength", &CorrelationPreference::penalty_strength)
        .def_rw("min_budget_frac", &CorrelationPreference::min_budget_frac);

    nb::class_<RegimeState>(m, "RegimeState")
        .def(nb::init<>())
        .def(nb::init<std::string>(), nb::arg("name"))
        .def_rw("name", &RegimeState::name);

    nb::class_<RiskDecision>(m, "RiskDecision")
        .def(nb::init<>())
        .def_rw("allowed", &RiskDecision::allowed)
        .def_rw("policy_code", &RiskDecision::policy_code)
        .def_rw("reason", &RiskDecision::reason)
        .def_rw("drawdown_frac", &RiskDecision::drawdown_frac)
        .def_rw("projected_gross_exposure", &RiskDecision::projected_gross_exposure)
        .def_rw("projected_net_exposure", &RiskDecision::projected_net_exposure);

    nb::enum_<RiskMode>(m, "RiskMode")
        .value("LIVE", RiskMode::Live)
        .value("BACKTEST", RiskMode::Backtest)
        .export_values();

    nb::enum_<RiskState>(m, "RiskState")
        .value("NORMAL", RiskState::Normal)
        .value("PROTECTIVE", RiskState::Protective)
        .value("HALT", RiskState::Halt)
        .export_values();

    nb::class_<IntradayRiskConfig>(m, "IntradayRiskConfig")
        .def(nb::init<>())
        .def_rw("protective_drawdown_frac", &IntradayRiskConfig::protective_drawdown_frac)
        .def_rw("halt_drawdown_frac", &IntradayRiskConfig::halt_drawdown_frac)
        .def_rw("volatility_spike_mult", &IntradayRiskConfig::volatility_spike_mult)
        .def_rw("halt_volatility_spike_mult", &IntradayRiskConfig::halt_volatility_spike_mult)
        .def_rw("volatility_window", &IntradayRiskConfig::volatility_window)
        .def_rw("use_hmm_proxy", &IntradayRiskConfig::use_hmm_proxy)
        .def_rw("hmm_stress_probability_threshold", &IntradayRiskConfig::hmm_stress_probability_threshold);

    nb::class_<IntradayRiskSnapshot>(m, "IntradayRiskSnapshot")
        .def(nb::init<>())
        .def_rw("state", &IntradayRiskSnapshot::state)
        .def_rw("drawdown_breached", &IntradayRiskSnapshot::drawdown_breached)
        .def_rw("volatility_spike", &IntradayRiskSnapshot::volatility_spike)
        .def_rw("used_hmm_proxy", &IntradayRiskSnapshot::used_hmm_proxy)
        .def_rw("drawdown_frac", &IntradayRiskSnapshot::drawdown_frac)
        .def_rw("volatility_now", &IntradayRiskSnapshot::volatility_now)
        .def_rw("volatility_baseline", &IntradayRiskSnapshot::volatility_baseline)
        .def_rw("hmm_stress_probability", &IntradayRiskSnapshot::hmm_stress_probability)
        .def_rw("reason", &IntradayRiskSnapshot::reason);

    nb::class_<IntradayRiskMonitor>(m, "IntradayRiskMonitor")
        .def(nb::init<IntradayRiskConfig>(), nb::arg("config") = IntradayRiskConfig{})
        .def("config", &IntradayRiskMonitor::config, nb::rv_policy::reference_internal)
        .def("evaluate", &IntradayRiskMonitor::evaluate, nb::arg("equity_curve"), nb::arg("returns_window"))
        .def(
            "evaluate_with_hmm",
            &IntradayRiskMonitor::evaluate_with_hmm,
            nb::arg("equity_curve"),
            nb::arg("returns_window"),
            nb::arg("hmm_stress_probability"));

    nb::class_<CircuitBreakerDecision>(m, "CircuitBreakerDecision")
        .def(nb::init<>())
        .def_rw("allowed", &CircuitBreakerDecision::allowed)
        .def_rw("global_halt", &CircuitBreakerDecision::global_halt)
        .def_rw("strategy_halt", &CircuitBreakerDecision::strategy_halt)
        .def_rw("policy_code", &CircuitBreakerDecision::policy_code)
        .def_rw("reason", &CircuitBreakerDecision::reason);

    nb::class_<CircuitBreaker>(m, "CircuitBreaker")
        .def(nb::init<>())
        .def("trip_global", &CircuitBreaker::trip_global, nb::arg("reason"))
        .def("reset_global", &CircuitBreaker::reset_global)
        .def("trip_strategy", &CircuitBreaker::trip_strategy, nb::arg("strategy_id"), nb::arg("reason"))
        .def("reset_strategy", &CircuitBreaker::reset_strategy, nb::arg("strategy_id"))
        .def("is_global_halt", &CircuitBreaker::is_global_halt)
        .def("is_strategy_halted", &CircuitBreaker::is_strategy_halted, nb::arg("strategy_id"))
        .def("can_trade", &CircuitBreaker::can_trade, nb::arg("strategy_id"));

    nb::enum_<SafeModeState>(m, "SafeModeState")
        .value("NORMAL", SafeModeState::Normal)
        .value("REDUCE_ONLY", SafeModeState::ReduceOnly)
        .value("HALT", SafeModeState::Halt)
        .value("EMERGENCY_SHUTDOWN", SafeModeState::EmergencyShutdown)
        .export_values();

    nb::class_<KillSwitchDecision>(m, "KillSwitchDecision")
        .def(nb::init<>())
        .def_rw("allowed", &KillSwitchDecision::allowed)
        .def_rw("state", &KillSwitchDecision::state)
        .def_rw("global_halt", &KillSwitchDecision::global_halt)
        .def_rw("strategy_halt", &KillSwitchDecision::strategy_halt)
        .def_rw("policy_code", &KillSwitchDecision::policy_code)
        .def_rw("reason", &KillSwitchDecision::reason)
        .def_rw("source", &KillSwitchDecision::source);

    nb::class_<KillSwitchSnapshot>(m, "KillSwitchSnapshot")
        .def(nb::init<>())
        .def_rw("state", &KillSwitchSnapshot::state)
        .def_rw("global_halt", &KillSwitchSnapshot::global_halt)
        .def_rw("strategy_halt_count", &KillSwitchSnapshot::strategy_halt_count)
        .def_rw("emergency_shutdown", &KillSwitchSnapshot::emergency_shutdown)
        .def_rw("last_reason", &KillSwitchSnapshot::last_reason)
        .def_rw("last_source", &KillSwitchSnapshot::last_source);

    nb::class_<KillSwitchController>(m, "KillSwitchController")
        .def(nb::init<>())
        .def("set_reduce_only", &KillSwitchController::set_reduce_only, nb::arg("reason"))
        .def("clear_reduce_only", &KillSwitchController::clear_reduce_only)
        .def("trigger_global_kill_switch", &KillSwitchController::trigger_global_kill_switch, nb::arg("reason"))
        .def("clear_global_kill_switch", &KillSwitchController::clear_global_kill_switch)
        .def(
            "trigger_strategy_kill_switch",
            &KillSwitchController::trigger_strategy_kill_switch,
            nb::arg("strategy_id"),
            nb::arg("reason"))
        .def("clear_strategy_kill_switch", &KillSwitchController::clear_strategy_kill_switch, nb::arg("strategy_id"))
        .def(
            "request_emergency_shutdown",
            &KillSwitchController::request_emergency_shutdown,
            nb::arg("source"),
            nb::arg("reason"))
        .def("clear_emergency_shutdown", &KillSwitchController::clear_emergency_shutdown)
        .def("state", &KillSwitchController::state)
        .def("can_trade", &KillSwitchController::can_trade, nb::arg("strategy_id"))
        .def("state_snapshot", &KillSwitchController::state_snapshot);

    nb::class_<RiskGovernorConfig>(m, "RiskGovernorConfig")
        .def(nb::init<>())
        .def_rw("max_drawdown_frac", &RiskGovernorConfig::max_drawdown_frac)
        .def_rw("max_gross_exposure", &RiskGovernorConfig::max_gross_exposure)
        .def_rw("max_net_exposure", &RiskGovernorConfig::max_net_exposure)
        .def_rw("live_limit_multiplier", &RiskGovernorConfig::live_limit_multiplier)
        .def_rw("backtest_limit_multiplier", &RiskGovernorConfig::backtest_limit_multiplier)
        .def_rw("min_order_size", &RiskGovernorConfig::min_order_size)
        .def_rw("max_order_size", &RiskGovernorConfig::max_order_size)
        .def_rw("max_margin_utilization", &RiskGovernorConfig::max_margin_utilization);

    nb::class_<RiskAccountState>(m, "RiskAccountState")
        .def(nb::init<>())
        .def_rw("equity", &RiskAccountState::equity)
        .def_rw("peak_equity", &RiskAccountState::peak_equity)
        .def_rw("gross_exposure", &RiskAccountState::gross_exposure)
        .def_rw("net_exposure", &RiskAccountState::net_exposure);

    nb::class_<RiskGovernor>(m, "RiskGovernor")
        .def(nb::init<RiskGovernorConfig>(), nb::arg("config") = RiskGovernorConfig{})
        .def("config", &RiskGovernor::config, nb::rv_policy::reference_internal)
        .def("drawdown_frac", &RiskGovernor::drawdown_frac, nb::arg("state"))
        .def(
            "can_trade",
            &RiskGovernor::can_trade,
            nb::arg("state"),
            nb::arg("candidate_gross_add") = 0.0,
            nb::arg("candidate_net_delta") = 0.0)
        .def(
            "can_trade_with_mode",
            &RiskGovernor::can_trade_with_mode,
            nb::arg("state"),
            nb::arg("candidate_size"),
            nb::arg("candidate_gross_add"),
            nb::arg("candidate_net_delta"),
            nb::arg("margin_required"),
            nb::arg("free_margin"),
            nb::arg("mode") = RiskMode::Live);

    nb::class_<RiskRegimeDetector>(m, "RiskRegimeDetector")
        .def(
            nb::init<double, double, double, int, int>(),
            nb::arg("vol_spike_mult") = 1.8,
            nb::arg("corr_spike_level") = 0.55,
            nb::arg("dd_trigger_frac") = 0.05,
            nb::arg("lookback") = 60,
            nb::arg("vol_med_window") = 20)
        .def(
            "detect",
            &RiskRegimeDetector::detect,
            nb::arg("returns_matrix"),
            nb::arg("equity_curve") = std::vector<double>{});

    nb::class_<PositionSizingConfig>(m, "PositionSizingConfig")
        .def(nb::init<>())
        .def_rw("lot_size", &PositionSizingConfig::lot_size)
        .def_rw("initial_balance", &PositionSizingConfig::initial_balance)
        .def_rw("base_lot_size", &PositionSizingConfig::base_lot_size)
        .def_rw("milestone_amount", &PositionSizingConfig::milestone_amount)
        .def_rw("lot_increment", &PositionSizingConfig::lot_increment)
        .def_rw("risk_percent", &PositionSizingConfig::risk_percent)
        .def_rw("kelly_fraction_limit", &PositionSizingConfig::kelly_fraction_limit)
        .def_rw("fraction", &PositionSizingConfig::fraction)
        .def_rw("atr_multiplier", &PositionSizingConfig::atr_multiplier);

    nb::class_<PositionSizer>(m, "PositionSizer")
        .def(nb::init<std::string, PositionSizingConfig>(),
             nb::arg("method") = "fixed_risk",
             nb::arg("config") = PositionSizingConfig{})
        .def(
            "calculate_size",
            &PositionSizer::calculate_size,
            nb::arg("account_balance"),
            nb::arg("entry_price"),
            nb::arg("stop_loss") = 0.0,
            nb::arg("contract_size") = 100000.0,
            nb::arg("atr") = 0.0,
            nb::arg("win_rate") = 0.5,
            nb::arg("avg_win") = 100.0,
            nb::arg("avg_loss") = 50.0)
        .def("method", &PositionSizer::method, nb::rv_policy::reference_internal)
        .def("config", &PositionSizer::config, nb::rv_policy::reference_internal);

    nb::class_<ExposureConstraints>(m, "ExposureConstraints")
        .def(nb::init<>())
        .def_rw("max_total_exposure", &ExposureConstraints::max_total_exposure)
        .def_rw("max_symbol_exposure", &ExposureConstraints::max_symbol_exposure)
        .def_rw("max_strategy_exposure", &ExposureConstraints::max_strategy_exposure)
        .def_rw("max_asset_exposure", &ExposureConstraints::max_asset_exposure);

    nb::class_<RiskBudgetAllocator>(m, "RiskBudgetAllocator")
        .def(nb::init<CorrelationPreference>(), nb::arg("corr_pref") = CorrelationPreference{})
        .def("corr_pref", &RiskBudgetAllocator::corr_pref, nb::rv_policy::reference_internal)
        .def(
            "compute_target_lots",
            &RiskBudgetAllocator::compute_target_lots,
            nb::arg("base_lots"),
            nb::arg("budgets") = std::unordered_map<std::string, double>{},
            nb::arg("corr_map") = std::unordered_map<std::string, double>{})
        .def("lots_to_deltas", &RiskBudgetAllocator::lots_to_deltas, nb::arg("current"), nb::arg("target"))
        .def(
            "apply_exposure_constraints",
            &RiskBudgetAllocator::apply_exposure_constraints,
            nb::arg("target_allocations"),
            nb::arg("symbol_to_strategy"),
            nb::arg("symbol_to_asset"),
            nb::arg("constraints"));

    m.def(
        "validate_position_size",
        &validate_position_size,
        nb::arg("size"),
        nb::arg("min_lot"),
        nb::arg("max_lot"),
        nb::arg("lot_step"),
        nb::arg("max_size") = 0.0,
        nb::arg("allow_fractional") = false);
}
