#include "core/backtest_simulator.hpp"
#include "util/currency_converter.hpp"
#include "util/logger.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <ctime>
#include <limits>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>

namespace haruquant::core {

namespace {

double read_double(const BacktestState::Dictionary& row, const std::string& key, double fallback = 0.0) {
    const auto it = row.find(key);
    if (it == row.end()) {
        return fallback;
    }
    try {
        return std::stod(it->second);
    } catch (...) {
        return fallback;
    }
}

std::string read_string(const BacktestState::Dictionary& row, const std::string& key) {
    const auto it = row.find(key);
    if (it == row.end()) {
        return {};
    }
    return it->second;
}

std::string normalize_token(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::toupper(c));
    });
    return value;
}

std::string trim_copy(const std::string& value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) {
        return {};
    }
    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

std::string to_upper_copy(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::toupper(c));
    });
    return value;
}

long parse_long_default(const std::string& text, long fallback = 0) {
    if (text.empty()) {
        return fallback;
    }
    try {
        return static_cast<long>(std::stoll(text));
    } catch (...) {
        return fallback;
    }
}

bool wildcard_match_case_insensitive(const std::string& value, const std::string& pattern) {
    std::string rx;
    rx.reserve(pattern.size() * 2);
    for (char ch : pattern) {
        switch (ch) {
            case '*':
                rx += ".*";
                break;
            case '?':
                rx += '.';
                break;
            case '.': case '^': case '$': case '+': case '(': case ')':
            case '[': case ']': case '{': case '}': case '|': case '\\':
                rx.push_back('\\');
                rx.push_back(ch);
                break;
            default:
                rx.push_back(ch);
                break;
        }
    }
    const std::regex re("^" + rx + "$", std::regex::icase);
    return std::regex_match(value, re);
}

bool group_match(const std::string& symbol, const std::string& group) {
    const std::string trimmed = trim_copy(group);
    if (trimmed.empty()) {
        return true;
    }

    bool included = false;
    bool has_include_rule = false;
    std::stringstream ss(trimmed);
    std::string token;
    while (std::getline(ss, token, ',')) {
        std::string rule = trim_copy(token);
        if (rule.empty()) {
            continue;
        }
        const bool exclude = !rule.empty() && rule.front() == '!';
        if (exclude) {
            rule.erase(rule.begin());
            rule = trim_copy(rule);
            if (rule.empty()) {
                continue;
            }
            if (wildcard_match_case_insensitive(symbol, rule)) {
                return false;
            }
            continue;
        }

        has_include_rule = true;
        if (wildcard_match_case_insensitive(symbol, rule)) {
            included = true;
        }
    }

    return has_include_rule ? included : true;
}

std::string to_string_num(long value) {
    return std::to_string(value);
}

std::string to_string_num(double value) {
    std::ostringstream oss;
    oss << value;
    return oss.str();
}

long next_ticket(const BacktestState::DictionaryMap& rows) {
    long max_ticket = 0;
    for (const auto& [key, row] : rows) {
        const long ticket = parse_long_default(read_string(row, "ticket"), parse_long_default(key, 0));
        max_ticket = std::max(max_ticket, ticket);
    }
    return max_ticket + 1;
}

std::string find_symbol_key(const BacktestState::DictionaryMap& symbols, const std::string& symbol) {
    if (symbols.find(symbol) != symbols.end()) {
        return symbol;
    }
    const std::string target = to_upper_copy(symbol);
    for (const auto& [key, _] : symbols) {
        if (to_upper_copy(key) == target) {
            return key;
        }
    }
    return {};
}

haruquant::CurrencyConverter build_currency_converter(const BacktestState& state) {
    haruquant::CurrencyConverter converter;
    for (const auto& [_, row] : state.trading_symbols) {
        const std::string base = read_string(row, "currency_base");
        const std::string quote = read_string(row, "currency_profit");
        if (base.empty() || quote.empty()) {
            continue;
        }

        const double bid = read_double(row, "bid", 0.0);
        const double ask = read_double(row, "ask", 0.0);
        const double last = read_double(row, "last", 0.0);

        if (bid > 0.0 && ask > 0.0) {
            // Use side-aware rates:
            // base->quote uses bid, quote->base uses 1/ask.
            converter.register_pair(base, quote, bid);
            converter.register_pair(quote, base, 1.0 / ask);
            continue;
        }

        if (last > 0.0) {
            converter.register_pair(base, quote, last);
            converter.register_pair(quote, base, 1.0 / last);
            continue;
        }

        if (bid > 0.0) {
            converter.register_pair(base, quote, bid);
            converter.register_pair(quote, base, 1.0 / bid);
            continue;
        }

        if (ask > 0.0) {
            converter.register_pair(base, quote, ask);
            converter.register_pair(quote, base, 1.0 / ask);
        }
    }
    return converter;
}

}  // namespace

