/**
FILE: src\util\validators.cpp

PURPOSE:
Defines validators.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Rule-level validators for symbol/volume/price/slippage/SLTP/expiration/account checks.
- Trade-level consolidated validators for open/modify/close position and pending-order flows.

DATA FLOW:
Callers provide requests or data -> this file applies core logic -> outputs state changes or results.

DEPENDENCIES:
- Internal modules: Neighboring headers under cpp/include and shared utility components.
- External systems: Standard C++ library and optional third-party libs linked by CMake.

DESIGN NOTES:
- Keep behavior deterministic for backtest and unit-test reliability.
- Prefer explicit validation and retcode-based failure signaling.
- Preserve low coupling between domains through typed interfaces.
*/
#include "util/validators.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <ctime>
#include <limits>
#include <sstream>

namespace haruquant::util {

namespace {

// Simple result helpers keep validator call sites readable and consistent.
RuleValidationResult ok(const std::string& message = "OK") {
    return RuleValidationResult{true, message};
}

RuleValidationResult fail(const std::string& message) {
    return RuleValidationResult{false, message};
}

TradeValidationResult fail_trade(int retcode, const std::string& comment) {
    TradeValidationResult out;
    out.ok = false;
    out.retcode = retcode;
    out.comment = comment;
    return out;
}

std::string to_upper(std::string value) {
    for (char& ch : value) {
        ch = static_cast<char>(std::toupper(static_cast<unsigned char>(ch)));
    }
    return value;
}

// Order-side helpers are reused by SL/TP and slippage checks.
bool is_market_order_type(int type) {
    return type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY) ||
           type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL);
}

bool is_pending_order_type(int type) {
    return type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT) ||
           type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_LIMIT) ||
           type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP) ||
           type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP) ||
           type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP_LIMIT) ||
           type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP_LIMIT);
}

bool is_buy_action(int order_type) {
    return order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY) ||
           order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT) ||
           order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP) ||
           order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP_LIMIT);
}

bool is_sell_action(int order_type) {
    return order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL) ||
           order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_LIMIT) ||
           order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP) ||
           order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP_LIMIT);
}

std::string trim_copy(const std::string& input) {
    std::size_t start = 0;
    while (start < input.size() && std::isspace(static_cast<unsigned char>(input[start]))) {
        ++start;
    }
    std::size_t end = input.size();
    while (end > start && std::isspace(static_cast<unsigned char>(input[end - 1]))) {
        --end;
    }
    return input.substr(start, end - start);
}

// Derive decimal precision implied by a step size (e.g. 0.01 -> 2).
int step_decimals(double step) {
    if (!(step > 0.0) || !std::isfinite(step)) {
        return 0;
    }
    constexpr int kMaxDigits = 8;
    double scaled = step;
    for (int digits = 0; digits <= kMaxDigits; ++digits) {
        const double rounded = std::round(scaled);
        if (std::abs(scaled - rounded) < 1e-8) {
            return digits;
        }
        scaled *= 10.0;
    }
    return kMaxDigits;
}

// Accept plain decimal forms only; scientific notation is intentionally rejected.
bool is_plain_decimal_number(const std::string& s) {
    if (s.empty()) {
        return false;
    }
    std::size_t i = 0;
    if (s[i] == '+' || s[i] == '-') {
        ++i;
    }
    bool seen_digit = false;
    bool seen_dot = false;
    for (; i < s.size(); ++i) {
        const char c = s[i];
        if (std::isdigit(static_cast<unsigned char>(c))) {
            seen_digit = true;
            continue;
        }
        if (c == '.' && !seen_dot) {
            seen_dot = true;
            continue;
        }
        return false;
    }
    return seen_digit;
}

double calculate_margin(
    const haruquant::AccountInfo& account,
    const haruquant::SymbolInfo& symbol_info,
    double volume,
    double price) {
    const double leverage = static_cast<double>(std::max(1L, account.Leverage()));
    const double notional = volume * symbol_info.TradeContractSize() * price;
    return notional / static_cast<double>(leverage);
}

int64_t now_unix_sec() {
    return static_cast<int64_t>(std::time(nullptr));
}

RuleValidationResult validate_price_relationship(
    double level_price,
    double entry_price,
    int order_type,
    bool is_stop_loss) {
    if (is_buy_action(order_type)) {
        if (is_stop_loss && level_price >= entry_price) {
            return fail("Stop loss for BUY must be below entry price");
        }
        if (!is_stop_loss && level_price <= entry_price) {
            return fail("Take profit for BUY must be above entry price");
        }
        return ok();
    }

    if (is_sell_action(order_type)) {
        if (is_stop_loss && level_price <= entry_price) {
            return fail("Stop loss for SELL must be above entry price");
        }
        if (!is_stop_loss && level_price >= entry_price) {
            return fail("Take profit for SELL must be below entry price");
        }
        return ok();
    }

    return ok();
}

RuleValidationResult validate_stop_freeze_distance(
    double level_price,
    double entry_price,
    int order_type,
    bool is_stop_loss,
    const haruquant::SymbolInfo& symbol_info,
    const std::string& level_name) {
    const double point = symbol_info.Point();
    if (!(point > 0.0) || !std::isfinite(point)) {
        return fail("Invalid symbol point value");
    }

    const int32_t stops_level = static_cast<int32_t>(symbol_info.TradeStopsLevel());
    const int32_t freeze_level = static_cast<int32_t>(symbol_info.TradeFreezeLevel());
    const int32_t required_level = std::max(stops_level, freeze_level);
    if (required_level <= 0) {
        return ok();
    }

    const double required_distance = static_cast<double>(required_level) * point;
    auto distance_fail = [&](const std::string& side_text) -> RuleValidationResult {
        std::ostringstream oss;
        oss << level_name << " for " << side_text << " must be at least "
            << required_level << " points from entry";
        return fail(oss.str());
    };

    if (is_buy_action(order_type)) {
        if (is_stop_loss) {
            if (level_price > (entry_price - required_distance)) {
                return distance_fail("BUY");
            }
            return ok();
        }
        if (level_price < (entry_price + required_distance)) {
            return distance_fail("BUY");
        }
        return ok();
    }

    if (is_sell_action(order_type)) {
        if (is_stop_loss) {
            if (level_price < (entry_price + required_distance)) {
                return distance_fail("SELL");
            }
            return ok();
        }
        if (level_price > (entry_price - required_distance)) {
            return distance_fail("SELL");
        }
        return ok();
    }

    return fail("Unknown order type");
}

