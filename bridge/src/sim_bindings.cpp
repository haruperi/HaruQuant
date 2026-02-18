/**
 * @file sim_bindings.cpp
 * @brief Nanobind bindings for the hqt::sim simulation API.
 *
 * PR-014: Exposes the full C++ sim API to Python under hqt_engine.sim.
 */

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/optional.h>
#include <nanobind/stl/pair.h>
#include <nanobind/stl/unordered_map.h>
#include <nanobind/stl/function.h>

#include "engine/engine.hpp"

#include <functional>
#include <utility>

namespace nb = nanobind;
using namespace hqt::sim;

namespace {

template <typename Func, typename... Args>
decltype(auto) call_without_gil(Func&& func, Args&&... args) {
    nb::gil_scoped_release release;
    return std::invoke(std::forward<Func>(func), std::forward<Args>(args)...);
}

}  // namespace

void register_sim_bindings(nb::module_& m) {
    // ── Structs ──────────────────────────────────────────────────────

    nb::class_<SimulatorState>(m, "SimulatorState")
        .def(nb::init<>())
        .def_rw("running", &SimulatorState::running)
        .def_rw("paused", &SimulatorState::paused)
        .def_rw("current_time_us", &SimulatorState::current_time_us)
        .def_rw("current_bar_index", &SimulatorState::current_bar_index)
        .def_rw("processed_events", &SimulatorState::processed_events)
        .def("reset", &SimulatorState::reset);

    nb::class_<AccountInfoData>(m, "AccountInfoData")
        .def(nb::init<>())
        .def_rw("login", &AccountInfoData::login)
        .def_rw("leverage", &AccountInfoData::leverage)
        .def_rw("margin_mode", &AccountInfoData::margin_mode)
        .def_rw("trade_allowed", &AccountInfoData::trade_allowed)
        .def_rw("trade_expert", &AccountInfoData::trade_expert)
        .def_rw("balance", &AccountInfoData::balance)
        .def_rw("credit", &AccountInfoData::credit)
        .def_rw("profit", &AccountInfoData::profit)
        .def_rw("equity", &AccountInfoData::equity)
        .def_rw("margin", &AccountInfoData::margin)
        .def_rw("margin_free", &AccountInfoData::margin_free)
        .def_rw("margin_level", &AccountInfoData::margin_level)
        .def_rw("commission_blocked", &AccountInfoData::commission_blocked)
        .def_rw("name", &AccountInfoData::name)
        .def_rw("server", &AccountInfoData::server)
        .def_rw("currency", &AccountInfoData::currency)
        .def_rw("company", &AccountInfoData::company)
        .def("to_dict", &AccountInfoData::to_dict);

    nb::class_<SymbolTickData>(m, "SymbolTickData")
        .def(nb::init<>())
        .def_rw("time", &SymbolTickData::time)
        .def_rw("bid", &SymbolTickData::bid)
        .def_rw("ask", &SymbolTickData::ask)
        .def_rw("last", &SymbolTickData::last)
        .def_rw("volume", &SymbolTickData::volume)
        .def_rw("time_msc", &SymbolTickData::time_msc)
        .def_rw("flags", &SymbolTickData::flags)
        .def_rw("volume_real", &SymbolTickData::volume_real)
        .def("to_dict", &SymbolTickData::to_dict);

    nb::class_<SymbolInfoData>(m, "SymbolInfoData")
        .def(nb::init<>())
        .def_rw("symbol", &SymbolInfoData::symbol)
        .def_rw("digits", &SymbolInfoData::digits)
        .def_rw("spread", &SymbolInfoData::spread)
        .def_rw("spread_float", &SymbolInfoData::spread_float)
        .def_rw("point", &SymbolInfoData::point)
        .def_rw("trade_calc_mode", &SymbolInfoData::trade_calc_mode)
        .def_rw("trade_mode", &SymbolInfoData::trade_mode)
        .def_rw("trade_stops_level", &SymbolInfoData::trade_stops_level)
        .def_rw("trade_freeze_level", &SymbolInfoData::trade_freeze_level)
        .def_rw("trade_exemode", &SymbolInfoData::trade_exemode)
        .def_rw("volume_min", &SymbolInfoData::volume_min)
        .def_rw("volume_max", &SymbolInfoData::volume_max)
        .def_rw("volume_step", &SymbolInfoData::volume_step)
        .def_rw("volume_limit", &SymbolInfoData::volume_limit)
        .def_rw("trade_tick_value", &SymbolInfoData::trade_tick_value)
        .def_rw("trade_tick_value_profit", &SymbolInfoData::trade_tick_value_profit)
        .def_rw("trade_tick_value_loss", &SymbolInfoData::trade_tick_value_loss)
        .def_rw("trade_tick_size", &SymbolInfoData::trade_tick_size)
        .def_rw("trade_contract_size", &SymbolInfoData::trade_contract_size)
        .def_rw("margin_initial", &SymbolInfoData::margin_initial)
        .def_rw("swap_mode", &SymbolInfoData::swap_mode)
        .def_rw("swap_long", &SymbolInfoData::swap_long)
        .def_rw("swap_short", &SymbolInfoData::swap_short)
        .def_rw("swap_rollover3days", &SymbolInfoData::swap_rollover3days)
        .def_rw("bid", &SymbolInfoData::bid)
        .def_rw("ask", &SymbolInfoData::ask)
        .def_rw("last", &SymbolInfoData::last)
        .def_rw("select", &SymbolInfoData::select)
        .def_rw("visible", &SymbolInfoData::visible)
        .def("to_dict", &SymbolInfoData::to_dict);

    nb::class_<TradeRecordData>(m, "TradeRecordData")
        .def(nb::init<>())
        .def_rw("ticket", &TradeRecordData::ticket)
        .def_rw("order", &TradeRecordData::order)
        .def_rw("time", &TradeRecordData::time)
        .def_rw("time_msc", &TradeRecordData::time_msc)
        .def_rw("expiration", &TradeRecordData::expiration)
        .def_rw("type", &TradeRecordData::type)
        .def_rw("type_time", &TradeRecordData::type_time)
        .def_rw("magic", &TradeRecordData::magic)
        .def_rw("identifier", &TradeRecordData::identifier)
        .def_rw("reason", &TradeRecordData::reason)
        .def_rw("volume", &TradeRecordData::volume)
        .def_rw("price_open", &TradeRecordData::price_open)
        .def_rw("sl", &TradeRecordData::sl)
        .def_rw("tp", &TradeRecordData::tp)
        .def_rw("price_current", &TradeRecordData::price_current)
        .def_rw("swap", &TradeRecordData::swap)
        .def_rw("profit", &TradeRecordData::profit)
        .def_rw("symbol", &TradeRecordData::symbol)
        .def_rw("comment", &TradeRecordData::comment)
        .def("to_dict", &TradeRecordData::to_dict);

    nb::class_<TradeRequest>(m, "TradeRequest")
        .def(nb::init<>())
        .def_rw("action", &TradeRequest::action)
        .def_rw("type", &TradeRequest::type)
        .def_rw("order", &TradeRequest::order)
        .def_rw("client_order_id", &TradeRequest::client_order_id)
        .def_rw("symbol", &TradeRequest::symbol)
        .def_rw("volume", &TradeRequest::volume)
        .def_rw("price", &TradeRequest::price)
        .def_rw("stoplimit", &TradeRequest::stoplimit)
        .def_rw("sl", &TradeRequest::sl)
        .def_rw("tp", &TradeRequest::tp)
        .def_rw("type_time", &TradeRequest::type_time)
        .def_rw("expiration", &TradeRequest::expiration)
        .def_rw("comment", &TradeRequest::comment);

    nb::class_<TradeResult>(m, "TradeResult")
        .def(nb::init<>())
        .def_rw("retcode", &TradeResult::retcode)
        .def_rw("deal", &TradeResult::deal)
        .def_rw("order", &TradeResult::order)
        .def_rw("volume", &TradeResult::volume)
        .def_rw("price", &TradeResult::price)
        .def_rw("bid", &TradeResult::bid)
        .def_rw("ask", &TradeResult::ask)
        .def_rw("comment", &TradeResult::comment);

    nb::class_<BacktestBarStep>(m, "BacktestBarStep")
        .def(nb::init<>())
        .def_rw("time_msc", &BacktestBarStep::time_msc)
        .def_rw("close", &BacktestBarStep::close)
        .def_rw("spread_points", &BacktestBarStep::spread_points)
        .def_rw("entry_signal", &BacktestBarStep::entry_signal)
        .def_rw("exit_signal", &BacktestBarStep::exit_signal)
        .def_rw("sl", &BacktestBarStep::sl)
        .def_rw("tp", &BacktestBarStep::tp);

    nb::class_<PositionTotals>(m, "PositionTotals")
        .def(nb::init<>())
        .def_rw("profit", &PositionTotals::profit)
        .def_rw("margin", &PositionTotals::margin)
        .def_rw("commission", &PositionTotals::commission)
        .def_rw("fee", &PositionTotals::fee)
        .def_rw("swap", &PositionTotals::swap);

    nb::class_<PositionAggregate>(m, "PositionAggregate")
        .def(nb::init<>())
        .def_rw("net_volume", &PositionAggregate::net_volume)
        .def_rw("long_volume", &PositionAggregate::long_volume)
        .def_rw("short_volume", &PositionAggregate::short_volume)
        .def_rw("margin", &PositionAggregate::margin)
        .def_rw("realized_pnl", &PositionAggregate::realized_pnl)
        .def_rw("unrealized_pnl", &PositionAggregate::unrealized_pnl);

    nb::class_<TickModelBar>(m, "TickModelBar")
        .def(nb::init<>())
        .def_rw("time_msc", &TickModelBar::time_msc)
        .def_rw("open", &TickModelBar::open)
        .def_rw("high", &TickModelBar::high)
        .def_rw("low", &TickModelBar::low)
        .def_rw("close", &TickModelBar::close)
        .def_rw("spread_points", &TickModelBar::spread_points);

    nb::class_<ModelTick>(m, "ModelTick")
        .def(nb::init<>())
        .def_rw("time_msc", &ModelTick::time_msc)
        .def_rw("bid", &ModelTick::bid)
        .def_rw("ask", &ModelTick::ask)
        .def_rw("last", &ModelTick::last)
        .def("__eq__", [](const ModelTick& self, const ModelTick& other) {
            return self == other;
        });

    nb::class_<TradeRecord>(m, "TradeRecord")
        .def(nb::init<>())
        .def_rw("ticket", &TradeRecord::ticket)
        .def_rw("symbol", &TradeRecord::symbol)
        .def_rw("is_buy", &TradeRecord::is_buy)
        .def_rw("volume", &TradeRecord::volume)
        .def_rw("open_price", &TradeRecord::open_price)
        .def_rw("close_price", &TradeRecord::close_price)
        .def_rw("stop_loss", &TradeRecord::stop_loss)
        .def_rw("take_profit", &TradeRecord::take_profit)
        .def_rw("open_time_msc", &TradeRecord::open_time_msc)
        .def_rw("close_time_msc", &TradeRecord::close_time_msc)
        .def_rw("time_in_trade_seconds", &TradeRecord::time_in_trade_seconds)
        .def_rw("bars_in_trade", &TradeRecord::bars_in_trade)
        .def_rw("initial_risk_usd", &TradeRecord::initial_risk_usd)
        .def_rw("profit_loss", &TradeRecord::profit_loss)
        .def_rw("mae_usd", &TradeRecord::mae_usd)
        .def_rw("mfe_usd", &TradeRecord::mfe_usd)
        .def_rw("r_multiple", &TradeRecord::r_multiple);

    nb::class_<PortfolioSymbolInput>(m, "PortfolioSymbolInput")
        .def(nb::init<>())
        .def_rw("symbol", &PortfolioSymbolInput::symbol)
        .def_rw("bars", &PortfolioSymbolInput::bars);

    nb::class_<ExposureConstraints>(m, "ExposureConstraints")
        .def(nb::init<>())
        .def_rw("max_total_exposure", &ExposureConstraints::max_total_exposure)
        .def_rw("max_symbol_exposure", &ExposureConstraints::max_symbol_exposure)
        .def_rw("max_strategy_exposure", &ExposureConstraints::max_strategy_exposure)
        .def_rw("max_asset_exposure", &ExposureConstraints::max_asset_exposure);

    nb::class_<RebalancePolicy>(m, "RebalancePolicy")
        .def(nb::init<>())
        .def_rw("schedule_interval_msc", &RebalancePolicy::schedule_interval_msc)
        .def_rw("drift_threshold", &RebalancePolicy::drift_threshold);

    nb::class_<ResultMetricsSummary>(m, "ResultMetricsSummary")
        .def(nb::init<>())
        .def_rw("initial_balance", &ResultMetricsSummary::initial_balance)
        .def_rw("final_balance", &ResultMetricsSummary::final_balance)
        .def_rw("total_return", &ResultMetricsSummary::total_return)
        .def_rw("total_return_pct", &ResultMetricsSummary::total_return_pct)
        .def_rw("total_trades", &ResultMetricsSummary::total_trades)
        .def_rw("winning_trades", &ResultMetricsSummary::winning_trades)
        .def_rw("losing_trades", &ResultMetricsSummary::losing_trades)
        .def_rw("breakeven_trades", &ResultMetricsSummary::breakeven_trades)
        .def_rw("win_rate", &ResultMetricsSummary::win_rate)
        .def_rw("gross_profit", &ResultMetricsSummary::gross_profit)
        .def_rw("gross_loss", &ResultMetricsSummary::gross_loss)
        .def_rw("profit_factor", &ResultMetricsSummary::profit_factor)
        .def_rw("max_drawdown", &ResultMetricsSummary::max_drawdown)
        .def_rw("max_drawdown_pct", &ResultMetricsSummary::max_drawdown_pct)
        .def_rw("sharpe_ratio", &ResultMetricsSummary::sharpe_ratio);

    // ── Enum ─────────────────────────────────────────────────────────

    nb::enum_<AutoCloseReason>(m, "AutoCloseReason")
        .value("StopLoss", AutoCloseReason::StopLoss)
        .value("TakeProfit", AutoCloseReason::TakeProfit);

    nb::enum_<OmsOrderState>(m, "OmsOrderState")
        .value("Unknown", OmsOrderState::Unknown)
        .value("New", OmsOrderState::New)
        .value("Accepted", OmsOrderState::Accepted)
        .value("PartiallyFilled", OmsOrderState::PartiallyFilled)
        .value("Filled", OmsOrderState::Filled)
        .value("Canceled", OmsOrderState::Canceled)
        .value("Expired", OmsOrderState::Expired)
        .value("Rejected", OmsOrderState::Rejected);

    // ── SimulatorClient ──────────────────────────────────────────────

    nb::class_<SimulatorClient>(m, "SimulatorClient")
        .def(nb::init<>())
        .def(nb::init<AccountInfoData>())
        .def("account_info", &SimulatorClient::account_info,
             nb::rv_policy::reference_internal)
        .def("symbol_info", [](const SimulatorClient& self, const std::string& symbol)
                -> std::optional<SymbolInfoData> {
            const auto* p = self.symbol_info(symbol);
            if (p) return *p;
            return std::nullopt;
        })
        .def("symbol_info_tick", [](const SimulatorClient& self, const std::string& symbol)
                -> std::optional<SymbolTickData> {
            const auto* p = self.symbol_info_tick(symbol);
            if (p) return *p;
            return std::nullopt;
        })
        .def("positions_get", [](const SimulatorClient& self,
                                  std::optional<uint64_t> ticket,
                                  std::optional<std::string> symbol) {
            std::optional<std::string_view> sv;
            if (symbol) sv = *symbol;
            return self.positions_get(ticket, sv);
        }, nb::arg("ticket") = nb::none(), nb::arg("symbol") = nb::none())
        .def("orders_get", [](const SimulatorClient& self,
                               std::optional<uint64_t> ticket,
                               std::optional<std::string> symbol) {
            std::optional<std::string_view> sv;
            if (symbol) sv = *symbol;
            return self.orders_get(ticket, sv);
        }, nb::arg("ticket") = nb::none(), nb::arg("symbol") = nb::none())
        .def("history_orders_get", &SimulatorClient::history_orders_get,
             nb::arg("ticket") = nb::none())
        .def("history_deals_get", &SimulatorClient::history_deals_get,
             nb::arg("ticket") = nb::none())
        .def("last_error", &SimulatorClient::last_error)
        .def("trade_retcode_description", &SimulatorClient::trade_retcode_description)
        .def("order_calc_margin", &SimulatorClient::order_calc_margin)
        .def("order_calc_profit", &SimulatorClient::order_calc_profit)
        .def("order_send", &SimulatorClient::order_send)
        .def("close_position", &SimulatorClient::close_position)
        .def("order_state", &SimulatorClient::order_state)
        .def("order_state_name", &SimulatorClient::order_state_name)
        .def("idempotency_cache_size", &SimulatorClient::idempotency_cache_size)
        .def("set_history_order_state", &SimulatorClient::set_history_order_state)
        .def("set_history_order_done_time", &SimulatorClient::set_history_order_done_time)
        .def("set_account_info", &SimulatorClient::set_account_info)
        .def("set_symbol_info", &SimulatorClient::set_symbol_info)
        .def("set_symbol_tick", &SimulatorClient::set_symbol_tick)
        .def("upsert_position", &SimulatorClient::upsert_position)
        .def("upsert_order", &SimulatorClient::upsert_order)
        .def("upsert_history_order", &SimulatorClient::upsert_history_order)
        .def("upsert_deal", &SimulatorClient::upsert_deal)
        .def("set_last_error", &SimulatorClient::set_last_error);

    // ── BacktestEngine ───────────────────────────────────────────────

    nb::class_<BacktestEngine>(m, "BacktestEngine")
        .def(nb::init<SimulatorClient&>(), nb::keep_alive<1, 2>())
        .def("set_on_bar_processed", [](BacktestEngine& self, nb::object callback) {
            self.set_on_bar_processed(
                [callback](std::size_t index, const BacktestBarStep& bar,
                           const SimulatorState& state) {
                    nb::gil_scoped_acquire gil;
                    callback(index, bar, state);
                });
        })
        .def("run_trading_timeframe",
             [](BacktestEngine& self, const std::string& symbol, double volume,
                const std::vector<BacktestBarStep>& bars) {
                 call_without_gil([&]() {
                     self.run_trading_timeframe(symbol, volume, bars);
                 });
             })
        .def("run_trading_timeframe_with_ticks",
             [](BacktestEngine& self, const std::string& symbol, double volume,
                const std::vector<BacktestBarStep>& bars,
                const std::vector<ModelTick>& ticks) {
                 call_without_gil([&]() {
                     self.run_trading_timeframe_with_ticks(symbol, volume, bars, ticks);
                 });
             })
        .def("state", &BacktestEngine::state,
             nb::rv_policy::reference_internal)
        .def("account_snapshot", &BacktestEngine::account_snapshot,
             nb::rv_policy::reference_internal)
        .def("close_reason", &BacktestEngine::close_reason)
        .def("completed_trades", &BacktestEngine::completed_trades,
             nb::rv_policy::reference_internal);

    // ── AccountMonitor ───────────────────────────────────────────────

    nb::class_<AccountMonitor>(m, "AccountMonitor")
        .def(nb::init<>())
        .def("monitor_positions", &AccountMonitor::monitor_positions)
        .def("monitor_account", &AccountMonitor::monitor_account);

    nb::class_<PortfolioState>(m, "PortfolioState")
        .def(nb::init<double, std::string>(), nb::arg("initial_balance") = 10000.0, nb::arg("currency") = "USD")
        .def("reset", &PortfolioState::reset, nb::arg("initial_balance") = 10000.0, nb::arg("currency") = "USD")
        .def("set_capital", &PortfolioState::set_capital, nb::arg("balance"), nb::arg("credit") = 0.0)
        .def("upsert_position",
             &PortfolioState::upsert_position,
             nb::arg("strategy_id"),
             nb::arg("symbol"),
             nb::arg("net_volume"),
             nb::arg("margin"),
             nb::arg("unrealized_pnl"))
        .def("clear_position", &PortfolioState::clear_position, nb::arg("strategy_id"), nb::arg("symbol"))
        .def("apply_realized_pnl",
             &PortfolioState::apply_realized_pnl,
             nb::arg("strategy_id"),
             nb::arg("symbol"),
             nb::arg("realized_pnl"),
             nb::arg("commission") = 0.0,
             nb::arg("swap") = 0.0)
        .def("account_snapshot", &PortfolioState::account_snapshot)
        .def("total_realized_pnl", &PortfolioState::total_realized_pnl)
        .def("total_unrealized_pnl", &PortfolioState::total_unrealized_pnl)
        .def("positions_by_symbol", &PortfolioState::positions_by_symbol)
        .def("positions_by_strategy", &PortfolioState::positions_by_strategy, nb::arg("strategy_id"));

    // ── TickModel ────────────────────────────────────────────────────

    nb::class_<TickModel>(m, "TickModel")
        .def_static("generate_m1_ohlc", &TickModel::generate_m1_ohlc)
        .def_static("generate_synthetic_ticks", &TickModel::generate_synthetic_ticks,
                     nb::arg("bars"), nb::arg("point"),
                     nb::arg("spread_default_points"),
                     nb::arg("support_points") = 2)
        .def_static("passthrough_real_ticks", &TickModel::passthrough_real_ticks);

    // ── TradeRecordTracker ───────────────────────────────────────────

    nb::class_<TradeRecordTracker>(m, "TradeRecordTracker")
        .def(nb::init<>())
        .def("reset", &TradeRecordTracker::reset)
        .def("has_open", &TradeRecordTracker::has_open)
        .def("on_open", &TradeRecordTracker::on_open)
        .def("on_update", &TradeRecordTracker::on_update)
        .def("on_close", &TradeRecordTracker::on_close)
        .def("completed_trades", &TradeRecordTracker::completed_trades,
             nb::rv_policy::reference_internal);

    // ── PortfolioEngine ──────────────────────────────────────────────

    nb::class_<PortfolioEngine>(m, "PortfolioEngine")
        .def(nb::init<SimulatorClient&>(), nb::keep_alive<1, 2>())
        .def("run_equal_weight",
             [](PortfolioEngine& self, const std::vector<PortfolioSymbolInput>& inputs,
                double base_volume) {
                 call_without_gil([&]() {
                     self.run_equal_weight(inputs, base_volume);
                 });
             })
        .def("run_with_allocations",
             [](PortfolioEngine& self, const std::vector<PortfolioSymbolInput>& inputs,
                double base_volume,
                const std::unordered_map<std::string, double>& allocations) {
                 call_without_gil([&]() {
                     self.run_with_allocations(inputs, base_volume, allocations);
                 });
             })
        .def("effective_allocations", &PortfolioEngine::effective_allocations,
             nb::rv_policy::reference_internal);

    nb::class_<PortfolioAllocator>(m, "PortfolioAllocator")
        .def_static("equal_weight", &PortfolioAllocator::equal_weight,
                    nb::arg("symbols"), nb::arg("max_total_exposure") = 1.0)
        .def_static("risk_parity", &PortfolioAllocator::risk_parity,
                    nb::arg("symbol_volatility"), nb::arg("max_total_exposure") = 1.0)
        .def_static("custom", &PortfolioAllocator::custom,
                    nb::arg("raw_weights"), nb::arg("max_total_exposure") = 1.0, nb::arg("normalize") = true)
        .def_static("apply_exposure_constraints", &PortfolioAllocator::apply_exposure_constraints,
                    nb::arg("target_allocations"),
                    nb::arg("symbol_to_strategy"),
                    nb::arg("symbol_to_asset"),
                    nb::arg("constraints"));

    nb::class_<RebalanceController>(m, "RebalanceController")
        .def(nb::init<RebalancePolicy>(), nb::arg("policy"))
        .def("should_rebalance", &RebalanceController::should_rebalance,
             nb::arg("now_msc"), nb::arg("current_allocations"), nb::arg("target_allocations"))
        .def("mark_rebalanced", &RebalanceController::mark_rebalanced, nb::arg("now_msc"))
        .def("last_rebalance_msc", &RebalanceController::last_rebalance_msc);

    // ── ResultMetrics ────────────────────────────────────────────────

    nb::class_<ResultMetrics>(m, "ResultMetrics")
        .def_static("from_trades", &ResultMetrics::from_trades);

    // ── Free functions ───────────────────────────────────────────────

    m.def("calc_margin", &calc_margin,
          "Calculate required margin using MT5-like calc mode semantics.");
    m.def("calc_profit", &calc_profit,
          "Calculate profit for BUY/SELL actions.");
}