BacktestSimulator::BacktestSimulator() {
    haruquant::util::info("Backtest Simulator successfully initialised");
}

BacktestSimulator::BacktestSimulator(const haruquant::trading::AccountInfo& account) : account_(account) {
    haruquant::util::info("Backtest Simulator successfully initialised with account");
}

void BacktestSimulator::set_last_error(int code, std::string message) {
    last_error_code_ = code;
    last_error_message_ = std::move(message);
}

std::pair<int, std::string> BacktestSimulator::last_error() const {
    return {last_error_code_, last_error_message_};
}

TradeResult BacktestSimulator::order_send(const TradeRequest& request) {
    TradeResult result;
    result.request = request;
    result.volume = request.volume;

    const auto* state_ro = account_.GetState();
    if (!state_ro) {
        result.retcode = 10013;
        result.comment = "BacktestSimulator has no shared BacktestState";
        set_last_error(-1, result.comment);
        return result;
    }
    auto* state = account_.GetSharedState().get();
    if (!state) {
        result.retcode = 10013;
        result.comment = "BacktestSimulator has no mutable BacktestState";
        set_last_error(-1, result.comment);
        return result;
    }

    const long action = (request.action == 0) ? 1 : request.action;  // TRADE_ACTION_DEAL
    const bool is_market_deal = (action == 1);
    const bool is_pending = (action == 5);  // TRADE_ACTION_PENDING
    if (!is_market_deal && !is_pending) {
        result.retcode = 10013;
        result.comment = "Unsupported trade action in tester order_send()";
        set_last_error(-2, result.comment);
        return result;
    }

    const std::string symbol_key = find_symbol_key(state->trading_symbols, request.symbol);
    if (symbol_key.empty()) {
        result.retcode = 10013;
        result.comment = "Unknown symbol";
        set_last_error(-2, result.comment);
        return result;
    }

    if (request.volume <= 0.0) {
        result.retcode = 10014;
        result.comment = "Volume must be > 0";
        set_last_error(-2, result.comment);
        return result;
    }

    const auto& sym_row = state->trading_symbols[symbol_key];
    const double bid = read_double(sym_row, "bid", 0.0);
    const double ask = read_double(sym_row, "ask", 0.0);
    const double last = read_double(sym_row, "last", 0.0);
    result.bid = bid;
    result.ask = ask;

    const long order_type = request.type;
    const bool is_buy = (order_type == 0);
    const bool is_sell = (order_type == 1);

    if (is_pending) {
        const bool is_buy_limit = (order_type == 2);
        const bool is_sell_limit = (order_type == 3);
        const bool is_buy_stop = (order_type == 4);
        const bool is_sell_stop = (order_type == 5);
        if (!is_buy_limit && !is_sell_limit && !is_buy_stop && !is_sell_stop) {
            result.retcode = 10013;
            result.comment = "Only BUY_LIMIT/SELL_LIMIT/BUY_STOP/SELL_STOP are supported";
            set_last_error(-2, result.comment);
            return result;
        }

        double pending_price = request.price;
        if (pending_price <= 0.0) {
            pending_price = request.stoplimit;
        }
        if (pending_price <= 0.0) {
            result.retcode = 10015;
            result.comment = "Pending price is invalid";
            set_last_error(-2, result.comment);
            return result;
        }

        const long now = static_cast<long>(std::time(nullptr));
        const long now_msc = now * 1000;
        const long order_ticket = next_ticket(state->trading_orders);

        const bool pending_buy_side = is_buy_limit || is_buy_stop;
        double margin_required = 0.0;
        try {
            margin_required = order_calc_margin(
                pending_buy_side ? "BUY" : "SELL",
                symbol_key,
                request.volume,
                pending_price);
        } catch (...) {
            margin_required = 0.0;
        }

        auto& order_row = state->trading_orders[to_string_num(order_ticket)];
        order_row["action"] = "order_open";
        order_row["ticket"] = to_string_num(order_ticket);
        order_row["time_setup"] = to_string_num(now);
        order_row["time_setup_msc"] = to_string_num(now_msc);
        order_row["time_done"] = "0";
        order_row["time_done_msc"] = "0";
        order_row["time_expiration"] = to_string_num(request.expiration);
        order_row["type"] = to_string_num(order_type);
        order_row["type_time"] = to_string_num(request.type_time);
        order_row["type_filling"] = to_string_num(request.type_filling);
        order_row["state"] = "1";  // ORDER_STATE_PLACED
        order_row["magic"] = to_string_num(request.magic);
        order_row["reason"] = "0";
        order_row["position_id"] = "0";
        order_row["position_by_id"] = "0";
        order_row["volume_initial"] = to_string_num(request.volume);
        order_row["volume_current"] = to_string_num(request.volume);
        order_row["price_open"] = to_string_num(pending_price);
        order_row["sl"] = to_string_num(request.sl);
        order_row["tp"] = to_string_num(request.tp);
        order_row["price_current"] = to_string_num(pending_price);
        order_row["price_stoplimit"] = to_string_num(request.stoplimit);
        order_row["symbol"] = symbol_key;
        order_row["comment"] = request.comment;
        order_row["external_id"] = "";
        order_row["margin_required"] = to_string_num(margin_required);

        result.retcode = 10008;
        result.deal = 0;
        result.order = order_ticket;
        result.price = pending_price;
        result.comment = "Order placed";
        set_last_error(0, "No error");
        return result;
    }

    if (!is_buy && !is_sell) {
        result.retcode = 10013;
        result.comment = "Only BUY/SELL are supported in tester order_send()";
        set_last_error(-2, result.comment);
        return result;
    }

    double exec_price = request.price;
    if (exec_price <= 0.0) {
        exec_price = is_buy ? ask : bid;
    }
    if (exec_price <= 0.0) {
        exec_price = last;
    }
    if (exec_price <= 0.0) {
        result.retcode = 10015;
        result.comment = "Price is invalid and no market quote is available";
        set_last_error(-2, result.comment);
        return result;
    }

    const long now = static_cast<long>(std::time(nullptr));
    const long now_msc = now * 1000;

    const long order_ticket = next_ticket(state->trading_orders);
    const long deal_ticket = next_ticket(state->trading_deals);
    const long position_ticket = next_ticket(state->trading_positions);

    double margin_required = 0.0;
    try {
        margin_required = order_calc_margin(is_buy ? "BUY" : "SELL", symbol_key, request.volume, exec_price);
    } catch (...) {
        margin_required = 0.0;
    }

    auto& order_row = state->trading_orders[to_string_num(order_ticket)];
    order_row["ticket"] = to_string_num(order_ticket);
    order_row["time_setup"] = to_string_num(now);
    order_row["time_setup_msc"] = to_string_num(now_msc);
    order_row["time_done"] = to_string_num(now);
    order_row["time_done_msc"] = to_string_num(now_msc);
    order_row["time_expiration"] = to_string_num(request.expiration);
    order_row["type"] = to_string_num(order_type);
    order_row["type_time"] = to_string_num(request.type_time);
    order_row["type_filling"] = to_string_num(request.type_filling);
    order_row["state"] = "4";
    order_row["magic"] = to_string_num(request.magic);
    order_row["reason"] = "0";
    order_row["position_id"] = to_string_num(position_ticket);
    order_row["position_by_id"] = to_string_num(request.position_by);
    order_row["volume_initial"] = to_string_num(request.volume);
    order_row["volume_current"] = "0";
    order_row["price_open"] = to_string_num(exec_price);
    order_row["sl"] = to_string_num(request.sl);
    order_row["tp"] = to_string_num(request.tp);
    order_row["price_current"] = to_string_num(exec_price);
    order_row["price_stoplimit"] = to_string_num(request.stoplimit);
    order_row["symbol"] = symbol_key;
    order_row["comment"] = request.comment;
    order_row["external_id"] = "";
    order_row["margin_required"] = to_string_num(margin_required);

    state->trading_history_orders[to_string_num(order_ticket)] = order_row;

    auto& deal_row = state->trading_deals[to_string_num(deal_ticket)];
    deal_row["ticket"] = to_string_num(deal_ticket);
    deal_row["order"] = to_string_num(order_ticket);
    deal_row["time"] = to_string_num(now);
    deal_row["time_msc"] = to_string_num(now_msc);
    deal_row["type"] = to_string_num(order_type);
    deal_row["entry"] = "0";
    deal_row["magic"] = to_string_num(request.magic);
    deal_row["reason"] = "0";
    deal_row["position_id"] = to_string_num(position_ticket);
    deal_row["volume"] = to_string_num(request.volume);
    deal_row["price"] = to_string_num(exec_price);
    deal_row["commission"] = "0";
    deal_row["swap"] = "0";
    deal_row["profit"] = "0";
    deal_row["fee"] = "0";
    deal_row["symbol"] = symbol_key;
    deal_row["comment"] = request.comment;
    deal_row["external_id"] = "";

    auto& pos_row = state->trading_positions[symbol_key];
    pos_row["ticket"] = to_string_num(position_ticket);
    pos_row["time"] = to_string_num(now);
    pos_row["time_msc"] = to_string_num(now_msc);
    pos_row["time_update"] = to_string_num(now);
    pos_row["time_update_msc"] = to_string_num(now_msc);
    pos_row["type"] = to_string_num(order_type);
    pos_row["magic"] = to_string_num(request.magic);
    pos_row["identifier"] = to_string_num(position_ticket);
    pos_row["reason"] = "0";
    pos_row["volume"] = to_string_num(request.volume);
    pos_row["price_open"] = to_string_num(exec_price);
    pos_row["sl"] = to_string_num(request.sl);
    pos_row["tp"] = to_string_num(request.tp);
    pos_row["price_current"] = to_string_num(exec_price);
    pos_row["swap"] = "0";
    pos_row["profit"] = "0";
    pos_row["commission"] = "0";
    pos_row["fee"] = "0";
    pos_row["margin_required"] = to_string_num(margin_required);
    pos_row["symbol"] = symbol_key;
    pos_row["comment"] = request.comment;
    pos_row["external_id"] = "";

    result.retcode = 10009;
    result.deal = deal_ticket;
    result.order = order_ticket;
    result.price = exec_price;
    result.comment = "Request executed";
    set_last_error(0, "No error");
    return result;
}