std::optional<int> parse_order_type_token(const std::string& order_type) {
    const std::string token = to_upper(order_type);
    if (token == "BUY") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY);
    if (token == "SELL") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL);
    if (token == "BUY_LIMIT") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT);
    if (token == "SELL_LIMIT") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_LIMIT);
    if (token == "BUY_STOP") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP);
    if (token == "SELL_STOP") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP);
    if (token == "BUY_STOP_LIMIT") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP_LIMIT);
    if (token == "SELL_STOP_LIMIT") return static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP_LIMIT);
    return std::nullopt;
}

double parse_double_or(const std::string& value, double fallback = 0.0) {
    if (value.empty()) {
        return fallback;
    }
    try {
        return std::stod(value);
    } catch (...) {
        return fallback;
    }
}

int parse_int_or(const std::string& value, int fallback = 0) {
    if (value.empty()) {
        return fallback;
    }
    try {
        return std::stoi(value);
    } catch (...) {
        return fallback;
    }
}

const core::BacktestState::Dictionary* find_symbol_row(
    const core::BacktestState* state,
    const std::string& symbol) {
    if (state == nullptr || symbol.empty()) {
        return nullptr;
    }
    const auto exact = state->trading_symbols.find(symbol);
    if (exact != state->trading_symbols.end()) {
        return &exact->second;
    }
    const std::string target = to_upper(symbol);
    for (const auto& kv : state->trading_symbols) {
        if (to_upper(kv.first) == target) {
            return &kv.second;
        }
    }
    return nullptr;
}

int count_open_pending_orders(const core::BacktestState* state) {
    if (state == nullptr) {
        return 0;
    }
    int count = 0;
    for (const auto& kv : state->trading_orders) {
        auto it = kv.second.find("action");
        if (it != kv.second.end() && it->second == "order_open") {
            ++count;
        }
    }
    return count;
}

double symbol_open_volume(const core::BacktestState* state, const std::string& symbol) {
    if (state == nullptr || symbol.empty()) {
        return 0.0;
    }
    const std::string target = to_upper(symbol);
    double total = 0.0;
    for (const auto& kv : state->trading_positions) {
        std::string row_symbol = kv.first;
        auto sym_it = kv.second.find("symbol");
        if (sym_it != kv.second.end() && !sym_it->second.empty()) {
            row_symbol = sym_it->second;
        }
        if (to_upper(row_symbol) != target) {
            continue;
        }
        auto vol_it = kv.second.find("volume");
        if (vol_it != kv.second.end()) {
            total += std::abs(parse_double_or(vol_it->second, 0.0));
        }
    }
    return total;
}

const core::BacktestState::Dictionary* find_order_row(
    const core::BacktestState* state,
    long ticket) {
    if (state == nullptr || ticket <= 0) {
        return nullptr;
    }
    const std::string ticket_str = std::to_string(ticket);
    const auto direct = state->trading_orders.find(ticket_str);
    if (direct != state->trading_orders.end()) {
        return &direct->second;
    }
    for (const auto& kv : state->trading_orders) {
        auto it = kv.second.find("ticket");
        if (it != kv.second.end() && it->second == ticket_str) {
            return &kv.second;
        }
    }
    return nullptr;
}

}  // namespace

TradeValidationResult validate_action_type(int action, int type) {
    if (action == 1) {
        if (!is_market_order_type(type)) {
            return fail_trade(10013, "Invalid order type for market execution");
        }
        return TradeValidationResult{};
    }
    if (action == 5) {
        if (!is_pending_order_type(type)) {
            return fail_trade(10013, "Invalid pending order type");
        }
        return TradeValidationResult{};
    }
    if (action == 6 || action == 7 || action == 8) {
        return TradeValidationResult{};
    }
    return fail_trade(10013, "Invalid request: missing or unsupported action");
}

TradeValidationResult validate_submission_inputs(
    const std::string& symbol,
    double volume,
    const haruquant::SymbolInfo* symbol_info,
    double bid,
    double ask) {
    if (symbol.empty()) {
        return fail_trade(10013, "Invalid request: missing symbol");
    }
    if (volume <= 0.0) {
        return fail_trade(10014, "Invalid volume");
    }
    if (symbol_info == nullptr) {
        return fail_trade(10021, "No quotes to process the request");
    }
    if (bid <= 0.0 || ask <= 0.0) {
        return fail_trade(10021, "No quotes to process the request");
    }
    return TradeValidationResult{};
}

TradeValidationResult validate_trade_request(
    const haruquant::MqlTradeRequest& request,
    const haruquant::AccountInfo& account,
    const haruquant::SymbolInfo* symbol_info) {
    TradeValidationResult out{};
    out.margin = account.Margin();
    out.margin_free = account.MarginFree();
    out.margin_level = account.MarginLevel();

    if (symbol_info == nullptr) {
        return fail_trade(10013, "Unknown symbol");
    }

    if (request.volume <= 0.0) {
        return fail_trade(10014, "Invalid volume");
    }

    if (request.volume < symbol_info->VolumeMin() || request.volume > symbol_info->VolumeMax()) {
        return fail_trade(10014, "Volume out of range");
    }

    if (request.action == static_cast<int>(haruquant::ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_DEAL) ||
        request.action == static_cast<int>(haruquant::ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_PENDING)) {
        double price = request.price;
        if (price <= 0.0) {
            const int type = static_cast<int>(request.type);
            price = (type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY))
                ? symbol_info->Ask()
                : symbol_info->Bid();
        }

        out.required_margin = calculate_margin(account, *symbol_info, request.volume, price);
        out.margin = account.Margin() + out.required_margin;
        out.margin_free = account.Equity() - out.margin;
        out.margin_level = (out.margin > 0.0) ? (account.Equity() / out.margin * 100.0) : 0.0;

        if (out.margin_free < 0.0) {
            return fail_trade(10019, "Insufficient margin");
        }
    }

    out.ok = true;
    out.retcode = 10009;
    out.comment = "Request valid";
    return out;
}

