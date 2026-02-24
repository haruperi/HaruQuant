#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>

#include "core/backtest_simulator.hpp"
#include "trading/account_info.hpp"
#include "trading/deal_info.hpp"
#include "trading/history_order_info.hpp"
#include "trading/order_info.hpp"
#include "trading/position_info.hpp"
#include "trading/symbol_info.hpp"

namespace nb = nanobind;

namespace {

template <typename T, typename Setter>
void assign_if_present(const nb::object& source, const char* name, Setter&& setter) {
    nb::object value;
    if (nb::isinstance<nb::dict>(source)) {
        nb::dict data = nb::cast<nb::dict>(source);
        nb::str key(name);
        if (!data.contains(key)) {
            return;
        }
        value = data[key];
    } else {
        if (!nb::hasattr(source, name)) {
            return;
        }
        value = source.attr(name);
    }

    if (value.is_none()) {
        return;
    }
    setter(nb::cast<T>(value));
}

haruquant::trading::AccountInfo account_from_object(const nb::object& source) {
    haruquant::trading::AccountInfo account;

    assign_if_present<long>(source, "login", [&](long v) { account.SetLogin(v); });
    assign_if_present<std::string>(source, "name", [&](const std::string& v) { account.SetName(v); });
    assign_if_present<std::string>(source, "server", [&](const std::string& v) { account.SetServer(v); });
    assign_if_present<std::string>(source, "currency", [&](const std::string& v) { account.SetCurrency(v); });
    assign_if_present<std::string>(source, "company", [&](const std::string& v) { account.SetCompany(v); });

    assign_if_present<long>(source, "trade_mode", [&](long v) { account.SetTradeMode(v); });
    assign_if_present<int>(source, "leverage", [&](int v) { account.SetLeverage(v); });
    assign_if_present<int>(source, "limit_orders", [&](int v) { account.SetLimitOrders(v); });
    assign_if_present<long>(source, "margin_mode", [&](long v) { account.SetMarginMode(v); });
    assign_if_present<bool>(source, "trade_allowed", [&](bool v) { account.SetTradeAllowed(v); });
    assign_if_present<bool>(source, "trade_expert", [&](bool v) { account.SetTradeExpert(v); });

    assign_if_present<double>(source, "balance", [&](double v) { account.SetBalance(v); });
    assign_if_present<double>(source, "credit", [&](double v) { account.SetCredit(v); });
    assign_if_present<double>(source, "profit", [&](double v) { account.SetProfit(v); });
    assign_if_present<double>(source, "equity", [&](double v) { account.SetEquity(v); });
    assign_if_present<double>(source, "margin", [&](double v) { account.SetMargin(v); });
    assign_if_present<double>(source, "margin_free", [&](double v) { account.SetMarginFree(v); });
    assign_if_present<double>(source, "margin_level", [&](double v) { account.SetMarginLevel(v); });
    assign_if_present<double>(source, "margin_so_call", [&](double v) { account.SetMarginCall(v); });
    assign_if_present<double>(source, "margin_so_so", [&](double v) { account.SetMarginStopOut(v); });

    return account;
}

haruquant::trading::DealInfo deal_from_object(const nb::object& source) {
    haruquant::trading::DealInfo deal;

    assign_if_present<long>(source, "ticket", [&](long v) { deal.SetTicket(v); });
    assign_if_present<long>(source, "order", [&](long v) { deal.SetOrder(v); });
    assign_if_present<long>(source, "time", [&](long v) { deal.SetTime(v); });
    assign_if_present<long>(source, "time_msc", [&](long v) { deal.SetTimeMsc(v); });
    assign_if_present<long>(source, "type", [&](long v) { deal.SetType(v); });
    assign_if_present<long>(source, "entry", [&](long v) { deal.SetEntry(v); });
    assign_if_present<long>(source, "magic", [&](long v) { deal.SetMagic(v); });
    assign_if_present<long>(source, "reason", [&](long v) { deal.SetReason(v); });
    assign_if_present<long>(source, "position_id", [&](long v) { deal.SetPositionId(v); });

    assign_if_present<double>(source, "volume", [&](double v) { deal.SetVolume(v); });
    assign_if_present<double>(source, "price", [&](double v) { deal.SetPrice(v); });
    assign_if_present<double>(source, "commission", [&](double v) { deal.SetCommission(v); });
    assign_if_present<double>(source, "swap", [&](double v) { deal.SetSwap(v); });
    assign_if_present<double>(source, "profit", [&](double v) { deal.SetProfit(v); });
    assign_if_present<double>(source, "fee", [&](double v) { deal.SetFee(v); });

    assign_if_present<std::string>(source, "symbol", [&](const std::string& v) { deal.SetSymbol(v); });
    assign_if_present<std::string>(source, "comment", [&](const std::string& v) { deal.SetComment(v); });
    assign_if_present<std::string>(source, "external_id", [&](const std::string& v) { deal.SetExternalId(v); });

    return deal;
}

haruquant::trading::HistoryOrderInfo history_order_from_object(const nb::object& source) {
    haruquant::trading::HistoryOrderInfo order;

    assign_if_present<long>(source, "ticket", [&](long v) { order.SetTicket(v); });
    assign_if_present<long>(source, "time_setup", [&](long v) { order.SetTimeSetup(v); });
    assign_if_present<long>(source, "time_setup_msc", [&](long v) { order.SetTimeSetupMsc(v); });
    assign_if_present<long>(source, "time_done", [&](long v) { order.SetTimeDone(v); });
    assign_if_present<long>(source, "time_done_msc", [&](long v) { order.SetTimeDoneMsc(v); });
    assign_if_present<long>(source, "time_expiration", [&](long v) { order.SetTimeExpiration(v); });
    assign_if_present<long>(source, "type", [&](long v) { order.SetType(v); });
    assign_if_present<long>(source, "type_time", [&](long v) { order.SetTypeTime(v); });
    assign_if_present<long>(source, "type_filling", [&](long v) { order.SetTypeFilling(v); });
    assign_if_present<long>(source, "state", [&](long v) { order.SetStateValue(v); });
    assign_if_present<long>(source, "magic", [&](long v) { order.SetMagic(v); });
    assign_if_present<long>(source, "reason", [&](long v) { order.SetReason(v); });
    assign_if_present<long>(source, "position_id", [&](long v) { order.SetPositionId(v); });

    assign_if_present<double>(source, "volume_initial", [&](double v) { order.SetVolumeInitial(v); });
    assign_if_present<double>(source, "volume_current", [&](double v) { order.SetVolumeCurrent(v); });
    assign_if_present<double>(source, "price_open", [&](double v) { order.SetPriceOpen(v); });
    assign_if_present<double>(source, "sl", [&](double v) { order.SetSl(v); });
    assign_if_present<double>(source, "tp", [&](double v) { order.SetTp(v); });
    assign_if_present<double>(source, "price_current", [&](double v) { order.SetPriceCurrent(v); });
    assign_if_present<double>(source, "price_stoplimit", [&](double v) { order.SetPriceStopLimit(v); });

    assign_if_present<std::string>(source, "symbol", [&](const std::string& v) { order.SetSymbol(v); });
    assign_if_present<std::string>(source, "comment", [&](const std::string& v) { order.SetComment(v); });
    assign_if_present<std::string>(source, "external_id", [&](const std::string& v) { order.SetExternalId(v); });

    return order;
}

haruquant::trading::OrderInfo order_from_object(const nb::object& source) {
    haruquant::trading::OrderInfo order;

    assign_if_present<long>(source, "ticket", [&](long v) { order.SetTicket(v); });
    assign_if_present<long>(source, "time_setup", [&](long v) { order.SetTimeSetup(v); });
    assign_if_present<long>(source, "time_setup_msc", [&](long v) { order.SetTimeSetupMsc(v); });
    assign_if_present<long>(source, "time_done", [&](long v) { order.SetTimeDone(v); });
    assign_if_present<long>(source, "time_done_msc", [&](long v) { order.SetTimeDoneMsc(v); });
    assign_if_present<long>(source, "time_expiration", [&](long v) { order.SetTimeExpiration(v); });
    assign_if_present<long>(source, "type", [&](long v) { order.SetType(v); });
    assign_if_present<long>(source, "type_time", [&](long v) { order.SetTypeTime(v); });
    assign_if_present<long>(source, "type_filling", [&](long v) { order.SetTypeFilling(v); });
    assign_if_present<long>(source, "state", [&](long v) { order.SetStateValue(v); });
    assign_if_present<long>(source, "magic", [&](long v) { order.SetMagic(v); });
    assign_if_present<long>(source, "reason", [&](long v) { order.SetReason(v); });
    assign_if_present<long>(source, "position_id", [&](long v) { order.SetPositionId(v); });
    assign_if_present<long>(source, "position_by_id", [&](long v) { order.SetPositionById(v); });

    assign_if_present<double>(source, "volume_initial", [&](double v) { order.SetVolumeInitial(v); });
    assign_if_present<double>(source, "volume_current", [&](double v) { order.SetVolumeCurrent(v); });
    assign_if_present<double>(source, "price_open", [&](double v) { order.SetPriceOpen(v); });
    assign_if_present<double>(source, "sl", [&](double v) { order.SetSl(v); });
    assign_if_present<double>(source, "tp", [&](double v) { order.SetTp(v); });
    assign_if_present<double>(source, "price_current", [&](double v) { order.SetPriceCurrent(v); });
    assign_if_present<double>(source, "price_stoplimit", [&](double v) { order.SetPriceStopLimit(v); });

    assign_if_present<std::string>(source, "symbol", [&](const std::string& v) { order.SetSymbol(v); });
    assign_if_present<std::string>(source, "comment", [&](const std::string& v) { order.SetComment(v); });
    assign_if_present<std::string>(source, "external_id", [&](const std::string& v) { order.SetExternalId(v); });

    return order;
}

haruquant::trading::PositionInfo position_from_object(const nb::object& source) {
    haruquant::trading::PositionInfo position;

    assign_if_present<std::string>(source, "symbol", [&](const std::string& v) { position.SetSymbol(v); });
    assign_if_present<long>(source, "ticket", [&](long v) { position.SetTicket(v); });
    assign_if_present<long>(source, "time", [&](long v) { position.SetTime(v); });
    assign_if_present<long>(source, "time_msc", [&](long v) { position.SetTimeMsc(v); });
    assign_if_present<long>(source, "time_update", [&](long v) { position.SetTimeUpdate(v); });
    assign_if_present<long>(source, "time_update_msc", [&](long v) { position.SetTimeUpdateMsc(v); });
    assign_if_present<long>(source, "type", [&](long v) { position.SetType(v); });
    assign_if_present<long>(source, "magic", [&](long v) { position.SetMagic(v); });
    assign_if_present<long>(source, "identifier", [&](long v) { position.SetIdentifier(v); });
    assign_if_present<long>(source, "reason", [&](long v) { position.SetReason(v); });

    assign_if_present<double>(source, "volume", [&](double v) { position.SetVolume(v); });
    assign_if_present<double>(source, "price_open", [&](double v) { position.SetPriceOpen(v); });
    assign_if_present<double>(source, "sl", [&](double v) { position.SetSl(v); });
    assign_if_present<double>(source, "tp", [&](double v) { position.SetTp(v); });
    assign_if_present<double>(source, "price_current", [&](double v) { position.SetPriceCurrent(v); });
    assign_if_present<double>(source, "swap", [&](double v) { position.SetSwap(v); });
    assign_if_present<double>(source, "profit", [&](double v) { position.SetProfit(v); });

    assign_if_present<std::string>(source, "comment", [&](const std::string& v) { position.SetComment(v); });
    assign_if_present<std::string>(source, "external_id", [&](const std::string& v) { position.SetExternalId(v); });
    return position;
}

haruquant::trading::SymbolInfo symbol_from_object(const nb::object& source) {
    haruquant::trading::SymbolInfo symbol;

    assign_if_present<std::string>(source, "symbol", [&](const std::string& v) { symbol.Name(v); });
    assign_if_present<std::string>(source, "name", [&](const std::string& v) { symbol.Name(v); });
    assign_if_present<std::string>(source, "description", [&](const std::string& v) { symbol.SetDescription(v); });
    assign_if_present<std::string>(source, "path", [&](const std::string& v) { symbol.SetPath(v); });
    assign_if_present<std::string>(source, "currency_base", [&](const std::string& v) { symbol.SetCurrencyBase(v); });
    assign_if_present<std::string>(source, "currency_profit", [&](const std::string& v) { symbol.SetCurrencyProfit(v); });
    assign_if_present<std::string>(source, "currency_margin", [&](const std::string& v) { symbol.SetCurrencyMargin(v); });

    assign_if_present<int>(source, "select", [&](int v) { symbol.SetSelect(v != 0); });
    assign_if_present<bool>(source, "spread_float", [&](bool v) { symbol.SetSpreadFloat(v); });
    assign_if_present<long>(source, "time", [&](long v) { symbol.SetTime(v); });
    assign_if_present<long>(source, "digits", [&](long v) { symbol.SetDigits(v); });
    assign_if_present<long>(source, "spread", [&](long v) { symbol.SetSpread(v); });
    assign_if_present<long>(source, "trade_mode", [&](long v) { symbol.SetTradeMode(v); });
    assign_if_present<long>(source, "trade_exemode", [&](long v) { symbol.SetTradeExemode(v); });
    assign_if_present<long>(source, "trade_calc_mode", [&](long v) { symbol.SetTradeCalcMode(v); });
    assign_if_present<long>(source, "trade_stops_level", [&](long v) { symbol.SetTradeStopsLevel(v); });
    assign_if_present<long>(source, "trade_freeze_level", [&](long v) { symbol.SetTradeFreezeLevel(v); });
    assign_if_present<long>(source, "swap_mode", [&](long v) { symbol.SetSwapMode(v); });
    assign_if_present<long>(source, "swap_rollover3days", [&](long v) { symbol.SetSwapRollover3days(v); });

    assign_if_present<double>(source, "bid", [&](double v) { symbol.SetBid(v); });
    assign_if_present<double>(source, "ask", [&](double v) { symbol.SetAsk(v); });
    assign_if_present<double>(source, "last", [&](double v) { symbol.SetLast(v); });
    assign_if_present<double>(source, "point", [&](double v) { symbol.SetPoint(v); });
    assign_if_present<double>(source, "trade_tick_size", [&](double v) { symbol.SetTradeTickSize(v); });
    assign_if_present<double>(source, "trade_tick_value", [&](double v) { symbol.SetTradeTickValue(v); });
    assign_if_present<double>(source, "trade_tick_value_profit", [&](double v) { symbol.SetTradeTickValueProfit(v); });
    assign_if_present<double>(source, "trade_tick_value_loss", [&](double v) { symbol.SetTradeTickValueLoss(v); });
    assign_if_present<double>(source, "trade_contract_size", [&](double v) { symbol.SetTradeContractSize(v); });
    assign_if_present<double>(source, "volume_min", [&](double v) { symbol.SetVolumeMin(v); });
    assign_if_present<double>(source, "volume_max", [&](double v) { symbol.SetVolumeMax(v); });
    assign_if_present<double>(source, "volume_step", [&](double v) { symbol.SetVolumeStep(v); });
    assign_if_present<double>(source, "volume_limit", [&](double v) { symbol.SetVolumeLimit(v); });
    assign_if_present<double>(source, "margin_initial", [&](double v) { symbol.SetMarginInitial(v); });
    assign_if_present<double>(source, "margin_maintenance", [&](double v) { symbol.SetMarginMaintenance(v); });
    assign_if_present<double>(source, "swap_long", [&](double v) { symbol.SetSwapLong(v); });
    assign_if_present<double>(source, "swap_short", [&](double v) { symbol.SetSwapShort(v); });

    return symbol;
}

}  // namespace