double BacktestSimulator::order_calc_profit(const std::string& action,
                                            const std::string& symbol,
                                            double lotsize,
                                            double entry_price,
                                            double exit_price) const {
    const auto round_2 = [](double value) -> double {
        return std::round(value * 100.0) / 100.0;
    };

    if (lotsize <= 0.0) {
        throw std::invalid_argument("lotsize must be > 0");
    }

    const auto* state = account_.GetState();
    if (!state) {
        throw std::runtime_error("BacktestSimulator has no shared BacktestState");
    }

    const auto sym_it = state->trading_symbols.find(symbol);
    if (sym_it == state->trading_symbols.end()) {
        throw std::runtime_error("symbol not found in BacktestState: " + symbol);
    }

    const auto action_token = normalize_token(action);
    const double signed_delta = (action_token == "BUY")
                                    ? (exit_price - entry_price)
                                    : (action_token == "SELL")
                                          ? (entry_price - exit_price)
                                          : 0.0;
    if (signed_delta == 0.0 && action_token != "BUY" && action_token != "SELL") {
        throw std::invalid_argument("action must be BUY or SELL");
    }

    const auto& row = sym_it->second;
    const long calc_mode = static_cast<long>(read_double(row, "trade_calc_mode", 0.0));
    const double contract_size = read_double(row, "trade_contract_size", 0.0);
    const double tick_size = read_double(row, "trade_tick_size", 0.0);
    const double directional_tick_value =
        (signed_delta >= 0.0) ? read_double(row, "trade_tick_value_profit", 0.0)
                              : read_double(row, "trade_tick_value_loss", 0.0);
    const double tick_value =
        (directional_tick_value > 0.0) ? directional_tick_value
                                       : read_double(row, "trade_tick_value", 0.0);

    const bool has_tick_formula = (tick_size > 0.0 && tick_value > 0.0);
    const bool has_contract_formula = (contract_size > 0.0);
    const std::string account_currency = read_string(state->trading_account, "currency");
    const std::string base_currency = read_string(row, "currency_base");
    const std::string profit_currency = read_string(row, "currency_profit");
    const bool needs_conversion =
        !account_currency.empty() && !profit_currency.empty() && account_currency != profit_currency;

    auto converter = build_currency_converter(*state);
    bool can_convert_profit = true;
    if (needs_conversion) {
        if (exit_price > 0.0 && !base_currency.empty() &&
            (account_currency == base_currency || profit_currency == base_currency)) {
            can_convert_profit = true;
        } else {
            can_convert_profit = !converter.find_path(profit_currency, account_currency).empty();
        }
    }

    const auto to_account_currency = [&](double profit_raw) -> double {
        if (profit_raw == 0.0 || account_currency.empty() || profit_currency.empty() ||
            account_currency == profit_currency) {
            return profit_raw;
        }

        // Direct symbol conversion using the provided close price aligns better
        // with MT5 OrderCalcProfit behavior for pairs like USDJPY on USD account.
        if (exit_price > 0.0 && !base_currency.empty()) {
            if (account_currency == base_currency && profit_currency != base_currency) {
                return profit_raw / exit_price;
            }
            if (profit_currency == base_currency && account_currency != base_currency) {
                return profit_raw * exit_price;
            }
        }

        try {
            return converter.convert(profit_raw, profit_currency, account_currency);
        } catch (...) {
            return profit_raw;
        }
    };

    const auto calc_tick = [&]() -> double {
        return has_tick_formula ? ((signed_delta * lotsize * tick_value) / tick_size) : 0.0;
    };
    const auto calc_contract = [&]() -> double {
        return has_contract_formula ? to_account_currency(signed_delta * contract_size * lotsize) : 0.0;
    };

    switch (calc_mode) {
        case 0:  // SYMBOL_CALC_MODE_FOREX
        case 2:  // SYMBOL_CALC_MODE_CFD
        case 3:  // SYMBOL_CALC_MODE_CFDINDEX
        case 4:  // SYMBOL_CALC_MODE_CFDLEVERAGE
        case 5:  // SYMBOL_CALC_MODE_EXCH_STOCKS
        case 8:  // SYMBOL_CALC_MODE_EXCH_BONDS / CFDCRYPTO fallback
            if (has_contract_formula && can_convert_profit) {
                return round_2(calc_contract());
            }
            if (has_tick_formula) {
                return round_2(calc_tick());
            }
            return 0.0;
        case 1:  // SYMBOL_CALC_MODE_FUTURES
        case 6:  // SYMBOL_CALC_MODE_EXCH_FUTURES
        case 7:  // SYMBOL_CALC_MODE_EXCH_OPTIONS
            if (has_tick_formula) {
                return round_2(calc_tick());
            }
            if (has_contract_formula) {
                return round_2(calc_contract());
            }
            return 0.0;
        default:
            if (has_tick_formula) {
                return round_2(calc_tick());
            }
            if (has_contract_formula) {
                return round_2(calc_contract());
            }
            return 0.0;
    }
}