RuleValidationResult validate_symbol(const std::string& symbol, const ValidationContext& ctx) {
    if (symbol.empty()) {
        return fail("Symbol must be a non-empty string");
    }
    if (!ctx.symbol_exists) {
        return fail("Symbol '" + symbol + "' not found");
    }
    if (!ctx.symbol_visible && !ctx.symbol_select_ok) {
        return fail("Symbol '" + symbol + "' cannot be selected");
    }
    return ok("Symbol is valid");
}

RuleValidationResult validate_volume_basic(double volume) {
    if (!std::isfinite(volume)) {
        return fail("Volume must be a number");
    }
    if (volume <= 0.0) {
        return fail("Volume must be positive");
    }
    return ok();
}

RuleValidationResult validate_volume_symbol_limits(double volume, const haruquant::SymbolInfo& symbol_info) {
    if (volume < symbol_info.VolumeMin()) {
        std::ostringstream oss;
        oss << "Volume " << volume << " below minimum " << symbol_info.VolumeMin();
        return fail(oss.str());
    }
    if (volume > symbol_info.VolumeMax()) {
        std::ostringstream oss;
        oss << "Volume " << volume << " above maximum " << symbol_info.VolumeMax();
        return fail(oss.str());
    }
    return ok();
}

RuleValidationResult validate_volume_step(double volume, const haruquant::SymbolInfo& symbol_info) {
    const double step = symbol_info.VolumeStep();
    if (step <= 0.0) {
        return ok();
    }
    const double vol_min = symbol_info.VolumeMin();
    const double steps = std::round((volume - vol_min) / step);
    const double aligned = vol_min + (steps * step);
    if (std::abs(volume - aligned) > 1e-8) {
        std::ostringstream oss;
        oss << "Volume " << volume << " not aligned with step " << step;
        return fail(oss.str());
    }
    return ok();
}

RuleValidationResult validate_volume_format(
    const std::string& volume_text,
    const ValidationContext& ctx,
    const ValidationRules& rules) {
    const std::string text = trim_copy(volume_text);
    if (!is_plain_decimal_number(text)) {
        return fail("Volume must be a plain numeric string");
    }

    const std::size_t dot = text.find('.');
    const int decimals = (dot == std::string::npos)
        ? 0
        : static_cast<int>(text.size() - dot - 1);
    // Prefer symbol-specific lot step when available; fallback to configured global rule.
    const double step = (ctx.symbol_info != nullptr && ctx.symbol_info->VolumeStep() > 0.0)
        ? ctx.symbol_info->VolumeStep()
        : rules.volume_step;
    const int allowed_decimals = step_decimals(step);
    if (decimals > allowed_decimals) {
        std::ostringstream oss;
        oss << "Volume format has " << decimals
            << " decimal places, max allowed is " << allowed_decimals;
        return fail(oss.str());
    }
    return ok();
}

RuleValidationResult validate_price_format(
    const std::string& price_text,
    const ValidationContext& ctx) {
    const std::string text = trim_copy(price_text);
    if (!is_plain_decimal_number(text)) {
        return fail("Price must be a plain numeric string");
    }

    const std::size_t dot = text.find('.');
    const int decimals = (dot == std::string::npos)
        ? 0
        : static_cast<int>(text.size() - dot - 1);

    int allowed_decimals = 8;
    if (ctx.symbol_info != nullptr) {
        if (ctx.symbol_info->Digits() > 0) {
            allowed_decimals = ctx.symbol_info->Digits();
        } else {
            // If digits are unavailable, infer precision from tick size/point.
            const double tick_size = ctx.symbol_info->TradeTickSize();
            const double point = ctx.symbol_info->Point();
            const double reference = (tick_size > 0.0) ? tick_size : point;
            if (reference > 0.0) {
                allowed_decimals = step_decimals(reference);
            }
        }
    }

    if (decimals > allowed_decimals) {
        std::ostringstream oss;
        oss << "Price format has " << decimals
            << " decimal places, max allowed is " << allowed_decimals;
        return fail(oss.str());
    }
    return ok();
}

RuleValidationResult validate_volume(double volume, const ValidationContext& ctx, const ValidationRules& rules) {
    RuleValidationResult base = validate_volume_basic(volume);
    if (!base.ok) {
        return base;
    }
    const double rule_min = rules.volume_min;
    const double rule_max = rules.volume_max;
    const double rule_step = rules.volume_step;

    if (volume < rule_min || volume > rule_max) {
        std::ostringstream oss;
        oss << "Volume " << volume << " outside valid range [" << rule_min << ", " << rule_max << "]";
        return fail(oss.str());
    }
    if (rule_step > 0.0) {
        const double steps = std::round((volume - rule_min) / rule_step);
        const double aligned = rule_min + (steps * rule_step);
        if (std::abs(volume - aligned) > 1e-8) {
            std::ostringstream oss;
            oss << "Volume " << volume << " not aligned with step " << rule_step;
            return fail(oss.str());
        }
    }

    // Rule-level checks run always; symbol-specific constraints are additive.
    if (ctx.symbol_info == nullptr) {
        return ok("Volume is valid");
    }
    RuleValidationResult limits = validate_volume_symbol_limits(volume, *ctx.symbol_info);
    if (!limits.ok) {
        return limits;
    }
    RuleValidationResult step = validate_volume_step(volume, *ctx.symbol_info);
    if (!step.ok) {
        return step;
    }
    return ok("Volume is valid");
}

