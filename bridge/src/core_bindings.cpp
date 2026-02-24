#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>

#include "core/backtest_simulator.hpp"
#include "trading/account_info.hpp"

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

    nb::class_<haruquant::core::BacktestSimulator>(m, "BacktestSimulator")
        .def(nb::init<>())
        .def(nb::init<const haruquant::trading::AccountInfo&>(), nb::arg("account"))
        .def("account_info", [](const haruquant::core::BacktestSimulator& self) {
            return self.account_info();
        });
}