double BacktestSimulator::order_calc_margin(const std::string& action,
                                            const std::string& symbol,
                                            double lotsize,
                                            double entry_price) const {
    const auto round_2 = [](double value) -> double {
        return std::round(value * 100.0) / 100.0;
    };

    if (lotsize <= 0.0 || entry_price <= 0.0) {
        return 0.0;
    }

    const auto action_token = normalize_token(action);
    if (action_token != "BUY" && action_token != "SELL") {
        throw std::invalid_argument("action must be BUY or SELL");
    }

    const auto* state = account_.GetState();
    if (!state) {
        throw std::runtime_error("BacktestSimulator has no shared BacktestState");
    }

    const auto sym_it = state->trading_symbols.find(symbol);
    if (sym_it == state->trading_symbols.end()) {
        throw std::runtime_error("symbol not found in BacktestState: " + symbol);
    }

    const auto& row = sym_it->second;
    const long calc_mode = static_cast<long>(read_double(row, "trade_calc_mode", 0.0));
    const double contract_size = read_double(row, "trade_contract_size", 0.0);
    const double tick_size = read_double(row, "trade_tick_size", 0.0);
    const double tick_value_raw = read_double(row, "trade_tick_value", 0.0);
    const double tick_value_profit = read_double(row, "trade_tick_value_profit", 0.0);
    const double tick_value_loss = read_double(row, "trade_tick_value_loss", 0.0);
    const double tick_value = std::max({tick_value_raw, tick_value_profit, tick_value_loss});
    const double margin_initial = read_double(row, "margin_initial", 0.0);
    const double margin_maintenance = read_double(row, "margin_maintenance", 0.0);
    double margin_rate = (margin_initial > 0.0) ? margin_initial : margin_maintenance;
    if (margin_rate <= 0.0) {
        margin_rate = 1.0;
    }
    const double face_value = read_double(row, "trade_face_value", 0.0);
    const std::string account_currency = read_string(state->trading_account, "currency");
    const std::string base_currency = read_string(row, "currency_base");
    const std::string profit_currency = read_string(row, "currency_profit");
    const long leverage_i = std::max<long>(1, account_.Leverage());
    const double leverage = static_cast<double>(leverage_i);
    auto converter = build_currency_converter(*state);

    auto margin_from_contract_price = [&]() -> double {
        return (contract_size > 0.0) ? (lotsize * contract_size * entry_price) : 0.0;
    };
    auto margin_from_contract_only = [&]() -> double {
        return (contract_size > 0.0) ? (lotsize * contract_size) : 0.0;
    };

    double margin = 0.0;
    switch (calc_mode) {
        case 0:  // SYMBOL_CALC_MODE_FOREX
            margin = margin_from_contract_only() / leverage;
            if (!account_currency.empty() && !base_currency.empty() &&
                account_currency != base_currency) {
                bool converted = false;

                if (account_currency == profit_currency && entry_price > 0.0) {
                    margin *= entry_price;
                    converted = true;
                }

                if (!converted) {
                    try {
                        if (!base_currency.empty()) {
                            margin = converter.convert(margin, base_currency, account_currency);
                            converted = true;
                        }
                    } catch (...) {
                    }
                }

                if (!converted && entry_price > 0.0 && tick_size > 0.0 && tick_value > 0.0 &&
                    contract_size > 0.0) {
                    const double profit_to_account = tick_value / (contract_size * tick_size);
                    margin = margin * entry_price * profit_to_account;
                    converted = true;
                }
            }
            break;
        case 5:  // SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE
            margin = margin_from_contract_price();
            break;
        case 2:   // SYMBOL_CALC_MODE_CFD
        case 3:   // SYMBOL_CALC_MODE_CFDINDEX
        case 32:  // SYMBOL_CALC_MODE_EXCH_STOCKS
        case 38:  // SYMBOL_CALC_MODE_EXCH_STOCKS_MOEX
            margin = margin_from_contract_price() * margin_rate;
            break;
        case 4:  // SYMBOL_CALC_MODE_CFDLEVERAGE
            margin = (margin_from_contract_price() * margin_rate) / leverage;
            break;
        case 1:   // SYMBOL_CALC_MODE_FUTURES
        case 33:  // SYMBOL_CALC_MODE_EXCH_FUTURES
            margin = lotsize * margin_initial;
            break;
        case 37:  // SYMBOL_CALC_MODE_EXCH_BONDS
        case 39:  // SYMBOL_CALC_MODE_EXCH_BONDS_MOEX
            margin = lotsize * contract_size * face_value * entry_price / 100.0;
            break;
        case 64:  // SYMBOL_CALC_MODE_SERV_COLLATERAL
            margin = 0.0;
            break;
        default:
            margin = margin_from_contract_price() / leverage;
            break;
    }

    return round_2(std::max(0.0, margin));
}