RuleValidationResult validate_price(double price, const ValidationContext& ctx, const ValidationRules& rules) {
    if (!std::isfinite(price)) {
        return fail("Price must be a number");
    }
    if (price <= 0.0) {
        return fail("Price must be positive");
    }
    if (price < rules.price_min || price > rules.price_max) {
        std::ostringstream oss;
        oss << "Price " << price << " outside valid range";
        return fail(oss.str());
    }
    if (ctx.symbol_info != nullptr) {
        const double tick_size = ctx.symbol_info->TradeTickSize();
        if (tick_size > 0.0) {
            const double ratio = price / tick_size;
            const double nearest = std::round(ratio);
            if (std::abs(ratio - nearest) > 1e-5) {
                std::ostringstream oss;
                oss << "Price " << price << " not aligned with tick size " << tick_size;
                return fail(oss.str());
            }
        }
    }
    return ok("Price is valid");
}

RuleValidationResult validate_order_type(int order_type) {
    if (is_market_order_type(order_type) || is_pending_order_type(order_type)) {
        return ok("Order type is valid");
    }
    return fail("Invalid order type constant: " + std::to_string(order_type));
}

RuleValidationResult validate_order_type(const std::string& order_type) {
    if (!parse_order_type_token(order_type).has_value()) {
        return fail("Invalid order type string: " + order_type);
    }
    return ok("Order type is valid");
}

RuleValidationResult validate_magic(int magic, const ValidationRules& rules) {
    if (magic < rules.magic_min || magic > rules.magic_max) {
        return fail("Magic number " + std::to_string(magic) + " outside valid range");
    }
    return ok("Magic number is valid");
}

RuleValidationResult validate_slippage(
    int slippage_points,
    double requested_price,
    int order_type,
    const ValidationContext& ctx,
    const ValidationRules& rules) {
    if (slippage_points < rules.deviation_min || slippage_points > rules.deviation_max) {
        return fail("Slippage " + std::to_string(slippage_points) + " outside valid range");
    }
    if (!std::isfinite(requested_price) || requested_price <= 0.0) {
        return fail("Requested price must be a positive number");
    }
    if (ctx.symbol_info == nullptr || !ctx.symbol_tick.has_value()) {
        return fail("Symbol info or tick data not available");
    }

    const double point = ctx.symbol_info->Point();
    if (!(point > 0.0) || !std::isfinite(point)) {
        return fail("Invalid symbol point value");
    }

    // MT5 convention: BUY compares against ask, SELL compares against bid.
    const double actual_price = is_buy_action(order_type) ? ctx.symbol_tick->ask : ctx.symbol_tick->bid;
    if (!(actual_price > 0.0) || !std::isfinite(actual_price)) {
        return fail("Invalid market price from recent tick");
    }
    if (!is_buy_action(order_type) && !is_sell_action(order_type)) {
        return fail("Invalid order type for slippage validation");
    }

    // Slippage points are converted to absolute price distance using symbol point.
    const double allowable = static_cast<double>(slippage_points) * point;
    const double diff = std::abs(requested_price - actual_price);
    if (diff > allowable + 1e-12) {
        std::ostringstream oss;
        oss << "Requested price outside slippage range (requested=" << requested_price
            << ", actual=" << actual_price
            << ", max_diff=" << allowable << ")";
        return fail(oss.str());
    }
    return ok("Slippage is valid");
}

RuleValidationResult validate_expiration_unix(int64_t expiration_unix_sec, int64_t now_unix_sec) {
    if (expiration_unix_sec <= now_unix_sec) {
        return fail("Expiration must be in the future");
    }
    const int64_t max_future = now_unix_sec + (365LL * 24LL * 60LL * 60LL);
    if (expiration_unix_sec > max_future) {
        return fail("Expiration too far in the future (max 1 year)");
    }
    return ok("Expiration is valid");
}

RuleValidationResult validate_expiration_mode(const std::string& expiration_mode) {
    const std::string mode = to_upper(expiration_mode);
    if (mode == "GTC" || mode == "DAILY" || mode == "DAILY_EXCLUDING_STOPS") {
        return ok("Expiration mode is valid");
    }
    return fail("Invalid expiration mode: " + expiration_mode);
}

RuleValidationResult validate_timeframe(const std::string& timeframe) {
    static const std::array<const char*, 9> valid = {
        "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"};
    const std::string tf = to_upper(timeframe);
    for (const char* item : valid) {
        if (tf == item) {
            return ok("Timeframe is valid");
        }
    }
    return fail("Invalid timeframe string: " + timeframe);
}

RuleValidationResult validate_timeframe(int timeframe) {
    // MT5 constants commonly used.
    static const std::array<int, 9> valid = {1, 5, 15, 30, 16385, 16388, 16408, 32769, 49153};
    for (int item : valid) {
        if (timeframe == item) {
            return ok("Timeframe is valid");
        }
    }
    return fail("Invalid timeframe constant: " + std::to_string(timeframe));
}

RuleValidationResult validate_date_range_unix(
    int64_t start_unix_sec,
    std::optional<int64_t> end_unix_sec,
    int64_t now_unix_sec) {
    const int64_t min_past = now_unix_sec - (3650LL * 24LL * 60LL * 60LL);
    if (start_unix_sec < min_past) {
        return fail("Start date too far in the past (max 10 years)");
    }
    if (end_unix_sec.has_value()) {
        if (*end_unix_sec <= start_unix_sec) {
            return fail("End date must be after start date");
        }
        if (*end_unix_sec > now_unix_sec) {
            return fail("End date cannot be in the future");
        }
    }
    return ok("Date range is valid");
}

RuleValidationResult validate_stop_loss(
    double stop_loss,
    std::optional<double> entry_price,
    std::optional<int> order_type,
    const ValidationContext& ctx,
    const ValidationRules& rules) {
    if (!(stop_loss > 0.0)) {
        return fail("Stop loss must be greater than 0");
    }
    RuleValidationResult price_ok = validate_price(stop_loss, ctx, rules);
    if (!price_ok.ok) {
        return fail("Invalid stop loss price: " + price_ok.message);
    }
    if (entry_price.has_value() && order_type.has_value()) {
        RuleValidationResult rel = validate_price_relationship(
            stop_loss, *entry_price, *order_type, true);
        if (!rel.ok) {
            return rel;
        }
    }
    if (entry_price.has_value() && ctx.symbol_info != nullptr) {
        RuleValidationResult dist = validate_stop_freeze_distance(
            stop_loss, *entry_price, order_type.value_or(0), true, *ctx.symbol_info, "Stop loss");
        if (!dist.ok) {
            return dist;
        }
    }
    return ok("Stop loss is valid");
}

