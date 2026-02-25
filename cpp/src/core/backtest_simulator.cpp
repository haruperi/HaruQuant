#include "core/backtest_simulator.hpp"
#include "util/currency_converter.hpp"
#include "util/logger.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
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

}  // namespace haruquant::core