std::vector<haruquant::trading::OrderInfo> BacktestSimulator::orders_get(const std::string& symbol,
                                                                          const std::string& group,
                                                                          long ticket) const {
    std::vector<haruquant::trading::OrderInfo> out;
    const auto* state = account_.GetState();
    if (!state) {
        return out;
    }

    const std::string symbol_filter = to_upper_copy(trim_copy(symbol));
    for (const auto& [key, row] : state->trading_orders) {
        const long row_ticket = parse_long_default(read_string(row, "ticket"), parse_long_default(key, 0));
        if (row_ticket <= 0) {
            continue;
        }
        if (ticket > 0 && row_ticket != ticket) {
            continue;
        }

        const std::string row_symbol = read_string(row, "symbol");
        if (!symbol_filter.empty() && to_upper_copy(row_symbol) != symbol_filter) {
            continue;
        }
        if (!group_match(row_symbol, group)) {
            continue;
        }

        haruquant::trading::OrderInfo item(account_.GetSharedState());
        if (item.Select(row_ticket)) {
            out.push_back(item);
        }
    }
    return out;
}

long BacktestSimulator::orders_total() const {
    return static_cast<long>(orders_get().size());
}

std::vector<haruquant::trading::PositionInfo> BacktestSimulator::positions_get(const std::string& symbol,
                                                                                const std::string& group,
                                                                                long ticket) const {
    std::vector<haruquant::trading::PositionInfo> out;
    const auto* state = account_.GetState();
    if (!state) {
        return out;
    }

    const std::string symbol_filter = to_upper_copy(trim_copy(symbol));
    for (const auto& [key, row] : state->trading_positions) {
        const long row_ticket = parse_long_default(read_string(row, "ticket"), 0);
        if (ticket > 0 && row_ticket != ticket) {
            continue;
        }

        const std::string row_symbol = read_string(row, "symbol").empty() ? key : read_string(row, "symbol");
        if (!symbol_filter.empty() && to_upper_copy(row_symbol) != symbol_filter) {
            continue;
        }
        if (!group_match(row_symbol, group)) {
            continue;
        }

        haruquant::trading::PositionInfo item(account_.GetSharedState());
        if (item.Select(row_symbol)) {
            out.push_back(item);
        }
    }
    return out;
}