RuleValidationResult validate_take_profit(
    double take_profit,
    std::optional<double> entry_price,
    std::optional<int> order_type,
    const ValidationContext& ctx,
    const ValidationRules& rules) {
    if (!(take_profit > 0.0)) {
        return fail("Take profit must be greater than 0");
    }
    RuleValidationResult price_ok = validate_price(take_profit, ctx, rules);
    if (!price_ok.ok) {
        return fail("Invalid take profit price: " + price_ok.message);
    }
    if (entry_price.has_value() && order_type.has_value()) {
        RuleValidationResult rel = validate_price_relationship(
            take_profit, *entry_price, *order_type, false);
        if (!rel.ok) {
            return rel;
        }
    }
    if (entry_price.has_value() && ctx.symbol_info != nullptr) {
        RuleValidationResult dist = validate_stop_freeze_distance(
            take_profit, *entry_price, order_type.value_or(0), false, *ctx.symbol_info, "Take profit");
        if (!dist.ok) {
            return dist;
        }
    }
    return ok("Take profit is valid");
}

RuleValidationResult validate_trade_request_payload(
    const TradeRequestPayload& request,
    const ValidationContext& ctx,
    const ValidationRules& rules) {
    if (request.symbol.empty()) {
        return fail("Missing required field: symbol");
    }
    RuleValidationResult symbol_ok = validate_symbol(request.symbol, ctx);
    if (!symbol_ok.ok) {
        return fail("Invalid symbol: " + symbol_ok.message);
    }
    RuleValidationResult volume_ok = validate_volume(request.volume, ctx, rules);
    if (!volume_ok.ok) {
        return fail("Invalid volume: " + volume_ok.message);
    }
    RuleValidationResult type_ok = validate_order_type(request.type);
    if (!type_ok.ok) {
        return fail("Invalid order type: " + type_ok.message);
    }
    if (request.price.has_value()) {
        RuleValidationResult price_ok = validate_price(*request.price, ctx, rules);
        if (!price_ok.ok) {
            return fail("Invalid price: " + price_ok.message);
        }
    }
    if (request.sl.has_value() && *request.sl > 0.0) {
        RuleValidationResult sl_ok = validate_stop_loss(
            *request.sl, request.price, request.type, ctx, rules);
        if (!sl_ok.ok) {
            return fail("Invalid stop loss: " + sl_ok.message);
        }
    }
    if (request.tp.has_value() && *request.tp > 0.0) {
        RuleValidationResult tp_ok = validate_take_profit(
            *request.tp, request.price, request.type, ctx, rules);
        if (!tp_ok.ok) {
            return fail("Invalid take profit: " + tp_ok.message);
        }
    }
    if (request.magic.has_value()) {
        RuleValidationResult mg = validate_magic(*request.magic, rules);
        if (!mg.ok) {
            return fail("Invalid magic: " + mg.message);
        }
    }
    // Backward compatibility: accept either `slippage` (new) or `deviation` (legacy).
    const std::optional<int> slippage =
        request.slippage.has_value() ? request.slippage : request.deviation;
    if (slippage.has_value()) {
        double requested_price = request.price.value_or(0.0);
        if (!(requested_price > 0.0) && ctx.symbol_tick.has_value()) {
            requested_price = is_buy_action(request.type) ? ctx.symbol_tick->ask : ctx.symbol_tick->bid;
        }
        RuleValidationResult slip = validate_slippage(
            *slippage, requested_price, request.type, ctx, rules);
        if (!slip.ok) {
            return fail("Invalid slippage: " + slip.message);
        }
    }
    return ok("Trade request is valid");
}

RuleValidationResult validate_credentials(const CredentialsPayload& credentials) {
    if (credentials.login <= 0) {
        return fail("Login must be a positive integer");
    }
    if (credentials.password.empty()) {
        return fail("Password must be a non-empty string");
    }
    if (credentials.server.empty()) {
        return fail("Server must be a non-empty string");
    }
    return ok("Credentials are valid");
}

RuleValidationResult validate_margin(double margin_required, const ValidationContext& ctx) {
    if (!std::isfinite(margin_required)) {
        return fail("Margin must be a number");
    }
    if (margin_required < 0.0) {
        return fail("Margin cannot be negative");
    }
    if (ctx.account == nullptr) {
        return fail("Cannot get account information");
    }
    const double free_margin = ctx.account->MarginFree();
    if (margin_required > free_margin) {
        std::ostringstream oss;
        oss << "Insufficient margin (required: " << margin_required
            << ", available: " << free_margin << ")";
        return fail(oss.str());
    }
    return ok("Sufficient margin available");
}

RuleValidationResult validate_ticket(int64_t ticket) {
    if (ticket <= 0) {
        return fail("Ticket must be positive");
    }
    return ok("Ticket is valid");
}

RuleValidationResult validate_max_orders(
    int open_orders,
    std::optional<int> account_limit,
    const ValidationContext& ctx) {
    if (open_orders < 0) {
        return fail("open_orders must be a non-negative integer");
    }
    int limit = account_limit.value_or(0);
    if (!account_limit.has_value() && ctx.account != nullptr) {
        limit = ctx.account->LimitOrders();
    }
    if (limit > 0 && open_orders >= limit) {
        return fail("Pending Orders limit of " + std::to_string(limit) + " is reached");
    }
    return ok("Order limit not reached");
}

