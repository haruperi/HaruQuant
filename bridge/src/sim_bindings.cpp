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
#include <nanobind/stl/unordered_set.h>
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

hqt::AccountInfo to_mt5_account(const hqt::AccountInfo& src) {
    return src;
}

hqt::SymbolInfo to_mt5_symbol(const hqt::SymbolInfo& src) {
    return src;
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

    nb::class_<hqt::AccountInfo>(m, "AccountInfo")
        .def(nb::init<double, const std::string&, int>(),
             nb::arg("initial_balance") = 10000.0,
             nb::arg("currency") = "USD",
             nb::arg("leverage") = 100)
        .def_prop_rw("login",
            [](const hqt::AccountInfo& self) { return self.Login(); },
            [](hqt::AccountInfo& self, int value) { self.SetLogin(value); })
        .def_prop_rw("name",
            [](const hqt::AccountInfo& self) { return self.Name(); },
            [](hqt::AccountInfo& self, const std::string& value) { self.SetName(value); })
        .def_prop_rw("server",
            [](const hqt::AccountInfo& self) { return self.Server(); },
            [](hqt::AccountInfo& self, const std::string& value) { self.SetServer(value); })
        .def_prop_rw("company",
            [](const hqt::AccountInfo& self) { return self.Company(); },
            [](hqt::AccountInfo& self, const std::string& value) { self.SetCompany(value); })
        .def_prop_rw("leverage",
            [](const hqt::AccountInfo& self) { return self.Leverage(); },
            [](hqt::AccountInfo& self, int value) { self.SetLeverage(value); })
        .def_prop_ro("currency", &hqt::AccountInfo::Currency)
        .def_prop_ro("balance", &hqt::AccountInfo::Balance)
        .def_prop_ro("credit", &hqt::AccountInfo::Credit)
        .def_prop_ro("profit", &hqt::AccountInfo::Profit)
        .def_prop_ro("equity", &hqt::AccountInfo::Equity)
        .def_prop_ro("margin", &hqt::AccountInfo::Margin)
        .def_prop_ro("margin_free", &hqt::AccountInfo::FreeMargin)
        .def_prop_ro("margin_level", &hqt::AccountInfo::MarginLevel)
        .def_prop_rw("margin_mode",
            [](const hqt::AccountInfo& self) { return static_cast<int>(self.MarginMode()); },
            [](hqt::AccountInfo& self, int value) {
                self.SetMarginMode(static_cast<hqt::ENUM_ACCOUNT_MARGIN_MODE>(value));
            })
        .def_prop_rw("trade_allowed",
            [](const hqt::AccountInfo& self) { return self.TradeAllowed(); },
            [](hqt::AccountInfo& self, bool value) { self.SetTradeAllowed(value); })
        .def_prop_rw("trade_expert",
            [](const hqt::AccountInfo& self) { return self.TradeExpert(); },
            [](hqt::AccountInfo& self, bool value) { self.SetTradeExpert(value); });

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

    nb::class_<hqt::SymbolInfo>(m, "SymbolInfo")
        .def(nb::init<>())
        .def_prop_rw("symbol",
            [](const hqt::SymbolInfo& self) { return self.Name(); },
            [](hqt::SymbolInfo& self, const std::string& value) { self.Name(value); })
        .def_prop_rw("digits",
            [](const hqt::SymbolInfo& self) { return self.Digits(); },
            [](hqt::SymbolInfo& self, int value) { self.SetDigits(value); })
        .def_prop_rw("spread",
            [](const hqt::SymbolInfo& self) { return self.Spread(); },
            [](hqt::SymbolInfo& self, int value) { self.SetSpread(value); })
        .def_prop_rw("spread_float",
            [](const hqt::SymbolInfo& self) { return self.SpreadFloat(); },
            [](hqt::SymbolInfo& self, bool value) { self.SetSpreadFloat(value); })
        .def_prop_rw("point",
            [](const hqt::SymbolInfo& self) { return self.Point(); },
            [](hqt::SymbolInfo& self, double value) { self.SetPoint(value); })
        .def_prop_rw("trade_calc_mode",
            [](const hqt::SymbolInfo& self) { return static_cast<int>(self.TradeCalcMode()); },
            [](hqt::SymbolInfo& self, int value) {
                self.SetTradeCalcMode(static_cast<hqt::ENUM_SYMBOL_CALC_MODE>(value));
            })
        .def_prop_rw("trade_mode",
            [](const hqt::SymbolInfo& self) { return static_cast<int>(self.TradeMode()); },
            [](hqt::SymbolInfo& self, int value) {
                self.SetTradeMode(static_cast<hqt::ENUM_SYMBOL_TRADE_MODE>(value));
            })
        .def_prop_rw("trade_stops_level",
            [](const hqt::SymbolInfo& self) { return self.StopsLevel(); },
            [](hqt::SymbolInfo& self, int value) { self.SetStopsLevel(value); })
        .def_prop_rw("trade_freeze_level",
            [](const hqt::SymbolInfo& self) { return self.FreezeLevel(); },
            [](hqt::SymbolInfo& self, int value) { self.SetFreezeLevel(value); })
        .def_prop_rw("trade_exemode",
            [](const hqt::SymbolInfo& self) { return static_cast<int>(self.TradeExecution()); },
            [](hqt::SymbolInfo& self, int value) {
                self.SetTradeExecution(static_cast<hqt::ENUM_SYMBOL_TRADE_EXECUTION>(value));
            })
        .def_prop_rw("volume_min",
            [](const hqt::SymbolInfo& self) { return self.LotsMin(); },
            [](hqt::SymbolInfo& self, double value) { self.SetVolumeMin(value); })
        .def_prop_rw("volume_max",
            [](const hqt::SymbolInfo& self) { return self.LotsMax(); },
            [](hqt::SymbolInfo& self, double value) { self.SetVolumeMax(value); })
        .def_prop_rw("volume_step",
            [](const hqt::SymbolInfo& self) { return self.LotsStep(); },
            [](hqt::SymbolInfo& self, double value) { self.SetVolumeStep(value); })
        .def_prop_rw("volume_limit",
            [](const hqt::SymbolInfo& self) { return self.LotsLimit(); },
            [](hqt::SymbolInfo& self, double value) { self.SetVolumeLimit(value); })
        .def_prop_rw("trade_tick_value",
            [](const hqt::SymbolInfo& self) { return self.TickValue(); },
            [](hqt::SymbolInfo& self, double value) { self.SetTickValue(value); })
        .def_prop_rw("trade_tick_value_profit",
            [](const hqt::SymbolInfo& self) { return self.TickValueProfit(); },
            [](hqt::SymbolInfo& self, double value) { self.SetTickValueProfit(value); })
        .def_prop_rw("trade_tick_value_loss",
            [](const hqt::SymbolInfo& self) { return self.TickValueLoss(); },
            [](hqt::SymbolInfo& self, double value) { self.SetTickValueLoss(value); })
        .def_prop_rw("trade_tick_size",
            [](const hqt::SymbolInfo& self) { return self.TickSize(); },
            [](hqt::SymbolInfo& self, double value) { self.SetTickSize(value); })
        .def_prop_rw("trade_contract_size",
            [](const hqt::SymbolInfo& self) { return self.ContractSize(); },
            [](hqt::SymbolInfo& self, double value) { self.SetContractSize(value); })
        .def_prop_rw("margin_initial",
            [](const hqt::SymbolInfo& self) { return self.MarginInitial(); },
            [](hqt::SymbolInfo& self, double value) { self.SetMarginInitial(value); })
        .def_prop_rw("swap_mode",
            [](const hqt::SymbolInfo& self) { return static_cast<int>(self.SwapMode()); },
            [](hqt::SymbolInfo& self, int value) {
                self.SetSwapMode(static_cast<hqt::ENUM_SYMBOL_SWAP_MODE>(value));
            })
        .def_prop_rw("swap_long",
            [](const hqt::SymbolInfo& self) { return self.SwapLong(); },
            [](hqt::SymbolInfo& self, double value) { self.SetSwapLong(value); })
        .def_prop_rw("swap_short",
            [](const hqt::SymbolInfo& self) { return self.SwapShort(); },
            [](hqt::SymbolInfo& self, double value) { self.SetSwapShort(value); })
        .def_prop_rw("swap_rollover3days",
            [](const hqt::SymbolInfo& self) { return static_cast<int>(self.SwapRollover3days()); },
            [](hqt::SymbolInfo& self, int value) {
                self.SetSwapRollover3days(static_cast<hqt::ENUM_DAY_OF_WEEK>(value));
            })
        .def_prop_rw("select",
            [](const hqt::SymbolInfo& self) { return self.Select(); },
            [](hqt::SymbolInfo& self, bool value) { self.Select(value); })
        .def_prop_rw("visible",
            [](const hqt::SymbolInfo& self) { return self.Select(); },
            [](hqt::SymbolInfo& self, bool value) { self.Select(value); })
        .def_prop_rw("bid",
            [](const hqt::SymbolInfo& self) { return self.Bid(); },
            [](hqt::SymbolInfo& self, double value) { self.UpdatePrice(value, self.Ask(), self.Time()); })
        .def_prop_rw("ask",
            [](const hqt::SymbolInfo& self) { return self.Ask(); },
            [](hqt::SymbolInfo& self, double value) { self.UpdatePrice(self.Bid(), value, self.Time()); })
        .def_prop_ro("last", &hqt::SymbolInfo::Last)
        .def("update_price", &hqt::SymbolInfo::UpdatePrice,
             nb::arg("bid"), nb::arg("ask"), nb::arg("timestamp") = 0);

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

    nb::class_<PositionLeg>(m, "PositionLeg")
        .def(nb::init<>())
        .def_rw("leg_id", &PositionLeg::leg_id)
        .def_rw("is_buy", &PositionLeg::is_buy)
        .def_rw("volume", &PositionLeg::volume)
        .def_rw("price", &PositionLeg::price)
        .def_rw("time_msc", &PositionLeg::time_msc);

    nb::class_<FillEvent>(m, "FillEvent")
        .def(nb::init<>())
        .def_rw("symbol", &FillEvent::symbol)
        .def_rw("is_buy", &FillEvent::is_buy)
        .def_rw("volume", &FillEvent::volume)
        .def_rw("price", &FillEvent::price)
        .def_rw("commission", &FillEvent::commission)
        .def_rw("swap", &FillEvent::swap)
        .def_rw("time_msc", &FillEvent::time_msc);

    nb::class_<ReconciliationReport>(m, "ReconciliationReport")
        .def(nb::init<>())
        .def_rw("ok", &ReconciliationReport::ok)
        .def_rw("trigger", &ReconciliationReport::trigger)
        .def_rw("position_mismatch_count", &ReconciliationReport::position_mismatch_count)
        .def_rw("account_mismatch_count", &ReconciliationReport::account_mismatch_count)
        .def_rw("issues", &ReconciliationReport::issues)
        .def_rw("severity", &ReconciliationReport::severity)
        .def_rw("requires_manual_resolution", &ReconciliationReport::requires_manual_resolution)
        .def_rw("block_new_orders", &ReconciliationReport::block_new_orders);

    nb::class_<BrokerSnapshot>(m, "BrokerSnapshot")
        .def(nb::init<>())
        .def_prop_rw(
            "account",
            [](const BrokerSnapshot& self) {
                return to_mt5_account(self.account);
            },
            [](BrokerSnapshot& self, const hqt::AccountInfo& account) {
                self.account = account;
            })
        .def_rw("positions", &BrokerSnapshot::positions);

    nb::class_<EscalationDecision>(m, "EscalationDecision")
        .def(nb::init<>())
        .def_rw("allow_new_orders", &EscalationDecision::allow_new_orders)
        .def_rw("requires_manual_resolution", &EscalationDecision::requires_manual_resolution)
        .def_rw("escalate_alert", &EscalationDecision::escalate_alert)
        .def_rw("policy", &EscalationDecision::policy)
        .def_rw("reason", &EscalationDecision::reason);

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

    nb::enum_<PositionMode>(m, "PositionMode")
        .value("Netting", PositionMode::Netting)
        .value("Hedging", PositionMode::Hedging);

    nb::enum_<ReconcilePolicy>(m, "ReconcilePolicy")
        .value("Auto", ReconcilePolicy::Auto)
        .value("Manual", ReconcilePolicy::Manual);

    nb::enum_<OmsOrderState>(m, "OmsOrderState")
        .value("Unknown", OmsOrderState::Unknown)
        .value("New", OmsOrderState::New)
        .value("Accepted", OmsOrderState::Accepted)
        .value("PartiallyFilled", OmsOrderState::PartiallyFilled)
        .value("Filled", OmsOrderState::Filled)
        .value("Canceled", OmsOrderState::Canceled)
        .value("Expired", OmsOrderState::Expired)
        .value("Rejected", OmsOrderState::Rejected);

    // ── TradeSimulator ──────────────────────────────────────────────

    nb::class_<TradeSimulator>(m, "TradeSimulator")
        .def(nb::init<>())
        .def(nb::init<hqt::AccountInfo>())
        .def("account_info", [](const TradeSimulator& self) {
            return to_mt5_account(self.account_info());
        })
        .def("symbol_info", [](const TradeSimulator& self, const std::string& symbol)
                -> std::optional<hqt::SymbolInfo> {
            const auto* p = self.symbol_info(symbol);
            if (p) return to_mt5_symbol(*p);
            return std::nullopt;
        })
        .def("symbol_info_tick", [](const TradeSimulator& self, const std::string& symbol)
                -> std::optional<SymbolTickData> {
            const auto* p = self.symbol_info_tick(symbol);
            if (p) return *p;
            return std::nullopt;
        })
        .def("positions_get", [](const TradeSimulator& self,
                                  std::optional<uint64_t> ticket,
                                  std::optional<std::string> symbol) {
            std::optional<std::string_view> sv;
            if (symbol) sv = *symbol;
            return self.positions_get(ticket, sv);
        }, nb::arg("ticket") = nb::none(), nb::arg("symbol") = nb::none())
        .def("orders_get", [](const TradeSimulator& self,
                               std::optional<uint64_t> ticket,
                               std::optional<std::string> symbol) {
            std::optional<std::string_view> sv;
            if (symbol) sv = *symbol;
            return self.orders_get(ticket, sv);
        }, nb::arg("ticket") = nb::none(), nb::arg("symbol") = nb::none())
        .def("history_orders_get", &TradeSimulator::history_orders_get,
             nb::arg("ticket") = nb::none())
        .def("history_deals_get", &TradeSimulator::history_deals_get,
             nb::arg("ticket") = nb::none())
        .def("last_error", &TradeSimulator::last_error)
        .def("trade_retcode_description", &TradeSimulator::trade_retcode_description)
        .def("order_calc_margin", &TradeSimulator::order_calc_margin)
        .def("order_calc_profit", &TradeSimulator::order_calc_profit)
        .def("order_send", &TradeSimulator::order_send)
        .def("close_position", &TradeSimulator::close_position)
        .def("order_state", &TradeSimulator::order_state)
        .def("order_state_name", &TradeSimulator::order_state_name)
        .def("idempotency_cache_size", &TradeSimulator::idempotency_cache_size)
        .def("set_history_order_state", &TradeSimulator::set_history_order_state)
        .def("set_history_order_done_time", &TradeSimulator::set_history_order_done_time)
        .def("set_account_info", [](TradeSimulator& self, const hqt::AccountInfo& data) {
            self.set_account_info(data);
        })
        .def("set_symbol_info", [](TradeSimulator& self, const hqt::SymbolInfo& data) {
            self.set_symbol_info(data);
        })
        .def("set_symbol_tick", &TradeSimulator::set_symbol_tick)
        .def("upsert_position", &TradeSimulator::upsert_position)
        .def("upsert_order", &TradeSimulator::upsert_order)
        .def("upsert_history_order", &TradeSimulator::upsert_history_order)
        .def("upsert_deal", &TradeSimulator::upsert_deal)
        .def("set_last_error", &TradeSimulator::set_last_error);

    nb::class_<MockBroker>(m, "MockBroker")
        .def(nb::init<>())
        .def(nb::init<TradeSimulator>())
        .def("connect", &MockBroker::connect)
        .def("submit", &MockBroker::submit, nb::arg("request"))
        .def("cancel", &MockBroker::cancel, nb::arg("order_id"))
        .def("fetch_state", &MockBroker::fetch_state)
        .def("set_partial_fill_ratio", &MockBroker::set_partial_fill_ratio, nb::arg("ratio"))
        .def("set_deterministic_price", &MockBroker::set_deterministic_price, nb::arg("price"))
        .def("clear_deterministic_price", &MockBroker::clear_deterministic_price);

    nb::class_<PaperTradingEngine>(m, "PaperTradingEngine")
        .def("__init__", [](PaperTradingEngine* self, MockBroker broker) {
            new (self) PaperTradingEngine(std::make_shared<MockBroker>(std::move(broker)));
        }, nb::arg("broker"))
        .def("connect", &PaperTradingEngine::connect)
        .def("submit_order", &PaperTradingEngine::submit_order, nb::arg("request"))
        .def("cancel_order", &PaperTradingEngine::cancel_order, nb::arg("order_id"))
        .def("snapshot_state", &PaperTradingEngine::snapshot_state);

    nb::class_<ExecutionPolicy>(m, "ExecutionPolicy")
        .def(nb::init<>())
        .def_rw("max_retries", &ExecutionPolicy::max_retries)
        .def_rw("max_orders_per_window", &ExecutionPolicy::max_orders_per_window)
        .def_rw("rate_limit_window_ms", &ExecutionPolicy::rate_limit_window_ms)
        .def_rw("escalation_after_failures", &ExecutionPolicy::escalation_after_failures);

    nb::class_<ExecutionRouteResult>(m, "ExecutionRouteResult")
        .def(nb::init<>())
        .def_rw("result", &ExecutionRouteResult::result)
        .def_rw("attempts", &ExecutionRouteResult::attempts)
        .def_rw("risk_blocked", &ExecutionRouteResult::risk_blocked)
        .def_rw("rate_limited", &ExecutionRouteResult::rate_limited)
        .def_rw("retried", &ExecutionRouteResult::retried)
        .def_rw("escalated", &ExecutionRouteResult::escalated)
        .def_rw("policy_code", &ExecutionRouteResult::policy_code)
        .def_rw("reason", &ExecutionRouteResult::reason)
        .def_rw("escalation_reason", &ExecutionRouteResult::escalation_reason);

    nb::class_<ExecutionSlice>(m, "ExecutionSlice")
        .def(nb::init<>())
        .def_rw("scheduled_time_ms", &ExecutionSlice::scheduled_time_ms)
        .def_rw("volume", &ExecutionSlice::volume)
        .def_rw("weight", &ExecutionSlice::weight);

    nb::class_<ExecutionQualitySummary>(m, "ExecutionQualitySummary")
        .def(nb::init<>())
        .def_rw("samples", &ExecutionQualitySummary::samples)
        .def_rw("partial_fill_count", &ExecutionQualitySummary::partial_fill_count)
        .def_rw("partial_fill_rate", &ExecutionQualitySummary::partial_fill_rate)
        .def_rw("avg_slippage", &ExecutionQualitySummary::avg_slippage)
        .def_rw("avg_spread", &ExecutionQualitySummary::avg_spread)
        .def_rw("avg_latency_ms", &ExecutionQualitySummary::avg_latency_ms)
        .def_rw("p99_latency_ms", &ExecutionQualitySummary::p99_latency_ms);

    nb::class_<ExecutionAlgoTWAP>(m, "ExecutionAlgoTWAP")
        .def_static(
            "build_schedule",
            &ExecutionAlgoTWAP::build_schedule,
            nb::arg("total_volume"),
            nb::arg("start_time_ms"),
            nb::arg("end_time_ms"),
            nb::arg("slices"));

    nb::class_<ExecutionAlgoVWAP>(m, "ExecutionAlgoVWAP")
        .def_static(
            "build_schedule",
            &ExecutionAlgoVWAP::build_schedule,
            nb::arg("total_volume"),
            nb::arg("start_time_ms"),
            nb::arg("end_time_ms"),
            nb::arg("market_volume_profile"));

    nb::class_<ExecutionRouter>(m, "ExecutionRouter")
        .def("__init__", [](ExecutionRouter* self, MockBroker broker, ExecutionPolicy policy) {
            new (self) ExecutionRouter(std::make_shared<MockBroker>(std::move(broker)), policy);
        }, nb::arg("broker"), nb::arg("policy") = ExecutionPolicy{})
        .def("connect", &ExecutionRouter::connect)
        .def("set_policy", &ExecutionRouter::set_policy, nb::arg("policy"))
        .def("policy", &ExecutionRouter::policy)
        .def(
            "set_risk_account_state",
            &ExecutionRouter::set_risk_account_state,
            nb::arg("equity"),
            nb::arg("peak_equity"),
            nb::arg("gross_exposure"),
            nb::arg("net_exposure"))
        .def("consecutive_failures", &ExecutionRouter::consecutive_failures)
        .def(
            "submit",
            &ExecutionRouter::submit,
            nb::arg("request"),
            nb::arg("candidate_gross_add") = 0.0,
            nb::arg("candidate_net_delta") = 0.0,
            nb::arg("margin_required") = 0.0,
            nb::arg("free_margin") = -1.0,
            nb::arg("live_mode") = true)
        .def("cancel", &ExecutionRouter::cancel, nb::arg("order_id"))
        .def("reset_quality_metrics", &ExecutionRouter::reset_quality_metrics)
        .def("quality_summary", &ExecutionRouter::quality_summary);

    // ── BacktestEngine ───────────────────────────────────────────────

    nb::class_<BacktestEngine>(m, "BacktestEngine")
        .def(nb::init<TradeSimulator&>(), nb::keep_alive<1, 2>())
        .def("set_on_bar_processed", [](BacktestEngine& self, nb::object callback) {
            self.set_on_bar_processed(
                [callback](std::size_t index, const BacktestBarStep& bar,
                           const SimulatorState& state) {
                    nb::gil_scoped_acquire gil;
                    callback(index, bar, state);
                });
        })
        .def("set_on_tick_processed", [](BacktestEngine& self, nb::object callback) {
            self.set_on_tick_processed(
                [callback](const ModelTick& tick, const SimulatorState& state) {
                    nb::gil_scoped_acquire gil;
                    callback(tick, state);
                });
        })
        .def("set_on_trade_event", [](BacktestEngine& self, nb::object callback) {
            self.set_on_trade_event(
                [callback](const BacktestTradeEvent& event, const SimulatorState& state) {
                    nb::gil_scoped_acquire gil;
                    callback(event, state);
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
        .def("account_snapshot", [](const BacktestEngine& self) {
            return to_mt5_account(self.account_snapshot());
        })
        .def("close_reason", &BacktestEngine::close_reason)
        .def("completed_trades", &BacktestEngine::completed_trades,
             nb::rv_policy::reference_internal);

    nb::class_<BacktestTradeEvent>(m, "BacktestTradeEvent")
        .def(nb::init<>())
        .def_rw("event_type", &BacktestTradeEvent::event_type)
        .def_rw("trade", &BacktestTradeEvent::trade);

    // ── AccountMonitor ───────────────────────────────────────────────

    nb::class_<AccountMonitor>(m, "AccountMonitor")
        .def(nb::init<>())
        .def("monitor_positions", &AccountMonitor::monitor_positions)
        .def("monitor_account", [](const AccountMonitor& self,
                                   const hqt::AccountInfo& base,
                                   const PositionTotals& totals) {
            return to_mt5_account(self.monitor_account(base, totals));
        });

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
        .def("account_snapshot", [](const PortfolioState& self) {
            return to_mt5_account(self.account_snapshot());
        })
        .def("total_realized_pnl", &PortfolioState::total_realized_pnl)
        .def("total_unrealized_pnl", &PortfolioState::total_unrealized_pnl)
        .def("positions_by_symbol", &PortfolioState::positions_by_symbol)
        .def("positions_by_strategy", &PortfolioState::positions_by_strategy, nb::arg("strategy_id"));

    nb::class_<PositionBook>(m, "PositionBook")
        .def(nb::init<PositionMode>(), nb::arg("mode") = PositionMode::Netting)
        .def("set_mode", &PositionBook::set_mode, nb::arg("mode"))
        .def("mode", &PositionBook::mode)
        .def("reset", &PositionBook::reset)
        .def("apply_fill", &PositionBook::apply_fill, nb::arg("fill"))
        .def("apply_account_snapshot",
             [](PositionBook& self, const hqt::AccountInfo& account) {
                 self.apply_account_snapshot(account);
             },
             nb::arg("account"))
        .def("snapshot_positions", &PositionBook::snapshot_positions)
        .def("snapshot_account", [](const PositionBook& self) {
            return to_mt5_account(self.snapshot_account());
        })
        .def("legs_for_symbol", &PositionBook::legs_for_symbol, nb::arg("symbol"))
        .def("reconcile_with_broker",
             [](const PositionBook& self,
                const std::unordered_map<std::string, PositionAggregate>& broker_positions,
                const hqt::AccountInfo& broker_account,
                const std::string& trigger) {
                 return self.reconcile_with_broker(
                     broker_positions,
                     broker_account,
                     trigger);
             },
             nb::arg("broker_positions"),
             nb::arg("broker_account"),
             nb::arg("trigger") = "manual")
        .def("periodic_reconcile",
             [](const PositionBook& self,
                const std::unordered_map<std::string, PositionAggregate>& broker_positions,
                const hqt::AccountInfo& broker_account) {
                 return self.periodic_reconcile(
                     broker_positions,
                     broker_account);
             },
             nb::arg("broker_positions"),
             nb::arg("broker_account"))
        .def("reconnect_reconcile",
             [](const PositionBook& self,
                const std::unordered_map<std::string, PositionAggregate>& broker_positions,
                const hqt::AccountInfo& broker_account) {
                 return self.reconnect_reconcile(
                     broker_positions,
                     broker_account);
             },
             nb::arg("broker_positions"),
             nb::arg("broker_account"))
        .def("evaluate_reconciliation",
             &PositionBook::evaluate_reconciliation,
             nb::arg("report"),
             nb::arg("policy") = ReconcilePolicy::Auto,
             nb::arg("major_threshold") = 2)
        .def("write_incident_report",
             &PositionBook::write_incident_report,
             nb::arg("path"),
             nb::arg("report"),
             nb::arg("decision"));

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
        .def(nb::init<TradeSimulator&>(), nb::keep_alive<1, 2>())
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

    nb::class_<VectorizedBacktestEngine>(m, "VectorizedBacktestEngine")
        .def(nb::init<TradeSimulator&>(), nb::keep_alive<1, 2>())
        .def(
            "run",
            [](VectorizedBacktestEngine& self, const std::string& symbol, double volume,
               const std::vector<BacktestBarStep>& bars) {
                call_without_gil([&]() { self.run(symbol, volume, bars); });
            },
            nb::arg("symbol"),
            nb::arg("volume"),
            nb::arg("bars"))
        .def("account_snapshot", [](const VectorizedBacktestEngine& self) {
            return to_mt5_account(self.account_snapshot());
        })
        .def("processed_bars", &VectorizedBacktestEngine::processed_bars)
        .def("total_trades", &VectorizedBacktestEngine::total_trades);

    nb::class_<ReplayTradeEvent>(m, "ReplayTradeEvent")
        .def(nb::init<>())
        .def_rw("time_msc", &ReplayTradeEvent::time_msc)
        .def_rw("symbol", &ReplayTradeEvent::symbol)
        .def_rw("side", &ReplayTradeEvent::side)
        .def_rw("price", &ReplayTradeEvent::price)
        .def_rw("volume", &ReplayTradeEvent::volume)
        .def_rw("ticket", &ReplayTradeEvent::ticket);

    nb::class_<ReplayCertificationResult>(m, "ReplayCertificationResult")
        .def(nb::init<>())
        .def_rw("consistent", &ReplayCertificationResult::consistent)
        .def_rw("baseline_fingerprint", &ReplayCertificationResult::baseline_fingerprint)
        .def_rw("candidate_fingerprint", &ReplayCertificationResult::candidate_fingerprint)
        .def_rw("message", &ReplayCertificationResult::message);

    nb::class_<ReplayCertifier>(m, "ReplayCertifier")
        .def_static("fingerprint", &ReplayCertifier::fingerprint, nb::arg("events"))
        .def_static("compare", &ReplayCertifier::compare, nb::arg("baseline"), nb::arg("candidate"));

    nb::class_<WfoSpec>(m, "WfoSpec")
        .def(nb::init<>())
        .def_rw("train_bars", &WfoSpec::train_bars)
        .def_rw("test_bars", &WfoSpec::test_bars)
        .def_rw("step_bars", &WfoSpec::step_bars);

    nb::class_<WfoWindow>(m, "WfoWindow")
        .def(nb::init<>())
        .def_rw("train_start", &WfoWindow::train_start)
        .def_rw("train_end", &WfoWindow::train_end)
        .def_rw("test_start", &WfoWindow::test_start)
        .def_rw("test_end", &WfoWindow::test_end);

    nb::class_<WfoWindowResult>(m, "WfoWindowResult")
        .def(nb::init<>())
        .def_rw("window", &WfoWindowResult::window)
        .def_rw("train_score", &WfoWindowResult::train_score)
        .def_rw("test_score", &WfoWindowResult::test_score);

    nb::class_<WfoSummary>(m, "WfoSummary")
        .def(nb::init<>())
        .def_rw("num_windows", &WfoSummary::num_windows)
        .def_rw("avg_train_score", &WfoSummary::avg_train_score)
        .def_rw("avg_test_score", &WfoSummary::avg_test_score)
        .def_rw("std_train_score", &WfoSummary::std_train_score)
        .def_rw("std_test_score", &WfoSummary::std_test_score)
        .def_rw("train_test_correlation", &WfoSummary::train_test_correlation)
        .def_rw("overfitting_ratio", &WfoSummary::overfitting_ratio);

    nb::class_<WfmCellResult>(m, "WfmCellResult")
        .def(nb::init<>())
        .def_rw("spec", &WfmCellResult::spec)
        .def_rw("summary", &WfmCellResult::summary);

    nb::class_<EdgeDetectorReport>(m, "EdgeDetectorReport")
        .def(nb::init<>())
        .def_rw("windows", &EdgeDetectorReport::windows)
        .def_rw("mean_test_score", &EdgeDetectorReport::mean_test_score)
        .def_rw("p_value", &EdgeDetectorReport::p_value)
        .def_rw("skill_confirmed", &EdgeDetectorReport::skill_confirmed)
        .def_rw("verdict", &EdgeDetectorReport::verdict);

    nb::class_<WfoWfmOrchestrator>(m, "WfoWfmOrchestrator")
        .def_static("build_windows", &WfoWfmOrchestrator::build_windows, nb::arg("total_bars"), nb::arg("spec"))
        .def_static(
            "run_wfo",
            [](std::size_t total_bars, const WfoSpec& spec, nb::callable evaluator) {
                std::function<double(const WfoWindow&, bool)> eval =
                    [evaluator](const WfoWindow& w, bool is_train) {
                        nb::gil_scoped_acquire gil;
                        return nb::cast<double>(evaluator(w, is_train));
                    };
                return WfoWfmOrchestrator::run_wfo(total_bars, spec, eval);
            },
            nb::arg("total_bars"),
            nb::arg("spec"),
            nb::arg("evaluator"))
        .def_static("summarize", &WfoWfmOrchestrator::summarize, nb::arg("results"))
        .def_static(
            "run_wfm",
            [](std::size_t total_bars, const std::vector<WfoSpec>& matrix_specs, nb::callable evaluator) {
                std::function<double(const WfoWindow&, bool)> eval =
                    [evaluator](const WfoWindow& w, bool is_train) {
                        nb::gil_scoped_acquire gil;
                        return nb::cast<double>(evaluator(w, is_train));
                    };
                return WfoWfmOrchestrator::run_wfm(total_bars, matrix_specs, eval);
            },
            nb::arg("total_bars"),
            nb::arg("matrix_specs"),
            nb::arg("evaluator"));

    nb::class_<EdgeDetector>(m, "EdgeDetector")
        .def_static("from_wfo", &EdgeDetector::from_wfo, nb::arg("results"), nb::arg("alpha") = 0.05);

    // ── ResultMetrics ────────────────────────────────────────────────

    nb::class_<ExperimentRecord>(m, "ExperimentRecord")
        .def(nb::init<>())
        .def_rw("experiment_id", &ExperimentRecord::experiment_id)
        .def_rw("strategy", &ExperimentRecord::strategy)
        .def_rw("symbol", &ExperimentRecord::symbol)
        .def_rw("timeframe", &ExperimentRecord::timeframe)
        .def_rw("period_start_msc", &ExperimentRecord::period_start_msc)
        .def_rw("period_end_msc", &ExperimentRecord::period_end_msc)
        .def_rw("metadata", &ExperimentRecord::metadata);

    nb::class_<ExperimentRegistry>(m, "ExperimentRegistry")
        .def(nb::init<>())
        .def("upsert", &ExperimentRegistry::upsert, nb::arg("record"))
        .def("all", &ExperimentRegistry::all)
        .def("query", &ExperimentRegistry::query,
             nb::arg("strategy") = std::nullopt,
             nb::arg("symbol") = std::nullopt,
             nb::arg("period_start_msc") = std::nullopt,
             nb::arg("period_end_msc") = std::nullopt);

    nb::class_<SymbolClassification>(m, "SymbolClassification")
        .def(nb::init<>())
        .def_rw("asset_class", &SymbolClassification::asset_class)
        .def_rw("volatility_regime", &SymbolClassification::volatility_regime);

    nb::class_<SymbolClassifier>(m, "SymbolClassifier")
        .def_static("classify", &SymbolClassifier::classify, nb::arg("symbol"), nb::arg("annualized_volatility"));

    nb::class_<SeasonalBucket>(m, "SeasonalBucket")
        .def(nb::init<>())
        .def_rw("key", &SeasonalBucket::key)
        .def_rw("count", &SeasonalBucket::count)
        .def_rw("mean_return", &SeasonalBucket::mean_return);

    nb::class_<SeasonalAnalysis>(m, "SeasonalAnalysis")
        .def(nb::init<>())
        .def_rw("day_of_week", &SeasonalAnalysis::day_of_week)
        .def_rw("holiday_vs_non_holiday", &SeasonalAnalysis::holiday_vs_non_holiday);

    nb::class_<SeasonalPatternAnalyzer>(m, "SeasonalPatternAnalyzer")
        .def_static("analyze", &SeasonalPatternAnalyzer::analyze,
                    nb::arg("timestamps_msc"),
                    nb::arg("returns"),
                    nb::arg("holiday_days_epoch") = std::unordered_set<int64_t>{});

    nb::class_<OptimizationTrial>(m, "OptimizationTrial")
        .def(nb::init<>())
        .def_rw("params", &OptimizationTrial::params)
        .def_rw("score", &OptimizationTrial::score)
        .def_rw("iteration", &OptimizationTrial::iteration)
        .def_rw("generation", &OptimizationTrial::generation);

    nb::class_<OptimizationWorkerPolicy>(m, "OptimizationWorkerPolicy")
        .def(nb::init<>())
        .def_rw("max_workers", &OptimizationWorkerPolicy::max_workers)
        .def_rw("max_restarts", &OptimizationWorkerPolicy::max_restarts)
        .def_rw("task_timeout_ms", &OptimizationWorkerPolicy::task_timeout_ms)
        .def_rw("heartbeat_ms", &OptimizationWorkerPolicy::heartbeat_ms);

    nb::class_<OptimizationWorkerHealth>(m, "OptimizationWorkerHealth")
        .def(nb::init<>())
        .def_rw("submitted", &OptimizationWorkerHealth::submitted)
        .def_rw("completed", &OptimizationWorkerHealth::completed)
        .def_rw("failed", &OptimizationWorkerHealth::failed)
        .def_rw("restarted", &OptimizationWorkerHealth::restarted)
        .def_rw("timeout_restarts", &OptimizationWorkerHealth::timeout_restarts);

    nb::class_<DistributedOptimizationResult>(m, "DistributedOptimizationResult")
        .def(nb::init<>())
        .def_rw("trials", &DistributedOptimizationResult::trials)
        .def_rw("health", &DistributedOptimizationResult::health);

    nb::enum_<MonteCarloMode>(m, "MonteCarloMode")
        .value("Shuffle", MonteCarloMode::Shuffle)
        .value("Bootstrap", MonteCarloMode::Bootstrap)
        .value("Perturb", MonteCarloMode::Perturb);

    nb::class_<MonteCarloSummary>(m, "MonteCarloSummary")
        .def(nb::init<>())
        .def_rw("simulations", &MonteCarloSummary::simulations)
        .def_rw("mean", &MonteCarloSummary::mean)
        .def_rw("stddev", &MonteCarloSummary::stddev)
        .def_rw("p05", &MonteCarloSummary::p05)
        .def_rw("p50", &MonteCarloSummary::p50)
        .def_rw("p95", &MonteCarloSummary::p95)
        .def_rw("probability_positive", &MonteCarloSummary::probability_positive);

    nb::class_<SensitivityPoint>(m, "SensitivityPoint")
        .def(nb::init<>())
        .def_rw("param", &SensitivityPoint::param)
        .def_rw("value", &SensitivityPoint::value)
        .def_rw("score", &SensitivityPoint::score);

    nb::class_<SensitivityReport>(m, "SensitivityReport")
        .def(nb::init<>())
        .def_rw("evaluations", &SensitivityReport::evaluations)
        .def_rw("stability_score", &SensitivityReport::stability_score)
        .def_rw("normalized_sensitivity", &SensitivityReport::normalized_sensitivity)
        .def_rw("points", &SensitivityReport::points);

    nb::class_<GridSearchRunner>(m, "GridSearchRunner")
        .def_static(
            "run",
            [](const OptimizationParamSpace& space, nb::callable evaluator, std::size_t max_evals) {
                std::function<double(const std::unordered_map<std::string, double>&)> eval =
                    [evaluator](const std::unordered_map<std::string, double>& p) {
                        nb::gil_scoped_acquire gil;
                        return nb::cast<double>(evaluator(p));
                    };
                return GridSearchRunner::run(space, eval, max_evals);
            },
            nb::arg("space"),
            nb::arg("evaluator"),
            nb::arg("max_evals") = 0U);

    nb::class_<RandomSearchRunner>(m, "RandomSearchRunner")
        .def_static(
            "run",
            [](const OptimizationParamSpace& space,
               std::size_t samples,
               std::uint64_t seed,
               nb::callable evaluator) {
                std::function<double(const std::unordered_map<std::string, double>&)> eval =
                    [evaluator](const std::unordered_map<std::string, double>& p) {
                        nb::gil_scoped_acquire gil;
                        return nb::cast<double>(evaluator(p));
                    };
                return RandomSearchRunner::run(space, samples, seed, eval);
            },
            nb::arg("space"),
            nb::arg("samples"),
            nb::arg("seed"),
            nb::arg("evaluator"));

    nb::class_<GeneticSearchRunner>(m, "GeneticSearchRunner")
        .def_static(
            "run",
            [](const OptimizationParamSpace& space,
               std::size_t population_size,
               std::size_t generations,
               std::uint64_t seed,
               nb::callable evaluator,
               double mutation_rate) {
                std::function<double(const std::unordered_map<std::string, double>&)> eval =
                    [evaluator](const std::unordered_map<std::string, double>& p) {
                        nb::gil_scoped_acquire gil;
                        return nb::cast<double>(evaluator(p));
                    };
                return GeneticSearchRunner::run(
                    space,
                    population_size,
                    generations,
                    seed,
                    eval,
                    mutation_rate);
            },
            nb::arg("space"),
            nb::arg("population_size"),
            nb::arg("generations"),
            nb::arg("seed"),
            nb::arg("evaluator"),
            nb::arg("mutation_rate") = 0.15);

    nb::class_<BayesianSearchRunner>(m, "BayesianSearchRunner")
        .def_static(
            "run",
            [](const OptimizationParamSpace& space,
               std::size_t iterations,
               std::uint64_t seed,
               nb::callable evaluator,
               std::size_t random_warmup,
               double exploration_weight) {
                std::function<double(const std::unordered_map<std::string, double>&)> eval =
                    [evaluator](const std::unordered_map<std::string, double>& p) {
                        nb::gil_scoped_acquire gil;
                        return nb::cast<double>(evaluator(p));
                    };
                return BayesianSearchRunner::run(
                    space,
                    iterations,
                    seed,
                    eval,
                    random_warmup,
                    exploration_weight);
            },
            nb::arg("space"),
            nb::arg("iterations"),
            nb::arg("seed"),
            nb::arg("evaluator"),
            nb::arg("random_warmup") = 5U,
            nb::arg("exploration_weight") = 0.20);

    nb::class_<DistributedOptimizationRunner>(m, "DistributedOptimizationRunner")
        .def_static(
            "run",
            [](const std::vector<std::unordered_map<std::string, double>>& params_list,
               nb::callable evaluator,
               const OptimizationWorkerPolicy& policy) {
                std::function<double(const std::unordered_map<std::string, double>&)> eval =
                    [evaluator](const std::unordered_map<std::string, double>& p) {
                        nb::gil_scoped_acquire gil;
                        return nb::cast<double>(evaluator(p));
                    };
                return DistributedOptimizationRunner::run(params_list, eval, policy);
            },
            nb::arg("params_list"),
            nb::arg("evaluator"),
            nb::arg("policy") = OptimizationWorkerPolicy{});

    nb::class_<MonteCarloAnalyzer>(m, "MonteCarloAnalyzer")
        .def_static(
            "simulate",
            &MonteCarloAnalyzer::simulate,
            nb::arg("pnl_series"),
            nb::arg("simulations"),
            nb::arg("seed") = 7U,
            nb::arg("mode") = MonteCarloMode::Bootstrap,
            nb::arg("perturb_scale") = 0.10);

    nb::class_<SensitivityAnalyzer>(m, "SensitivityAnalyzer")
        .def_static(
            "analyze",
            [](const OptimizationParamSpace& space,
               nb::callable evaluator,
               std::size_t max_points) {
                std::function<double(const std::unordered_map<std::string, double>&)> eval =
                    [evaluator](const std::unordered_map<std::string, double>& p) {
                        nb::gil_scoped_acquire gil;
                        return nb::cast<double>(evaluator(p));
                    };
                return SensitivityAnalyzer::analyze(space, eval, max_points);
            },
            nb::arg("space"),
            nb::arg("evaluator"),
            nb::arg("max_points") = 0U);

    nb::class_<ResultMetrics>(m, "ResultMetrics")
        .def_static("from_trades", &ResultMetrics::from_trades);

    // ── Free functions ───────────────────────────────────────────────

    m.def("calc_margin", &calc_margin,
          "Calculate required margin using MT5-like calc mode semantics.");
    m.def("calc_profit", &calc_profit,
          "Calculate profit for BUY/SELL actions.");
}


