#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>

#include "core/backtest_simulator.hpp"
#include "trading/account_info.hpp"
#include "trading/deal_info.hpp"
#include "trading/history_order_info.hpp"
#include "trading/order_info.hpp"

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

    nb::class_<haruquant::core::BacktestSimulator>(m, "BacktestSimulator")
        .def(nb::init<>())
        .def(nb::init<const haruquant::trading::AccountInfo&>(), nb::arg("account"))
        .def("account_info", [](const haruquant::core::BacktestSimulator& self) {
            return self.account_info();
        });
}