RuleValidationResult validate_symbol_volume(
    double symbol_volume,
    std::optional<double> volume_limit,
    const ValidationContext& ctx) {
    if (!std::isfinite(symbol_volume) || symbol_volume < 0.0) {
        return fail("symbol_volume must be a non-negative number");
    }
    double limit = volume_limit.value_or(0.0);
    if (!volume_limit.has_value()) {
        if (ctx.symbol_info == nullptr) {
            return fail("volume_limit or symbol is required");
        }
        limit = ctx.symbol_info->VolumeLimit();
    }
    if (limit > 0.0 && symbol_volume >= limit) {
        std::ostringstream oss;
        oss << "Symbol Volume limit of " << limit << " is reached";
        return fail(oss.str());
    }
    return ok("Symbol volume within limit");
}

TradeValidationResult open_position_validations(
    const haruquant::MqlTradeRequest& request,
    const haruquant::trading::AccountInfo& account,
    const haruquant::trading::SymbolInfo* symbol_info) {
    ValidationContext ctx{};
    ctx.account = &account;
    ctx.symbol_info = symbol_info;
    ctx.symbol_exists = (symbol_info != nullptr);
    ctx.symbol_visible = true;
    ctx.symbol_select_ok = true;
    if (symbol_info != nullptr) {
        ctx.symbol_tick = SymbolTickData{symbol_info->Bid(), symbol_info->Ask()};
    }
    ValidationRules rules{};
    const auto* state = account.GetState();

    RuleValidationResult symbol_ok = validate_symbol(request.symbol, ctx);
    if (!symbol_ok.ok) {
        return fail_trade(10013, symbol_ok.message);
    }

    RuleValidationResult type_ok = validate_order_type(request.type);
    if (!type_ok.ok) {
        return fail_trade(10013, type_ok.message);
    }

    RuleValidationResult vol_ok = validate_volume(request.volume, ctx, rules);
    if (!vol_ok.ok) {
        return fail_trade(10014, vol_ok.message);
    }

    TradeValidationResult out = validate_action_type(request.action, request.type);
    if (!out.ok) {
        return out;
    }

    const double bid = (symbol_info != nullptr) ? symbol_info->Bid() : 0.0;
    const double ask = (symbol_info != nullptr) ? symbol_info->Ask() : 0.0;
    out = validate_submission_inputs(request.symbol, request.volume, symbol_info, bid, ask);
    if (!out.ok) {
        return out;
    }

    if (request.price > 0.0) {
        RuleValidationResult price_ok = validate_price(request.price, ctx, rules);
        if (!price_ok.ok) {
            return fail_trade(10015, price_ok.message);
        }
    }

    if (request.deviation > 0) {
        double requested_price = request.price;
        if (!(requested_price > 0.0) && symbol_info != nullptr) {
            requested_price = is_buy_action(request.type) ? symbol_info->Ask() : symbol_info->Bid();
        }
        RuleValidationResult slip_ok = validate_slippage(
            request.deviation, requested_price, request.type, ctx, rules);
        if (!slip_ok.ok) {
            return fail_trade(10015, slip_ok.message);
        }
    }

    if (request.sl > 0.0) {
        RuleValidationResult sl_ok = validate_stop_loss(
            request.sl,
            (request.price > 0.0) ? std::optional<double>(request.price) : std::nullopt,
            request.type,
            ctx,
            rules);
        if (!sl_ok.ok) {
            return fail_trade(10016, sl_ok.message);
        }
    }
    if (request.tp > 0.0) {
        RuleValidationResult tp_ok = validate_take_profit(
            request.tp,
            (request.price > 0.0) ? std::optional<double>(request.price) : std::nullopt,
            request.type,
            ctx,
            rules);
        if (!tp_ok.ok) {
            return fail_trade(10016, tp_ok.message);
        }
    }

    const int open_orders = count_open_pending_orders(state);
    RuleValidationResult max_orders_ok = validate_max_orders(open_orders, account.LimitOrders(), ctx);
    if (!max_orders_ok.ok) {
        return fail_trade(10033, max_orders_ok.message);
    }
    const double symbol_volume = symbol_open_volume(state, request.symbol);
    RuleValidationResult symbol_volume_ok = validate_symbol_volume(symbol_volume, std::nullopt, ctx);
    if (!symbol_volume_ok.ok) {
        return fail_trade(10034, symbol_volume_ok.message);
    }

    out = validate_trade_request(request, account, symbol_info);
    if (!out.ok) {
        return out;
    }

    RuleValidationResult margin_ok = validate_margin(out.required_margin, ctx);
    if (!margin_ok.ok) {
        return fail_trade(10019, margin_ok.message);
    }
    return out;
}

TradeValidationResult modify_position_validations(
    const std::string& symbol,
    long ticket,
    const haruquant::core::BacktestState* state) {
    const bool has_ticket = ticket > 0;
    const bool has_symbol = !symbol.empty();
    if (!has_ticket && !has_symbol) {
        return fail_trade(10013, "Provide symbol or ticket to modify position");
    }

    if (has_ticket) {
        RuleValidationResult ticket_ok = validate_ticket(ticket);
        if (!ticket_ok.ok) {
            return fail_trade(10013, ticket_ok.message);
        }
    }

    if (state == nullptr) {
        return fail_trade(10013, "Missing backtest state");
    }

    bool found = false;
    std::string found_symbol{};
    if (has_symbol) {
        found = state->trading_positions.find(symbol) != state->trading_positions.end();
        if (found) {
            found_symbol = symbol;
        }
    } else {
        const std::string ticket_str = std::to_string(ticket);
        for (const auto& kv : state->trading_positions) {
            auto it = kv.second.find("ticket");
            if (it != kv.second.end() && it->second == ticket_str) {
                found = true;
                found_symbol = kv.first;
                break;
            }
        }
    }
    if (!found) {
        return fail_trade(10036, "Position not found");
    }
    if (has_ticket && has_symbol && !found_symbol.empty() && found_symbol != symbol) {
        return fail_trade(10013, "Ticket does not belong to the provided symbol");
    }
    return TradeValidationResult{};
}

