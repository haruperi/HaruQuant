/**
FILE: src\util\validators.cpp

PURPOSE:
Defines validators.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Classes/Types used in this file:
  RuleValidationResult, TradeValidationResult, ValidationContext, ValidationRules, CredentialsPayload.
- File-local helper methods (anonymous namespace):
  ok(const std::string& message = "OK") -> RuleValidationResult
  fail(const std::string& message) -> RuleValidationResult
  fail_trade(int retcode, const std::string& comment) -> TradeValidationResult
  to_upper(std::string value) -> std::string
  is_market_order_type(int type) -> bool
  is_pending_order_type(int type) -> bool
  is_buy_action(int order_type) -> bool
  is_sell_action(int order_type) -> bool
  trim_copy(const std::string& input) -> std::string
  step_decimals(double step) -> int
  is_plain_decimal_number(const std::string& s) -> bool
  calculate_margin(const haruquant::AccountInfo& account, const haruquant::SymbolInfo& symbol_info, double volume, double price) -> double
  now_unix_sec() -> int64_t
  validate_price_relationship(double level_price, double entry_price, int order_type, bool is_stop_loss) -> RuleValidationResult
  validate_stop_freeze_distance(double level_price, double entry_price, int order_type, bool is_stop_loss, const haruquant::SymbolInfo& symbol_info, const std::string& level_name) -> RuleValidationResult
  parse_order_type_token(const std::string& order_type) -> std::optional<int>
- Public validation/trade-check methods implemented:
  validate_action_type(int action, int type) -> TradeValidationResult
  validate_submission_inputs(const std::string& symbol, double volume, double bid, double ask, const haruquant::SymbolInfo* symbol_info, const ValidationRules& rules) -> TradeValidationResult
  validate_trade_request(const haruquant::MqlTradeRequest& request, const haruquant::AccountInfo& account, const haruquant::SymbolInfo* symbol_info) -> TradeValidationResult
  validate_symbol(const std::string& symbol, const ValidationContext& ctx) -> RuleValidationResult
  validate_volume_basic(double volume) -> RuleValidationResult
  validate_volume_symbol_limits(double volume, const haruquant::SymbolInfo& symbol_info) -> RuleValidationResult
  validate_volume_step(double volume, const haruquant::SymbolInfo& symbol_info) -> RuleValidationResult
  validate_volume_format(const std::string& volume_text, const ValidationContext& ctx, const ValidationRules& rules) -> RuleValidationResult
  validate_price_format(const std::string& price_text, const ValidationContext& ctx) -> RuleValidationResult
  validate_volume(double volume, const ValidationContext& ctx, const ValidationRules& rules) -> RuleValidationResult
  validate_price(double price, const ValidationContext& ctx, const ValidationRules& rules) -> RuleValidationResult
  validate_order_type(int order_type) -> RuleValidationResult
  validate_order_type(const std::string& order_type) -> RuleValidationResult
  validate_magic(int magic, const ValidationRules& rules) -> RuleValidationResult
  validate_slippage(double slippage_points, int order_type, double requested_price, const ValidationContext& ctx) -> RuleValidationResult
  validate_expiration_unix(int64_t expiration_unix_sec, int64_t now_unix_sec) -> RuleValidationResult
  validate_expiration_mode(const std::string& expiration_mode) -> RuleValidationResult
  validate_timeframe(const std::string& timeframe) -> RuleValidationResult
  validate_timeframe(int timeframe) -> RuleValidationResult
  validate_date_range_unix(int64_t start_unix_sec, int64_t end_unix_sec) -> RuleValidationResult
  validate_stop_loss(double stop_loss, double open_price, int order_type, const ValidationContext& ctx) -> RuleValidationResult
  validate_take_profit(double take_profit, double open_price, int order_type, const ValidationContext& ctx) -> RuleValidationResult
  validate_trade_request_payload(const TradeRequestPayload& payload, const ValidationContext& ctx, const ValidationRules& rules) -> RuleValidationResult
  validate_credentials(const CredentialsPayload& credentials) -> RuleValidationResult
  validate_margin(double margin_required, const ValidationContext& ctx) -> RuleValidationResult
  validate_ticket(int64_t ticket) -> RuleValidationResult
  validate_max_orders(int open_orders, std::optional<int> account_limit, const ValidationContext& ctx) -> RuleValidationResult
  validate_symbol_volume(double symbol_volume, std::optional<double> volume_limit, const ValidationContext& ctx) -> RuleValidationResult

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
    const double leverage = std::max(1, account.Leverage());
    const double notional = volume * symbol_info.ContractSize() * price;
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

    const int32_t stops_level = symbol_info.StopsLevel();
    const int32_t freeze_level = symbol_info.FreezeLevel();
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
    out.margin_free = account.FreeMargin();
    out.margin_level = account.MarginLevel();

    if (symbol_info == nullptr) {
        return fail_trade(10013, "Unknown symbol");
    }

    if (request.volume <= 0.0) {
        return fail_trade(10014, "Invalid volume");
    }

    if (request.volume < symbol_info->LotsMin() || request.volume > symbol_info->LotsMax()) {
        return fail_trade(10014, "Volume out of range");
    }

    if (request.action == haruquant::ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_DEAL ||
        request.action == haruquant::ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_PENDING) {
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
    if (volume < symbol_info.LotsMin()) {
        std::ostringstream oss;
        oss << "Volume " << volume << " below minimum " << symbol_info.LotsMin();
        return fail(oss.str());
    }
    if (volume > symbol_info.LotsMax()) {
        std::ostringstream oss;
        oss << "Volume " << volume << " above maximum " << symbol_info.LotsMax();
        return fail(oss.str());
    }
    return ok();
}

RuleValidationResult validate_volume_step(double volume, const haruquant::SymbolInfo& symbol_info) {
    const double step = symbol_info.LotsStep();
    if (step <= 0.0) {
        return ok();
    }
    const double vol_min = symbol_info.LotsMin();
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
    const double step = (ctx.symbol_info != nullptr && ctx.symbol_info->LotsStep() > 0.0)
        ? ctx.symbol_info->LotsStep()
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
            const double tick_size = ctx.symbol_info->TickSize();
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
        const double tick_size = ctx.symbol_info->TickSize();
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
        const double requested_price = request.price.value_or(0.0);
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
    const double free_margin = ctx.account->FreeMargin();
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
        limit = ctx.symbol_info->LotsLimit();
    }
    if (limit > 0.0 && symbol_volume >= limit) {
        std::ostringstream oss;
        oss << "Symbol Volume limit of " << limit << " is reached";
        return fail(oss.str());
    }
    return ok("Symbol volume within limit");
}

}  // namespace haruquant::util

