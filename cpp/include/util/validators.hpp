/**
FILE: include\util\validators.hpp

PURPOSE:
Defines validators.hpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in validators.hpp.
- File-local helpers supporting the main public or internal entry points.

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
#pragma once

#include "trading/account_info.hpp"
#include "trading/symbol_info.hpp"
#include "trading/trade.hpp"

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace haruquant {

using AccountInfo = trading::AccountInfo;
using SymbolInfo = trading::SymbolInfo;

enum class ENUM_ORDER_TYPE : int {
    ORDER_TYPE_BUY = 0,
    ORDER_TYPE_SELL = 1,
    ORDER_TYPE_BUY_LIMIT = 2,
    ORDER_TYPE_SELL_LIMIT = 3,
    ORDER_TYPE_BUY_STOP = 4,
    ORDER_TYPE_SELL_STOP = 5,
    ORDER_TYPE_BUY_STOP_LIMIT = 6,
    ORDER_TYPE_SELL_STOP_LIMIT = 7
};

enum class ENUM_TRADE_REQUEST_ACTIONS : int {
    TRADE_ACTION_DEAL = 1,
    TRADE_ACTION_PENDING = 5,
    TRADE_ACTION_SLTP = 6,
    TRADE_ACTION_MODIFY = 7,
    TRADE_ACTION_REMOVE = 8
};

struct MqlTradeRequest {
    int action{0};
    std::string symbol{};
    double volume{0.0};
    int type{0};
    double price{0.0};
    double sl{0.0};
    double tp{0.0};
};

}  // namespace haruquant

namespace haruquant::util {

struct SymbolTickData {
    double bid{0.0};
    double ask{0.0};
};

struct RuleValidationResult {
    bool ok{true};
    std::string message{"OK"};
};

struct TradeValidationResult {
    bool ok{true};
    int retcode{10009};
    std::string comment{"Request valid"};
    double required_margin{0.0};
    double margin{0.0};
    double margin_free{0.0};
    double margin_level{0.0};
};

struct CredentialsPayload {
    int login{0};
    std::string password{};
    std::string server{};
};

struct TradeRequestPayload {
    int action{0};
    std::string symbol{};
    double volume{0.0};
    int type{0};
    std::optional<double> price{};
    std::optional<double> sl{};
    std::optional<double> tp{};
    std::optional<int> magic{};
    std::optional<int> deviation{};
    std::optional<int> slippage{};
};

struct ValidationRules {
    double volume_min{0.01};
    double volume_max{100.0};
    double volume_step{0.01};
    double price_min{0.0};
    double price_max{1000000.0};
    int deviation_min{0};
    int deviation_max{100};
    int magic_min{0};
    int magic_max{2147483647};
};

struct ValidationContext {
    const haruquant::trading::AccountInfo* account{nullptr};
    const haruquant::trading::SymbolInfo* symbol_info{nullptr};
    std::optional<SymbolTickData> symbol_tick{};
    bool symbol_exists{false};
    bool symbol_visible{true};
    bool symbol_select_ok{true};
};

/**
 * Validate gateway-level action/type compatibility.
 */
TradeValidationResult validate_action_type(int action, int type);

/**
 * Validate gateway-level symbol/volume/quotes presence.
 */
TradeValidationResult validate_submission_inputs(
    const std::string& symbol,
    double volume,
    const haruquant::trading::SymbolInfo* symbol_info,
    double bid,
    double ask);

/**
 * Validate trading constraints shared across execution flows.
 */
TradeValidationResult validate_trade_request(
    const haruquant::MqlTradeRequest& request,
    const haruquant::trading::AccountInfo& account,
    const haruquant::trading::SymbolInfo* symbol_info);

RuleValidationResult validate_symbol(const std::string& symbol, const ValidationContext& ctx);
RuleValidationResult validate_volume_basic(double volume);
RuleValidationResult validate_volume_symbol_limits(double volume, const haruquant::trading::SymbolInfo& symbol_info);
RuleValidationResult validate_volume_step(double volume, const haruquant::trading::SymbolInfo& symbol_info);
RuleValidationResult validate_volume_format(
    const std::string& volume_text,
    const ValidationContext& ctx,
    const ValidationRules& rules);
RuleValidationResult validate_price_format(
    const std::string& price_text,
    const ValidationContext& ctx);
RuleValidationResult validate_volume(double volume, const ValidationContext& ctx, const ValidationRules& rules);
RuleValidationResult validate_price(double price, const ValidationContext& ctx, const ValidationRules& rules);
RuleValidationResult validate_order_type(int order_type);
RuleValidationResult validate_order_type(const std::string& order_type);
RuleValidationResult validate_magic(int magic, const ValidationRules& rules);
RuleValidationResult validate_slippage(
    int slippage_points,
    double requested_price,
    int order_type,
    const ValidationContext& ctx,
    const ValidationRules& rules);
RuleValidationResult validate_expiration_unix(int64_t expiration_unix_sec, int64_t now_unix_sec);
RuleValidationResult validate_expiration_mode(const std::string& expiration_mode);
RuleValidationResult validate_timeframe(const std::string& timeframe);
RuleValidationResult validate_timeframe(int timeframe);
RuleValidationResult validate_date_range_unix(
    int64_t start_unix_sec,
    std::optional<int64_t> end_unix_sec,
    int64_t now_unix_sec);
RuleValidationResult validate_stop_loss(
    double stop_loss,
    std::optional<double> entry_price,
    std::optional<int> order_type,
    const ValidationContext& ctx,
    const ValidationRules& rules);
RuleValidationResult validate_take_profit(
    double take_profit,
    std::optional<double> entry_price,
    std::optional<int> order_type,
    const ValidationContext& ctx,
    const ValidationRules& rules);
RuleValidationResult validate_trade_request_payload(
    const TradeRequestPayload& request,
    const ValidationContext& ctx,
    const ValidationRules& rules);
RuleValidationResult validate_credentials(const CredentialsPayload& credentials);
RuleValidationResult validate_margin(double margin_required, const ValidationContext& ctx);
RuleValidationResult validate_ticket(int64_t ticket);
RuleValidationResult validate_max_orders(
    int open_orders,
    std::optional<int> account_limit,
    const ValidationContext& ctx);
RuleValidationResult validate_symbol_volume(
    double symbol_volume,
    std::optional<double> volume_limit,
    const ValidationContext& ctx);

}  // namespace haruquant::util