TradeValidationResult open_pending_order_validations(
    const haruquant::MqlTradeRequest& request,
    const haruquant::trading::AccountInfo& account,
    const haruquant::trading::SymbolInfo* symbol_info) {
    ValidationContext ctx{};
    ctx.account = &account;
    ctx.symbol_info = symbol_info;
    ctx.symbol_exists = (symbol_info != nullptr);
    ctx.symbol_visible = true;
    ctx.symbol_select_ok = true;
    if (symbol_info != nullptr) {
        ctx.symbol_tick = SymbolTickData{symbol_info->Bid(), symbol_info->Ask()};
    }
    ValidationRules rules{};
    const auto* state = account.GetState();

    RuleValidationResult symbol_ok = validate_symbol(request.symbol, ctx);
    if (!symbol_ok.ok) {
        return fail_trade(10013, symbol_ok.message);
    }

    RuleValidationResult type_ok = validate_order_type(request.type);
    if (!type_ok.ok) {
        return fail_trade(10013, type_ok.message);
    }

    RuleValidationResult volume_ok = validate_volume(request.volume, ctx, rules);
    if (!volume_ok.ok) {
        return fail_trade(10014, volume_ok.message);
    }

    TradeValidationResult out = validate_action_type(
        static_cast<int>(haruquant::ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_PENDING),
        request.type);
    if (!out.ok) {
        return out;
    }

    const double bid = (symbol_info != nullptr) ? symbol_info->Bid() : 0.0;
    const double ask = (symbol_info != nullptr) ? symbol_info->Ask() : 0.0;
    out = validate_submission_inputs(request.symbol, request.volume, symbol_info, bid, ask);
    if (!out.ok) {
        return out;
    }

    RuleValidationResult price_ok = validate_price(request.price, ctx, rules);
    if (!price_ok.ok) {
        return fail_trade(10015, price_ok.message);
    }

    if (symbol_info != nullptr) {
        const double bid_px = symbol_info->Bid();
        const double ask_px = symbol_info->Ask();
        const int t = request.type;
        if (t == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT) &&
            request.price >= ask_px) {
            return fail_trade(10015, "BUY_LIMIT price must be below ask");
        }
        if (t == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_LIMIT) &&
            request.price <= bid_px) {
            return fail_trade(10015, "SELL_LIMIT price must be above bid");
        }
        if (t == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP) &&
            request.price <= ask_px) {
            return fail_trade(10015, "BUY_STOP price must be above ask");
        }
        if (t == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP) &&
            request.price >= bid_px) {
            return fail_trade(10015, "SELL_STOP price must be below bid");
        }
        if (t == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP_LIMIT) &&
            request.price <= ask_px) {
            return fail_trade(10015, "BUY_STOP_LIMIT trigger must be above ask");
        }
        if (t == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP_LIMIT) &&
            request.price >= bid_px) {
            return fail_trade(10015, "SELL_STOP_LIMIT trigger must be below bid");
        }
    }

    if (request.sl > 0.0) {
        RuleValidationResult sl_ok = validate_stop_loss(
            request.sl, request.price, request.type, ctx, rules);
        if (!sl_ok.ok) {
            return fail_trade(10016, sl_ok.message);
        }
    }
    if (request.tp > 0.0) {
        RuleValidationResult tp_ok = validate_take_profit(
            request.tp, request.price, request.type, ctx, rules);
        if (!tp_ok.ok) {
            return fail_trade(10016, tp_ok.message);
        }
    }
    if (request.expiration > 0) {
        RuleValidationResult exp_ok = validate_expiration_unix(
            static_cast<int64_t>(request.expiration),
            now_unix_sec());
        if (!exp_ok.ok) {
            return fail_trade(10022, exp_ok.message);
        }
    }

    const int open_orders = count_open_pending_orders(state);
    RuleValidationResult max_orders_ok = validate_max_orders(open_orders, account.LimitOrders(), ctx);
    if (!max_orders_ok.ok) {
        return fail_trade(10033, max_orders_ok.message);
    }
    const double symbol_volume = symbol_open_volume(state, request.symbol);
    RuleValidationResult symbol_volume_ok = validate_symbol_volume(symbol_volume, std::nullopt, ctx);
    if (!symbol_volume_ok.ok) {
        return fail_trade(10034, symbol_volume_ok.message);
    }

    out = validate_trade_request(request, account, symbol_info);
    if (!out.ok) {
        return out;
    }
    RuleValidationResult margin_ok = validate_margin(out.required_margin, ctx);
    if (!margin_ok.ok) {
        return fail_trade(10019, margin_ok.message);
    }
    return out;
}

