/**
FILE: tests\test_validators.cpp

PURPOSE:
Defines test_validators.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_validators.cpp.
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
#include <gtest/gtest.h>

#include "util/validators.hpp"

using namespace haruquant;
using namespace haruquant::util;

namespace {

SymbolInfo make_symbol() {
    SymbolInfo symbol;
    symbol.Name("EURUSD");
    symbol.SetDigits(5);
    symbol.SetPoint(0.00001);
    symbol.SetTickSize(0.00001);
    symbol.SetContractSize(100000.0);
    symbol.SetVolumeMin(0.01);
    symbol.SetVolumeMax(100.0);
    symbol.SetVolumeStep(0.01);
    symbol.SetVolumeLimit(50.0);
    symbol.SetStopsLevel(10);
    symbol.SetFreezeLevel(0);
    symbol.UpdatePrice(1.10000, 1.10020, 0);
    return symbol;
}

ValidationContext make_context(
    const SymbolInfo* symbol = nullptr,
    std::optional<haruquant::sim::SymbolTickData> tick = std::nullopt) {
    ValidationContext ctx;
    ctx.symbol_info = symbol;
    ctx.symbol_exists = true;
    ctx.symbol_visible = true;
    ctx.symbol_select_ok = true;
    ctx.symbol_tick = tick;
    return ctx;
}

}  // namespace

TEST(ValidatorsTest, SymbolValidationRejectsMissingSymbol) {
    ValidationContext ctx{};
    ctx.symbol_exists = false;

    const RuleValidationResult result = validate_symbol("EURUSD", ctx);
    EXPECT_FALSE(result.ok);
}

TEST(ValidatorsTest, VolumeFormatRejectsTooManyDecimalsForStep) {
    const SymbolInfo symbol = make_symbol();
    const ValidationContext ctx = make_context(&symbol);
    const ValidationRules rules{};

    const RuleValidationResult result = validate_volume_format("0.1000", ctx, rules);
    EXPECT_FALSE(result.ok);
}

TEST(ValidatorsTest, VolumeFormatAcceptsStepAlignedPrecision) {
    const SymbolInfo symbol = make_symbol();
    const ValidationContext ctx = make_context(&symbol);
    const ValidationRules rules{};

    const RuleValidationResult result = validate_volume_format("0.10", ctx, rules);
    EXPECT_TRUE(result.ok);
}

TEST(ValidatorsTest, PriceFormatRejectsPrecisionBeyondDigits) {
    const SymbolInfo symbol = make_symbol();
    const ValidationContext ctx = make_context(&symbol);

    const RuleValidationResult result = validate_price_format("1.10020000", ctx);
    EXPECT_FALSE(result.ok);
}

TEST(ValidatorsTest, SlippageValidationUsesAskForBuy) {
    const SymbolInfo symbol = make_symbol();
    haruquant::sim::SymbolTickData tick;
    tick.bid = 1.10000;
    tick.ask = 1.10020;
    const ValidationContext ctx = make_context(&symbol, tick);
    const ValidationRules rules{};

    const int buy = static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_BUY);
    const RuleValidationResult result = validate_slippage(10, 1.10029, buy, ctx, rules);
    EXPECT_TRUE(result.ok);
}

TEST(ValidatorsTest, SlippageValidationUsesBidForSell) {
    const SymbolInfo symbol = make_symbol();
    haruquant::sim::SymbolTickData tick;
    tick.bid = 1.10000;
    tick.ask = 1.10020;
    const ValidationContext ctx = make_context(&symbol, tick);
    const ValidationRules rules{};

    const int sell = static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_SELL);
    const RuleValidationResult result = validate_slippage(10, 1.09991, sell, ctx, rules);
    EXPECT_TRUE(result.ok);
}

TEST(ValidatorsTest, SlippageValidationRejectsWhenOutsideAllowedRange) {
    const SymbolInfo symbol = make_symbol();
    haruquant::sim::SymbolTickData tick;
    tick.bid = 1.10000;
    tick.ask = 1.10020;
    const ValidationContext ctx = make_context(&symbol, tick);
    const ValidationRules rules{};

    const int buy = static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_BUY);
    const RuleValidationResult result = validate_slippage(10, 1.10040, buy, ctx, rules);
    EXPECT_FALSE(result.ok);
}

TEST(ValidatorsTest, SlippageValidationRejectsWhenTickMissing) {
    const SymbolInfo symbol = make_symbol();
    const ValidationContext ctx = make_context(&symbol, std::nullopt);
    const ValidationRules rules{};

    const int buy = static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_BUY);
    const RuleValidationResult result = validate_slippage(10, 1.10020, buy, ctx, rules);
    EXPECT_FALSE(result.ok);
}

TEST(ValidatorsTest, TradeRequestPayloadValidatesWithSlippageField) {
    const SymbolInfo symbol = make_symbol();
    haruquant::sim::SymbolTickData tick;
    tick.bid = 1.10000;
    tick.ask = 1.10020;
    const ValidationContext ctx = make_context(&symbol, tick);
    const ValidationRules rules{};

    TradeRequestPayload request;
    request.action = 1;
    request.symbol = "EURUSD";
    request.volume = 0.10;
    request.type = static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_BUY);
    request.price = 1.10020;
    request.sl = 1.09900;
    request.tp = 1.10150;
    request.magic = 123456;
    request.slippage = 10;

    const RuleValidationResult result = validate_trade_request_payload(request, ctx, rules);
    EXPECT_TRUE(result.ok);
}

TEST(ValidatorsTest, TradeRequestPayloadSupportsLegacyDeviationField) {
    const SymbolInfo symbol = make_symbol();
    haruquant::sim::SymbolTickData tick;
    tick.bid = 1.10000;
    tick.ask = 1.10020;
    const ValidationContext ctx = make_context(&symbol, tick);
    const ValidationRules rules{};

    TradeRequestPayload request;
    request.action = 1;
    request.symbol = "EURUSD";
    request.volume = 0.10;
    request.type = static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_BUY);
    request.price = 1.10020;
    request.sl = 1.09900;
    request.tp = 1.10150;
    request.magic = 123456;
    request.deviation = 10;

    const RuleValidationResult result = validate_trade_request_payload(request, ctx, rules);
    EXPECT_TRUE(result.ok);
}

TEST(ValidatorsTest, TradeRequestPayloadRejectsWhenSlippageOutOfRange) {
    const SymbolInfo symbol = make_symbol();
    haruquant::sim::SymbolTickData tick;
    tick.bid = 1.10000;
    tick.ask = 1.10020;
    const ValidationContext ctx = make_context(&symbol, tick);
    const ValidationRules rules{};

    TradeRequestPayload request;
    request.action = 1;
    request.symbol = "EURUSD";
    request.volume = 0.10;
    request.type = static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_BUY);
    request.price = 1.10060;
    request.slippage = 10;

    const RuleValidationResult result = validate_trade_request_payload(request, ctx, rules);
    EXPECT_FALSE(result.ok);
}

TEST(ValidatorsTest, ActionTypeValidationCoversSupportedAndUnsupportedActions) {
    const int buy = static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_BUY);
    const int buy_limit = static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT);

    EXPECT_TRUE(validate_action_type(1, buy).ok);
    EXPECT_TRUE(validate_action_type(5, buy_limit).ok);
    EXPECT_TRUE(validate_action_type(6, buy).ok);
    EXPECT_FALSE(validate_action_type(1, buy_limit).ok);
    EXPECT_FALSE(validate_action_type(99, buy).ok);
}

TEST(ValidatorsTest, SubmissionInputsValidationChecksSymbolVolumeAndQuotes) {
    const SymbolInfo symbol = make_symbol();

    EXPECT_FALSE(validate_submission_inputs("", 0.1, &symbol, 1.0, 1.1).ok);
    EXPECT_FALSE(validate_submission_inputs("EURUSD", 0.0, &symbol, 1.0, 1.1).ok);
    EXPECT_FALSE(validate_submission_inputs("EURUSD", 0.1, nullptr, 1.0, 1.1).ok);
    EXPECT_FALSE(validate_submission_inputs("EURUSD", 0.1, &symbol, 0.0, 1.1).ok);
    EXPECT_TRUE(validate_submission_inputs("EURUSD", 0.1, &symbol, 1.0, 1.1).ok);
}

TEST(ValidatorsTest, TradeRequestValidationChecksVolumeAndMargin) {
    SymbolInfo symbol = make_symbol();
    AccountInfo account(1000.0, "USD", 100);
    account.SetMargin(0.0);
    account.SetFreeMargin(1000.0);
    account.SetEquity(1000.0);

    MqlTradeRequest req;
    req.action = ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_DEAL;
    req.type = ENUM_ORDER_TYPE::ORDER_TYPE_BUY;
    req.symbol = "EURUSD";
    req.volume = 0.10;
    req.price = 1.10020;

    EXPECT_FALSE(validate_trade_request(req, account, nullptr).ok);

    req.volume = 0.0;
    EXPECT_FALSE(validate_trade_request(req, account, &symbol).ok);

    req.volume = 1000.0;
    EXPECT_FALSE(validate_trade_request(req, account, &symbol).ok);

    req.volume = 50.0;
    account.SetFreeMargin(10.0);
    account.SetEquity(10.0);
    EXPECT_FALSE(validate_trade_request(req, account, &symbol).ok);

    req.volume = 0.10;
    account.SetFreeMargin(1000.0);
    account.SetEquity(1000.0);
    EXPECT_TRUE(validate_trade_request(req, account, &symbol).ok);
}

TEST(ValidatorsTest, SymbolValidationChecksSelectionState) {
    const SymbolInfo symbol = make_symbol();
    ValidationContext ctx = make_context(&symbol);
    ctx.symbol_exists = true;
    ctx.symbol_visible = false;
    ctx.symbol_select_ok = false;
    EXPECT_FALSE(validate_symbol("EURUSD", ctx).ok);
}

TEST(ValidatorsTest, VolumeValidationCoversBasicRangeAndStep) {
    SymbolInfo symbol = make_symbol();
    ValidationContext ctx = make_context(&symbol);
    ValidationRules rules;
    rules.volume_min = 0.01;
    rules.volume_max = 1.00;
    rules.volume_step = 0.01;

    EXPECT_FALSE(validate_volume(-1.0, ctx, rules).ok);
    EXPECT_FALSE(validate_volume(0.005, ctx, rules).ok);
    EXPECT_FALSE(validate_volume(0.105, ctx, rules).ok);

    symbol.SetVolumeStep(0.05);
    ctx = make_context(&symbol);
    EXPECT_FALSE(validate_volume(0.12, ctx, rules).ok);
}

TEST(ValidatorsTest, PriceValidationCoversRangeAndTickAlignment) {
    SymbolInfo symbol = make_symbol();
    symbol.SetTickSize(0.00010);
    ValidationContext ctx = make_context(&symbol);
    ValidationRules rules;
    rules.price_min = 1.0;
    rules.price_max = 2.0;

    EXPECT_FALSE(validate_price(-1.0, ctx, rules).ok);
    EXPECT_FALSE(validate_price(2.5, ctx, rules).ok);
    EXPECT_FALSE(validate_price(1.10025, ctx, rules).ok);
    EXPECT_TRUE(validate_price(1.10020, ctx, rules).ok);
}

TEST(ValidatorsTest, OrderTypeStringAndMagicValidation) {
    EXPECT_TRUE(validate_order_type("BUY").ok);
    EXPECT_FALSE(validate_order_type("INVALID").ok);
    EXPECT_TRUE(validate_order_type(static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_SELL)).ok);
    EXPECT_FALSE(validate_order_type(999).ok);

    ValidationRules rules;
    rules.magic_min = 10;
    rules.magic_max = 20;
    EXPECT_TRUE(validate_magic(15, rules).ok);
    EXPECT_FALSE(validate_magic(9, rules).ok);
}

TEST(ValidatorsTest, SlippageValidationRejectsInvalidInputs) {
    const SymbolInfo symbol = make_symbol();
    haruquant::sim::SymbolTickData tick;
    tick.bid = 1.10000;
    tick.ask = 1.10020;
    const ValidationContext ctx = make_context(&symbol, tick);
    const ValidationRules rules{};

    EXPECT_FALSE(validate_slippage(-1, 1.1002, static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_BUY), ctx, rules).ok);
    EXPECT_FALSE(validate_slippage(10, -1.0, static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_BUY), ctx, rules).ok);
    EXPECT_FALSE(validate_slippage(10, 1.1002, 999, ctx, rules).ok);
}

TEST(ValidatorsTest, ExpirationAndTimeframeValidation) {
    const int64_t now = 1'700'000'000;
    EXPECT_FALSE(validate_expiration_unix(now - 1, now).ok);
    EXPECT_FALSE(validate_expiration_unix(now + (366LL * 24LL * 60LL * 60LL), now).ok);
    EXPECT_TRUE(validate_expiration_unix(now + 60, now).ok);

    EXPECT_TRUE(validate_expiration_mode("GTC").ok);
    EXPECT_FALSE(validate_expiration_mode("WEEKLY").ok);
    EXPECT_TRUE(validate_timeframe("M15").ok);
    EXPECT_FALSE(validate_timeframe("M2").ok);
    EXPECT_TRUE(validate_timeframe(16385).ok);
    EXPECT_FALSE(validate_timeframe(2).ok);
}

TEST(ValidatorsTest, DateRangeValidation) {
    const int64_t now = 1'700'000'000;
    const int64_t too_old = now - (3651LL * 24LL * 60LL * 60LL);
    EXPECT_FALSE(validate_date_range_unix(too_old, std::nullopt, now).ok);
    EXPECT_FALSE(validate_date_range_unix(now - 1000, now - 2000, now).ok);
    EXPECT_FALSE(validate_date_range_unix(now - 1000, now + 1, now).ok);
    EXPECT_TRUE(validate_date_range_unix(now - 1000, now - 500, now).ok);
}

TEST(ValidatorsTest, StopLossAndTakeProfitValidationRelationshipAndDistance) {
    SymbolInfo symbol = make_symbol();
    symbol.SetStopsLevel(10);
    symbol.SetFreezeLevel(20);
    ValidationContext ctx = make_context(&symbol);
    ValidationRules rules{};
    const double entry = 1.10020;
    const int buy = static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_BUY);
    const int sell = static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_SELL);

    EXPECT_FALSE(validate_stop_loss(1.10030, entry, buy, ctx, rules).ok);
    EXPECT_FALSE(validate_take_profit(1.10010, entry, buy, ctx, rules).ok);
    EXPECT_FALSE(validate_stop_loss(1.10005, entry, buy, ctx, rules).ok);
    EXPECT_FALSE(validate_take_profit(1.10035, entry, buy, ctx, rules).ok);
    EXPECT_TRUE(validate_stop_loss(1.09900, entry, buy, ctx, rules).ok);
    EXPECT_TRUE(validate_take_profit(1.10150, entry, buy, ctx, rules).ok);
    EXPECT_FALSE(validate_stop_loss(1.10010, entry, sell, ctx, rules).ok);
    EXPECT_FALSE(validate_take_profit(1.10030, entry, sell, ctx, rules).ok);
    EXPECT_FALSE(validate_stop_loss(1.10035, entry, sell, ctx, rules).ok);
    EXPECT_FALSE(validate_take_profit(1.10005, entry, sell, ctx, rules).ok);
    EXPECT_TRUE(validate_stop_loss(1.10100, entry, sell, ctx, rules).ok);
    EXPECT_TRUE(validate_take_profit(1.09900, entry, sell, ctx, rules).ok);

    EXPECT_FALSE(validate_stop_loss(0.0, entry, buy, ctx, rules).ok);
    EXPECT_FALSE(validate_take_profit(0.0, entry, buy, ctx, rules).ok);
}

TEST(ValidatorsTest, CredentialsMarginAndTicketValidation) {
    CredentialsPayload creds;
    creds.login = 123;
    creds.password = "pw";
    creds.server = "demo";
    EXPECT_TRUE(validate_credentials(creds).ok);

    creds.password.clear();
    EXPECT_FALSE(validate_credentials(creds).ok);

    AccountInfo account(1000.0, "USD", 100);
    account.SetFreeMargin(50.0);
    ValidationContext ctx{};
    ctx.account = &account;
    EXPECT_FALSE(validate_margin(-1.0, ctx).ok);
    EXPECT_FALSE(validate_margin(100.0, ctx).ok);
    EXPECT_TRUE(validate_margin(10.0, ctx).ok);
    EXPECT_FALSE(validate_ticket(0).ok);
    EXPECT_TRUE(validate_ticket(1).ok);
}

TEST(ValidatorsTest, MaxOrdersAndSymbolVolumeValidation) {
    AccountInfo account(1000.0, "USD", 100);
    account.SetLimitOrders(2);
    SymbolInfo symbol = make_symbol();
    symbol.SetVolumeLimit(1.0);
    ValidationContext ctx = make_context(&symbol);
    ctx.account = &account;

    EXPECT_FALSE(validate_max_orders(-1, std::nullopt, ctx).ok);
    EXPECT_TRUE(validate_max_orders(1, std::nullopt, ctx).ok);
    EXPECT_FALSE(validate_max_orders(2, std::nullopt, ctx).ok);
    EXPECT_FALSE(validate_max_orders(3, 3, ctx).ok);

    EXPECT_FALSE(validate_symbol_volume(-1.0, std::nullopt, ctx).ok);
    EXPECT_TRUE(validate_symbol_volume(0.5, std::nullopt, ctx).ok);
    EXPECT_FALSE(validate_symbol_volume(1.0, std::nullopt, ctx).ok);

    ValidationContext no_symbol{};
    EXPECT_FALSE(validate_symbol_volume(0.1, std::nullopt, no_symbol).ok);
    EXPECT_TRUE(validate_symbol_volume(0.1, 2.0, no_symbol).ok);
}

