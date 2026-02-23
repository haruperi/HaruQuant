/**
FILE: src\engine\trading.cpp

PURPOSE:
Defines trading.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in trading.cpp.
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
#include "engine/engine.hpp"
#include "util/error.hpp"
#include "util/logger.hpp"
#include "util/validators.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <optional>
#include <sstream>
#include <string>

namespace haruquant::sim {

namespace {
std::string order_type_to_text(int order_type) {
    switch (order_type) {
        case 0: return "BUY";
        case 1: return "SELL";
        case 2: return "BUY_LIMIT";
        case 3: return "SELL_LIMIT";
        case 4: return "BUY_STOP";
        case 5: return "SELL_STOP";
        case 6: return "BUY_STOP_LIMIT";
        case 7: return "SELL_STOP_LIMIT";
        case 8: return "CLOSE_BY";
        default: return std::to_string(order_type);
    }
}
}  // namespace

double calc_margin(
    int trade_calc_mode,
    double volume,
    double price,
    double contract_size,
    double leverage,
    double tick_size,
    double tick_value,
    double margin_initial) {
    const double lv = leverage > 0.0 ? leverage : 1.0;

    switch (trade_calc_mode) {
        case 0:  // FOREX
            return (volume * contract_size) / lv;
        case 1:  // FOREX_NO_LEVERAGE
            return volume * contract_size;
        case 2:  // CFD
            return volume * contract_size * price;
        case 3:  // CFDLEVERAGE
            return (volume * contract_size * price) / lv;
        case 4:  // CFDINDEX
            if (tick_size > 0.0) {
                return volume * contract_size * price * tick_value / tick_size;
            }
            break;
        case 5:  // EXCH_STOCKS
        case 6:  // EXCH_STOCKS_MOEX
            return volume * contract_size * price;
        case 7:  // FUTURES
        case 8:  // EXCH_FUTURES
            return volume * margin_initial;
        default:
            break;
    }

    return (volume * contract_size * price) / lv;
}

double calc_profit(
    int trade_calc_mode,
    int action,
    double volume,
    double price_open,
    double price_close,
    double tick_size,
    double tick_value,
    double contract_size) {
    const double direction = (action == 0) ? 1.0 : -1.0;
    const double price_delta = (price_close - price_open) * direction;

    const bool has_tick_formula = (tick_size > 0.0 && tick_value > 0.0);
    const bool has_contract_formula = (contract_size > 0.0);

    const auto calc_tick = [&]() -> double {
        return has_tick_formula ? ((price_delta * volume * tick_value) / tick_size) : 0.0;
    };
    const auto calc_contract = [&]() -> double {
        return has_contract_formula ? (price_delta * contract_size * volume) : 0.0;
    };

    switch (trade_calc_mode) {
        case 0:  // SYMBOL_CALC_MODE_FOREX
        case 2:  // SYMBOL_CALC_MODE_CFD
        case 3:  // SYMBOL_CALC_MODE_CFDINDEX
        case 4:  // SYMBOL_CALC_MODE_CFDLEVERAGE
        case 5:  // SYMBOL_CALC_MODE_EXCH_STOCKS
        case 8:  // SYMBOL_CALC_MODE_EXCH_BONDS / CFDCRYPTO (fallback without extra bond fields)
            if (has_contract_formula) {
                return calc_contract();
            }
            if (has_tick_formula) {
                return calc_tick();
            }
            return 0.0;
        case 1:  // SYMBOL_CALC_MODE_FUTURES
        case 6:  // SYMBOL_CALC_MODE_EXCH_FUTURES
            if (has_tick_formula) {
                return calc_tick();
            }
            if (has_contract_formula) {
                return calc_contract();
            }
            return 0.0;
        case 7:  // SYMBOL_CALC_MODE_EXCH_OPTIONS
            if (has_tick_formula) {
                return calc_tick();
            }
            if (has_contract_formula) {
                return calc_contract();
            }
            return 0.0;
        default:
            if (has_tick_formula) {
                return calc_tick();
            }
            if (has_contract_formula) {
                return calc_contract();
            }
            return 0.0;
    }
}

PositionTotals AccountMonitor::monitor_positions(
    const TradeSimulator& client,
    const std::string& symbol,
    double bid,
    double ask) const {
    PositionTotals totals;
    if (bid <= 0.0 || ask <= 0.0) {
        return totals;
    }

    const auto positions = client.positions_get(symbol, std::nullopt, std::nullopt);
    for (const auto& pos : positions) {
        const bool is_buy = (static_cast<int>(pos.PositionType()) == 0);
        const int action = is_buy ? 0 : 1;
        const double close_price = is_buy ? bid : ask;

        totals.profit += client.order_calc_profit(
            action,
            symbol,
            pos.Volume(),
            pos.PriceOpen(),
            close_price);
        totals.margin += client.order_calc_margin(
            action,
            symbol,
            pos.Volume(),
            pos.PriceOpen());
        totals.commission += 0.0;
        totals.fee += 0.0;
        totals.swap += pos.Swap();
    }

    return totals;
}

haruquant::AccountInfo AccountMonitor::monitor_account(
    const haruquant::AccountInfo& base,
    const PositionTotals& totals) const {
    haruquant::AccountInfo updated = base;
    const auto margin_fp = static_cast<int64_t>(std::llround(totals.margin * 1'000'000.0));
    const auto profit_fp = static_cast<int64_t>(std::llround(totals.profit * 1'000'000.0));
    updated.SetMargin(margin_fp);
    updated.UpdateEquity(profit_fp);
    return updated;
}

void TradeRecordTracker::reset() {
    open_.clear();
    completed_.clear();
}

bool TradeRecordTracker::has_open(uint64_t ticket) const {
    return open_.find(ticket) != open_.end();
}

void TradeRecordTracker::on_open(
    uint64_t ticket,
    const std::string& symbol,
    bool is_buy,
    double volume,
    double open_price,
    double sl,
    double tp,
    int64_t open_time_msc,
    double initial_risk_usd) {
    if (ticket == 0 || has_open(ticket)) {
        return;
    }

    OpenTradeState state;
    state.record.ticket = ticket;
    state.record.symbol = symbol;
    state.record.is_buy = is_buy;
    state.record.volume = volume;
    state.record.open_price = open_price;
    state.record.stop_loss = sl;
    state.record.take_profit = tp;
    state.record.open_time_msc = open_time_msc;
    state.record.initial_risk_usd = initial_risk_usd;
    open_[ticket] = state;
}

void TradeRecordTracker::on_update(uint64_t ticket, double profit_usd) {
    const auto it = open_.find(ticket);
    if (it == open_.end()) {
        return;
    }

    OpenTradeState& state = it->second;
    state.record.bars_in_trade += 1;
    if (profit_usd > state.mfe_usd) {
        state.mfe_usd = profit_usd;
    }
    if (profit_usd < state.mae_usd) {
        state.mae_usd = profit_usd;
    }
}

bool TradeRecordTracker::on_close(
    uint64_t ticket,
    int64_t close_time_msc,
    double close_price,
    double profit_loss_usd) {
    const auto it = open_.find(ticket);
    if (it == open_.end()) {
        return false;
    }

    TradeRecord record = it->second.record;
    record.close_time_msc = close_time_msc;
    record.close_price = close_price;
    record.time_in_trade_seconds = static_cast<double>(record.close_time_msc - record.open_time_msc) / 1000.0;
    record.profit_loss = profit_loss_usd;
    record.mfe_usd = it->second.mfe_usd;
    record.mae_usd = std::abs(it->second.mae_usd);
    if (record.initial_risk_usd > 0.0) {
        record.r_multiple = record.profit_loss / record.initial_risk_usd;
    }

    completed_.push_back(record);
    open_.erase(it);
    return true;
}

const std::vector<TradeRecord>& TradeRecordTracker::completed_trades() const noexcept {
    return completed_;
}

namespace {

TradeResult invalid_result(const std::string& comment, int retcode = 10013) {
    util::warning("TradeGateway invalid request: " + comment + " (retcode=" + std::to_string(retcode) + ")");
    TradeResult result;
    result.retcode = retcode;
    result.comment = comment;
    return result;
}

MqlTradeRequest to_mql_request(const TradeRequest& request) {
    MqlTradeRequest out;
    out.action = static_cast<ENUM_TRADE_REQUEST_ACTIONS>(request.action);
    out.order = request.order;
    out.symbol = request.symbol;
    out.volume = request.volume;
    out.price = request.price;
    out.stoplimit = request.stoplimit;
    out.sl = request.sl;
    out.tp = request.tp;
    out.type = static_cast<ENUM_ORDER_TYPE>(request.type);
    out.type_time = static_cast<ENUM_ORDER_TYPE_TIME>(request.type_time);
    out.expiration = request.expiration;
    out.comment = request.comment;
    return out;
}

}  // namespace

TradeGateway::TradeGateway(const haruquant::AccountInfo& account)
    : trade_(account.Balance(), account.Currency(), static_cast<uint32_t>(account.Leverage())) {}

void TradeGateway::register_symbol(const haruquant::SymbolInfo& symbol) {
    symbols_[symbol.Name()] = symbol;
    trade_.RegisterSymbol(symbol);
}

TradeResult TradeGateway::order_send(const TradeRequest& request, const SymbolTickData* tick) {
    bool ok = false;
    const util::ValidationRules validation_rules{};
    const auto build_validation_ctx = [&](const haruquant::SymbolInfo* symbol_info, double bid, double ask) {
        util::ValidationContext ctx{};
        ctx.account = &trade_.Account();
        ctx.symbol_info = symbol_info;
        ctx.symbol_exists = (symbol_info != nullptr);
        ctx.symbol_visible = true;
        ctx.symbol_select_ok = true;
        if (tick != nullptr) {
            ctx.symbol_tick = *tick;
        } else {
            SymbolTickData synthetic_tick{};
            synthetic_tick.bid = bid;
            synthetic_tick.ask = ask;
            ctx.symbol_tick = synthetic_tick;
        }
        return ctx;
    };
    const auto is_buy_side = [](int order_type) {
        return order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY) ||
            order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT) ||
            order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP) ||
            order_type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP_LIMIT);
    };
    const auto validate_freeze_for_levels = [&](int order_type,
                                                double bid,
                                                double ask,
                                                std::optional<double> sl,
                                                std::optional<double> tp,
                                                const haruquant::SymbolInfo* symbol_info) -> util::RuleValidationResult {
        if (symbol_info == nullptr) {
            return util::RuleValidationResult{false, "Unknown symbol"};
        }
        const int freeze_level = symbol_info->FreezeLevel();
        if (freeze_level <= 0) {
            return util::RuleValidationResult{true, "OK"};
        }
        const double point = symbol_info->Point();
        if (!(point > 0.0)) {
            return util::RuleValidationResult{false, "Invalid symbol point value"};
        }
        const double freeze_distance = static_cast<double>(freeze_level) * point;
        if (is_buy_side(order_type)) {
            if (sl.has_value() && *sl > 0.0 && (bid - *sl) < freeze_distance) {
                return util::RuleValidationResult{false, "SL inside freeze level from market"};
            }
            if (tp.has_value() && *tp > 0.0 && (*tp - bid) < freeze_distance) {
                return util::RuleValidationResult{false, "TP inside freeze level from market"};
            }
            return util::RuleValidationResult{true, "OK"};
        }
        if (sl.has_value() && *sl > 0.0 && (*sl - ask) < freeze_distance) {
            return util::RuleValidationResult{false, "SL inside freeze level from market"};
        }
        if (tp.has_value() && *tp > 0.0 && (ask - *tp) < freeze_distance) {
            return util::RuleValidationResult{false, "TP inside freeze level from market"};
        }
        return util::RuleValidationResult{true, "OK"};
    };

    // Closing branch (market deal with existing position ticket).
    if (request.action == 1 && request.order != 0) {
        const auto positions = trade_.positions_get(std::nullopt, std::nullopt, request.order);
        if (positions.empty()) {
            return invalid_result("Invalid request: position not found", 10013);
        }
        const auto& pos = positions.front();
        const auto sym_it = symbols_.find(pos.Symbol());
        const haruquant::SymbolInfo* symbol_info = (sym_it == symbols_.end()) ? nullptr : &sym_it->second;
        if (symbol_info == nullptr) {
            return invalid_result("Unknown symbol", 10013);
        }
        const double bid = tick ? tick->bid : symbol_info->Bid();
        const double ask = tick ? tick->ask : symbol_info->Ask();
        if (bid <= 0.0 || ask <= 0.0) {
            return invalid_result("No quotes to process the request", 10021);
        }

        const bool is_buy_position =
            (pos.PositionType() == haruquant::ENUM_POSITION_TYPE::POSITION_TYPE_BUY);
        const int expected_close_type = is_buy_position
            ? static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL)
            : static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY);
        if (request.type != expected_close_type) {
            return invalid_result("Invalid close order type for position side", 10013);
        }

        const double expected_close_price = is_buy_position ? bid : ask;
        if (request.price > 0.0) {
            const double tolerance = symbol_info->Point() > 0.0 ? (symbol_info->Point() * 0.5) : 1e-9;
            if (std::abs(request.price - expected_close_price) > tolerance) {
                return invalid_result("Invalid close price for position side", 10015);
            }
        }

        trade_.UpdatePrices(pos.Symbol(), bid, ask, tick ? (tick->time_msc * 1000) : 0);
        ok = trade_.PositionClose(request.order);
    } else if (request.action == 1 || request.action == 5) {
        const auto action_check = util::validate_action_type(request.action, request.type);
        if (!action_check.ok) {
            return invalid_result(action_check.comment, action_check.retcode);
        }
        const auto sym_it = symbols_.find(request.symbol);
        const haruquant::SymbolInfo* symbol_info = (sym_it == symbols_.end()) ? nullptr : &sym_it->second;

        const double bid = tick ? tick->bid : (symbol_info ? symbol_info->Bid() : 0.0);
        const double ask = tick ? tick->ask : (symbol_info ? symbol_info->Ask() : 0.0);
        const auto input_check =
            util::validate_submission_inputs(request.symbol, request.volume, symbol_info, bid, ask);
        if (!input_check.ok) {
            return invalid_result(input_check.comment, input_check.retcode);
        }
        const util::ValidationContext validation_ctx = build_validation_ctx(symbol_info, bid, ask);

        // Price validation for pending orders is mandatory; for market orders validate when provided.
        if (request.action == 5) {
            if (!(request.price > 0.0)) {
                return invalid_result("Invalid price", 10015);
            }
            const auto price_ok = util::validate_price(request.price, validation_ctx, validation_rules);
            if (!price_ok.ok) {
                return invalid_result("Invalid price: " + price_ok.message, 10015);
            }
        } else if (request.price > 0.0) {
            const auto price_ok = util::validate_price(request.price, validation_ctx, validation_rules);
            if (!price_ok.ok) {
                return invalid_result("Invalid price: " + price_ok.message, 10015);
            }
        }

        std::optional<double> entry_price = std::nullopt;
        if (request.price > 0.0) {
            entry_price = request.price;
        } else if (request.action == 1) {
            if (request.type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY)) {
                entry_price = ask;
            } else if (request.type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL)) {
                entry_price = bid;
            }
        }

        if (request.sl > 0.0) {
            const auto sl_ok = util::validate_stop_loss(
                request.sl,
                entry_price,
                request.type,
                validation_ctx,
                validation_rules);
            if (!sl_ok.ok) {
                return invalid_result("Invalid stop loss: " + sl_ok.message, 10016);
            }
        }
        if (request.tp > 0.0) {
            const auto tp_ok = util::validate_take_profit(
                request.tp,
                entry_price,
                request.type,
                validation_ctx,
                validation_rules);
            if (!tp_ok.ok) {
                return invalid_result("Invalid take profit: " + tp_ok.message, 10016);
            }
        }

        // Slippage applies to market execution when a requested price is provided.
        if (request.action == 1 && request.price > 0.0) {
            const auto slippage_ok = util::validate_slippage(
                static_cast<int>(trade_.DeviationInPoints()),
                request.price,
                request.type,
                validation_ctx,
                validation_rules);
            if (!slippage_ok.ok) {
                return invalid_result("Invalid slippage: " + slippage_ok.message, 10020);
            }
        }

        const MqlTradeRequest mql_request = to_mql_request(request);
        const auto request_check =
            util::validate_trade_request(mql_request, trade_.Account(), symbol_info);
        if (!request_check.ok) {
            return invalid_result(request_check.comment, request_check.retcode);
        }

        // Explicit market freeze validation for stop levels during open/place flows.
        const auto freeze_ok = validate_freeze_for_levels(
            request.type,
            bid,
            ask,
            request.sl > 0.0 ? std::optional<double>(request.sl) : std::nullopt,
            request.tp > 0.0 ? std::optional<double>(request.tp) : std::nullopt,
            symbol_info);
        if (!freeze_ok.ok) {
            return invalid_result("Invalid stops: " + freeze_ok.message, 10029);
        }

        // Enforce per-instrument cumulative volume cap (positions + pending + incoming request).
        double symbol_volume = 0.0;
        for (const auto& pos : trade_.positions_get(request.symbol, std::nullopt, std::nullopt)) {
            symbol_volume += pos.Volume();
        }
        for (const auto& ord : trade_.orders_get(request.symbol, std::nullopt, std::nullopt)) {
            symbol_volume += ord.VolumeCurrent();
        }
        symbol_volume += request.volume;
        const auto symbol_volume_ok =
            util::validate_symbol_volume(symbol_volume, std::nullopt, validation_ctx);
        if (!symbol_volume_ok.ok) {
            return invalid_result(symbol_volume_ok.message, 10034);
        }

        // Pending order count gate.
        if (request.action == 5) {
            const int pending_orders = static_cast<int>(trade_.orders_total());
            const auto max_orders_ok =
                util::validate_max_orders(pending_orders, std::nullopt, validation_ctx);
            if (!max_orders_ok.ok) {
                return invalid_result(max_orders_ok.message, 10033);
            }
        }

        trade_.UpdatePrices(request.symbol, bid, ask, tick ? (tick->time_msc * 1000) : 0);

        if (request.action == 1) {
            if (request.type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY)) {
                ok = trade_.Buy(
                    request.volume,
                    request.symbol,
                    request.price,
                    request.sl,
                    request.tp,
                    request.comment);
            } else if (request.type == static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL)) {
                ok = trade_.Sell(
                    request.volume,
                    request.symbol,
                    request.price,
                    request.sl,
                    request.tp,
                    request.comment);
            } else {
                return invalid_result("Invalid order type for market execution", 10013);
            }
        } else {
            // Pending place flow
            using OT = haruquant::ENUM_ORDER_TYPE;
            OT order_type;
            switch (request.type) {
                case 2: order_type = OT::ORDER_TYPE_BUY_LIMIT; break;
                case 3: order_type = OT::ORDER_TYPE_SELL_LIMIT; break;
                case 4: order_type = OT::ORDER_TYPE_BUY_STOP; break;
                case 5: order_type = OT::ORDER_TYPE_SELL_STOP; break;
                case 6: order_type = OT::ORDER_TYPE_BUY_STOP_LIMIT; break;
                case 7: order_type = OT::ORDER_TYPE_SELL_STOP_LIMIT; break;
                default:
                    return invalid_result("Invalid pending order type", 10013);
            }

            ok = trade_.OrderOpen(
                request.symbol,
                order_type,
                request.volume,
                request.price,
                request.stoplimit,
                request.sl,
                request.tp,
                static_cast<haruquant::ENUM_ORDER_TYPE_TIME>(request.type_time),
                request.expiration,
                request.comment);
        }
    } else if (request.action == 6) {
        uint64_t target_ticket = request.order;
        if (target_ticket == 0) {
            if (request.symbol.empty()) {
                return invalid_result("Invalid request: missing position or symbol", 10013);
            }
            const auto positions = trade_.positions_get(request.symbol, std::nullopt, std::nullopt);
            if (positions.empty()) {
                return invalid_result("Invalid request: position not found", 10013);
            }
            target_ticket = positions.front().Ticket();
        }
        const auto positions = trade_.positions_get(std::nullopt, std::nullopt, target_ticket);
        if (positions.empty()) {
            return invalid_result("Invalid request: position not found", 10013);
        }
        const auto& pos = positions.front();
        const auto sym_it = symbols_.find(pos.Symbol());
        const haruquant::SymbolInfo* symbol_info = (sym_it == symbols_.end()) ? nullptr : &sym_it->second;
        if (symbol_info == nullptr) {
            return invalid_result("Unknown symbol", 10013);
        }
        const double bid = tick ? tick->bid : symbol_info->Bid();
        const double ask = tick ? tick->ask : symbol_info->Ask();
        if (bid <= 0.0 || ask <= 0.0) {
            return invalid_result("No quotes to process the request", 10021);
        }
        const util::ValidationContext validation_ctx = build_validation_ctx(symbol_info, bid, ask);
        const int order_type = (pos.PositionType() == haruquant::ENUM_POSITION_TYPE::POSITION_TYPE_BUY)
            ? static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY)
            : static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL);
        const double entry = pos.PriceOpen();

        if (request.sl > 0.0) {
            const auto sl_ok = util::validate_stop_loss(
                request.sl, entry, order_type, validation_ctx, validation_rules);
            if (!sl_ok.ok) {
                return invalid_result("Invalid stop loss: " + sl_ok.message, 10016);
            }
        }
        if (request.tp > 0.0) {
            const auto tp_ok = util::validate_take_profit(
                request.tp, entry, order_type, validation_ctx, validation_rules);
            if (!tp_ok.ok) {
                return invalid_result("Invalid take profit: " + tp_ok.message, 10016);
            }
        }
        const auto freeze_ok = validate_freeze_for_levels(
            order_type,
            bid,
            ask,
            request.sl > 0.0 ? std::optional<double>(request.sl) : std::nullopt,
            request.tp > 0.0 ? std::optional<double>(request.tp) : std::nullopt,
            symbol_info);
        if (!freeze_ok.ok) {
            return invalid_result("Invalid stops: " + freeze_ok.message, 10029);
        }

        trade_.UpdatePrices(pos.Symbol(), bid, ask, tick ? (tick->time_msc * 1000) : 0);
        ok = trade_.PositionModify(target_ticket, request.sl, request.tp);
    } else if (request.action == 7) {
        if (request.order == 0) {
            return invalid_result("Invalid request: missing order", 10013);
        }
        const auto orders = trade_.orders_get(std::nullopt, std::nullopt, request.order);
        if (orders.empty()) {
            return invalid_result("Invalid request: order not found", 10035);
        }
        const auto& ord = orders.front();
        const auto sym_it = symbols_.find(ord.Symbol());
        const haruquant::SymbolInfo* symbol_info = (sym_it == symbols_.end()) ? nullptr : &sym_it->second;
        if (symbol_info == nullptr) {
            return invalid_result("Unknown symbol", 10013);
        }
        const double bid = tick ? tick->bid : symbol_info->Bid();
        const double ask = tick ? tick->ask : symbol_info->Ask();
        if (bid <= 0.0 || ask <= 0.0) {
            return invalid_result("No quotes to process the request", 10021);
        }
        const util::ValidationContext validation_ctx = build_validation_ctx(symbol_info, bid, ask);
        const int order_type = static_cast<int>(ord.OrderType());
        const double entry = (request.price > 0.0) ? request.price : ord.PriceOpen();

        if (request.price > 0.0) {
            const auto price_ok = util::validate_price(request.price, validation_ctx, validation_rules);
            if (!price_ok.ok) {
                return invalid_result("Invalid price: " + price_ok.message, 10015);
            }
        }
        if (request.sl > 0.0) {
            const auto sl_ok = util::validate_stop_loss(
                request.sl, entry, order_type, validation_ctx, validation_rules);
            if (!sl_ok.ok) {
                return invalid_result("Invalid stop loss: " + sl_ok.message, 10016);
            }
        }
        if (request.tp > 0.0) {
            const auto tp_ok = util::validate_take_profit(
                request.tp, entry, order_type, validation_ctx, validation_rules);
            if (!tp_ok.ok) {
                return invalid_result("Invalid take profit: " + tp_ok.message, 10016);
            }
        }

        const int freeze_level = symbol_info->FreezeLevel();
        if (freeze_level > 0) {
            const double point = symbol_info->Point();
            if (!(point > 0.0)) {
                return invalid_result("Invalid symbol point value", 10013);
            }
            const double freeze_distance = static_cast<double>(freeze_level) * point;
            const double order_entry = entry;
            bool entry_frozen = false;
            switch (order_type) {
                case static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT):
                    entry_frozen = (ask - order_entry) < freeze_distance; break;
                case static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_LIMIT):
                    entry_frozen = (order_entry - bid) < freeze_distance; break;
                case static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP):
                case static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP_LIMIT):
                    entry_frozen = (order_entry - ask) < freeze_distance; break;
                case static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP):
                case static_cast<int>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP_LIMIT):
                    entry_frozen = (bid - order_entry) < freeze_distance; break;
                default:
                    return invalid_result("Invalid pending order type", 10013);
            }
            if (entry_frozen) {
                return invalid_result("Order entry inside freeze level from market", 10029);
            }
        }

        const auto freeze_ok = validate_freeze_for_levels(
            order_type,
            bid,
            ask,
            request.sl > 0.0 ? std::optional<double>(request.sl) : std::nullopt,
            request.tp > 0.0 ? std::optional<double>(request.tp) : std::nullopt,
            symbol_info);
        if (!freeze_ok.ok) {
            return invalid_result("Invalid stops: " + freeze_ok.message, 10029);
        }

        trade_.UpdatePrices(ord.Symbol(), bid, ask, tick ? (tick->time_msc * 1000) : 0);
        ok = trade_.OrderModify(
            request.order,
            request.price,
            request.sl,
            request.tp,
            request.stoplimit,
            request.expiration);
    } else if (request.action == 8) {
        if (request.order == 0) {
            return invalid_result("Invalid request: missing order", 10013);
        }
        ok = trade_.OrderDelete(request.order);
    } else {
        return invalid_result("Invalid request: missing or unsupported action", 10013);
    }

    TradeResult result;
    result.retcode = static_cast<int>(trade_.ResultRetcode());
    result.deal = trade_.ResultDeal();
    result.order = trade_.ResultOrder();
    result.volume = trade_.ResultVolume();
    result.price = trade_.ResultPrice();
    result.bid = trade_.ResultBid();
    result.ask = trade_.ResultAsk();
    result.comment = trade_.ResultComment();

    if (!ok && result.retcode == 0) {
        result.retcode = 10011;
    }
    if (!ok) {
        util::warning("TradeGateway order_send failed: " + result.comment +
                      " (retcode=" + std::to_string(result.retcode) + ")");
    }
    return result;
}

TradeSimulator::TradeSimulator()
    : account_info_(),
      trade_gateway_(account_info_) {
    util::info("TradeSimulator initialized");
}

TradeSimulator::TradeSimulator(haruquant::AccountInfo account)
    : account_info_(std::move(account)),
      trade_gateway_(account_info_) {
    util::info("TradeSimulator initialized");
}

const haruquant::AccountInfo& TradeSimulator::account_info() const noexcept {
    return account_info_;
}

const haruquant::SymbolInfo* TradeSimulator::symbol_info(const std::string& symbol) const noexcept {
    const auto it = symbols_data_.find(symbol);
    return it == symbols_data_.end() ? nullptr : &it->second;
}

const SymbolTickData* TradeSimulator::symbol_info_tick(const std::string& symbol) const noexcept {
    const auto it = ticks_data_.find(symbol);
    return it == ticks_data_.end() ? nullptr : &it->second;
}

std::vector<haruquant::PositionInfo> TradeSimulator::positions_get(
    std::optional<std::string> symbol,
    std::optional<std::string> group,
    std::optional<uint64_t> ticket) const {
    return trade_gateway_.trade().positions_get(symbol, group, ticket);
}

std::size_t TradeSimulator::positions_total() const noexcept {
    return trade_gateway_.trade().positions_total();
}

std::vector<haruquant::OrderInfo> TradeSimulator::orders_get(
    std::optional<std::string> symbol,
    std::optional<std::string> group,
    std::optional<uint64_t> ticket) const {
    return trade_gateway_.trade().orders_get(symbol, group, ticket);
}

std::size_t TradeSimulator::orders_total() const noexcept {
    return trade_gateway_.trade().orders_total();
}

std::vector<haruquant::HistoryOrderInfo> TradeSimulator::history_orders_get(
    std::optional<uint64_t> ticket) const {
    return trade_gateway_.trade().history_orders_get(ticket);
}

std::vector<haruquant::HistoryOrderInfo> TradeSimulator::history_orders_get(
    int64_t date_from_sec,
    int64_t date_to_sec,
    std::optional<std::string> group,
    std::optional<uint64_t> ticket) const {
    return trade_gateway_.trade().history_orders_get(date_from_sec, date_to_sec, group, ticket);
}

std::size_t TradeSimulator::history_orders_total() const noexcept {
    return trade_gateway_.trade().history_orders_total();
}

std::vector<haruquant::DealInfo> TradeSimulator::history_deals_get(
    std::optional<uint64_t> ticket) const {
    return trade_gateway_.trade().history_deals_get(ticket);
}

std::vector<haruquant::DealInfo> TradeSimulator::history_deals_get(
    int64_t date_from_sec,
    int64_t date_to_sec,
    std::optional<std::string> group,
    std::optional<uint64_t> ticket) const {
    return trade_gateway_.trade().history_deals_get(date_from_sec, date_to_sec, group, ticket);
}

std::size_t TradeSimulator::history_deals_total() const noexcept {
    return trade_gateway_.trade().history_deals_total();
}

bool TradeSimulator::symbol_select(const std::string& symbol, bool enable) {
    const bool ok = trade_gateway_.trade().symbol_select(symbol, enable);
    if (ok) {
        last_error_code_ = 1;
        last_error_message_ = "Success";
    } else {
        last_error_code_ = 10013;
        last_error_message_ = "Unknown symbol";
    }
    return ok;
}

std::vector<haruquant::SymbolInfo> TradeSimulator::symbols_get(std::optional<std::string> group) const {
    return trade_gateway_.trade().symbols_get(group);
}

std::size_t TradeSimulator::symbols_total() const noexcept {
    return trade_gateway_.trade().symbols_total();
}

std::pair<int, std::string> TradeSimulator::last_error() const {
    return {last_error_code_, last_error_message_};
}

std::string TradeSimulator::trade_retcode_description(int retcode) const {
    return util::error_from_retcode(retcode).message;
}

TradeCheckResult TradeSimulator::order_check(const TradeRequest& request) const {
    const MqlTradeRequest mql = to_mql_request(request);
    const MqlTradeCheckResult check = trade_gateway_.trade().OrderCheck(mql);
    TradeCheckResult out;
    out.retcode = static_cast<int>(check.retcode);
    out.balance = check.balance;
    out.equity = check.equity;
    out.profit = check.profit;
    out.margin = check.margin;
    out.margin_free = check.margin_free;
    out.margin_level = check.margin_level;
    out.comment = check.comment;
    return out;
}

double TradeSimulator::order_calc_margin(
    int action,
    const std::string& symbol,
    double volume,
    double price) const {
    (void)action;
    const auto* info = symbol_info(symbol);
    if (info == nullptr) {
        util::warning("TradeSimulator::order_calc_margin unknown symbol: " + symbol);
        return 0.0;
    }
    return calc_margin(
        static_cast<int>(info->TradeCalcMode()),
        volume,
        price,
        info->ContractSize(),
        static_cast<double>(account_info_.Leverage()),
        info->TickSize() > 0.0 ? info->TickSize() : info->Point(),
        info->TickValue(),
        info->MarginInitial());
}

double TradeSimulator::order_calc_profit(
    int action,
    const std::string& symbol,
    double volume,
    double price_open,
    double price_close) const {
    const auto* info = symbol_info(symbol);
    if (info == nullptr) {
        util::warning("TradeSimulator::order_calc_profit unknown symbol: " + symbol);
        return 0.0;
    }
    return calc_profit(
        static_cast<int>(info->TradeCalcMode()),
        action,
        volume,
        price_open,
        price_close,
        info->TickSize() > 0.0 ? info->TickSize() : info->Point(),
        info->TickValue(),
        info->ContractSize());
}

TradeResult TradeSimulator::PositionOpen(
    const std::string& symbol,
    int order_type,
    double volume,
    double price,
    double sl,
    double tp,
    const std::string& comment) {
    TradeRequest request;
    request.action = 1;  // TRADE_ACTION_DEAL
    request.type = order_type;
    request.symbol = symbol;
    request.volume = volume;
    request.price = price;
    request.sl = sl;
    request.tp = tp;
    request.type_time = 0;  // ORDER_TIME_GTC
    request.comment = comment;
    TradeResult result = order_send(request);
    const bool ok = (result.retcode == 10008 || result.retcode == 10009 || result.retcode == 10010);
    if (ok) {
        util::info(
            "PositionOpen success symbol=" + symbol +
            " type=" + order_type_to_text(order_type) +
            " volume=" + std::to_string(volume) +
            " price=" + std::to_string(result.price) +
            " order=" + std::to_string(result.order) +
            " deal=" + std::to_string(result.deal));
    } else {
        util::warning(
            "PositionOpen failed symbol=" + symbol +
            " type=" + order_type_to_text(order_type) +
            " volume=" + std::to_string(volume) +
            " retcode=" + std::to_string(result.retcode) +
            " comment=" + result.comment);
    }
    return result;
}

TradeResult TradeSimulator::PositionModify(
    std::optional<std::string> symbol,
    std::optional<uint64_t> ticket,
    double sl,
    double tp) {
    TradeRequest request;
    request.action = 6;  // TRADE_ACTION_SLTP
    if (symbol.has_value()) {
        request.symbol = *symbol;
    }
    if (ticket.has_value()) {
        request.order = *ticket;
    }
    request.sl = sl;
    request.tp = tp;
    TradeResult result = order_send(request);
    const bool ok = (result.retcode == 10008 || result.retcode == 10009 || result.retcode == 10010);
    const std::string target = ticket.has_value()
        ? ("ticket=" + std::to_string(*ticket))
        : ("symbol=" + (symbol.has_value() ? *symbol : ""));
    if (ok) {
        util::info("PositionModify success " + target +
                   " sl=" + std::to_string(sl) +
                   " tp=" + std::to_string(tp));
    } else {
        util::warning("PositionModify failed " + target +
                      " retcode=" + std::to_string(result.retcode) +
                      " comment=" + result.comment);
    }
    return result;
}

TradeResult TradeSimulator::PositionClose(
    std::optional<std::string> symbol,
    std::optional<uint64_t> ticket,
    uint64_t deviation) {
    (void)deviation;
    if (ticket.has_value()) {
        TradeResult result = close_position(*ticket);
        const bool ok = (result.retcode == 10008 || result.retcode == 10009 || result.retcode == 10010);
        if (ok) {
            util::info("PositionClose success ticket=" + std::to_string(*ticket) +
                       " deal=" + std::to_string(result.deal));
        } else {
            util::warning("PositionClose failed ticket=" + std::to_string(*ticket) +
                          " retcode=" + std::to_string(result.retcode) +
                          " comment=" + result.comment);
        }
        return result;
    }
    if (!symbol.has_value()) {
        return invalid_result("Invalid request: missing symbol or ticket", 10013);
    }

    const auto positions = positions_get(*symbol, std::nullopt, std::nullopt);
    if (positions.empty()) {
        return invalid_result("Invalid request: position not found", 10013);
    }
    const uint64_t close_ticket = positions.front().Ticket();
    TradeResult result = close_position(close_ticket);
    const bool ok = (result.retcode == 10008 || result.retcode == 10009 || result.retcode == 10010);
    if (ok) {
        util::info("PositionClose success symbol=" + *symbol +
                   " ticket=" + std::to_string(close_ticket) +
                   " deal=" + std::to_string(result.deal));
    } else {
        util::warning("PositionClose failed symbol=" + *symbol +
                      " ticket=" + std::to_string(close_ticket) +
                      " retcode=" + std::to_string(result.retcode) +
                      " comment=" + result.comment);
    }
    return result;
}

TradeResult TradeSimulator::OrderOpen(
    const std::string& symbol,
    int order_type,
    double volume,
    double price,
    double stoplimit,
    double sl,
    double tp,
    int type_time,
    int64_t expiration,
    const std::string& comment) {
    TradeRequest request;
    request.action = 5;  // TRADE_ACTION_PENDING
    request.type = order_type;
    request.symbol = symbol;
    request.volume = volume;
    request.price = price;
    request.stoplimit = stoplimit;
    request.sl = sl;
    request.tp = tp;
    request.type_time = type_time;
    request.expiration = expiration;
    request.comment = comment;
    TradeResult result = order_send(request);
    const bool ok = (result.retcode == 10008 || result.retcode == 10009 || result.retcode == 10010);
    if (ok) {
        util::info(
            "OrderOpen success symbol=" + symbol +
            " type=" + std::to_string(order_type) +
            " volume=" + std::to_string(volume) +
            " price=" + std::to_string(price) +
            " order=" + std::to_string(result.order));
    } else {
        util::warning(
            "OrderOpen failed symbol=" + symbol +
            " type=" + std::to_string(order_type) +
            " volume=" + std::to_string(volume) +
            " retcode=" + std::to_string(result.retcode) +
            " comment=" + result.comment);
    }
    return result;
}

TradeResult TradeSimulator::OrderModify(
    uint64_t ticket,
    double price,
    double sl,
    double tp,
    double stoplimit,
    int64_t expiration,
    const std::string& comment) {
    TradeRequest request;
    request.action = 7;  // TRADE_ACTION_MODIFY
    request.order = ticket;
    request.price = price;
    request.stoplimit = stoplimit;
    request.sl = sl;
    request.tp = tp;
    request.expiration = expiration;
    request.comment = comment;
    TradeResult result = order_send(request);
    const bool ok = (result.retcode == 10008 || result.retcode == 10009 || result.retcode == 10010);
    if (ok) {
        util::info("OrderModify success ticket=" + std::to_string(ticket) +
                   " price=" + std::to_string(price) +
                   " sl=" + std::to_string(sl) +
                   " tp=" + std::to_string(tp));
    } else {
        util::warning("OrderModify failed ticket=" + std::to_string(ticket) +
                      " retcode=" + std::to_string(result.retcode) +
                      " comment=" + result.comment);
    }
    return result;
}

TradeResult TradeSimulator::OrderDelete(uint64_t ticket, const std::string& comment) {
    TradeRequest request;
    request.action = 8;  // TRADE_ACTION_REMOVE
    request.order = ticket;
    request.comment = comment;
    TradeResult result = order_send(request);
    const bool ok = (result.retcode == 10008 || result.retcode == 10009 || result.retcode == 10010);
    if (ok) {
        util::info("OrderDelete success ticket=" + std::to_string(ticket));
    } else {
        util::warning("OrderDelete failed ticket=" + std::to_string(ticket) +
                      " retcode=" + std::to_string(result.retcode) +
                      " comment=" + result.comment);
    }
    return result;
}

TradeResult TradeSimulator::order_send(const TradeRequest& request) {
    const bool is_submission = (request.action == 1 || request.action == 5);
    const std::string client_order_id = request.client_order_id;
    const std::string fingerprint = submission_fingerprint(request);
    if (is_submission && !client_order_id.empty()) {
        const auto idem_it = idempotency_by_client_order_id_.find(client_order_id);
        if (idem_it != idempotency_by_client_order_id_.end()) {
            if (idem_it->second.fingerprint != fingerprint) {
                return invalid_result("Duplicate client_order_id with different payload", 10013);
            }
            return idem_it->second.result;
        }
    }

    const SymbolTickData* tick = symbol_info_tick(request.symbol);
    TradeResult result = trade_gateway_.order_send(request, tick);
    if (result.retcode == 10008 || result.retcode == 10009 || result.retcode == 10010) {
        sync_state_from_trade();
        util::debug("TradeSimulator::order_send success retcode=" + std::to_string(result.retcode));
    } else {
        util::warning("TradeSimulator::order_send failed retcode=" + std::to_string(result.retcode) +
                      " comment=" + result.comment);
    }

    if (is_submission && !client_order_id.empty()) {
        if (result.retcode == 10008 || result.retcode == 10009 || result.retcode == 10010) {
            idempotency_by_client_order_id_[client_order_id] = IdempotencyEntry{fingerprint, result};
        }
    }

    if (request.action == 1 || request.action == 5) {
        if (result.order > 0) {
            set_order_state(result.order, OmsOrderState::New);
            if (result.retcode == 10008 || result.retcode == 10009 || result.retcode == 10010) {
                set_order_state(result.order, OmsOrderState::Accepted);
                if (request.action == 1) {
                    if (result.retcode == 10010) {
                        set_order_state(result.order, OmsOrderState::PartiallyFilled);
                    } else if (result.retcode == 10009) {
                        set_order_state(result.order, OmsOrderState::Filled);
                    }
                }
            } else {
                set_order_state(result.order, OmsOrderState::Rejected);
            }
        }
    } else if (request.action == 8 && request.order > 0 &&
               (result.retcode == 10009 || result.retcode == 10010)) {
        set_order_state(request.order, OmsOrderState::Canceled);
    }

    last_error_code_ = result.retcode;
    last_error_message_ = result.comment.empty()
        ? trade_retcode_description(result.retcode)
        : result.comment;
    return result;
}

TradeResult TradeSimulator::close_position(uint64_t ticket) {
    if (ticket == 0) {
        util::warning("TradeSimulator::close_position called with ticket=0");
        TradeResult invalid;
        invalid.retcode = 10013;
        invalid.comment = "Invalid request: missing position ticket";
        return invalid;
    }

    std::string symbol;
    const auto pos = trade_gateway_.trade().positions_get(std::nullopt, std::nullopt, ticket);
    if (!pos.empty()) {
        symbol = pos.front().Symbol();
    }

    if (!symbol.empty()) {
        const auto tick_it = ticks_data_.find(symbol);
        if (tick_it != ticks_data_.end()) {
            const auto& tick = tick_it->second;
            trade_gateway_.trade().UpdatePrices(symbol, tick.bid, tick.ask, tick.time_msc * 1000);
        }
    }

    const bool ok = trade_gateway_.trade().PositionClose(ticket);

    TradeResult result;
    result.retcode = static_cast<int>(trade_gateway_.trade().ResultRetcode());
    result.deal = trade_gateway_.trade().ResultDeal();
    result.order = trade_gateway_.trade().ResultOrder();
    result.volume = trade_gateway_.trade().ResultVolume();
    result.price = trade_gateway_.trade().ResultPrice();
    result.bid = trade_gateway_.trade().ResultBid();
    result.ask = trade_gateway_.trade().ResultAsk();
    result.comment = trade_gateway_.trade().ResultComment();

    if (ok && (result.retcode == 10009 || result.retcode == 10010)) {
        sync_state_from_trade();
        util::debug("TradeSimulator::close_position success ticket=" + std::to_string(ticket));
    } else if (!ok && result.retcode == 0) {
        result.retcode = 10011;
        util::warning("TradeSimulator::close_position failed ticket=" + std::to_string(ticket));
    }

    last_error_code_ = result.retcode;
    last_error_message_ = result.comment.empty()
        ? trade_retcode_description(result.retcode)
        : result.comment;
    return result;
}

bool TradeSimulator::set_history_order_state(uint64_t ticket, uint64_t state) {
    const bool updated = trade_gateway_.trade().history_order_set_state(
        ticket, static_cast<haruquant::ENUM_ORDER_STATE>(state));
    if (!updated) {
        return false;
    }
    sync_state_from_trade();
    set_order_state(ticket, map_order_state(state));
    return true;
}

bool TradeSimulator::set_history_order_done_time(uint64_t ticket, int64_t time_sec, int64_t time_msc) {
    const bool updated = trade_gateway_.trade().history_order_set_done_time(ticket, time_sec, time_msc);
    if (!updated) {
        return false;
    }
    sync_state_from_trade();
    return true;
}

void TradeSimulator::set_account_info(const haruquant::AccountInfo& data) {
    account_info_ = data;
    trade_gateway_ = TradeGateway(account_info_);
    for (const auto& [_, symbol] : symbols_data_) {
        trade_gateway_.register_symbol(symbol);
    }
}

void TradeSimulator::set_symbol_info(const haruquant::SymbolInfo& data) {
    symbols_data_[data.Name()] = data;
    trade_gateway_.register_symbol(data);
    if (data.Bid() > 0.0 && data.Ask() > 0.0) {
        SymbolTickData tick;
        tick.time = data.Time();
        if (tick.time <= 0) {
            const auto now = std::chrono::system_clock::now();
            tick.time = static_cast<int64_t>(std::chrono::duration_cast<std::chrono::seconds>(
                now.time_since_epoch()).count());
        }
        tick.time_msc = tick.time * 1000;
        tick.bid = data.Bid();
        tick.ask = data.Ask();
        tick.last = data.Last() > 0.0 ? data.Last() : (tick.bid + tick.ask) / 2.0;
        tick.volume = 0;
        tick.flags = 0;
        tick.volume_real = 0.0;
        ticks_data_[data.Name()] = tick;
    }
    util::debug("TradeSimulator::set_symbol_info symbol=" + data.Name());
}

void TradeSimulator::set_symbol_tick(const std::string& symbol, const SymbolTickData& tick) {
    ticks_data_[symbol] = tick;
}

void TradeSimulator::upsert_position_info(const haruquant::PositionInfo& data) {
    positions_info_data_[data.Ticket()] = data;
    trade_gateway_.trade().upsert_position(data);
}

void TradeSimulator::upsert_order_info(const haruquant::OrderInfo& data) {
    orders_info_data_[data.Ticket()] = data;
    trade_gateway_.trade().upsert_active_order(data);
}

void TradeSimulator::upsert_history_order_info(const haruquant::HistoryOrderInfo& data) {
    history_orders_info_data_[data.Ticket()] = data;
    trade_gateway_.trade().upsert_history_order(data);
}

void TradeSimulator::upsert_deal_info(const haruquant::DealInfo& data) {
    deals_info_data_[data.Ticket()] = data;
    trade_gateway_.trade().upsert_history_deal(data);
}

void TradeSimulator::set_last_error(int code, const std::string& message) {
    last_error_code_ = code;
    last_error_message_ = message;
    util::warning("TradeSimulator::set_last_error code=" + std::to_string(code) + " message=" + message);
}

OmsOrderState TradeSimulator::order_state(uint64_t ticket) const {
    const auto it = order_states_.find(ticket);
    if (it == order_states_.end()) {
        return OmsOrderState::Unknown;
    }
    return it->second;
}

std::string TradeSimulator::order_state_name(uint64_t ticket) const {
    return order_state_label(order_state(ticket));
}

std::size_t TradeSimulator::idempotency_cache_size() const noexcept {
    return idempotency_by_client_order_id_.size();
}

std::string TradeSimulator::submission_fingerprint(const TradeRequest& request) {
    std::ostringstream oss;
    oss << request.action << '|'
        << request.type << '|'
        << request.symbol << '|'
        << request.volume << '|'
        << request.price << '|'
        << request.stoplimit << '|'
        << request.sl << '|'
        << request.tp << '|'
        << request.type_time << '|'
        << request.expiration << '|'
        << request.comment;
    return oss.str();
}

OmsOrderState TradeSimulator::map_order_state(uint64_t raw_state) noexcept {
    switch (raw_state) {
        case 0: return OmsOrderState::New;
        case 1: return OmsOrderState::Accepted;
        case 2: return OmsOrderState::Canceled;
        case 3: return OmsOrderState::PartiallyFilled;
        case 4: return OmsOrderState::Filled;
        case 5: return OmsOrderState::Rejected;
        case 6: return OmsOrderState::Expired;
        default: return OmsOrderState::Unknown;
    }
}

std::string TradeSimulator::order_state_label(OmsOrderState state) {
    switch (state) {
        case OmsOrderState::New: return "NEW";
        case OmsOrderState::Accepted: return "ACCEPTED";
        case OmsOrderState::PartiallyFilled: return "PARTIALLY_FILLED";
        case OmsOrderState::Filled: return "FILLED";
        case OmsOrderState::Canceled: return "CANCELED";
        case OmsOrderState::Expired: return "EXPIRED";
        case OmsOrderState::Rejected: return "REJECTED";
        default: return "UNKNOWN";
    }
}

void TradeSimulator::set_order_state(uint64_t ticket, OmsOrderState state) {
    if (ticket == 0) {
        return;
    }
    order_states_[ticket] = state;
}

void TradeSimulator::rebuild_order_states_from_snapshots() {
    for (const auto& [ticket, record] : orders_info_data_) {
        order_states_[ticket] = map_order_state(static_cast<uint64_t>(record.State()));
    }
    for (const auto& [ticket, record] : history_orders_info_data_) {
        order_states_[ticket] = map_order_state(static_cast<uint64_t>(record.State()));
    }
}

void TradeSimulator::sync_state_from_trade() {
    positions_info_data_.clear();
    orders_info_data_.clear();
    deals_info_data_.clear();
    history_orders_info_data_.clear();

    const auto& trade = trade_gateway_.trade();
    const auto& account = trade.Account();

    account_info_ = account;

    for (const auto& pos : trade.positions_get()) {
        positions_info_data_[pos.Ticket()] = pos;
    }

    for (const auto& ord : trade.orders_get()) {
        orders_info_data_[ord.Ticket()] = ord;
    }

    for (const auto& deal : trade.history_deals_get()) {
        deals_info_data_[deal.Ticket()] = deal;
    }

    for (const auto& hist : trade.history_orders_get()) {
        history_orders_info_data_[hist.Ticket()] = hist;
    }

    util::debug(
        "TradeSimulator::sync_state_from_trade positions=" + std::to_string(positions_info_data_.size()) +
        " orders=" + std::to_string(orders_info_data_.size()) +
        " deals=" + std::to_string(deals_info_data_.size()) +
        " history_orders=" + std::to_string(history_orders_info_data_.size()));
    rebuild_order_states_from_snapshots();
}

MockBroker::MockBroker(TradeSimulator client)
    : client_(std::move(client)) {}

void MockBroker::set_partial_fill_ratio(double ratio) {
    partial_fill_ratio_ = std::clamp(ratio, 0.0, 1.0);
}

void MockBroker::set_deterministic_price(double price) {
    if (price > 0.0) {
        deterministic_price_ = price;
    }
}

void MockBroker::clear_deterministic_price() {
    deterministic_price_.reset();
}

bool MockBroker::connect() {
    connected_ = true;
    return true;
}

TradeResult MockBroker::submit(const TradeRequest& request) {
    if (!connected_) {
        TradeResult out;
        out.retcode = 10031;
        out.comment = "MockBroker not connected";
        return out;
    }

    TradeRequest effective = scaled_request(request, partial_fill_ratio_);
    if (deterministic_price_.has_value()) {
        effective.price = *deterministic_price_;
    }
    TradeResult out = client_.order_send(effective);
    if (request.volume > 0.0 && effective.volume > 0.0 && effective.volume < request.volume &&
        haruquant::util::is_success_retcode(out.retcode)) {
        out.retcode = 10010;
        out.volume = effective.volume;
        if (out.comment.empty()) {
            out.comment = "Partial fill (mock ratio)";
        }
    }
    return out;
}

TradeResult MockBroker::cancel(uint64_t order_id) {
    if (!connected_) {
        TradeResult out;
        out.retcode = 10031;
        out.comment = "MockBroker not connected";
        return out;
    }
    TradeRequest req;
    req.action = 8;
    req.order = order_id;
    return client_.order_send(req);
}

BrokerSnapshot MockBroker::fetch_state() const {
    BrokerSnapshot snapshot;
    snapshot.account = client_.account_info();
    snapshot.positions = aggregate_positions();
    return snapshot;
}

TradeRequest MockBroker::scaled_request(const TradeRequest& request, double ratio) {
    TradeRequest out = request;
    if (out.volume > 0.0) {
        out.volume = std::max(0.0, out.volume * std::clamp(ratio, 0.0, 1.0));
    }
    return out;
}

std::unordered_map<std::string, PositionAggregate> MockBroker::aggregate_positions() const {
    std::unordered_map<std::string, PositionAggregate> out;
    for (const auto& pos : client_.positions_get()) {
        auto& agg = out[pos.Symbol()];
        const bool is_buy = (static_cast<int>(pos.PositionType()) == 0);
        if (is_buy) {
            agg.long_volume += pos.Volume();
            agg.net_volume += pos.Volume();
        } else {
            agg.short_volume += pos.Volume();
            agg.net_volume -= pos.Volume();
        }
    }
    return out;
}

PaperTradingEngine::PaperTradingEngine(std::shared_ptr<BrokerAdapter> adapter)
    : adapter_(std::move(adapter)) {}

bool PaperTradingEngine::connect() {
    if (!adapter_) {
        return false;
    }
    return adapter_->connect();
}

TradeResult PaperTradingEngine::submit_order(const TradeRequest& request) {
    if (!adapter_) {
        TradeResult out;
        out.retcode = 10031;
        out.comment = "PaperTradingEngine adapter missing";
        return out;
    }
    return adapter_->submit(request);
}

TradeResult PaperTradingEngine::cancel_order(uint64_t order_id) {
    if (!adapter_) {
        TradeResult out;
        out.retcode = 10031;
        out.comment = "PaperTradingEngine adapter missing";
        return out;
    }
    return adapter_->cancel(order_id);
}

BrokerSnapshot PaperTradingEngine::snapshot_state() const {
    if (!adapter_) {
        return {};
    }
    return adapter_->fetch_state();
}

std::vector<ExecutionSlice> ExecutionAlgoTWAP::build_schedule(
    const double total_volume,
    const int64_t start_time_ms,
    const int64_t end_time_ms,
    const std::size_t slices) {
    std::vector<ExecutionSlice> out;
    if (total_volume <= 0.0 || slices == 0U || end_time_ms < start_time_ms) {
        return out;
    }
    out.reserve(slices);

    const double slice_volume = total_volume / static_cast<double>(slices);
    const int64_t span = end_time_ms - start_time_ms;
    const int64_t step = (slices > 1U) ? (span / static_cast<int64_t>(slices - 1U)) : 0;
    double assigned = 0.0;

    for (std::size_t i = 0; i < slices; ++i) {
        ExecutionSlice s{};
        s.scheduled_time_ms = start_time_ms + (step * static_cast<int64_t>(i));
        s.weight = 1.0 / static_cast<double>(slices);
        s.volume = (i + 1U == slices) ? (total_volume - assigned) : slice_volume;
        assigned += s.volume;
        out.push_back(s);
    }
    return out;
}

std::vector<ExecutionSlice> ExecutionAlgoVWAP::build_schedule(
    const double total_volume,
    const int64_t start_time_ms,
    const int64_t end_time_ms,
    const std::vector<double>& market_volume_profile) {
    std::vector<ExecutionSlice> out;
    const std::size_t slices = market_volume_profile.size();
    if (total_volume <= 0.0 || slices == 0U || end_time_ms < start_time_ms) {
        return out;
    }
    out.reserve(slices);

    double weight_sum = 0.0;
    for (const double v : market_volume_profile) {
        if (v > 0.0) {
            weight_sum += v;
        }
    }
    if (weight_sum <= 0.0) {
        return ExecutionAlgoTWAP::build_schedule(total_volume, start_time_ms, end_time_ms, slices);
    }

    const int64_t span = end_time_ms - start_time_ms;
    const int64_t step = (slices > 1U) ? (span / static_cast<int64_t>(slices - 1U)) : 0;
    double assigned = 0.0;

    for (std::size_t i = 0; i < slices; ++i) {
        const double raw = std::max(0.0, market_volume_profile[i]);
        const double weight = raw / weight_sum;
        ExecutionSlice s{};
        s.scheduled_time_ms = start_time_ms + (step * static_cast<int64_t>(i));
        s.weight = weight;
        s.volume = (i + 1U == slices) ? (total_volume - assigned) : (total_volume * weight);
        assigned += s.volume;
        out.push_back(s);
    }
    return out;
}

ExecutionRouter::ExecutionRouter(
    std::shared_ptr<BrokerAdapter> adapter,
    ExecutionPolicy policy)
    : adapter_(std::move(adapter)),
      policy_(policy) {}

bool ExecutionRouter::connect() {
    if (!adapter_) {
        return false;
    }
    connected_ = adapter_->connect();
    return connected_;
}

void ExecutionRouter::set_policy(const ExecutionPolicy& policy) {
    std::scoped_lock lock(mutex_);
    policy_ = policy;
}

ExecutionPolicy ExecutionRouter::policy() const {
    std::scoped_lock lock(mutex_);
    return policy_;
}

void ExecutionRouter::set_risk_account_state(
    const double equity,
    const double peak_equity,
    const double gross_exposure,
    const double net_exposure) {
    std::scoped_lock lock(mutex_);
    risk_state_.equity = equity;
    risk_state_.peak_equity = peak_equity;
    risk_state_.gross_exposure = gross_exposure;
    risk_state_.net_exposure = net_exposure;
}

std::size_t ExecutionRouter::consecutive_failures() const {
    std::scoped_lock lock(mutex_);
    return consecutive_failures_;
}

ExecutionRouteResult ExecutionRouter::submit(
    const TradeRequest& request,
    const double candidate_gross_add,
    const double candidate_net_delta,
    const double margin_required,
    const double free_margin,
    const bool live_mode) {
    ExecutionRouteResult out;
    if (!adapter_ || !connected_) {
        out.result.retcode = 10031;
        out.result.comment = "ExecutionRouter adapter unavailable";
        out.policy_code = "CONNECTION";
        out.reason = "adapter_unavailable";
        return out;
    }

    haruquant::risk::RiskAccountState risk_state{};
    {
        std::scoped_lock lock(mutex_);
        risk_state = risk_state_;
    }
    const auto mode = live_mode ? haruquant::risk::RiskMode::Live : haruquant::risk::RiskMode::Backtest;
    const auto risk_decision = governor_.can_trade_with_mode(
        risk_state,
        request.volume,
        candidate_gross_add,
        candidate_net_delta,
        margin_required,
        free_margin,
        mode);
    if (!risk_decision.allowed) {
        out.risk_blocked = true;
        out.policy_code = risk_decision.policy_code;
        out.reason = risk_decision.reason;
        out.result.retcode = 10006;
        out.result.comment = "Risk gate rejected order";
        return out;
    }

    const auto now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                            std::chrono::steady_clock::now().time_since_epoch())
                            .count();
    {
        std::scoped_lock lock(mutex_);
        if (!check_rate_limit_unlocked(now_ms)) {
            out.rate_limited = true;
            out.policy_code = "RATE_LIMIT";
            out.reason = "too_many_requests";
            out.result.retcode = 10024;
            out.result.comment = "Order spam prevention triggered";
            return out;
        }
        recent_submissions_ms_.push_back(now_ms);
    }

    const auto start_ts = std::chrono::steady_clock::now();
    const int max_attempts = std::max(1, policy().max_retries + 1);
    for (int attempt = 1; attempt <= max_attempts; ++attempt) {
        out.attempts = attempt;
        out.result = adapter_->submit(request);
        if (haruquant::util::is_success_retcode(out.result.retcode)) {
            std::scoped_lock lock(mutex_);
            consecutive_failures_ = 0;
            out.retried = (attempt > 1);
            break;
        }

        const auto error_info = haruquant::util::error_from_retcode(out.result.retcode);
        const bool can_retry = error_info.retryable && attempt < max_attempts;
        if (!can_retry) {
            break;
        }
    }

    if (!haruquant::util::is_success_retcode(out.result.retcode)) {
        out.retried = out.attempts > 1;
        {
            std::scoped_lock lock(mutex_);
            ++consecutive_failures_;
            if (consecutive_failures_ >= policy_.escalation_after_failures) {
                out.escalated = true;
                out.escalation_reason = "bounded_failure_threshold_reached";
            }
        }
        out.policy_code = "EXECUTION_FAILED";
        out.reason = "execution_retry_exhausted";
    }

    const auto end_ts = std::chrono::steady_clock::now();
    const double latency_ms = std::chrono::duration_cast<std::chrono::microseconds>(
                                  end_ts - start_ts)
                                  .count() /
        1000.0;
    {
        std::scoped_lock lock(mutex_);
        latencies_ms_.push_back(latency_ms);
        latency_sum_ms_ += latency_ms;
        ++quality_samples_;

        const bool partial_fill = (out.result.retcode == 10010) ||
            (request.volume > 0.0 && out.result.volume > 0.0 && out.result.volume < request.volume);
        if (partial_fill) {
            ++partial_fill_count_;
        }

        const bool is_buy = (request.type == 0 || request.type == 2 || request.type == 4 || request.type == 6);
        const double spread = std::max(0.0, out.result.ask - out.result.bid);
        spread_sum_ += spread;

        double expected_price = request.price;
        if (request.action == 1 && expected_price <= 0.0) {
            expected_price = is_buy ? out.result.ask : out.result.bid;
        }
        if (expected_price > 0.0 && out.result.price > 0.0) {
            const double slippage = is_buy
                ? std::max(0.0, out.result.price - expected_price)
                : std::max(0.0, expected_price - out.result.price);
            slippage_sum_ += slippage;
        }
    }
    return out;
}

TradeResult ExecutionRouter::cancel(const uint64_t order_id) {
    if (!adapter_ || !connected_) {
        TradeResult out;
        out.retcode = 10031;
        out.comment = "ExecutionRouter adapter unavailable";
        return out;
    }
    return adapter_->cancel(order_id);
}

bool ExecutionRouter::check_rate_limit_unlocked(const int64_t now_ms) {
    const int64_t window_ms = std::max<int64_t>(1, policy_.rate_limit_window_ms);
    while (!recent_submissions_ms_.empty() &&
           (now_ms - recent_submissions_ms_.front()) > window_ms) {
        recent_submissions_ms_.pop_front();
    }
    return recent_submissions_ms_.size() < policy_.max_orders_per_window;
}

void ExecutionRouter::reset_quality_metrics() {
    std::scoped_lock lock(mutex_);
    latencies_ms_.clear();
    latency_sum_ms_ = 0.0;
    slippage_sum_ = 0.0;
    spread_sum_ = 0.0;
    quality_samples_ = 0U;
    partial_fill_count_ = 0U;
}

ExecutionQualitySummary ExecutionRouter::quality_summary() const {
    std::scoped_lock lock(mutex_);
    ExecutionQualitySummary out{};
    out.samples = quality_samples_;
    out.partial_fill_count = partial_fill_count_;
    if (quality_samples_ == 0U) {
        return out;
    }

    out.partial_fill_rate = static_cast<double>(partial_fill_count_) / static_cast<double>(quality_samples_);
    out.avg_latency_ms = latency_sum_ms_ / static_cast<double>(quality_samples_);
    out.avg_slippage = slippage_sum_ / static_cast<double>(quality_samples_);
    out.avg_spread = spread_sum_ / static_cast<double>(quality_samples_);

    std::vector<double> sorted = latencies_ms_;
    std::sort(sorted.begin(), sorted.end());
    const std::size_t idx = static_cast<std::size_t>(
        std::ceil(0.99 * static_cast<double>(sorted.size()))) - 1U;
    out.p99_latency_ms = sorted[std::min(idx, sorted.size() - 1U)];
    return out;
}

}  // namespace haruquant::sim