TradeValidationResult modify_pending_order_validations(
    long ticket,
    double price,
    double sl,
    double tp,
    long expiration,
    const haruquant::core::BacktestState* state,
    const haruquant::trading::SymbolInfo* symbol_info) {
    RuleValidationResult ticket_ok = validate_ticket(ticket);
    if (!ticket_ok.ok) {
        return fail_trade(10013, ticket_ok.message);
    }
    if (state == nullptr) {
        return fail_trade(10013, "Missing backtest state");
    }
    const auto* order_row = find_order_row(state, ticket);
    if (order_row == nullptr) {
        return fail_trade(10035, "Order not found");
    }

    int order_type = parse_int_or(
        (order_row->count("type") > 0) ? order_row->at("type") : "",
        static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT));
    RuleValidationResult type_ok = validate_order_type(order_type);
    if (!type_ok.ok) {
        return fail_trade(10013, type_ok.message);
    }
    double entry_price = parse_double_or(
        (order_row->count("price") > 0) ? order_row->at("price") : "", 0.0);
    if (!(entry_price > 0.0)) {
        entry_price = parse_double_or(
            (order_row->count("limit_price") > 0) ? order_row->at("limit_price") : "", 0.0);
    }
    if (price > 0.0) {
        entry_price = price;
    }

    if (symbol_info != nullptr) {
        ValidationContext ctx{};
        ctx.symbol_info = symbol_info;
        ctx.symbol_exists = true;
        ctx.symbol_visible = true;
        ctx.symbol_select_ok = true;
        ctx.symbol_tick = SymbolTickData{symbol_info->Bid(), symbol_info->Ask()};
        ValidationRules rules{};
        if (price > 0.0) {
            RuleValidationResult px = validate_price(price, ctx, rules);
            if (!px.ok) {
                return fail_trade(10015, px.message);
            }

            const double bid_px = symbol_info->Bid();
            const double ask_px = symbol_info->Ask();
            if (order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT) &&
                price >= ask_px) {
                return fail_trade(10015, "BUY_LIMIT price must be below ask");
            }
            if (order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_LIMIT) &&
                price <= bid_px) {
                return fail_trade(10015, "SELL_LIMIT price must be above bid");
            }
            if (order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP) &&
                price <= ask_px) {
                return fail_trade(10015, "BUY_STOP price must be above ask");
            }
            if (order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP) &&
                price >= bid_px) {
                return fail_trade(10015, "SELL_STOP price must be below bid");
            }
            if (order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP_LIMIT) &&
                price <= ask_px) {
                return fail_trade(10015, "BUY_STOP_LIMIT trigger must be above ask");
            }
            if (order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP_LIMIT) &&
                price >= bid_px) {
                return fail_trade(10015, "SELL_STOP_LIMIT trigger must be below bid");
            }
        }

        const std::optional<double> entry_opt = (entry_price > 0.0)
            ? std::optional<double>(entry_price)
            : std::nullopt;
        const std::optional<int> type_opt = std::optional<int>(order_type);

        if (sl > 0.0) {
            RuleValidationResult sl_ok = validate_stop_loss(
                sl,
                entry_opt,
                type_opt,
                ctx,
                rules);
            if (!sl_ok.ok) {
                return fail_trade(10016, sl_ok.message);
            }
        }
        if (tp > 0.0) {
            RuleValidationResult tp_ok = validate_take_profit(
                tp,
                entry_opt,
                type_opt,
                ctx,
                rules);
            if (!tp_ok.ok) {
                return fail_trade(10016, tp_ok.message);
            }
        }
    }
    if (expiration > 0) {
        RuleValidationResult exp_ok = validate_expiration_unix(
            static_cast<int64_t>(expiration),
            now_unix_sec());
        if (!exp_ok.ok) {
            return fail_trade(10022, exp_ok.message);
        }
    }
    return TradeValidationResult{};
}

TradeValidationResult delete_pending_order_validations(
    long ticket,
    const haruquant::core::BacktestState* state) {
    RuleValidationResult ticket_ok = validate_ticket(ticket);
    if (!ticket_ok.ok) {
        return fail_trade(10013, ticket_ok.message);
    }
    if (state == nullptr) {
        return fail_trade(10013, "Missing backtest state");
    }
    const auto* row = find_order_row(state, ticket);
    if (row == nullptr) {
        return fail_trade(10035, "Order not found");
    }
    return TradeValidationResult{};
}

TradeValidationResult close_position_validations(
    const std::string& symbol,
    long ticket,
    const haruquant::core::BacktestState* state) {
    return modify_position_validations(symbol, ticket, state);
}

TradeValidationResult close_partial_position_validations(
    const std::string& symbol,
    long ticket,
    double volume,
    const haruquant::core::BacktestState* state) {
    TradeValidationResult base = close_position_validations(symbol, ticket, state);
    if (!base.ok) {
        return base;
    }
    if (!(volume > 0.0)) {
        return fail_trade(10014, "Volume must be > 0 for partial close");
    }
    if (state == nullptr) {
        return fail_trade(10013, "Missing backtest state");
    }

    double position_volume = 0.0;
    bool has_volume = false;
    const std::string ticket_str = std::to_string(ticket);
    if (!symbol.empty()) {
        auto it = state->trading_positions.find(symbol);
        if (it != state->trading_positions.end()) {
            auto vit = it->second.find("volume");
            if (vit != it->second.end()) {
                try {
                    position_volume = std::stod(vit->second);
                    has_volume = true;
                } catch (...) {
                }
            }
        }
    }
    if (!has_volume && ticket > 0) {
        for (const auto& kv : state->trading_positions) {
            auto tit = kv.second.find("ticket");
            if (tit == kv.second.end() || tit->second != ticket_str) {
                continue;
            }
            auto vit = kv.second.find("volume");
            if (vit != kv.second.end()) {
                try {
                    position_volume = std::stod(vit->second);
                    has_volume = true;
                } catch (...) {
                }
            }
            break;
        }
    }
    if (has_volume && volume - position_volume > 1e-12) {
        return fail_trade(10014, "Partial close volume exceeds position volume");
    }

    std::string resolved_symbol = symbol;
    if (resolved_symbol.empty() && ticket > 0) {
        for (const auto& kv : state->trading_positions) {
            auto tit = kv.second.find("ticket");
            if (tit != kv.second.end() && tit->second == ticket_str) {
                resolved_symbol = kv.first;
                auto sit = kv.second.find("symbol");
                if (sit != kv.second.end() && !sit->second.empty()) {
                    resolved_symbol = sit->second;
                }
                break;
            }
        }
    }

    const auto* sym_row = find_symbol_row(state, resolved_symbol);
    if (sym_row != nullptr) {
        const double min_vol = parse_double_or(
            (sym_row->count("volume_min") > 0) ? sym_row->at("volume_min") : "", 0.0);
        const double max_vol = parse_double_or(
            (sym_row->count("volume_max") > 0) ? sym_row->at("volume_max") : "", 0.0);
        const double step = parse_double_or(
            (sym_row->count("volume_step") > 0) ? sym_row->at("volume_step") : "", 0.0);

        if (min_vol > 0.0 && volume < min_vol) {
            return fail_trade(10014, "Partial close volume below minimum");
        }
        if (max_vol > 0.0 && volume > max_vol) {
            return fail_trade(10014, "Partial close volume above maximum");
        }
        if (step > 0.0) {
            if (min_vol > 0.0) {
                const double align_base = min_vol;
                const double steps = std::round((volume - align_base) / step);
                const double aligned = align_base + (steps * step);
                if (std::abs(volume - aligned) > 1e-8) {
                    return fail_trade(10014, "Partial close volume not aligned with symbol step");
                }
            }
        }
    }
    return TradeValidationResult{};
}

}  // namespace haruquant::util