long BacktestSimulator::positions_total() const {
    return static_cast<long>(positions_get().size());
}

std::vector<haruquant::trading::HistoryOrderInfo> BacktestSimulator::history_orders_get(
    long date_from,
    long date_to,
    const std::string& group,
    long ticket) const {
    std::vector<haruquant::trading::HistoryOrderInfo> out;
    const auto* state = account_.GetState();
    if (!state) {
        return out;
    }

    const long from = std::max<long>(0, date_from);
    const long to = (date_to <= 0) ? std::numeric_limits<long>::max() : date_to;
    for (const auto& [key, row] : state->trading_history_orders) {
        const long row_ticket = parse_long_default(read_string(row, "ticket"), parse_long_default(key, 0));
        if (row_ticket <= 0) {
            continue;
        }
        if (ticket > 0 && row_ticket != ticket) {
            continue;
        }

        const long time_done = parse_long_default(read_string(row, "time_done"), 0);
        const long time_setup = parse_long_default(read_string(row, "time_setup"), 0);
        const long row_time = (time_done > 0) ? time_done : time_setup;
        if (row_time < from || row_time > to) {
            continue;
        }

        const std::string row_symbol = read_string(row, "symbol");
        if (!group_match(row_symbol, group)) {
            continue;
        }

        haruquant::trading::HistoryOrderInfo item(account_.GetSharedState());
        if (item.Ticket(row_ticket)) {
            out.push_back(item);
        }
    }
    return out;
}

