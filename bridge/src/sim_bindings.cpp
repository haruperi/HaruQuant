/**
 * @file sim_bindings.cpp
 * @brief Nanobind bindings for the haruquant::sim simulation API.
 *
 * PR-014: Exposes the full C++ sim API to Python under haruquant.sim.
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
#include <cctype>
#include <utility>

namespace nb = nanobind;
using namespace haruquant::sim;

namespace {

template <typename Func, typename... Args>
decltype(auto) call_without_gil(Func&& func, Args&&... args) {
    nb::gil_scoped_release release;
    return std::invoke(std::forward<Func>(func), std::forward<Args>(args)...);
}

haruquant::AccountInfo to_mt5_account(const haruquant::AccountInfo& src) {
    return src;
}

haruquant::SymbolInfo to_mt5_symbol(const haruquant::SymbolInfo& src) {
    return src;
}

template <typename T>
nb::tuple to_tuple(const std::vector<T>& values) {
    nb::object tuple_type = nb::module_::import_("builtins").attr("tuple");
    nb::object out = tuple_type(nb::cast(values));
    return nb::cast<nb::tuple>(out);
}

int64_t to_unix_seconds(const nb::object& value) {
    if (value.is_none()) {
        return 0;
    }
    if (nb::hasattr(value, "timestamp")) {
        nb::object ts = value.attr("timestamp")();
        return static_cast<int64_t>(nb::cast<double>(ts));
    }
    if (nb::isinstance<nb::int_>(value)) {
        return nb::cast<int64_t>(value);
    }
    if (nb::isinstance<nb::float_>(value)) {
        return static_cast<int64_t>(nb::cast<double>(value));
    }
    throw nb::type_error("Expected datetime or epoch seconds for date argument");
}

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

haruquant::SymbolInfo symbol_from_object(const nb::object& source) {
    haruquant::SymbolInfo sym;

    auto read_str = [&](const char* name, const std::function<void(const std::string&)>& setter) {
        if (!nb::hasattr(source, name)) return;
        nb::object value = source.attr(name);
        if (value.is_none()) return;
        setter(nb::cast<std::string>(value));
    };
    auto read_int = [&](const char* name, const std::function<void(int)>& setter) {
        if (!nb::hasattr(source, name)) return;
        nb::object value = source.attr(name);
        if (value.is_none()) return;
        setter(nb::cast<int>(value));
    };
    auto read_u32 = [&](const char* name, const std::function<void(uint32_t)>& setter) {
        if (!nb::hasattr(source, name)) return;
        nb::object value = source.attr(name);
        if (value.is_none()) return;
        setter(nb::cast<uint32_t>(value));
    };
    auto read_double = [&](const char* name, const std::function<void(double)>& setter) {
        if (!nb::hasattr(source, name)) return;
        nb::object value = source.attr(name);
        if (value.is_none()) return;
        setter(nb::cast<double>(value));
    };
    auto read_bool = [&](const char* name, const std::function<void(bool)>& setter) {
        if (!nb::hasattr(source, name)) return;
        nb::object value = source.attr(name);
        if (value.is_none()) return;
        setter(nb::cast<bool>(value));
    };

    read_str("symbol", [&](const std::string& v) { sym.Name(v); });
    read_str("name", [&](const std::string& v) { sym.Name(v); });
    read_u32("symbol_id", [&](uint32_t v) { sym.SetSymbolId(v); });
    read_int("digits", [&](int v) { sym.SetDigits(v); });
    read_double("point", [&](double v) { sym.SetPoint(v); });
    read_int("spread", [&](int v) { sym.SetSpread(v); });
    read_bool("spread_float", [&](bool v) { sym.SetSpreadFloat(v); });

    read_int("trade_mode", [&](int v) {
        sym.SetTradeMode(static_cast<haruquant::ENUM_SYMBOL_TRADE_MODE>(v));
    });
    read_int("trade_exemode", [&](int v) {
        sym.SetTradeExecution(static_cast<haruquant::ENUM_SYMBOL_TRADE_EXECUTION>(v));
    });
    read_int("trade_calc_mode", [&](int v) {
        sym.SetTradeCalcMode(static_cast<haruquant::ENUM_SYMBOL_CALC_MODE>(v));
    });

    read_double("volume_min", [&](double v) { sym.SetVolumeMin(v); });
    read_double("volume_max", [&](double v) { sym.SetVolumeMax(v); });
    read_double("volume_step", [&](double v) { sym.SetVolumeStep(v); });
    read_double("trade_contract_size", [&](double v) { sym.SetContractSize(v); });
    read_double("trade_tick_size", [&](double v) { sym.SetTickSize(v); });
    read_double("trade_tick_value", [&](double v) { sym.SetTickValue(v); });
    read_double("trade_tick_value_profit", [&](double v) { sym.SetTickValueProfit(v); });
    read_double("trade_tick_value_loss", [&](double v) { sym.SetTickValueLoss(v); });

    double bid = 0.0;
    double ask = 0.0;
    double last = 0.0;
    int64_t ts = 0;
    read_double("bid", [&](double v) { bid = v; });
    read_double("ask", [&](double v) { ask = v; });
    read_double("last", [&](double v) { last = v; });
    read_int("time", [&](int v) { ts = static_cast<int64_t>(v); });
    if (bid > 0.0 && ask > 0.0) {
        sym.UpdatePrice(bid, ask, ts);
    } else if (last > 0.0) {
        sym.UpdatePrice(last, last, ts);
    }

    return sym;
}

std::string normalize_order_type_token(std::string token) {
    std::string out;
    out.reserve(token.size());
    for (char ch : token) {
        if (ch == ' ' || ch == '-') {
            out.push_back('_');
        } else {
            out.push_back(static_cast<char>(std::toupper(static_cast<unsigned char>(ch))));
        }
    }
    constexpr const char* kPrefix = "ORDER_TYPE_";
    if (out.rfind(kPrefix, 0) == 0) {
        out.erase(0, std::char_traits<char>::length(kPrefix));
    }
    return out;
}

int resolve_order_type(const nb::object& order_type) {
    if (nb::isinstance<nb::int_>(order_type)) {
        return nb::cast<int>(order_type);
    }
    if (!nb::isinstance<nb::str>(order_type)) {
        throw nb::type_error("order_type must be int or string");
    }

    const std::string token = normalize_order_type_token(nb::cast<std::string>(order_type));
    if (token == "BUY") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY);
    if (token == "SELL") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL);
    if (token == "BUY_LIMIT") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT);
    if (token == "SELL_LIMIT") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_LIMIT);
    if (token == "BUY_STOP") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP);
    if (token == "SELL_STOP") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP);
    if (token == "BUY_STOP_LIMIT") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP_LIMIT);
    if (token == "SELL_STOP_LIMIT") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP_LIMIT);

    throw nb::value_error("Unsupported order_type string");
}

int resolve_order_time(const nb::object& type_time) {
    if (type_time.is_none()) {
        return 0;
    }
    if (nb::isinstance<nb::int_>(type_time)) {
        return nb::cast<int>(type_time);
    }
    if (!nb::isinstance<nb::str>(type_time)) {
        throw nb::type_error("type_time must be int or string");
    }

    std::string token = nb::cast<std::string>(type_time);
    for (char& ch : token) {
        if (ch == ' ' || ch == '-') {
            ch = '_';
        } else {
            ch = static_cast<char>(std::toupper(static_cast<unsigned char>(ch)));
        }
    }
    constexpr const char* kPrefix = "ORDER_TIME_";
    if (token.rfind(kPrefix, 0) == 0) {
        token.erase(0, std::char_traits<char>::length(kPrefix));
    }

    if (token == "GTC") {
        return static_cast<int>(haruquant::ENUM_ORDER_TYPE_TIME::ORDER_TIME_GTC);
    }
    if (token == "DAY") {
        return static_cast<int>(haruquant::ENUM_ORDER_TYPE_TIME::ORDER_TIME_DAY);
    }
    if (token == "SPECIFIED") {
        return static_cast<int>(haruquant::ENUM_ORDER_TYPE_TIME::ORDER_TIME_SPECIFIED);
    }
    if (token == "SPECIFIED_DAY") {
        return static_cast<int>(haruquant::ENUM_ORDER_TYPE_TIME::ORDER_TIME_SPECIFIED_DAY);
    }
    throw nb::value_error("Unsupported type_time string");
}

std::string position_type_name(haruquant::ENUM_POSITION_TYPE value) {
    switch (value) {
        case haruquant::ENUM_POSITION_TYPE::POSITION_TYPE_BUY:
            return "BUY";
        case haruquant::ENUM_POSITION_TYPE::POSITION_TYPE_SELL:
            return "SELL";
        default:
            return "UNKNOWN";
    }
}

haruquant::ENUM_POSITION_TYPE resolve_position_type(const nb::object& value) {
    if (nb::isinstance<nb::int_>(value)) {
        return static_cast<haruquant::ENUM_POSITION_TYPE>(nb::cast<int>(value));
    }
    if (!nb::isinstance<nb::str>(value)) {
        throw nb::type_error("position type must be int or string");
    }

    std::string token = nb::cast<std::string>(value);
    for (char& ch : token) {
        if (ch == ' ' || ch == '-') {
            ch = '_';
        } else {
            ch = static_cast<char>(std::toupper(static_cast<unsigned char>(ch)));
        }
    }
    constexpr const char* kPrefix = "POSITION_TYPE_";
    if (token.rfind(kPrefix, 0) == 0) {
        token.erase(0, std::char_traits<char>::length(kPrefix));
    }

    if (token == "BUY") {
        return haruquant::ENUM_POSITION_TYPE::POSITION_TYPE_BUY;
    }
    if (token == "SELL") {
        return haruquant::ENUM_POSITION_TYPE::POSITION_TYPE_SELL;
    }
    throw nb::value_error("Unsupported position type string");
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

    nb::class_<haruquant::AccountInfo>(m, "AccountInfo")
        .def(nb::init<>())
        .def("__init__", [](haruquant::AccountInfo* self, nb::object source) {
            new (self) haruquant::AccountInfo(account_from_object(source));
        }, nb::arg("source"))
        .def(nb::init<double, const std::string&, int>(),
             nb::arg("initial_balance"),
             nb::arg("currency"),
             nb::arg("leverage"))
        .def("Login", &haruquant::AccountInfo::Login)
        .def("Name", &haruquant::AccountInfo::Name)
        .def("Server", &haruquant::AccountInfo::Server)
        .def("Currency", &haruquant::AccountInfo::Currency)
        .def("Company", &haruquant::AccountInfo::Company)
        .def("TradeMode", [](const haruquant::AccountInfo& self) { return static_cast<int>(self.TradeMode()); })
        .def("TradeModeDescription", [](const haruquant::AccountInfo& self) { return self.TradeModeDescription(); })
        .def("TradeModeDescription", [](const haruquant::AccountInfo& self, int trade_mode) {
            return self.TradeModeDescription(trade_mode);
        }, nb::arg("trade_mode"))
        .def("Leverage", &haruquant::AccountInfo::Leverage)
        .def("TradeAllowed", &haruquant::AccountInfo::TradeAllowed)
        .def("TradeExpert", &haruquant::AccountInfo::TradeExpert)
        .def("LimitOrders", &haruquant::AccountInfo::LimitOrders)
        .def("CurrencyDigits", &haruquant::AccountInfo::CurrencyDigits)
        .def("FifoClose", &haruquant::AccountInfo::FifoClose)
        .def("Balance", &haruquant::AccountInfo::Balance)
        .def("Credit", &haruquant::AccountInfo::Credit)
        .def("Profit", &haruquant::AccountInfo::Profit)
        .def("Equity", &haruquant::AccountInfo::Equity)
        .def("Margin", &haruquant::AccountInfo::Margin)
        .def("FreeMargin", &haruquant::AccountInfo::FreeMargin)
        .def("MarginLevel", &haruquant::AccountInfo::MarginLevel)
        .def("MarginCall", &haruquant::AccountInfo::MarginCall)
        .def("MarginStopOut", &haruquant::AccountInfo::MarginStopOut)
        .def("MarginInitial", &haruquant::AccountInfo::MarginInitial)
        .def("MarginMaintenance", &haruquant::AccountInfo::MarginMaintenance)
        .def("Assets", &haruquant::AccountInfo::Assets)
        .def("Liabilities", &haruquant::AccountInfo::Liabilities)
        .def("CommissionBlocked", &haruquant::AccountInfo::CommissionBlocked)
        .def("MarginMode", [](const haruquant::AccountInfo& self) { return static_cast<int>(self.MarginMode()); })
        .def("MarginModeDescription", [](const haruquant::AccountInfo& self) { return self.MarginModeDescription(); })
        .def("MarginModeDescription", [](const haruquant::AccountInfo& self, int margin_mode) {
            return self.MarginModeDescription(margin_mode);
        }, nb::arg("margin_mode"))
        .def("StopoutMode", [](const haruquant::AccountInfo& self) { return static_cast<int>(self.StopoutMode()); })
        .def("StopoutModeDescription", [](const haruquant::AccountInfo& self) { return self.StopoutModeDescription(); })
        .def("StopoutModeDescription", [](const haruquant::AccountInfo& self, int margin_so_mode) {
            return self.StopoutModeDescription(margin_so_mode);
        }, nb::arg("margin_so_mode"))
        .def("apply_snapshot", &haruquant::AccountInfo::ApplySnapshot,
             nb::arg("balance"),
             nb::arg("credit"),
             nb::arg("profit"),
             nb::arg("margin"),
             nb::arg("margin_call"),
             nb::arg("margin_stopout"))
        .def_prop_rw("login",
            [](const haruquant::AccountInfo& self) { return self.Login(); },
            [](haruquant::AccountInfo& self, int value) { self.SetLogin(value); })
        .def_prop_rw("name",
            [](const haruquant::AccountInfo& self) { return self.Name(); },
            [](haruquant::AccountInfo& self, const std::string& value) { self.SetName(value); })
        .def_prop_rw("server",
            [](const haruquant::AccountInfo& self) { return self.Server(); },
            [](haruquant::AccountInfo& self, const std::string& value) { self.SetServer(value); })
        .def_prop_rw("company",
            [](const haruquant::AccountInfo& self) { return self.Company(); },
            [](haruquant::AccountInfo& self, const std::string& value) { self.SetCompany(value); })
        .def_prop_rw("leverage",
            [](const haruquant::AccountInfo& self) { return self.Leverage(); },
            [](haruquant::AccountInfo& self, int value) { self.SetLeverage(value); })
        .def_prop_rw("trade_mode",
            [](const haruquant::AccountInfo& self) { return static_cast<int>(self.TradeMode()); },
            [](haruquant::AccountInfo& self, int value) {
                self.SetTradeMode(static_cast<haruquant::ENUM_ACCOUNT_TRADE_MODE>(value));
            })
        .def_prop_rw("limit_orders",
            [](const haruquant::AccountInfo& self) { return self.LimitOrders(); },
            [](haruquant::AccountInfo& self, int value) { self.SetLimitOrders(value); })
        .def_prop_rw("margin_so_mode",
            [](const haruquant::AccountInfo& self) { return static_cast<int>(self.StopoutMode()); },
            [](haruquant::AccountInfo& self, int value) {
                self.SetStopoutMode(static_cast<haruquant::ENUM_ACCOUNT_STOPOUT_MODE>(value));
            })
        .def_prop_rw("currency_digits",
            [](const haruquant::AccountInfo& self) { return self.CurrencyDigits(); },
            [](haruquant::AccountInfo& self, int value) { self.SetCurrencyDigits(value); })
        .def_prop_rw("fifo_close",
            [](const haruquant::AccountInfo& self) { return self.FifoClose(); },
            [](haruquant::AccountInfo& self, bool value) { self.SetFifoClose(value); })
        .def_prop_rw("currency",
            [](const haruquant::AccountInfo& self) { return self.Currency(); },
            [](haruquant::AccountInfo& self, const std::string& value) { self.SetCurrency(value); })
        .def_prop_rw("balance",
            [](const haruquant::AccountInfo& self) { return self.Balance(); },
            [](haruquant::AccountInfo& self, double value) { self.SetBalance(value); })
        .def_prop_rw("credit",
            [](const haruquant::AccountInfo& self) { return self.Credit(); },
            [](haruquant::AccountInfo& self, double value) { self.SetCredit(value); })
        .def_prop_rw("profit",
            [](const haruquant::AccountInfo& self) { return self.Profit(); },
            [](haruquant::AccountInfo& self, double value) { self.SetProfit(value); })
        .def_prop_rw("equity",
            [](const haruquant::AccountInfo& self) { return self.Equity(); },
            [](haruquant::AccountInfo& self, double value) { self.SetEquity(value); })
        .def_prop_rw("margin",
            [](const haruquant::AccountInfo& self) { return self.Margin(); },
            [](haruquant::AccountInfo& self, double value) { self.SetMargin(value); })
        .def_prop_rw("margin_free",
            [](const haruquant::AccountInfo& self) { return self.FreeMargin(); },
            [](haruquant::AccountInfo& self, double value) { self.SetFreeMargin(value); })
        .def_prop_rw("margin_level",
            [](const haruquant::AccountInfo& self) { return self.MarginLevel(); },
            [](haruquant::AccountInfo& self, double value) { self.SetMarginLevel(value); })
        .def_prop_rw("margin_so_call",
            [](const haruquant::AccountInfo& self) { return self.MarginCall(); },
            [](haruquant::AccountInfo& self, double value) { self.SetMarginCall(value); })
        .def_prop_rw("margin_so_so",
            [](const haruquant::AccountInfo& self) { return self.MarginStopOut(); },
            [](haruquant::AccountInfo& self, double value) { self.SetMarginStopOut(value); })
        .def_prop_rw("margin_initial",
            [](const haruquant::AccountInfo& self) { return self.MarginInitial(); },
            [](haruquant::AccountInfo& self, double value) { self.SetMarginInitial(value); })
        .def_prop_rw("margin_maintenance",
            [](const haruquant::AccountInfo& self) { return self.MarginMaintenance(); },
            [](haruquant::AccountInfo& self, double value) { self.SetMarginMaintenance(value); })
        .def_prop_rw("assets",
            [](const haruquant::AccountInfo& self) { return self.Assets(); },
            [](haruquant::AccountInfo& self, double value) { self.SetAssets(value); })
        .def_prop_rw("liabilities",
            [](const haruquant::AccountInfo& self) { return self.Liabilities(); },
            [](haruquant::AccountInfo& self, double value) { self.SetLiabilities(value); })
        .def_prop_rw("commission_blocked",
            [](const haruquant::AccountInfo& self) { return self.CommissionBlocked(); },
            [](haruquant::AccountInfo& self, double value) { self.SetCommissionBlocked(value); })
        .def_prop_rw("margin_mode",
            [](const haruquant::AccountInfo& self) { return static_cast<int>(self.MarginMode()); },
            [](haruquant::AccountInfo& self, int value) {
                self.SetMarginMode(static_cast<haruquant::ENUM_ACCOUNT_MARGIN_MODE>(value));
            })
        .def_prop_rw("trade_allowed",
            [](const haruquant::AccountInfo& self) { return self.TradeAllowed(); },
            [](haruquant::AccountInfo& self, bool value) { self.SetTradeAllowed(value); })
        .def_prop_rw("trade_expert",
            [](const haruquant::AccountInfo& self) { return self.TradeExpert(); },
            [](haruquant::AccountInfo& self, bool value) { self.SetTradeExpert(value); });

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

    nb::class_<haruquant::SymbolInfo>(m, "SymbolInfo")
        .def(nb::init<>())
        .def("__init__", [](haruquant::SymbolInfo* self, nb::object source) {
            new (self) haruquant::SymbolInfo(symbol_from_object(source));
        }, nb::arg("source"))
        .def("Name", [](const haruquant::SymbolInfo& self) { return self.Name(); })
        .def("Description", &haruquant::SymbolInfo::Description)
        .def("Path", &haruquant::SymbolInfo::Path)
        .def("Select", [](haruquant::SymbolInfo& self) { return self.Select(); })
        .def("Select", [](haruquant::SymbolInfo& self, bool selected) {
            self.Select(selected);
            return self.Select();
        }, nb::arg("selected"))
        .def("Bid", &haruquant::SymbolInfo::Bid)
        .def("BidHigh", &haruquant::SymbolInfo::BidHigh)
        .def("BidLow", &haruquant::SymbolInfo::BidLow)
        .def("Ask", &haruquant::SymbolInfo::Ask)
        .def("AskHigh", &haruquant::SymbolInfo::AskHigh)
        .def("AskLow", &haruquant::SymbolInfo::AskLow)
        .def("Last", &haruquant::SymbolInfo::Last)
        .def("Spread", &haruquant::SymbolInfo::Spread)
        .def("SpreadFloat", &haruquant::SymbolInfo::SpreadFloat)
        .def("Time", &haruquant::SymbolInfo::Time)
        .def("Volume", &haruquant::SymbolInfo::Volume)
        .def("VolumeHigh", &haruquant::SymbolInfo::VolumeHigh)
        .def("VolumeLow", &haruquant::SymbolInfo::VolumeLow)
        .def("Digits", &haruquant::SymbolInfo::Digits)
        .def("Point", &haruquant::SymbolInfo::Point)
        .def("TickValue", &haruquant::SymbolInfo::TickValue)
        .def("TickSize", &haruquant::SymbolInfo::TickSize)
        .def("TickValueProfit", &haruquant::SymbolInfo::TickValueProfit)
        .def("TickValueLoss", &haruquant::SymbolInfo::TickValueLoss)
        .def("ContractSize", &haruquant::SymbolInfo::ContractSize)
        .def("LotsMin", &haruquant::SymbolInfo::LotsMin)
        .def("LotsMax", &haruquant::SymbolInfo::LotsMax)
        .def("LotsStep", &haruquant::SymbolInfo::LotsStep)
        .def("LotsLimit", &haruquant::SymbolInfo::LotsLimit)
        .def("MarginInitial", &haruquant::SymbolInfo::MarginInitial)
        .def("MarginMaintenance", &haruquant::SymbolInfo::MarginMaintenance)
        .def("MarginLong", &haruquant::SymbolInfo::MarginLong)
        .def("MarginShort", &haruquant::SymbolInfo::MarginShort)
        .def("MarginLimit", &haruquant::SymbolInfo::MarginLimit)
        .def("MarginStop", &haruquant::SymbolInfo::MarginStop)
        .def("MarginStopLimit", &haruquant::SymbolInfo::MarginStopLimit)
        .def("SwapLong", &haruquant::SymbolInfo::SwapLong)
        .def("SwapShort", &haruquant::SymbolInfo::SwapShort)
        .def("SwapMode", [](const haruquant::SymbolInfo& self) { return static_cast<int>(self.SwapMode()); })
        .def("SwapModeDescription", &haruquant::SymbolInfo::SwapModeDescription)
        .def("SwapRollover3days", [](const haruquant::SymbolInfo& self) { return static_cast<int>(self.SwapRollover3days()); })
        .def("SwapRollover3daysDescription", &haruquant::SymbolInfo::SwapRollover3daysDescription)
        .def("SwapRollover3DaysDescription", &haruquant::SymbolInfo::SwapRollover3daysDescription)
        .def("TradeMode", [](const haruquant::SymbolInfo& self) { return static_cast<int>(self.TradeMode()); })
        .def("TradeModeDescription", &haruquant::SymbolInfo::TradeModeDescription)
        .def("TradeExecution", [](const haruquant::SymbolInfo& self) { return static_cast<int>(self.TradeExecution()); })
        .def("TradeExecutionDescription", &haruquant::SymbolInfo::TradeExecutionDescription)
        .def("TradeCalcMode", [](const haruquant::SymbolInfo& self) { return static_cast<int>(self.TradeCalcMode()); })
        .def("TradeCalcModeDescription", &haruquant::SymbolInfo::TradeCalcModeDescription)
        .def("StopsLevel", &haruquant::SymbolInfo::StopsLevel)
        .def("FreezeLevel", &haruquant::SymbolInfo::FreezeLevel)
        .def("CurrencyBase", &haruquant::SymbolInfo::CurrencyBase)
        .def("CurrencyProfit", &haruquant::SymbolInfo::CurrencyProfit)
        .def("CurrencyMargin", &haruquant::SymbolInfo::CurrencyMargin)
        .def("NormalizePrice", &haruquant::SymbolInfo::NormalizePrice)
        .def("Refresh", &haruquant::SymbolInfo::Refresh)
        .def("RefreshRates", &haruquant::SymbolInfo::RefreshRates)
        .def_prop_rw("symbol",
            [](const haruquant::SymbolInfo& self) { return self.Name(); },
            [](haruquant::SymbolInfo& self, const std::string& value) { self.Name(value); })
        .def_prop_rw("symbol_id",
            [](const haruquant::SymbolInfo& self) { return self.SymbolId(); },
            [](haruquant::SymbolInfo& self, uint32_t value) { self.SetSymbolId(value); })
        .def_prop_rw("digits",
            [](const haruquant::SymbolInfo& self) { return self.Digits(); },
            [](haruquant::SymbolInfo& self, int value) { self.SetDigits(value); })
        .def_prop_rw("spread",
            [](const haruquant::SymbolInfo& self) { return self.Spread(); },
            [](haruquant::SymbolInfo& self, int value) { self.SetSpread(value); })
        .def_prop_rw("spread_float",
            [](const haruquant::SymbolInfo& self) { return self.SpreadFloat(); },
            [](haruquant::SymbolInfo& self, bool value) { self.SetSpreadFloat(value); })
        .def_prop_rw("point",
            [](const haruquant::SymbolInfo& self) { return self.Point(); },
            [](haruquant::SymbolInfo& self, double value) { self.SetPoint(value); })
        .def_prop_rw("trade_calc_mode",
            [](const haruquant::SymbolInfo& self) { return static_cast<int>(self.TradeCalcMode()); },
            [](haruquant::SymbolInfo& self, int value) {
                self.SetTradeCalcMode(static_cast<haruquant::ENUM_SYMBOL_CALC_MODE>(value));
            })
        .def_prop_rw("trade_mode",
            [](const haruquant::SymbolInfo& self) { return static_cast<int>(self.TradeMode()); },
            [](haruquant::SymbolInfo& self, int value) {
                self.SetTradeMode(static_cast<haruquant::ENUM_SYMBOL_TRADE_MODE>(value));
            })
        .def_prop_rw("trade_stops_level",
            [](const haruquant::SymbolInfo& self) { return self.StopsLevel(); },
            [](haruquant::SymbolInfo& self, int value) { self.SetStopsLevel(value); })
        .def_prop_rw("trade_freeze_level",
            [](const haruquant::SymbolInfo& self) { return self.FreezeLevel(); },
            [](haruquant::SymbolInfo& self, int value) { self.SetFreezeLevel(value); })
        .def_prop_rw("trade_exemode",
            [](const haruquant::SymbolInfo& self) { return static_cast<int>(self.TradeExecution()); },
            [](haruquant::SymbolInfo& self, int value) {
                self.SetTradeExecution(static_cast<haruquant::ENUM_SYMBOL_TRADE_EXECUTION>(value));
            })
        .def_prop_rw("volume_min",
            [](const haruquant::SymbolInfo& self) { return self.LotsMin(); },
            [](haruquant::SymbolInfo& self, double value) { self.SetVolumeMin(value); })
        .def_prop_rw("volume_max",
            [](const haruquant::SymbolInfo& self) { return self.LotsMax(); },
            [](haruquant::SymbolInfo& self, double value) { self.SetVolumeMax(value); })
        .def_prop_rw("volume_step",
            [](const haruquant::SymbolInfo& self) { return self.LotsStep(); },
            [](haruquant::SymbolInfo& self, double value) { self.SetVolumeStep(value); })
        .def_prop_rw("volume_limit",
            [](const haruquant::SymbolInfo& self) { return self.LotsLimit(); },
            [](haruquant::SymbolInfo& self, double value) { self.SetVolumeLimit(value); })
        .def_prop_rw("trade_tick_value",
            [](const haruquant::SymbolInfo& self) { return self.TickValue(); },
            [](haruquant::SymbolInfo& self, double value) { self.SetTickValue(value); })
        .def_prop_rw("trade_tick_value_profit",
            [](const haruquant::SymbolInfo& self) { return self.TickValueProfit(); },
            [](haruquant::SymbolInfo& self, double value) { self.SetTickValueProfit(value); })
        .def_prop_rw("trade_tick_value_loss",
            [](const haruquant::SymbolInfo& self) { return self.TickValueLoss(); },
            [](haruquant::SymbolInfo& self, double value) { self.SetTickValueLoss(value); })
        .def_prop_rw("trade_tick_size",
            [](const haruquant::SymbolInfo& self) { return self.TickSize(); },
            [](haruquant::SymbolInfo& self, double value) { self.SetTickSize(value); })
        .def_prop_rw("trade_contract_size",
            [](const haruquant::SymbolInfo& self) { return self.ContractSize(); },
            [](haruquant::SymbolInfo& self, double value) { self.SetContractSize(value); })
        .def_prop_rw("margin_initial",
            [](const haruquant::SymbolInfo& self) { return self.MarginInitial(); },
            [](haruquant::SymbolInfo& self, double value) { self.SetMarginInitial(value); })
        .def_prop_rw("swap_mode",
            [](const haruquant::SymbolInfo& self) { return static_cast<int>(self.SwapMode()); },
            [](haruquant::SymbolInfo& self, int value) {
                self.SetSwapMode(static_cast<haruquant::ENUM_SYMBOL_SWAP_MODE>(value));
            })
        .def_prop_rw("swap_long",
            [](const haruquant::SymbolInfo& self) { return self.SwapLong(); },
            [](haruquant::SymbolInfo& self, double value) { self.SetSwapLong(value); })
        .def_prop_rw("swap_short",
            [](const haruquant::SymbolInfo& self) { return self.SwapShort(); },
            [](haruquant::SymbolInfo& self, double value) { self.SetSwapShort(value); })
        .def_prop_rw("swap_rollover3days",
            [](const haruquant::SymbolInfo& self) { return static_cast<int>(self.SwapRollover3days()); },
            [](haruquant::SymbolInfo& self, int value) {
                self.SetSwapRollover3days(static_cast<haruquant::ENUM_DAY_OF_WEEK>(value));
            })
        .def_prop_rw("select",
            [](const haruquant::SymbolInfo& self) { return self.Select(); },
            [](haruquant::SymbolInfo& self, bool value) { self.Select(value); })
        .def_prop_rw("visible",
            [](const haruquant::SymbolInfo& self) { return self.Select(); },
            [](haruquant::SymbolInfo& self, bool value) { self.Select(value); })
        .def_prop_rw("bid",
            [](const haruquant::SymbolInfo& self) { return self.Bid(); },
            [](haruquant::SymbolInfo& self, double value) { self.UpdatePrice(value, self.Ask(), self.Time()); })
        .def_prop_rw("ask",
            [](const haruquant::SymbolInfo& self) { return self.Ask(); },
            [](haruquant::SymbolInfo& self, double value) { self.UpdatePrice(self.Bid(), value, self.Time()); })
        .def_prop_ro("last", &haruquant::SymbolInfo::Last)
        .def("update_price", &haruquant::SymbolInfo::UpdatePrice,
             nb::arg("bid"), nb::arg("ask"), nb::arg("timestamp") = 0);

    nb::class_<haruquant::CTrade>(m, "CTrade")
        .def(nb::init<double, const std::string&, uint32_t>(),
             nb::arg("initial_balance") = 10000.0,
             nb::arg("currency") = "USD",
             nb::arg("leverage") = 100)
        .def("LogLevel", [](const haruquant::CTrade& self) { return self.LogLevel(); })
        .def("SetLogLevel", [](haruquant::CTrade& self, int level) { self.LogLevel(level); })
        .def("SetExpertMagicNumber", &haruquant::CTrade::SetExpertMagicNumber)
        .def("ExpertMagicNumber", &haruquant::CTrade::ExpertMagicNumber)
        .def("SetDeviationInPoints", &haruquant::CTrade::SetDeviationInPoints)
        .def("DeviationInPoints", &haruquant::CTrade::DeviationInPoints)
        .def("SetTypeFillingBySymbol", &haruquant::CTrade::SetTypeFillingBySymbol)
        .def("SetAsyncMode", &haruquant::CTrade::SetAsyncMode)
        .def("AsyncMode", &haruquant::CTrade::AsyncMode)
        .def("PositionOpen",
            [](haruquant::CTrade& self,
               const std::string& symbol,
               int order_type,
               double volume,
               double price,
               double sl,
               double tp,
               const std::string& comment) {
                return self.PositionOpen(
                    symbol,
                    static_cast<haruquant::ENUM_ORDER_TYPE>(order_type),
                    volume,
                    price,
                    sl,
                    tp,
                    comment
                );
            },
            nb::arg("symbol"),
            nb::arg("order_type"),
            nb::arg("volume"),
            nb::arg("price") = 0.0,
            nb::arg("sl") = 0.0,
            nb::arg("tp") = 0.0,
            nb::arg("comment") = "")
        .def("PositionModify",
            [](haruquant::CTrade& self, const std::string& symbol, double sl, double tp) {
                return self.PositionModify(symbol, sl, tp);
            },
            nb::arg("symbol"), nb::arg("sl"), nb::arg("tp"))
        .def("PositionClose",
            [](haruquant::CTrade& self, const std::string& symbol, uint64_t deviation) {
                return self.PositionClose(symbol, deviation);
            },
            nb::arg("symbol"), nb::arg("deviation") = 0)
        .def("OrderOpen",
            [](haruquant::CTrade& self,
               const std::string& symbol,
               int order_type,
               double volume,
               double limit_price,
               double stop_price,
               double sl,
               double tp,
               int type_time,
               int64_t expiration,
               const std::string& comment) {
                return self.OrderOpen(
                    symbol,
                    static_cast<haruquant::ENUM_ORDER_TYPE>(order_type),
                    volume,
                    limit_price,
                    stop_price,
                    sl,
                    tp,
                    static_cast<haruquant::ENUM_ORDER_TYPE_TIME>(type_time),
                    expiration,
                    comment
                );
            },
            nb::arg("symbol"),
            nb::arg("order_type"),
            nb::arg("volume"),
            nb::arg("limit_price"),
            nb::arg("stop_price") = 0.0,
            nb::arg("sl") = 0.0,
            nb::arg("tp") = 0.0,
            nb::arg("type_time") = 0,
            nb::arg("expiration") = 0,
            nb::arg("comment") = "")
        .def("RequestOrder", &haruquant::CTrade::RequestOrder)
        .def("RequestSymbol", &haruquant::CTrade::RequestSymbol)
        .def("RequestVolume", &haruquant::CTrade::RequestVolume)
        .def("RequestPrice", &haruquant::CTrade::RequestPrice)
        .def("ResultRetcode",
            [](const haruquant::CTrade& self) { return static_cast<int>(self.ResultRetcode()); })
        .def("ResultOrder", &haruquant::CTrade::ResultOrder)
        .def("ResultDeal", &haruquant::CTrade::ResultDeal)
        .def("ResultVolume", &haruquant::CTrade::ResultVolume)
        .def("ResultPrice", &haruquant::CTrade::ResultPrice)
        .def("ResultComment", &haruquant::CTrade::ResultComment)
        .def("CheckResultComment", &haruquant::CTrade::CheckResultComment)
        .def("RegisterSymbol", &haruquant::CTrade::RegisterSymbol)
        .def("UpdatePrices", &haruquant::CTrade::UpdatePrices,
             nb::arg("symbol"), nb::arg("bid"), nb::arg("ask"), nb::arg("timestamp") = 0)
        .def("positions_get",
            [](const haruquant::CTrade& self,
               std::optional<std::string> symbol,
               std::optional<std::string> group,
               std::optional<uint64_t> ticket) {
                return to_tuple(self.positions_get(symbol, group, ticket));
            },
             nb::arg("symbol") = nb::none(),
             nb::arg("group") = nb::none(),
             nb::arg("ticket") = nb::none())
        .def("positions_total", &haruquant::CTrade::positions_total)
        .def("orders_get",
            [](const haruquant::CTrade& self,
               std::optional<std::string> symbol,
               std::optional<std::string> group,
               std::optional<uint64_t> ticket) {
                return to_tuple(self.orders_get(symbol, group, ticket));
            },
             nb::arg("symbol") = nb::none(),
             nb::arg("group") = nb::none(),
             nb::arg("ticket") = nb::none())
        .def("orders_total", &haruquant::CTrade::orders_total)
        .def("history_orders_get",
            [](const haruquant::CTrade& self, std::optional<uint64_t> ticket) {
                return to_tuple(self.history_orders_get(ticket));
            },
             nb::arg("ticket") = nb::none())
        .def("history_orders_get",
            [](const haruquant::CTrade& self,
               nb::object date_from,
               nb::object date_to,
               std::optional<std::string> group,
               std::optional<uint64_t> ticket) {
                return to_tuple(
                    self.history_orders_get(to_unix_seconds(date_from), to_unix_seconds(date_to), group, ticket));
            },
             nb::arg("date_from"),
             nb::arg("date_to"),
             nb::arg("group") = nb::none(),
             nb::arg("ticket") = nb::none())
        .def("history_orders_total", &haruquant::CTrade::history_orders_total)
        .def("history_deals_get",
            [](const haruquant::CTrade& self, std::optional<uint64_t> ticket) {
                return to_tuple(self.history_deals_get(ticket));
            },
             nb::arg("ticket") = nb::none())
        .def("history_deals_get",
            [](const haruquant::CTrade& self,
               nb::object date_from,
               nb::object date_to,
               std::optional<std::string> group,
               std::optional<uint64_t> ticket) {
                return to_tuple(
                    self.history_deals_get(to_unix_seconds(date_from), to_unix_seconds(date_to), group, ticket));
            },
             nb::arg("date_from"),
             nb::arg("date_to"),
             nb::arg("group") = nb::none(),
             nb::arg("ticket") = nb::none())
        .def("history_deals_total", &haruquant::CTrade::history_deals_total)
        .def("symbol_select", &haruquant::CTrade::symbol_select,
             nb::arg("symbol"), nb::arg("select") = true)
        .def("symbols_get",
            [](const haruquant::CTrade& self, std::optional<std::string> group) {
                return to_tuple(self.symbols_get(group));
            },
            nb::arg("group") = nb::none())
        .def("symbols_total", &haruquant::CTrade::symbols_total)
        .def("Account", [](const haruquant::CTrade& self) { return self.Account(); });

    nb::class_<haruquant::DealInfo>(m, "DealInfo")
        .def(nb::init<>())
        .def("Ticket", &haruquant::DealInfo::Ticket)
        .def("Order", &haruquant::DealInfo::Order)
        .def("Time", &haruquant::DealInfo::Time)
        .def("TimeMsc", &haruquant::DealInfo::TimeMsc)
        .def("DealType", [](const haruquant::DealInfo& self) { return static_cast<int>(self.DealType()); })
        .def("DealTypeDescription", &haruquant::DealInfo::TypeDescription)
        .def("Entry", [](const haruquant::DealInfo& self) { return static_cast<int>(self.Entry()); })
        .def("EntryDescription", &haruquant::DealInfo::EntryDescription)
        .def("Magic", &haruquant::DealInfo::Magic)
        .def("PositionId", &haruquant::DealInfo::PositionId)
        .def("Volume", &haruquant::DealInfo::Volume)
        .def("Price", &haruquant::DealInfo::Price)
        .def("Commission", &haruquant::DealInfo::Commission)
        .def("Commision", &haruquant::DealInfo::Commision)
        .def("Swap", &haruquant::DealInfo::Swap)
        .def("Profit", &haruquant::DealInfo::Profit)
        .def("Symbol", &haruquant::DealInfo::Symbol)
        .def("Comment", &haruquant::DealInfo::Comment)
        .def("ExternalId", [](const haruquant::DealInfo&) { return std::string{}; })
        .def("Select", &haruquant::DealInfo::Select)
        .def("SelectByIndex", &haruquant::DealInfo::SelectByIndex)
        .def("NetProfit", &haruquant::DealInfo::NetProfit)
        .def("HoldingTime", &haruquant::DealInfo::HoldingTime)
        .def("HoldingTimeDays", &haruquant::DealInfo::HoldingTimeDays)
        .def("IsWinner", &haruquant::DealInfo::IsWinner)
        .def("IsLoser", &haruquant::DealInfo::IsLoser)
        .def("IsTrade", &haruquant::DealInfo::IsTrade)
        .def("IsBuy", &haruquant::DealInfo::IsBuy)
        .def("IsSell", &haruquant::DealInfo::IsSell)
        .def("IsEntry", &haruquant::DealInfo::IsEntry)
        .def("IsExit", &haruquant::DealInfo::IsExit)
        .def("PriceMovementPoints", &haruquant::DealInfo::PriceMovementPoints)
        .def("ROIPercent", &haruquant::DealInfo::ROIPercent)
        .def("EntryPrice", &haruquant::DealInfo::EntryPrice)
        .def("ExitPrice", &haruquant::DealInfo::ExitPrice)
        .def("EntryTime", &haruquant::DealInfo::EntryTime)
        .def("ExitTime", &haruquant::DealInfo::ExitTime)
        .def_prop_rw("ticket", &haruquant::DealInfo::Ticket, &haruquant::DealInfo::SetTicket)
        .def_prop_rw("order", &haruquant::DealInfo::Order, &haruquant::DealInfo::SetOrder)
        .def_prop_rw("position_id", &haruquant::DealInfo::PositionId, &haruquant::DealInfo::SetPositionId)
        .def_prop_rw("symbol", &haruquant::DealInfo::Symbol, &haruquant::DealInfo::SetSymbol)
        .def_prop_rw("magic",
            [](const haruquant::DealInfo& self) { return self.Magic(); },
            [](haruquant::DealInfo& self, uint32_t value) { self.SetMagic(value); })
        .def_prop_rw("type",
            [](const haruquant::DealInfo& self) { return static_cast<int>(self.DealType()); },
            [](haruquant::DealInfo& self, int value) { self.SetType(static_cast<haruquant::ENUM_DEAL_TYPE>(value)); })
        .def_prop_rw("entry",
            [](const haruquant::DealInfo& self) { return static_cast<int>(self.Entry()); },
            [](haruquant::DealInfo& self, int value) { self.SetEntry(static_cast<haruquant::ENUM_DEAL_ENTRY>(value)); })
        .def_prop_rw("volume", &haruquant::DealInfo::Volume, &haruquant::DealInfo::SetVolume)
        .def_prop_rw("price", &haruquant::DealInfo::Price, &haruquant::DealInfo::SetPrice)
        .def_prop_rw("profit", &haruquant::DealInfo::Profit, &haruquant::DealInfo::SetProfit)
        .def_prop_rw("commission", &haruquant::DealInfo::Commission, &haruquant::DealInfo::SetCommission)
        .def_prop_rw("swap", &haruquant::DealInfo::Swap, &haruquant::DealInfo::SetSwap)
        .def_prop_rw("comment", &haruquant::DealInfo::Comment, &haruquant::DealInfo::SetComment)
        .def("set_time", &haruquant::DealInfo::SetTime, nb::arg("time_sec"), nb::arg("time_msc") = 0)
        .def("set_digits", &haruquant::DealInfo::SetDigits)
        .def("set_entry_price", &haruquant::DealInfo::SetEntryPrice)
        .def("set_exit_price", &haruquant::DealInfo::SetExitPrice)
        .def("set_entry_time", &haruquant::DealInfo::SetEntryTime)
        .def("set_exit_time", &haruquant::DealInfo::SetExitTime);

    nb::class_<haruquant::HistoryOrderInfo>(m, "HistoryOrderInfo")
        .def(nb::init<>())
        .def("Ticket", &haruquant::HistoryOrderInfo::Ticket)
        .def("TimeSetup", &haruquant::HistoryOrderInfo::TimeSetup)
        .def("TimeSetupMsc", &haruquant::HistoryOrderInfo::TimeSetupMsc)
        .def("OrderType", [](const haruquant::HistoryOrderInfo& self) { return static_cast<int>(self.OrderType()); })
        .def("OrderTypeDescription", &haruquant::HistoryOrderInfo::OrderTypeDescription)
        .def("State", [](const haruquant::HistoryOrderInfo& self) { return static_cast<int>(self.State()); })
        .def("StateDescription", &haruquant::HistoryOrderInfo::StateDescription)
        .def("TimeExpiration", &haruquant::HistoryOrderInfo::TimeExpiration)
        .def("TimeDone", &haruquant::HistoryOrderInfo::TimeDone)
        .def("TimeDoneMsc", &haruquant::HistoryOrderInfo::TimeDoneMsc)
        .def("TypeFilling", [](const haruquant::HistoryOrderInfo& self) { return static_cast<int>(self.TypeFilling()); })
        .def("TypeFillingDescription", &haruquant::HistoryOrderInfo::TypeFillingDescription)
        .def("TypeTime", [](const haruquant::HistoryOrderInfo& self) { return static_cast<int>(self.TypeTime()); })
        .def("TypeTimeDescription", &haruquant::HistoryOrderInfo::TypeTimeDescription)
        .def("Magic", &haruquant::HistoryOrderInfo::Magic)
        .def("PositionId", &haruquant::HistoryOrderInfo::PositionId)
        .def("PositionByID", &haruquant::HistoryOrderInfo::PositionId)
        .def("VolumeInitial", &haruquant::HistoryOrderInfo::VolumeInitial)
        .def("VolumeCurrent", &haruquant::HistoryOrderInfo::VolumeCurrent)
        .def("PriceOpen", &haruquant::HistoryOrderInfo::PriceOpen)
        .def("StopLoss", &haruquant::HistoryOrderInfo::StopLoss)
        .def("TakeProfit", &haruquant::HistoryOrderInfo::TakeProfit)
        .def("PriceCurrent", &haruquant::HistoryOrderInfo::PriceCurrent)
        .def("PriceStopLimit", &haruquant::HistoryOrderInfo::PriceStopLimit)
        .def("Symbol", &haruquant::HistoryOrderInfo::Symbol)
        .def("Comment", &haruquant::HistoryOrderInfo::Comment)
        .def("ExternalID", [](const haruquant::HistoryOrderInfo&) { return std::string{}; })
        .def("Select", &haruquant::HistoryOrderInfo::Select)
        .def("SelectByIndex", &haruquant::HistoryOrderInfo::SelectByIndex)
        .def("Lifetime", &haruquant::HistoryOrderInfo::Lifetime)
        .def("WasFilled", &haruquant::HistoryOrderInfo::WasFilled)
        .def("WasCanceled", &haruquant::HistoryOrderInfo::WasCanceled)
        .def("WasRejected", &haruquant::HistoryOrderInfo::WasRejected)
        .def("WasExpired", &haruquant::HistoryOrderInfo::WasExpired)
        .def("WasPartiallyFilled", &haruquant::HistoryOrderInfo::WasPartiallyFilled)
        .def("VolumeFilled", &haruquant::HistoryOrderInfo::VolumeFilled)
        .def("FillRatio", &haruquant::HistoryOrderInfo::FillRatio)
        .def("IsBuy", &haruquant::HistoryOrderInfo::IsBuy)
        .def("IsSell", &haruquant::HistoryOrderInfo::IsSell)
        .def("IsMarket", &haruquant::HistoryOrderInfo::IsMarket)
        .def("IsLimit", &haruquant::HistoryOrderInfo::IsLimit)
        .def("IsStop", &haruquant::HistoryOrderInfo::IsStop)
        .def_prop_rw("ticket", &haruquant::HistoryOrderInfo::Ticket, &haruquant::HistoryOrderInfo::SetTicket)
        .def_prop_rw("symbol", &haruquant::HistoryOrderInfo::Symbol, &haruquant::HistoryOrderInfo::SetSymbol)
        .def_prop_rw("magic",
            [](const haruquant::HistoryOrderInfo& self) { return self.Magic(); },
            [](haruquant::HistoryOrderInfo& self, uint32_t value) { self.SetMagic(value); })
        .def_prop_rw("position_id", &haruquant::HistoryOrderInfo::PositionId, &haruquant::HistoryOrderInfo::SetPositionId)
        .def_prop_rw("type",
            [](const haruquant::HistoryOrderInfo& self) { return static_cast<int>(self.OrderType()); },
            [](haruquant::HistoryOrderInfo& self, int value) { self.SetOrderType(static_cast<haruquant::ENUM_ORDER_TYPE>(value)); })
        .def_prop_rw("state",
            [](const haruquant::HistoryOrderInfo& self) { return static_cast<int>(self.State()); },
            [](haruquant::HistoryOrderInfo& self, int value) { self.SetState(static_cast<haruquant::ENUM_ORDER_STATE>(value)); })
        .def_prop_rw("volume_initial", &haruquant::HistoryOrderInfo::VolumeInitial, &haruquant::HistoryOrderInfo::SetVolumeInitial)
        .def_prop_rw("volume_current", &haruquant::HistoryOrderInfo::VolumeCurrent, &haruquant::HistoryOrderInfo::SetVolumeCurrent)
        .def_prop_rw("price_open", &haruquant::HistoryOrderInfo::PriceOpen, &haruquant::HistoryOrderInfo::SetPriceOpen)
        .def_prop_rw("price_current", &haruquant::HistoryOrderInfo::PriceCurrent, &haruquant::HistoryOrderInfo::SetPriceCurrent)
        .def_prop_rw("price_stoplimit", &haruquant::HistoryOrderInfo::PriceStopLimit, &haruquant::HistoryOrderInfo::SetPriceStopLimit)
        .def_prop_rw("sl", &haruquant::HistoryOrderInfo::StopLoss, &haruquant::HistoryOrderInfo::SetStopLoss)
        .def_prop_rw("tp", &haruquant::HistoryOrderInfo::TakeProfit, &haruquant::HistoryOrderInfo::SetTakeProfit)
        .def_prop_rw("comment", &haruquant::HistoryOrderInfo::Comment, &haruquant::HistoryOrderInfo::SetComment)
        .def("set_time_setup", &haruquant::HistoryOrderInfo::SetTimeSetup, nb::arg("time_sec"), nb::arg("time_msc") = 0)
        .def("set_time_expiration", &haruquant::HistoryOrderInfo::SetTimeExpiration)
        .def("set_time_done", &haruquant::HistoryOrderInfo::SetTimeDone, nb::arg("time_sec"), nb::arg("time_msc") = 0)
        .def("set_type_filling",
            [](haruquant::HistoryOrderInfo& self, int value) {
                self.SetTypeFilling(static_cast<haruquant::ENUM_ORDER_TYPE_FILLING>(value));
            })
        .def("set_type_time",
            [](haruquant::HistoryOrderInfo& self, int value) {
                self.SetTypeTime(static_cast<haruquant::ENUM_ORDER_TYPE_TIME>(value));
            })
        .def("set_digits", &haruquant::HistoryOrderInfo::SetDigits);

    nb::class_<haruquant::OrderInfo>(m, "OrderInfo")
        .def(nb::init<>())
        .def("Ticket", &haruquant::OrderInfo::Ticket)
        .def("TimeSetup", &haruquant::OrderInfo::TimeSetup)
        .def("TimeSetupMsc", &haruquant::OrderInfo::TimeSetupMsc)
        .def("Type", [](const haruquant::OrderInfo& self) { return static_cast<int>(self.OrderType()); })
        .def("TypeDescription", &haruquant::OrderInfo::OrderTypeDescription)
        .def("OrderType", [](const haruquant::OrderInfo& self) { return static_cast<int>(self.OrderType()); })
        .def("OrderTypeDescription", &haruquant::OrderInfo::OrderTypeDescription)
        .def("State", [](const haruquant::OrderInfo& self) { return static_cast<int>(self.State()); })
        .def("StateDescription", &haruquant::OrderInfo::StateDescription)
        .def("TimeExpiration", &haruquant::OrderInfo::TimeExpiration)
        .def("TimeDone", &haruquant::OrderInfo::TimeDone)
        .def("TimeDoneMsc", &haruquant::OrderInfo::TimeDoneMsc)
        .def("TypeFilling", [](const haruquant::OrderInfo& self) { return static_cast<int>(self.TypeFilling()); })
        .def("TypeFillingDescription", &haruquant::OrderInfo::TypeFillingDescription)
        .def("TypeTime", [](const haruquant::OrderInfo& self) { return static_cast<int>(self.TypeTime()); })
        .def("TypeTimeDescription", &haruquant::OrderInfo::TypeTimeDescription)
        .def("Magic", &haruquant::OrderInfo::Magic)
        .def("PositionId", &haruquant::OrderInfo::PositionId)
        .def("PositionById", &haruquant::OrderInfo::PositionId)
        .def("PositionByID", &haruquant::OrderInfo::PositionId)
        .def("VolumeInitial", &haruquant::OrderInfo::VolumeInitial)
        .def("VolumeCurrent", &haruquant::OrderInfo::VolumeCurrent)
        .def("PriceOpen", &haruquant::OrderInfo::PriceOpen)
        .def("StopLoss", &haruquant::OrderInfo::StopLoss)
        .def("TakeProfit", &haruquant::OrderInfo::TakeProfit)
        .def("PriceCurrent", &haruquant::OrderInfo::PriceCurrent)
        .def("PriceStopLimit", &haruquant::OrderInfo::PriceStopLimit)
        .def("Symbol", &haruquant::OrderInfo::Symbol)
        .def("Comment", &haruquant::OrderInfo::Comment)
        .def("ExternalId", [](const haruquant::OrderInfo&) { return std::string{}; })
        .def("ExternalID", [](const haruquant::OrderInfo&) { return std::string{}; })
        .def("StoreState", &haruquant::OrderInfo::StoreState)
        .def("CheckState", &haruquant::OrderInfo::CheckState)
        .def("Select", &haruquant::OrderInfo::Select)
        .def("SelectByIndex", &haruquant::OrderInfo::SelectByIndex)
        .def("IsBuy", &haruquant::OrderInfo::IsBuy)
        .def("IsSell", &haruquant::OrderInfo::IsSell)
        .def_prop_rw("ticket", &haruquant::OrderInfo::Ticket, &haruquant::OrderInfo::SetTicket)
        .def_prop_rw("symbol", &haruquant::OrderInfo::Symbol, &haruquant::OrderInfo::SetSymbol)
        .def_prop_rw("magic",
            [](const haruquant::OrderInfo& self) { return self.Magic(); },
            [](haruquant::OrderInfo& self, uint32_t value) { self.SetMagic(value); })
        .def_prop_rw("position_id", &haruquant::OrderInfo::PositionId, &haruquant::OrderInfo::SetPositionId)
        .def_prop_rw("type",
            [](const haruquant::OrderInfo& self) { return static_cast<int>(self.OrderType()); },
            [](haruquant::OrderInfo& self, int value) { self.SetOrderType(static_cast<haruquant::ENUM_ORDER_TYPE>(value)); })
        .def_prop_rw("state",
            [](const haruquant::OrderInfo& self) { return static_cast<int>(self.State()); },
            [](haruquant::OrderInfo& self, int value) { self.SetState(static_cast<haruquant::ENUM_ORDER_STATE>(value)); })
        .def_prop_rw("volume_initial", &haruquant::OrderInfo::VolumeInitial, &haruquant::OrderInfo::SetVolumeInitial)
        .def_prop_rw("volume_current", &haruquant::OrderInfo::VolumeCurrent, &haruquant::OrderInfo::SetVolumeCurrent)
        .def_prop_rw("price_open", &haruquant::OrderInfo::PriceOpen, &haruquant::OrderInfo::SetPriceOpen)
        .def_prop_rw("price_current", &haruquant::OrderInfo::PriceCurrent, &haruquant::OrderInfo::SetPriceCurrent)
        .def_prop_rw("price_stoplimit", &haruquant::OrderInfo::PriceStopLimit, &haruquant::OrderInfo::SetPriceStopLimit)
        .def_prop_rw("sl", &haruquant::OrderInfo::StopLoss, &haruquant::OrderInfo::SetStopLoss)
        .def_prop_rw("tp", &haruquant::OrderInfo::TakeProfit, &haruquant::OrderInfo::SetTakeProfit)
        .def_prop_rw("comment", &haruquant::OrderInfo::Comment, &haruquant::OrderInfo::SetComment)
        .def("set_time_setup", &haruquant::OrderInfo::SetTimeSetup, nb::arg("time_sec"), nb::arg("time_msc") = 0)
        .def("set_time_expiration", &haruquant::OrderInfo::SetTimeExpiration)
        .def("set_time_done", &haruquant::OrderInfo::SetTimeDone, nb::arg("time_sec"), nb::arg("time_msc") = 0)
        .def("set_type_filling",
            [](haruquant::OrderInfo& self, int value) {
                self.SetTypeFilling(static_cast<haruquant::ENUM_ORDER_TYPE_FILLING>(value));
            })
        .def("set_type_time",
            [](haruquant::OrderInfo& self, int value) {
                self.SetTypeTime(static_cast<haruquant::ENUM_ORDER_TYPE_TIME>(value));
            })
        .def("set_digits", &haruquant::OrderInfo::SetDigits);

    nb::class_<haruquant::PositionInfo>(m, "PositionInfo")
        .def(nb::init<>())
        .def("Time", &haruquant::PositionInfo::Time)
        .def("TimeMsc", &haruquant::PositionInfo::TimeMsc)
        .def("TimeUpdate", &haruquant::PositionInfo::TimeUpdate)
        .def("TimeUpdateMsc", &haruquant::PositionInfo::TimeUpdateMsc)
        .def("Type", [](const haruquant::PositionInfo& self) { return static_cast<int>(self.PositionType()); })
        .def("PositionType", [](const haruquant::PositionInfo& self) { return static_cast<int>(self.PositionType()); })
        .def("TypeDescription", &haruquant::PositionInfo::TypeDescription)
        .def("Magic", &haruquant::PositionInfo::Magic)
        .def("Identifier", &haruquant::PositionInfo::Identifier)
        .def("Ticket", &haruquant::PositionInfo::Ticket)
        .def("Volume", &haruquant::PositionInfo::Volume)
        .def("PriceOpen", &haruquant::PositionInfo::PriceOpen)
        .def("StopLoss", &haruquant::PositionInfo::StopLoss)
        .def("TakeProfit", &haruquant::PositionInfo::TakeProfit)
        .def("PriceCurrent", &haruquant::PositionInfo::PriceCurrent)
        .def("Commission", &haruquant::PositionInfo::Commission)
        .def("Swap", &haruquant::PositionInfo::Swap)
        .def("Profit", &haruquant::PositionInfo::Profit)
        .def("Symbol", &haruquant::PositionInfo::Symbol)
        .def("Comment", &haruquant::PositionInfo::Comment)
        .def("ExternalId", [](const haruquant::PositionInfo&) { return std::string{}; })
        .def("ExternalID", [](const haruquant::PositionInfo&) { return std::string{}; })
        .def("StoreState", &haruquant::PositionInfo::StoreState)
        .def("CheckState", &haruquant::PositionInfo::CheckState)
        .def("Select", nb::overload_cast<uint64_t>(&haruquant::PositionInfo::Select))
        .def("Select", nb::overload_cast<const std::string&>(&haruquant::PositionInfo::Select))
        .def("SelectByIndex", &haruquant::PositionInfo::SelectByIndex)
        .def("SelectByMagic", &haruquant::PositionInfo::SelectByMagic)
        .def("SelectByTicket", &haruquant::PositionInfo::SelectByTicket)
        .def("NetProfit", &haruquant::PositionInfo::NetProfit)
        .def("DistanceInPoints", &haruquant::PositionInfo::DistanceInPoints)
        .def("IsBuy", &haruquant::PositionInfo::IsBuy)
        .def("IsSell", &haruquant::PositionInfo::IsSell)
        .def_prop_rw("ticket", &haruquant::PositionInfo::Ticket, &haruquant::PositionInfo::SetTicket)
        .def_prop_rw("identifier", &haruquant::PositionInfo::Identifier, &haruquant::PositionInfo::SetIdentifier)
        .def_prop_rw("symbol", &haruquant::PositionInfo::Symbol, &haruquant::PositionInfo::SetSymbol)
        .def_prop_rw("magic",
            [](const haruquant::PositionInfo& self) { return self.Magic(); },
            [](haruquant::PositionInfo& self, uint32_t value) { self.SetMagic(value); })
        .def_prop_rw("type",
            [](const haruquant::PositionInfo& self) { return position_type_name(self.PositionType()); },
            [](haruquant::PositionInfo& self, const nb::object& value) { self.SetType(resolve_position_type(value)); })
        .def_prop_rw("volume", &haruquant::PositionInfo::Volume, &haruquant::PositionInfo::SetVolume)
        .def_prop_rw("price_open", &haruquant::PositionInfo::PriceOpen, &haruquant::PositionInfo::SetPriceOpen)
        .def_prop_rw("price_current", &haruquant::PositionInfo::PriceCurrent, &haruquant::PositionInfo::SetPriceCurrent)
        .def_prop_rw("sl", &haruquant::PositionInfo::StopLoss, &haruquant::PositionInfo::SetStopLoss)
        .def_prop_rw("tp", &haruquant::PositionInfo::TakeProfit, &haruquant::PositionInfo::SetTakeProfit)
        .def_prop_rw("commission", &haruquant::PositionInfo::Commission, &haruquant::PositionInfo::SetCommission)
        .def_prop_rw("swap", &haruquant::PositionInfo::Swap, &haruquant::PositionInfo::SetSwap)
        .def_prop_rw("profit",
            &haruquant::PositionInfo::Profit,
            [](haruquant::PositionInfo& self, double value) {
                self.SetProfitFP(static_cast<int64_t>(std::llround(value * 1'000'000.0)));
            })
        .def_prop_rw("comment", &haruquant::PositionInfo::Comment, &haruquant::PositionInfo::SetComment)
        .def("set_time", &haruquant::PositionInfo::SetTime, nb::arg("time_sec"), nb::arg("time_msc") = 0)
        .def("set_time_update", &haruquant::PositionInfo::SetTimeUpdate, nb::arg("time_sec"), nb::arg("time_msc") = 0)
        .def("set_digits", &haruquant::PositionInfo::SetDigits)
        .def("set_point", &haruquant::PositionInfo::SetPoint)
        .def("set_contract_size", &haruquant::PositionInfo::SetContractSize)
        .def("update_price", &haruquant::PositionInfo::UpdatePrice);

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

    nb::class_<TradeCheckResult>(m, "TradeCheckResult")
        .def(nb::init<>())
        .def_rw("retcode", &TradeCheckResult::retcode)
        .def_rw("balance", &TradeCheckResult::balance)
        .def_rw("equity", &TradeCheckResult::equity)
        .def_rw("profit", &TradeCheckResult::profit)
        .def_rw("margin", &TradeCheckResult::margin)
        .def_rw("margin_free", &TradeCheckResult::margin_free)
        .def_rw("margin_level", &TradeCheckResult::margin_level)
        .def_rw("comment", &TradeCheckResult::comment);

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
            [](BrokerSnapshot& self, const haruquant::AccountInfo& account) {
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
        .def(nb::init<haruquant::AccountInfo>())
        .def("account_info", [](const TradeSimulator& self) {
            return to_mt5_account(self.account_info());
        })
        .def("symbol_info", [](const TradeSimulator& self, const std::string& symbol)
                -> std::optional<haruquant::SymbolInfo> {
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
        .def("positions_get",
            [](const TradeSimulator& self,
               std::optional<std::string> symbol,
               std::optional<std::string> group,
               std::optional<uint64_t> ticket) {
                return to_tuple(self.positions_get(symbol, group, ticket));
            },
             nb::arg("symbol") = nb::none(),
             nb::arg("group") = nb::none(),
             nb::arg("ticket") = nb::none())
        .def("positions_total", &TradeSimulator::positions_total)
        .def("orders_get",
            [](const TradeSimulator& self,
               std::optional<std::string> symbol,
               std::optional<std::string> group,
               std::optional<uint64_t> ticket) {
                return to_tuple(self.orders_get(symbol, group, ticket));
            },
             nb::arg("symbol") = nb::none(),
             nb::arg("group") = nb::none(),
             nb::arg("ticket") = nb::none())
        .def("orders_total", &TradeSimulator::orders_total)
        .def("history_orders_get",
             [](const TradeSimulator& self, std::optional<uint64_t> ticket) {
                return to_tuple(self.history_orders_get(ticket));
             },
             nb::arg("ticket") = nb::none())
        .def("history_orders_get",
             [](const TradeSimulator& self,
                nb::object date_from,
                nb::object date_to,
                std::optional<std::string> group,
                std::optional<uint64_t> ticket) {
                return to_tuple(
                    self.history_orders_get(to_unix_seconds(date_from), to_unix_seconds(date_to), group, ticket));
             },
             nb::arg("date_from"),
             nb::arg("date_to"),
             nb::arg("group") = nb::none(),
             nb::arg("ticket") = nb::none())
        .def("history_orders_total", &TradeSimulator::history_orders_total)
        .def("history_deals_get",
             [](const TradeSimulator& self, std::optional<uint64_t> ticket) {
                return to_tuple(self.history_deals_get(ticket));
             },
             nb::arg("ticket") = nb::none())
        .def("history_deals_get",
             [](const TradeSimulator& self,
                nb::object date_from,
                nb::object date_to,
                std::optional<std::string> group,
                std::optional<uint64_t> ticket) {
                return to_tuple(
                    self.history_deals_get(to_unix_seconds(date_from), to_unix_seconds(date_to), group, ticket));
             },
             nb::arg("date_from"),
             nb::arg("date_to"),
             nb::arg("group") = nb::none(),
             nb::arg("ticket") = nb::none())
        .def("history_deals_total", &TradeSimulator::history_deals_total)
        .def("symbol_select", &TradeSimulator::symbol_select,
             nb::arg("symbol"),
             nb::arg("enable") = true)
        .def("symbols_get",
            [](const TradeSimulator& self, std::optional<std::string> group) {
                return to_tuple(self.symbols_get(group));
            },
             nb::arg("group") = nb::none())
        .def("symbols_total", &TradeSimulator::symbols_total)
        .def("last_error", &TradeSimulator::last_error)
        .def("trade_retcode_description", &TradeSimulator::trade_retcode_description)
        .def("order_check", &TradeSimulator::order_check)
        .def("order_calc_margin", &TradeSimulator::order_calc_margin)
        .def("order_calc_profit", &TradeSimulator::order_calc_profit)
        .def("PositionOpen",
             [](TradeSimulator& self,
                const std::string& symbol,
                const nb::object& order_type,
                double volume,
                double price,
                double sl,
                double tp,
                const std::string& comment) {
                 return self.PositionOpen(
                     symbol, resolve_order_type(order_type), volume, price, sl, tp, comment);
             },
             nb::arg("symbol"),
             nb::arg("order_type"),
             nb::arg("volume"),
             nb::arg("price") = 0.0,
             nb::arg("sl") = 0.0,
             nb::arg("tp") = 0.0,
             nb::arg("comment") = "")
        .def("PositionModify", &TradeSimulator::PositionModify,
             nb::arg("symbol") = nb::none(),
             nb::arg("ticket") = nb::none(),
             nb::arg("sl") = 0.0,
             nb::arg("tp") = 0.0)
        .def("PositionClose", &TradeSimulator::PositionClose,
             nb::arg("symbol") = nb::none(),
             nb::arg("ticket") = nb::none(),
             nb::arg("deviation") = 0)
        .def("OrderOpen",
             [](TradeSimulator& self,
                const std::string& symbol,
                const nb::object& order_type,
                double volume,
                double price,
                double stoplimit,
                double sl,
                double tp,
                nb::object type_time,
                int64_t expiration,
                const std::string& comment) {
                 return self.OrderOpen(
                     symbol,
                     resolve_order_type(order_type),
                     volume,
                     price,
                     stoplimit,
                     sl,
                     tp,
                     resolve_order_time(type_time),
                     expiration,
                     comment);
             },
             nb::arg("symbol"),
             nb::arg("order_type"),
             nb::arg("volume"),
             nb::arg("price"),
             nb::arg("stoplimit") = 0.0,
             nb::arg("sl") = 0.0,
             nb::arg("tp") = 0.0,
             nb::arg("type_time") = nb::none(),
             nb::arg("expiration") = 0,
             nb::arg("comment") = "")
        .def("OrderModify", &TradeSimulator::OrderModify,
             nb::arg("ticket"),
             nb::arg("price"),
             nb::arg("sl") = 0.0,
             nb::arg("tp") = 0.0,
             nb::arg("stoplimit") = 0.0,
             nb::arg("expiration") = 0,
             nb::arg("comment") = "")
        .def("OrderDelete", &TradeSimulator::OrderDelete,
             nb::arg("ticket"),
             nb::arg("comment") = "")
        .def("order_send", &TradeSimulator::order_send)
        .def("close_position", &TradeSimulator::close_position)
        .def("order_state", &TradeSimulator::order_state)
        .def("order_state_name", &TradeSimulator::order_state_name)
        .def("idempotency_cache_size", &TradeSimulator::idempotency_cache_size)
        .def("set_history_order_state", &TradeSimulator::set_history_order_state)
        .def("set_history_order_done_time", &TradeSimulator::set_history_order_done_time)
        .def("set_account_info", [](TradeSimulator& self, const haruquant::AccountInfo& data) {
            self.set_account_info(data);
        })
        .def("set_symbol_info", [](TradeSimulator& self, const haruquant::SymbolInfo& data) {
            self.set_symbol_info(data);
        })
        .def("set_symbol_info", [](TradeSimulator& self, nb::object source) {
            self.set_symbol_info(symbol_from_object(source));
        }, nb::arg("source"))
        .def("set_symbol_tick", &TradeSimulator::set_symbol_tick)
        .def("upsert_position_info", &TradeSimulator::upsert_position_info)
        .def("upsert_order_info", &TradeSimulator::upsert_order_info)
        .def("upsert_history_order_info", &TradeSimulator::upsert_history_order_info)
        .def("upsert_deal_info", &TradeSimulator::upsert_deal_info)
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
                                   const haruquant::AccountInfo& base,
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
             [](PositionBook& self, const haruquant::AccountInfo& account) {
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
                const haruquant::AccountInfo& broker_account,
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
                const haruquant::AccountInfo& broker_account) {
                 return self.periodic_reconcile(
                     broker_positions,
                     broker_account);
             },
             nb::arg("broker_positions"),
             nb::arg("broker_account"))
        .def("reconnect_reconcile",
             [](const PositionBook& self,
                const std::unordered_map<std::string, PositionAggregate>& broker_positions,
                const haruquant::AccountInfo& broker_account) {
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