void register_core_bindings(nb::module_& m) {
    m.doc() = "Core engine bindings";

    nb::class_<haruquant::trading::AccountInfo>(m, "AccountInfo")
        .def(nb::init<>())
        .def("__init__", [](haruquant::trading::AccountInfo* self, nb::object source) {
            new (self) haruquant::trading::AccountInfo(account_from_object(source));
        }, nb::arg("source"))
        .def("Login", &haruquant::trading::AccountInfo::Login)
        .def("Name", &haruquant::trading::AccountInfo::Name)
        .def("Server", &haruquant::trading::AccountInfo::Server)
        .def("Currency", &haruquant::trading::AccountInfo::Currency)
        .def("Company", &haruquant::trading::AccountInfo::Company)
        .def("TradeMode", &haruquant::trading::AccountInfo::TradeMode)
        .def("Leverage", &haruquant::trading::AccountInfo::Leverage)
        .def("TradeAllowed", &haruquant::trading::AccountInfo::TradeAllowed)
        .def("TradeExpert", &haruquant::trading::AccountInfo::TradeExpert)
        .def("LimitOrders", &haruquant::trading::AccountInfo::LimitOrders)
        .def("MarginMode", &haruquant::trading::AccountInfo::MarginMode)
        .def("Balance", &haruquant::trading::AccountInfo::Balance)
        .def("Credit", &haruquant::trading::AccountInfo::Credit)
        .def("Profit", &haruquant::trading::AccountInfo::Profit)
        .def("Equity", &haruquant::trading::AccountInfo::Equity)
        .def("Margin", &haruquant::trading::AccountInfo::Margin)
        .def("MarginFree", &haruquant::trading::AccountInfo::MarginFree)
        .def("MarginLevel", &haruquant::trading::AccountInfo::MarginLevel)
        .def("MarginCall", &haruquant::trading::AccountInfo::MarginCall)
        .def("MarginStopOut", &haruquant::trading::AccountInfo::MarginStopOut)
        .def("SetLogin", &haruquant::trading::AccountInfo::SetLogin, nb::arg("value"))
        .def("SetName", &haruquant::trading::AccountInfo::SetName, nb::arg("value"))
        .def("SetServer", &haruquant::trading::AccountInfo::SetServer, nb::arg("value"))
        .def("SetCurrency", &haruquant::trading::AccountInfo::SetCurrency, nb::arg("value"))
        .def("SetCompany", &haruquant::trading::AccountInfo::SetCompany, nb::arg("value"))
        .def("SetTradeMode", &haruquant::trading::AccountInfo::SetTradeMode, nb::arg("value"))
        .def("SetLeverage", &haruquant::trading::AccountInfo::SetLeverage, nb::arg("value"))
        .def("SetLimitOrders", &haruquant::trading::AccountInfo::SetLimitOrders, nb::arg("value"))
        .def("SetMarginMode", &haruquant::trading::AccountInfo::SetMarginMode, nb::arg("value"))
        .def("SetTradeAllowed", &haruquant::trading::AccountInfo::SetTradeAllowed, nb::arg("value"))
        .def("SetTradeExpert", &haruquant::trading::AccountInfo::SetTradeExpert, nb::arg("value"))
        .def("SetBalance", &haruquant::trading::AccountInfo::SetBalance, nb::arg("value"))
        .def("SetCredit", &haruquant::trading::AccountInfo::SetCredit, nb::arg("value"))
        .def("SetProfit", &haruquant::trading::AccountInfo::SetProfit, nb::arg("value"))
        .def("SetEquity", &haruquant::trading::AccountInfo::SetEquity, nb::arg("value"))
        .def("SetMargin", &haruquant::trading::AccountInfo::SetMargin, nb::arg("value"))
        .def("SetMarginFree", &haruquant::trading::AccountInfo::SetMarginFree, nb::arg("value"))
        .def("SetMarginLevel", &haruquant::trading::AccountInfo::SetMarginLevel, nb::arg("value"))
        .def("SetMarginCall", &haruquant::trading::AccountInfo::SetMarginCall, nb::arg("value"))
        .def("SetMarginStopOut", &haruquant::trading::AccountInfo::SetMarginStopOut, nb::arg("value"));

    nb::class_<haruquant::trading::DealInfo>(m, "DealInfo")
        .def(nb::init<>())
        .def("__init__", [](haruquant::trading::DealInfo* self, nb::object source) {
            new (self) haruquant::trading::DealInfo(deal_from_object(source));
        }, nb::arg("source"))
        .def("SelectTicket", static_cast<bool (haruquant::trading::DealInfo::*)(long)>(&haruquant::trading::DealInfo::Ticket), nb::arg("ticket"))
        .def("Ticket", static_cast<long (haruquant::trading::DealInfo::*)() const>(&haruquant::trading::DealInfo::Ticket))
        .def("Order", &haruquant::trading::DealInfo::Order)
        .def("Time", &haruquant::trading::DealInfo::Time)
        .def("TimeMsc", &haruquant::trading::DealInfo::TimeMsc)
        .def("Type", &haruquant::trading::DealInfo::Type)
        .def("Entry", &haruquant::trading::DealInfo::Entry)
        .def("Magic", &haruquant::trading::DealInfo::Magic)
        .def("Reason", &haruquant::trading::DealInfo::Reason)
        .def("PositionId", &haruquant::trading::DealInfo::PositionId)
        .def("Volume", &haruquant::trading::DealInfo::Volume)
        .def("Price", &haruquant::trading::DealInfo::Price)
        .def("Commission", &haruquant::trading::DealInfo::Commission)
        .def("Swap", &haruquant::trading::DealInfo::Swap)
        .def("Profit", &haruquant::trading::DealInfo::Profit)
        .def("Fee", &haruquant::trading::DealInfo::Fee)
        .def("Symbol", &haruquant::trading::DealInfo::Symbol)
        .def("Comment", &haruquant::trading::DealInfo::Comment)
        .def("ExternalId", &haruquant::trading::DealInfo::ExternalId)
        .def("SetTicket", &haruquant::trading::DealInfo::SetTicket, nb::arg("value"))
        .def("SetOrder", &haruquant::trading::DealInfo::SetOrder, nb::arg("value"))
        .def("SetTime", &haruquant::trading::DealInfo::SetTime, nb::arg("value"))
        .def("SetTimeMsc", &haruquant::trading::DealInfo::SetTimeMsc, nb::arg("value"))
        .def("SetType", &haruquant::trading::DealInfo::SetType, nb::arg("value"))
        .def("SetEntry", &haruquant::trading::DealInfo::SetEntry, nb::arg("value"))
        .def("SetMagic", &haruquant::trading::DealInfo::SetMagic, nb::arg("value"))
        .def("SetReason", &haruquant::trading::DealInfo::SetReason, nb::arg("value"))
        .def("SetPositionId", &haruquant::trading::DealInfo::SetPositionId, nb::arg("value"))
        .def("SetVolume", &haruquant::trading::DealInfo::SetVolume, nb::arg("value"))
        .def("SetPrice", &haruquant::trading::DealInfo::SetPrice, nb::arg("value"))
        .def("SetCommission", &haruquant::trading::DealInfo::SetCommission, nb::arg("value"))
        .def("SetSwap", &haruquant::trading::DealInfo::SetSwap, nb::arg("value"))
        .def("SetProfit", &haruquant::trading::DealInfo::SetProfit, nb::arg("value"))
        .def("SetFee", &haruquant::trading::DealInfo::SetFee, nb::arg("value"))
        .def("SetSymbol", &haruquant::trading::DealInfo::SetSymbol, nb::arg("value"))
        .def("SetComment", &haruquant::trading::DealInfo::SetComment, nb::arg("value"))
        .def("SetExternalId", &haruquant::trading::DealInfo::SetExternalId, nb::arg("value"));

    nb::class_<haruquant::trading::HistoryOrderInfo>(m, "HistoryOrderInfo")
        .def(nb::init<>())
        .def("__init__", [](haruquant::trading::HistoryOrderInfo* self, nb::object source) {
            new (self) haruquant::trading::HistoryOrderInfo(history_order_from_object(source));
        }, nb::arg("source"))
        .def("SelectTicket", static_cast<bool (haruquant::trading::HistoryOrderInfo::*)(long)>(&haruquant::trading::HistoryOrderInfo::Ticket), nb::arg("ticket"))
        .def("Ticket", static_cast<long (haruquant::trading::HistoryOrderInfo::*)() const>(&haruquant::trading::HistoryOrderInfo::Ticket))
        .def("TimeSetup", &haruquant::trading::HistoryOrderInfo::TimeSetup)
        .def("TimeSetupMsc", &haruquant::trading::HistoryOrderInfo::TimeSetupMsc)
        .def("TimeDone", &haruquant::trading::HistoryOrderInfo::TimeDone)
        .def("TimeDoneMsc", &haruquant::trading::HistoryOrderInfo::TimeDoneMsc)
        .def("TimeExpiration", &haruquant::trading::HistoryOrderInfo::TimeExpiration)
        .def("Type", &haruquant::trading::HistoryOrderInfo::Type)
        .def("TypeTime", &haruquant::trading::HistoryOrderInfo::TypeTime)
        .def("TypeFilling", &haruquant::trading::HistoryOrderInfo::TypeFilling)
        .def("State", &haruquant::trading::HistoryOrderInfo::State)
        .def("Magic", &haruquant::trading::HistoryOrderInfo::Magic)
        .def("Reason", &haruquant::trading::HistoryOrderInfo::Reason)
        .def("PositionId", &haruquant::trading::HistoryOrderInfo::PositionId)
        .def("VolumeInitial", &haruquant::trading::HistoryOrderInfo::VolumeInitial)
        .def("VolumeCurrent", &haruquant::trading::HistoryOrderInfo::VolumeCurrent)
        .def("PriceOpen", &haruquant::trading::HistoryOrderInfo::PriceOpen)
        .def("Sl", &haruquant::trading::HistoryOrderInfo::Sl)
        .def("Tp", &haruquant::trading::HistoryOrderInfo::Tp)
        .def("PriceCurrent", &haruquant::trading::HistoryOrderInfo::PriceCurrent)
        .def("PriceStopLimit", &haruquant::trading::HistoryOrderInfo::PriceStopLimit)
        .def("Symbol", &haruquant::trading::HistoryOrderInfo::Symbol)
        .def("Comment", &haruquant::trading::HistoryOrderInfo::Comment)
        .def("ExternalId", &haruquant::trading::HistoryOrderInfo::ExternalId)
        .def("SetTicket", &haruquant::trading::HistoryOrderInfo::SetTicket, nb::arg("value"))
        .def("SetTimeSetup", &haruquant::trading::HistoryOrderInfo::SetTimeSetup, nb::arg("value"))
        .def("SetTimeSetupMsc", &haruquant::trading::HistoryOrderInfo::SetTimeSetupMsc, nb::arg("value"))
        .def("SetTimeDone", &haruquant::trading::HistoryOrderInfo::SetTimeDone, nb::arg("value"))
        .def("SetTimeDoneMsc", &haruquant::trading::HistoryOrderInfo::SetTimeDoneMsc, nb::arg("value"))
        .def("SetTimeExpiration", &haruquant::trading::HistoryOrderInfo::SetTimeExpiration, nb::arg("value"))
        .def("SetType", &haruquant::trading::HistoryOrderInfo::SetType, nb::arg("value"))
        .def("SetTypeTime", &haruquant::trading::HistoryOrderInfo::SetTypeTime, nb::arg("value"))
        .def("SetTypeFilling", &haruquant::trading::HistoryOrderInfo::SetTypeFilling, nb::arg("value"))
        .def("SetState", &haruquant::trading::HistoryOrderInfo::SetStateValue, nb::arg("value"))
        .def("SetMagic", &haruquant::trading::HistoryOrderInfo::SetMagic, nb::arg("value"))
        .def("SetReason", &haruquant::trading::HistoryOrderInfo::SetReason, nb::arg("value"))
        .def("SetPositionId", &haruquant::trading::HistoryOrderInfo::SetPositionId, nb::arg("value"))
        .def("SetVolumeInitial", &haruquant::trading::HistoryOrderInfo::SetVolumeInitial, nb::arg("value"))
        .def("SetVolumeCurrent", &haruquant::trading::HistoryOrderInfo::SetVolumeCurrent, nb::arg("value"))
        .def("SetPriceOpen", &haruquant::trading::HistoryOrderInfo::SetPriceOpen, nb::arg("value"))
        .def("SetSl", &haruquant::trading::HistoryOrderInfo::SetSl, nb::arg("value"))
        .def("SetTp", &haruquant::trading::HistoryOrderInfo::SetTp, nb::arg("value"))
        .def("SetPriceCurrent", &haruquant::trading::HistoryOrderInfo::SetPriceCurrent, nb::arg("value"))
        .def("SetPriceStopLimit", &haruquant::trading::HistoryOrderInfo::SetPriceStopLimit, nb::arg("value"))
        .def("SetSymbol", &haruquant::trading::HistoryOrderInfo::SetSymbol, nb::arg("value"))
        .def("SetComment", &haruquant::trading::HistoryOrderInfo::SetComment, nb::arg("value"))
        .def("SetExternalId", &haruquant::trading::HistoryOrderInfo::SetExternalId, nb::arg("value"));

    nb::class_<haruquant::trading::OrderInfo>(m, "OrderInfo")
        .def(nb::init<>())
        .def("__init__", [](haruquant::trading::OrderInfo* self, nb::object source) {
            new (self) haruquant::trading::OrderInfo(order_from_object(source));
        }, nb::arg("source"))
        .def("SelectTicket", &haruquant::trading::OrderInfo::Select, nb::arg("ticket"))
        .def("SelectByIndex", &haruquant::trading::OrderInfo::SelectByIndex, nb::arg("index"))
        .def("Ticket", &haruquant::trading::OrderInfo::Ticket)
        .def("TimeSetup", &haruquant::trading::OrderInfo::TimeSetup)
        .def("TimeSetupMsc", &haruquant::trading::OrderInfo::TimeSetupMsc)
        .def("TimeDone", &haruquant::trading::OrderInfo::TimeDone)
        .def("TimeDoneMsc", &haruquant::trading::OrderInfo::TimeDoneMsc)
        .def("TimeExpiration", &haruquant::trading::OrderInfo::TimeExpiration)
        .def("Type", &haruquant::trading::OrderInfo::Type)
        .def("TypeTime", &haruquant::trading::OrderInfo::TypeTime)
        .def("TypeFilling", &haruquant::trading::OrderInfo::TypeFilling)
        .def("State", &haruquant::trading::OrderInfo::State)
        .def("Magic", &haruquant::trading::OrderInfo::Magic)
        .def("Reason", &haruquant::trading::OrderInfo::Reason)
        .def("PositionId", &haruquant::trading::OrderInfo::PositionId)
        .def("PositionById", &haruquant::trading::OrderInfo::PositionById)
        .def("VolumeInitial", &haruquant::trading::OrderInfo::VolumeInitial)
        .def("VolumeCurrent", &haruquant::trading::OrderInfo::VolumeCurrent)
        .def("PriceOpen", &haruquant::trading::OrderInfo::PriceOpen)
        .def("Sl", &haruquant::trading::OrderInfo::Sl)
        .def("Tp", &haruquant::trading::OrderInfo::Tp)
        .def("PriceCurrent", &haruquant::trading::OrderInfo::PriceCurrent)
        .def("PriceStopLimit", &haruquant::trading::OrderInfo::PriceStopLimit)
        .def("Symbol", &haruquant::trading::OrderInfo::Symbol)
        .def("Comment", &haruquant::trading::OrderInfo::Comment)
        .def("ExternalId", &haruquant::trading::OrderInfo::ExternalId)
        .def("SetTicket", &haruquant::trading::OrderInfo::SetTicket, nb::arg("value"))
        .def("SetTimeSetup", &haruquant::trading::OrderInfo::SetTimeSetup, nb::arg("value"))
        .def("SetTimeSetupMsc", &haruquant::trading::OrderInfo::SetTimeSetupMsc, nb::arg("value"))
        .def("SetTimeDone", &haruquant::trading::OrderInfo::SetTimeDone, nb::arg("value"))
        .def("SetTimeDoneMsc", &haruquant::trading::OrderInfo::SetTimeDoneMsc, nb::arg("value"))
        .def("SetTimeExpiration", &haruquant::trading::OrderInfo::SetTimeExpiration, nb::arg("value"))
        .def("SetType", &haruquant::trading::OrderInfo::SetType, nb::arg("value"))
        .def("SetTypeTime", &haruquant::trading::OrderInfo::SetTypeTime, nb::arg("value"))
        .def("SetTypeFilling", &haruquant::trading::OrderInfo::SetTypeFilling, nb::arg("value"))
        .def("SetState", &haruquant::trading::OrderInfo::SetStateValue, nb::arg("value"))
        .def("SetMagic", &haruquant::trading::OrderInfo::SetMagic, nb::arg("value"))
        .def("SetReason", &haruquant::trading::OrderInfo::SetReason, nb::arg("value"))
        .def("SetPositionId", &haruquant::trading::OrderInfo::SetPositionId, nb::arg("value"))
        .def("SetPositionById", &haruquant::trading::OrderInfo::SetPositionById, nb::arg("value"))
        .def("SetVolumeInitial", &haruquant::trading::OrderInfo::SetVolumeInitial, nb::arg("value"))
        .def("SetVolumeCurrent", &haruquant::trading::OrderInfo::SetVolumeCurrent, nb::arg("value"))
        .def("SetPriceOpen", &haruquant::trading::OrderInfo::SetPriceOpen, nb::arg("value"))
        .def("SetSl", &haruquant::trading::OrderInfo::SetSl, nb::arg("value"))
        .def("SetTp", &haruquant::trading::OrderInfo::SetTp, nb::arg("value"))
        .def("SetPriceCurrent", &haruquant::trading::OrderInfo::SetPriceCurrent, nb::arg("value"))
        .def("SetPriceStopLimit", &haruquant::trading::OrderInfo::SetPriceStopLimit, nb::arg("value"))
        .def("SetSymbol", &haruquant::trading::OrderInfo::SetSymbol, nb::arg("value"))
        .def("SetComment", &haruquant::trading::OrderInfo::SetComment, nb::arg("value"))
        .def("SetExternalId", &haruquant::trading::OrderInfo::SetExternalId, nb::arg("value"));

    nb::class_<haruquant::trading::PositionInfo>(m, "PositionInfo")
        .def(nb::init<>())
        .def("__init__", [](haruquant::trading::PositionInfo* self, nb::object source) {
            new (self) haruquant::trading::PositionInfo(position_from_object(source));
        }, nb::arg("source"))
        .def("Select", &haruquant::trading::PositionInfo::Select, nb::arg("symbol"))
        .def("SelectByTicket", &haruquant::trading::PositionInfo::SelectByTicket, nb::arg("ticket"))
        .def("SelectByIndex", &haruquant::trading::PositionInfo::SelectByIndex, nb::arg("index"))
        .def("Ticket", &haruquant::trading::PositionInfo::Ticket)
        .def("Time", &haruquant::trading::PositionInfo::Time)
        .def("TimeMsc", &haruquant::trading::PositionInfo::TimeMsc)
        .def("TimeUpdate", &haruquant::trading::PositionInfo::TimeUpdate)
        .def("TimeUpdateMsc", &haruquant::trading::PositionInfo::TimeUpdateMsc)
        .def("Type", &haruquant::trading::PositionInfo::Type)
        .def("Magic", &haruquant::trading::PositionInfo::Magic)
        .def("Identifier", &haruquant::trading::PositionInfo::Identifier)
        .def("Reason", &haruquant::trading::PositionInfo::Reason)
        .def("Volume", &haruquant::trading::PositionInfo::Volume)
        .def("PriceOpen", &haruquant::trading::PositionInfo::PriceOpen)
        .def("Sl", &haruquant::trading::PositionInfo::Sl)
        .def("Tp", &haruquant::trading::PositionInfo::Tp)
        .def("PriceCurrent", &haruquant::trading::PositionInfo::PriceCurrent)
        .def("Swap", &haruquant::trading::PositionInfo::Swap)
        .def("Profit", &haruquant::trading::PositionInfo::Profit)
        .def("Symbol", &haruquant::trading::PositionInfo::Symbol)
        .def("Comment", &haruquant::trading::PositionInfo::Comment)
        .def("ExternalId", &haruquant::trading::PositionInfo::ExternalId)
        .def("SetTicket", &haruquant::trading::PositionInfo::SetTicket, nb::arg("value"))
        .def("SetTime", &haruquant::trading::PositionInfo::SetTime, nb::arg("value"))
        .def("SetTimeMsc", &haruquant::trading::PositionInfo::SetTimeMsc, nb::arg("value"))
        .def("SetTimeUpdate", &haruquant::trading::PositionInfo::SetTimeUpdate, nb::arg("value"))
        .def("SetTimeUpdateMsc", &haruquant::trading::PositionInfo::SetTimeUpdateMsc, nb::arg("value"))
        .def("SetType", &haruquant::trading::PositionInfo::SetType, nb::arg("value"))
        .def("SetMagic", &haruquant::trading::PositionInfo::SetMagic, nb::arg("value"))
        .def("SetIdentifier", &haruquant::trading::PositionInfo::SetIdentifier, nb::arg("value"))
        .def("SetReason", &haruquant::trading::PositionInfo::SetReason, nb::arg("value"))
        .def("SetVolume", &haruquant::trading::PositionInfo::SetVolume, nb::arg("value"))
        .def("SetPriceOpen", &haruquant::trading::PositionInfo::SetPriceOpen, nb::arg("value"))
        .def("SetSl", &haruquant::trading::PositionInfo::SetSl, nb::arg("value"))
        .def("SetTp", &haruquant::trading::PositionInfo::SetTp, nb::arg("value"))
        .def("SetPriceCurrent", &haruquant::trading::PositionInfo::SetPriceCurrent, nb::arg("value"))
        .def("SetSwap", &haruquant::trading::PositionInfo::SetSwap, nb::arg("value"))
        .def("SetProfit", &haruquant::trading::PositionInfo::SetProfit, nb::arg("value"))
        .def("SetSymbol", &haruquant::trading::PositionInfo::SetSymbol, nb::arg("value"))
        .def("SetComment", &haruquant::trading::PositionInfo::SetComment, nb::arg("value"))
        .def("SetExternalId", &haruquant::trading::PositionInfo::SetExternalId, nb::arg("value"));

    nb::class_<haruquant::trading::SymbolInfo>(m, "SymbolInfo")
        .def(nb::init<>())
        .def("__init__", [](haruquant::trading::SymbolInfo* self, nb::object source) {
            new (self) haruquant::trading::SymbolInfo(symbol_from_object(source));
        }, nb::arg("source"))
        .def("Name", static_cast<std::string (haruquant::trading::SymbolInfo::*)() const>(&haruquant::trading::SymbolInfo::Name))
        .def("Description", &haruquant::trading::SymbolInfo::Description)
        .def("Path", &haruquant::trading::SymbolInfo::Path)
        .def("Bid", &haruquant::trading::SymbolInfo::Bid)
        .def("Ask", &haruquant::trading::SymbolInfo::Ask)
        .def("Last", &haruquant::trading::SymbolInfo::Last)
        .def("Spread", &haruquant::trading::SymbolInfo::Spread)
        .def("SpreadFloat", &haruquant::trading::SymbolInfo::SpreadFloat)
        .def("Time", &haruquant::trading::SymbolInfo::Time)
        .def("Digits", &haruquant::trading::SymbolInfo::Digits)
        .def("Point", &haruquant::trading::SymbolInfo::Point)
        .def("TradeMode", &haruquant::trading::SymbolInfo::TradeMode)
        .def("TradeExemode", &haruquant::trading::SymbolInfo::TradeExemode)
        .def("TradeCalcMode", &haruquant::trading::SymbolInfo::TradeCalcMode)
        .def("TradeStopsLevel", &haruquant::trading::SymbolInfo::TradeStopsLevel)
        .def("TradeFreezeLevel", &haruquant::trading::SymbolInfo::TradeFreezeLevel)
        .def("TradeTickSize", &haruquant::trading::SymbolInfo::TradeTickSize)
        .def("TradeTickValue", &haruquant::trading::SymbolInfo::TradeTickValue)
        .def("TradeTickValueProfit", &haruquant::trading::SymbolInfo::TradeTickValueProfit)
        .def("TradeTickValueLoss", &haruquant::trading::SymbolInfo::TradeTickValueLoss)
        .def("TradeContractSize", &haruquant::trading::SymbolInfo::TradeContractSize)
        .def("VolumeMin", &haruquant::trading::SymbolInfo::VolumeMin)
        .def("VolumeMax", &haruquant::trading::SymbolInfo::VolumeMax)
        .def("VolumeStep", &haruquant::trading::SymbolInfo::VolumeStep)
        .def("VolumeLimit", &haruquant::trading::SymbolInfo::VolumeLimit)
        .def("MarginInitial", &haruquant::trading::SymbolInfo::MarginInitial)
        .def("MarginMaintenance", &haruquant::trading::SymbolInfo::MarginMaintenance)
        .def("SwapMode", &haruquant::trading::SymbolInfo::SwapMode)
        .def("SwapLong", &haruquant::trading::SymbolInfo::SwapLong)
        .def("SwapShort", &haruquant::trading::SymbolInfo::SwapShort)
        .def("SwapRollover3days", &haruquant::trading::SymbolInfo::SwapRollover3days)
        .def("CurrencyBase", &haruquant::trading::SymbolInfo::CurrencyBase)
        .def("CurrencyProfit", &haruquant::trading::SymbolInfo::CurrencyProfit)
        .def("CurrencyMargin", &haruquant::trading::SymbolInfo::CurrencyMargin)
        .def("NormalizePrice", &haruquant::trading::SymbolInfo::NormalizePrice, nb::arg("price"))
        .def("SetName", [](haruquant::trading::SymbolInfo& self, const std::string& value) {
            self.Name(value);
        }, nb::arg("value"))
        .def("SetDescription", &haruquant::trading::SymbolInfo::SetDescription, nb::arg("value"))
        .def("SetPath", &haruquant::trading::SymbolInfo::SetPath, nb::arg("value"))
        .def("SetSelect", &haruquant::trading::SymbolInfo::SetSelect, nb::arg("value"))
        .def("SetTime", &haruquant::trading::SymbolInfo::SetTime, nb::arg("value"))
        .def("SetDigits", &haruquant::trading::SymbolInfo::SetDigits, nb::arg("value"))
        .def("SetSpread", &haruquant::trading::SymbolInfo::SetSpread, nb::arg("value"))
        .def("SetSpreadFloat", &haruquant::trading::SymbolInfo::SetSpreadFloat, nb::arg("value"))
        .def("SetTradeMode", &haruquant::trading::SymbolInfo::SetTradeMode, nb::arg("value"))
        .def("SetTradeExemode", &haruquant::trading::SymbolInfo::SetTradeExemode, nb::arg("value"))
        .def("SetTradeCalcMode", &haruquant::trading::SymbolInfo::SetTradeCalcMode, nb::arg("value"))
        .def("SetTradeStopsLevel", &haruquant::trading::SymbolInfo::SetTradeStopsLevel, nb::arg("value"))
        .def("SetTradeFreezeLevel", &haruquant::trading::SymbolInfo::SetTradeFreezeLevel, nb::arg("value"))
        .def("SetBid", &haruquant::trading::SymbolInfo::SetBid, nb::arg("value"))
        .def("SetAsk", &haruquant::trading::SymbolInfo::SetAsk, nb::arg("value"))
        .def("SetLast", &haruquant::trading::SymbolInfo::SetLast, nb::arg("value"))
        .def("SetPoint", &haruquant::trading::SymbolInfo::SetPoint, nb::arg("value"))
        .def("SetTradeTickSize", &haruquant::trading::SymbolInfo::SetTradeTickSize, nb::arg("value"))
        .def("SetTradeTickValue", &haruquant::trading::SymbolInfo::SetTradeTickValue, nb::arg("value"))
        .def("SetTradeTickValueProfit", &haruquant::trading::SymbolInfo::SetTradeTickValueProfit, nb::arg("value"))
        .def("SetTradeTickValueLoss", &haruquant::trading::SymbolInfo::SetTradeTickValueLoss, nb::arg("value"))
        .def("SetTradeContractSize", &haruquant::trading::SymbolInfo::SetTradeContractSize, nb::arg("value"))
        .def("SetVolumeMin", &haruquant::trading::SymbolInfo::SetVolumeMin, nb::arg("value"))
        .def("SetVolumeMax", &haruquant::trading::SymbolInfo::SetVolumeMax, nb::arg("value"))
        .def("SetVolumeStep", &haruquant::trading::SymbolInfo::SetVolumeStep, nb::arg("value"))
        .def("SetVolumeLimit", &haruquant::trading::SymbolInfo::SetVolumeLimit, nb::arg("value"))
        .def("SetMarginInitial", &haruquant::trading::SymbolInfo::SetMarginInitial, nb::arg("value"))
        .def("SetMarginMaintenance", &haruquant::trading::SymbolInfo::SetMarginMaintenance, nb::arg("value"))
        .def("SetSwapMode", &haruquant::trading::SymbolInfo::SetSwapMode, nb::arg("value"))
        .def("SetSwapLong", &haruquant::trading::SymbolInfo::SetSwapLong, nb::arg("value"))
        .def("SetSwapShort", &haruquant::trading::SymbolInfo::SetSwapShort, nb::arg("value"))
        .def("SetSwapRollover3days", &haruquant::trading::SymbolInfo::SetSwapRollover3days, nb::arg("value"))
        .def("SetCurrencyBase", &haruquant::trading::SymbolInfo::SetCurrencyBase, nb::arg("value"))
        .def("SetCurrencyProfit", &haruquant::trading::SymbolInfo::SetCurrencyProfit, nb::arg("value"))
        .def("SetCurrencyMargin", &haruquant::trading::SymbolInfo::SetCurrencyMargin, nb::arg("value"));

    nb::class_<haruquant::core::BacktestSimulator>(m, "BacktestSimulator")
        .def(nb::init<>())
        .def(nb::init<const haruquant::trading::AccountInfo&>(), nb::arg("account"))
        .def("account_info", [](const haruquant::core::BacktestSimulator& self) {
            return self.account_info();
        });
}