std::vector<haruquant::trading::HistoryOrderInfo> BacktestSimulator::history_orders_get(long ticket) const {
    return history_orders_get(0, std::numeric_limits<long>::max(), "", ticket);
}

long BacktestSimulator::history_orders_total(long date_from, long date_to) const {
    return static_cast<long>(history_orders_get(date_from, date_to).size());
}

std::vector<haruquant::trading::DealInfo> BacktestSimulator::history_deals_get(
    long date_from,
    long date_to,
    const std::string& group,
    long ticket) const {
    std::vector<haruquant::trading::DealInfo> out;
    const auto* state = account_.GetState();
    if (!state) {
        return out;
    }

    const long from = std::max<long>(0, date_from);
    const long to = (date_to <= 0) ? std::numeric_limits<long>::max() : date_to;
    for (const auto& [key, row] : state->trading_deals) {
        const long row_ticket = parse_long_default(read_string(row, "ticket"), parse_long_default(key, 0));
        if (row_ticket <= 0) {
            continue;
        }
        if (ticket > 0 && row_ticket != ticket) {
            continue;
        }

        const long row_time = parse_long_default(read_string(row, "time"), 0);
        if (row_time < from || row_time > to) {
            continue;
        }

        const std::string row_symbol = read_string(row, "symbol");
        if (!group_match(row_symbol, group)) {
            continue;
        }

        haruquant::trading::DealInfo item(account_.GetSharedState());
        if (item.Ticket(row_ticket)) {
            out.push_back(item);
        }
    }
    return out;
}

std::vector<haruquant::trading::DealInfo> BacktestSimulator::history_deals_get(long ticket) const {
    return history_deals_get(0, std::numeric_limits<long>::max(), "", ticket);
}

long BacktestSimulator::history_deals_total(long date_from, long date_to) const {
    return static_cast<long>(history_deals_get(date_from, date_to).size());
}

}  // namespace haruquant::core
