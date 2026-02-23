#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>

#include "core/backtest_simulator.hpp"
#include "trading/account_info.hpp"

#include <functional>

namespace nb = nanobind;

namespace {

template <typename T>
void assign_if_present(const nb::object& source, const char* name, const std::function<void(T)>& setter) {
    if (!nb::hasattr(source, name)) {
        return;
    }
    nb::object value = source.attr(name);
    if (value.is_none()) {
        return;
    }
    setter(nb::cast<T>(value));
}

haruquant::AccountInfo account_from_object(const nb::object& source) {
    haruquant::AccountInfo acc;

    assign_if_present<int>(source, "login", [&](int v) { acc.SetLogin(v); });
    assign_if_present<std::string>(source, "name", [&](const std::string& v) { acc.SetName(v); });
    assign_if_present<std::string>(source, "server", [&](const std::string& v) { acc.SetServer(v); });
    assign_if_present<std::string>(source, "currency", [&](const std::string& v) { acc.SetCurrency(v); });
    assign_if_present<std::string>(source, "company", [&](const std::string& v) { acc.SetCompany(v); });

    assign_if_present<int>(source, "trade_mode", [&](int v) {
        acc.SetTradeMode(static_cast<haruquant::ENUM_ACCOUNT_TRADE_MODE>(v));
    });
    assign_if_present<int>(source, "leverage", [&](int v) { acc.SetLeverage(v); });
    assign_if_present<int>(source, "limit_orders", [&](int v) { acc.SetLimitOrders(v); });
    assign_if_present<int>(source, "margin_so_mode", [&](int v) {
        acc.SetStopoutMode(static_cast<haruquant::ENUM_ACCOUNT_STOPOUT_MODE>(v));
    });
    assign_if_present<bool>(source, "trade_allowed", [&](bool v) { acc.SetTradeAllowed(v); });
    assign_if_present<bool>(source, "trade_expert", [&](bool v) { acc.SetTradeExpert(v); });
    assign_if_present<int>(source, "margin_mode", [&](int v) {
        acc.SetMarginMode(static_cast<haruquant::ENUM_ACCOUNT_MARGIN_MODE>(v));
    });
    assign_if_present<int>(source, "currency_digits", [&](int v) { acc.SetCurrencyDigits(v); });
    assign_if_present<bool>(source, "fifo_close", [&](bool v) { acc.SetFifoClose(v); });

    assign_if_present<double>(source, "balance", [&](double v) { acc.SetBalance(v); });
    assign_if_present<double>(source, "credit", [&](double v) { acc.SetCredit(v); });
    assign_if_present<double>(source, "profit", [&](double v) { acc.SetProfit(v); });
    assign_if_present<double>(source, "equity", [&](double v) { acc.SetEquity(v); });
    assign_if_present<double>(source, "margin", [&](double v) { acc.SetMargin(v); });
    assign_if_present<double>(source, "margin_free", [&](double v) { acc.SetFreeMargin(v); });
    assign_if_present<double>(source, "margin_level", [&](double v) { acc.SetMarginLevel(v); });
    assign_if_present<double>(source, "margin_so_call", [&](double v) { acc.SetMarginCall(v); });
    assign_if_present<double>(source, "margin_so_so", [&](double v) { acc.SetMarginStopOut(v); });
    assign_if_present<double>(source, "margin_initial", [&](double v) { acc.SetMarginInitial(v); });
    assign_if_present<double>(source, "margin_maintenance", [&](double v) { acc.SetMarginMaintenance(v); });
    assign_if_present<double>(source, "assets", [&](double v) { acc.SetAssets(v); });
    assign_if_present<double>(source, "liabilities", [&](double v) { acc.SetLiabilities(v); });
    assign_if_present<double>(source, "commission_blocked", [&](double v) { acc.SetCommissionBlocked(v); });

    return acc;
}

}  // namespace

void register_core_bindings(nb::module_& m) {
    m.doc() = "Core engine bindings";

    nb::class_<haruquant::AccountInfo>(m, "AccountInfo")
        .def(nb::init<>())
        .def("__init__", [](haruquant::AccountInfo* self, nb::object source) {
            new (self) haruquant::AccountInfo(account_from_object(source));
        }, nb::arg("source"))
        .def(nb::init<double, const std::string&, int>(),
             nb::arg("initial_balance"),
             nb::arg("currency"),
             nb::arg("leverage"));

    nb::class_<haruquant::core::BacktestSimulator>(m, "BacktestSimulator")
        .def(nb::init<const haruquant::AccountInfo&>(), nb::arg("account_info"));
}
