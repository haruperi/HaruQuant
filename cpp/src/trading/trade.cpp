/**
FILE: src\trading\trade.cpp

PURPOSE:
Defines trade.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in trade.cpp.
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
#include "trading/trade.hpp"
#include "util/logger.hpp"
#include <sstream>
#include <iomanip>
#include <cmath>
#include <algorithm>
#include <cctype>
#include <vector>

namespace haruquant {

namespace {

std::string trim_copy(const std::string& value) {
    std::size_t start = 0;
    std::size_t end = value.size();
    while (start < end && std::isspace(static_cast<unsigned char>(value[start])) != 0) {
        ++start;
    }
    while (end > start && std::isspace(static_cast<unsigned char>(value[end - 1])) != 0) {
        --end;
    }
    return value.substr(start, end - start);
}

std::vector<std::string> split_csv(const std::string& value) {
    std::vector<std::string> out;
    std::size_t start = 0;
    while (start <= value.size()) {
        const std::size_t comma = value.find(',', start);
        if (comma == std::string::npos) {
            out.push_back(trim_copy(value.substr(start)));
            break;
        }
        out.push_back(trim_copy(value.substr(start, comma - start)));
        start = comma + 1;
    }
    return out;
}

}  // namespace

// ===================================================================
// Position Management Implementation
// ===================================================================

bool CTrade::PositionOpen(const std::string& symbol,
                         ENUM_ORDER_TYPE order_type,
                         double volume,
                         double price,
                         double sl,
                         double tp,
                         const std::string& comment) noexcept {
    // Build request
    last_request_ = MqlTradeRequest();
    last_request_.action = ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_DEAL;
    last_request_.symbol = symbol;
    last_request_.type = order_type;
    last_request_.volume = volume;
    last_request_.price = price;
    last_request_.sl = sl;
    last_request_.tp = tp;
    last_request_.deviation = deviation_;
    last_request_.type_filling = type_filling_;
    last_request_.magic = magic_number_;
    last_request_.comment = comment;
    // Validation authority is centralized in TradeGateway::order_send.
    last_check_ = MqlTradeCheckResult();
    last_check_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_DONE;
    last_check_.balance = account_.Balance();
    last_check_.equity = account_.Equity();
    last_check_.margin = account_.Margin();
    last_check_.margin_free = account_.FreeMargin();
    last_check_.margin_level = account_.MarginLevel();
    last_check_.comment = "Validated by gateway";

    // Execute request
    bool success = ExecuteRequest(last_request_, last_result_);

    if (log_level_ >= 1) {
        PrintRequest();
        PrintResult();
    }

    return success;
}

bool CTrade::PositionModify(const std::string& symbol,
                           double sl,
                           double tp) noexcept {
    // Find position by symbol
    PositionInfo* pos = nullptr;
    for (auto& [ticket, p] : positions_) {
        if (p.Symbol() == symbol) {
            pos = &p;
            break;
        }
    }

    if (!pos) {
        last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID_ORDER;
        last_result_.comment = "Position not found";
        return false;
    }

    return PositionModify(pos->Ticket(), sl, tp);
}

bool CTrade::PositionModify(uint64_t ticket,
                           double sl,
                           double tp) noexcept {
    auto it = positions_.find(ticket);
    if (it == positions_.end()) {
        last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID_ORDER;
        last_result_.comment = "Position not found";
        return false;
    }

    PositionInfo& pos = it->second;

    // Build request
    last_request_ = MqlTradeRequest();
    last_request_.action = ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_SLTP;
    last_request_.position = ticket;
    last_request_.symbol = pos.Symbol();
    last_request_.sl = sl;
    last_request_.tp = tp;
    last_request_.magic = magic_number_;

    // Update position
    if (sl > 0.0) pos.SetStopLoss(sl);
    if (tp > 0.0) pos.SetTakeProfit(tp);

    // Set result
    last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_DONE;
    last_result_.comment = "Position modified";

    return true;
}

bool CTrade::PositionClose(const std::string& symbol,
                          uint64_t deviation) noexcept {
    // Find position by symbol
    uint64_t ticket = 0;
    for (const auto& [t, pos] : positions_) {
        if (pos.Symbol() == symbol) {
            ticket = t;
            break;
        }
    }

    if (ticket == 0) {
        last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID_ORDER;
        last_result_.comment = "Position not found";
        return false;
    }

    return PositionClose(ticket, deviation);
}

bool CTrade::PositionClose(uint64_t ticket,
                          uint64_t deviation) noexcept {
    auto it = positions_.find(ticket);
    if (it == positions_.end()) {
        last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_POSITION_CLOSED;
        last_result_.comment = "Position not found";
        return false;
    }

    const PositionInfo& pos = it->second;

    // Build request
    last_request_ = MqlTradeRequest();
    last_request_.action = ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_DEAL;
    last_request_.position = ticket;
    last_request_.symbol = pos.Symbol();
    last_request_.volume = pos.Volume();
    last_request_.deviation = (deviation > 0) ? deviation : deviation_;
    last_request_.magic = magic_number_;

    // Get current market price
    const SymbolInfo* info = GetSymbolInfo(pos.Symbol());
    if (!info) {
        last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID;
        last_result_.comment = "Symbol not found";
        return false;
    }

    // Close at current market price (opposite side)
    double close_price = (pos.PositionType() == ENUM_POSITION_TYPE::POSITION_TYPE_BUY)
        ? info->Bid() : info->Ask();

    return InternalPositionClose(ticket, pos.Volume(), close_price);
}

bool CTrade::PositionClosePartial(const std::string& symbol,
                                 double volume,
                                 uint64_t deviation) noexcept {
    // Find position by symbol
    uint64_t ticket = 0;
    for (const auto& [t, pos] : positions_) {
        if (pos.Symbol() == symbol) {
            ticket = t;
            break;
        }
    }

    if (ticket == 0) {
        last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID_ORDER;
        last_result_.comment = "Position not found";
        return false;
    }

    return PositionClosePartial(ticket, volume, deviation);
}

bool CTrade::PositionClosePartial(uint64_t ticket,
                                 double volume,
                                 uint64_t deviation) noexcept {
    auto it = positions_.find(ticket);
    if (it == positions_.end()) {
        last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_POSITION_CLOSED;
        last_result_.comment = "Position not found";
        return false;
    }

    const PositionInfo& pos = it->second;

    if (volume >= pos.Volume()) {
        // Close entire position
        return PositionClose(ticket, deviation);
    }

    // Get current market price
    const SymbolInfo* info = GetSymbolInfo(pos.Symbol());
    if (!info) {
        last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID;
        last_result_.comment = "Symbol not found";
        return false;
    }

    double close_price = (pos.PositionType() == ENUM_POSITION_TYPE::POSITION_TYPE_BUY)
        ? info->Bid() : info->Ask();

    // Build request
    last_request_ = MqlTradeRequest();
    last_request_.action = ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_DEAL;
    last_request_.position = ticket;
    last_request_.symbol = pos.Symbol();
    last_request_.volume = volume;
    last_request_.deviation = (deviation > 0) ? deviation : deviation_;
    last_request_.magic = magic_number_;

    return InternalPositionClose(ticket, volume, close_price);
}

bool CTrade::PositionCloseBy(uint64_t ticket,
                            uint64_t ticket_by) noexcept {
    auto it1 = positions_.find(ticket);
    auto it2 = positions_.find(ticket_by);

    if (it1 == positions_.end() || it2 == positions_.end()) {
        last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID_ORDER;
        last_result_.comment = "Position not found";
        return false;
    }

    const PositionInfo& pos1 = it1->second;
    const PositionInfo& pos2 = it2->second;

    // Must be opposite positions on same symbol
    if (pos1.Symbol() != pos2.Symbol()) {
        last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID;
        last_result_.comment = "Positions must be on same symbol";
        return false;
    }

    if (pos1.PositionType() == pos2.PositionType()) {
        last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID;
        last_result_.comment = "Positions must be opposite types";
        return false;
    }

    // Build request
    last_request_ = MqlTradeRequest();
    last_request_.action = ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_CLOSE_BY;
    last_request_.position = ticket;
    last_request_.position_by = ticket_by;
    last_request_.magic = magic_number_;

    // Close the smaller volume from both
    double volume = std::min(pos1.Volume(), pos2.Volume());

    const SymbolInfo* info = GetSymbolInfo(pos1.Symbol());
    if (!info) {
        last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID;
        last_result_.comment = "Symbol not found";
        return false;
    }

    // Use current bid for both (they offset each other)
    double price = info->Bid();

    bool success = InternalPositionClose(ticket, volume, price);
    if (success) {
        InternalPositionClose(ticket_by, volume, price);
    }

    return success;
}

// ===================================================================
// Order Management Implementation
// ===================================================================

bool CTrade::OrderOpen(const std::string& symbol,
                      ENUM_ORDER_TYPE order_type,
                      double volume,
                      double limit_price,
                      double stop_price,
                      double sl,
                      double tp,
                      ENUM_ORDER_TYPE_TIME type_time,
                      int64_t expiration,
                      const std::string& comment) noexcept {
    // Build request
    last_request_ = MqlTradeRequest();
    last_request_.action = ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_PENDING;
    last_request_.symbol = symbol;
    last_request_.type = order_type;
    last_request_.volume = volume;
    last_request_.price = limit_price;
    last_request_.stoplimit = stop_price;
    last_request_.sl = sl;
    last_request_.tp = tp;
    last_request_.type_filling = type_filling_;
    last_request_.type_time = type_time;
    last_request_.expiration = expiration;
    last_request_.magic = magic_number_;
    last_request_.comment = comment;
    // Validation authority is centralized in TradeGateway::order_send.
    last_check_ = MqlTradeCheckResult();
    last_check_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_DONE;
    last_check_.balance = account_.Balance();
    last_check_.equity = account_.Equity();
    last_check_.margin = account_.Margin();
    last_check_.margin_free = account_.FreeMargin();
    last_check_.margin_level = account_.MarginLevel();
    last_check_.comment = "Validated by gateway";

    // Execute request
    bool success = ExecuteRequest(last_request_, last_result_);

    if (log_level_ >= 1) {
        PrintRequest();
        PrintResult();
    }

    return success;
}

bool CTrade::OrderModify(uint64_t ticket,
                        double price,
                        double sl,
                        double tp,
                        double stop_limit,
                        int64_t expiration) noexcept {
    auto it = orders_.find(ticket);
    if (it == orders_.end()) {
        last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID_ORDER;
        last_result_.comment = "Order not found";
        return false;
    }

    OrderInfo& order = it->second;

    // Build request
    last_request_ = MqlTradeRequest();
    last_request_.action = ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_MODIFY;
    last_request_.order = ticket;
    last_request_.price = price;
    last_request_.stoplimit = stop_limit;
    last_request_.sl = sl;
    last_request_.tp = tp;
    last_request_.expiration = expiration;
    last_request_.magic = magic_number_;

    // Update order
    if (price > 0.0) order.SetPriceOpen(price);
    if (sl > 0.0) order.SetStopLoss(sl);
    if (tp > 0.0) order.SetTakeProfit(tp);
    if (stop_limit > 0.0) order.SetPriceStopLimit(stop_limit);
    if (expiration > 0) order.SetTimeExpiration(expiration);

    // Set result
    last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_DONE;
    last_result_.order = ticket;
    last_result_.comment = "Order modified";

    return true;
}

bool CTrade::OrderDelete(uint64_t ticket) noexcept {
    auto it = orders_.find(ticket);
    if (it == orders_.end()) {
        last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID_ORDER;
        last_result_.comment = "Order not found";
        return false;
    }

    OrderInfo& order = it->second;

    // Build request
    last_request_ = MqlTradeRequest();
    last_request_.action = ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_REMOVE;
    last_request_.order = ticket;
    last_request_.magic = magic_number_;

    // Mark as cancelled
    order.SetState(ENUM_ORDER_STATE::ORDER_STATE_CANCELED);
    order.SetTimeDone(current_time_us_);

    // Move to history
    history_orders_.push_back(HistoryOrderInfo(order));

    // Remove from active orders
    orders_.erase(it);

    // Set result
    last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_DONE;
    last_result_.comment = "Order deleted";

    return true;
}

// ===================================================================
// Utility Methods Implementation
// ===================================================================

void CTrade::PrintRequest() const noexcept {
    std::string formatted = FormatRequest(last_request_);
    util::info(formatted);
}

void CTrade::PrintResult() const noexcept {
    std::string formatted = FormatRequestResult(last_request_, last_result_);
    util::info(formatted);
}

std::string CTrade::FormatRequest(const MqlTradeRequest& request) const noexcept {
    std::ostringstream oss;
    oss << "Trade Request: ";
    oss << "Action=" << static_cast<int>(request.action) << ", ";
    oss << "Symbol=" << request.symbol << ", ";
    oss << "Volume=" << std::fixed << std::setprecision(2) << request.volume << ", ";
    oss << "Price=" << std::setprecision(5) << request.price;
    if (request.sl > 0.0) oss << ", SL=" << request.sl;
    if (request.tp > 0.0) oss << ", TP=" << request.tp;
    if (!request.comment.empty()) oss << ", Comment=" << request.comment;
    return oss.str();
}

std::string CTrade::FormatRequestResult(const MqlTradeRequest& request,
                                       const MqlTradeResult& result) const noexcept {
    (void)request;  // Unused parameter
    std::ostringstream oss;
    oss << "Trade Result: ";
    oss << "Retcode=" << static_cast<int>(result.retcode) << ", ";
    if (result.deal > 0) oss << "Deal=" << result.deal << ", ";
    if (result.order > 0) oss << "Order=" << result.order << ", ";
    oss << "Comment=" << result.comment;
    return oss.str();
}

// ===================================================================
// MT5 Python-style Query API
// ===================================================================

bool CTrade::MatchPattern(const std::string& value, const std::string& pattern) noexcept {
    std::size_t v = 0;
    std::size_t p = 0;
    std::size_t star = std::string::npos;
    std::size_t match = 0;

    while (v < value.size()) {
        if (p < pattern.size() && (pattern[p] == value[v])) {
            ++v;
            ++p;
            continue;
        }
        if (p < pattern.size() && pattern[p] == '*') {
            star = p++;
            match = v;
            continue;
        }
        if (star != std::string::npos) {
            p = star + 1;
            v = ++match;
            continue;
        }
        return false;
    }

    while (p < pattern.size() && pattern[p] == '*') {
        ++p;
    }
    return p == pattern.size();
}

bool CTrade::MatchGroupFilter(const std::string& value, const std::string& group) noexcept {
    if (group.empty()) {
        return true;
    }

    const std::vector<std::string> raw_parts = split_csv(group);
    struct Cond {
        bool exclude{false};
        std::string pattern{};
    };
    std::vector<Cond> conds;
    conds.reserve(raw_parts.size());

    bool has_include = false;
    for (const std::string& raw : raw_parts) {
        if (raw.empty()) {
            continue;
        }
        Cond c;
        c.pattern = raw;
        if (!c.pattern.empty() && c.pattern.front() == '!') {
            c.exclude = true;
            c.pattern = trim_copy(c.pattern.substr(1));
        } else {
            has_include = true;
        }
        if (!c.pattern.empty()) {
            conds.push_back(std::move(c));
        }
    }

    bool selected = !has_include;
    for (const Cond& cond : conds) {
        if (!MatchPattern(value, cond.pattern)) {
            continue;
        }
        if (cond.exclude) {
            selected = false;
        } else {
            selected = true;
        }
    }
    return selected;
}

std::vector<PositionInfo> CTrade::positions_get(
    std::optional<std::string> symbol,
    std::optional<std::string> group,
    std::optional<uint64_t> ticket) const noexcept {
    std::vector<PositionInfo> out;

    // MT5 behavior: if symbol is provided, ticket is ignored.
    if (symbol.has_value() && !symbol->empty()) {
        for (const auto& [_, pos] : positions_) {
            if (pos.Symbol() == *symbol) {
                out.push_back(pos);
            }
        }
        return out;
    }

    if (ticket.has_value()) {
        const auto it = positions_.find(*ticket);
        if (it != positions_.end()) {
            out.push_back(it->second);
        }
        return out;
    }

    out.reserve(positions_.size());
    for (const auto& [_, pos] : positions_) {
        if (group.has_value() && !group->empty() && !MatchGroupFilter(pos.Symbol(), *group)) {
            continue;
        }
        out.push_back(pos);
    }
    return out;
}

void CTrade::upsert_position(const PositionInfo& position) noexcept {
    positions_[position.Ticket()] = position;
}

std::vector<OrderInfo> CTrade::orders_get(
    std::optional<std::string> symbol,
    std::optional<std::string> group,
    std::optional<uint64_t> ticket) const noexcept {
    std::vector<OrderInfo> out;

    // MT5 behavior: if symbol is provided, ticket is ignored.
    if (symbol.has_value() && !symbol->empty()) {
        for (const auto& [_, ord] : orders_) {
            if (ord.Symbol() == *symbol) {
                out.push_back(ord);
            }
        }
        return out;
    }

    if (ticket.has_value()) {
        const auto it = orders_.find(*ticket);
        if (it != orders_.end()) {
            out.push_back(it->second);
        }
        return out;
    }

    out.reserve(orders_.size());
    for (const auto& [_, ord] : orders_) {
        if (group.has_value() && !group->empty() && !MatchGroupFilter(ord.Symbol(), *group)) {
            continue;
        }
        out.push_back(ord);
    }
    return out;
}

void CTrade::upsert_active_order(const OrderInfo& order) noexcept {
    orders_[order.Ticket()] = order;
}

std::vector<HistoryOrderInfo> CTrade::history_orders_get(
    std::optional<uint64_t> ticket) const noexcept {
    std::vector<HistoryOrderInfo> out;
    if (ticket.has_value()) {
        for (const auto& ord : history_orders_) {
            if (ord.Ticket() == *ticket) {
                out.push_back(ord);
                break;
            }
        }
        return out;
    }
    out = history_orders_;
    return out;
}

std::vector<HistoryOrderInfo> CTrade::history_orders_get(
    int64_t date_from_sec,
    int64_t date_to_sec,
    std::optional<std::string> group,
    std::optional<uint64_t> ticket) const noexcept {
    std::vector<HistoryOrderInfo> out;
    if (date_to_sec > 0 && date_from_sec > date_to_sec) {
        return out;
    }

    for (const auto& ord : history_orders_) {
        if (ticket.has_value() && ord.Ticket() != *ticket) {
            continue;
        }
        if (date_from_sec > 0 && ord.TimeSetup() < date_from_sec) {
            continue;
        }
        if (date_to_sec > 0 && ord.TimeSetup() > date_to_sec) {
            continue;
        }
        if (group.has_value() && !group->empty() && !MatchGroupFilter(ord.Symbol(), *group)) {
            continue;
        }
        out.push_back(ord);
    }
    return out;
}

void CTrade::upsert_history_order(const HistoryOrderInfo& order) noexcept {
    for (auto& existing : history_orders_) {
        if (existing.Ticket() == order.Ticket()) {
            existing = order;
            return;
        }
    }
    history_orders_.push_back(order);
}

std::vector<DealInfo> CTrade::history_deals_get(
    std::optional<uint64_t> ticket) const noexcept {
    std::vector<DealInfo> out;
    if (ticket.has_value()) {
        for (const auto& deal : deals_) {
            if (deal.Ticket() == *ticket) {
                out.push_back(deal);
                break;
            }
        }
        return out;
    }
    out = deals_;
    return out;
}

std::vector<DealInfo> CTrade::history_deals_get(
    int64_t date_from_sec,
    int64_t date_to_sec,
    std::optional<std::string> group,
    std::optional<uint64_t> ticket) const noexcept {
    std::vector<DealInfo> out;
    if (date_to_sec > 0 && date_from_sec > date_to_sec) {
        return out;
    }

    for (const auto& deal : deals_) {
        if (ticket.has_value() && deal.Ticket() != *ticket) {
            continue;
        }
        if (date_from_sec > 0 && deal.Time() < date_from_sec) {
            continue;
        }
        if (date_to_sec > 0 && deal.Time() > date_to_sec) {
            continue;
        }
        if (group.has_value() && !group->empty() && !MatchGroupFilter(deal.Symbol(), *group)) {
            continue;
        }
        out.push_back(deal);
    }
    return out;
}

void CTrade::upsert_history_deal(const DealInfo& deal) noexcept {
    for (auto& existing : deals_) {
        if (existing.Ticket() == deal.Ticket()) {
            existing = deal;
            return;
        }
    }
    deals_.push_back(deal);
}

bool CTrade::symbol_select(const std::string& symbol, bool select) noexcept {
    const SymbolInfo* info = GetSymbolInfo(symbol);
    if (!info) {
        return false;
    }

    const auto name_it = symbol_name_to_id_.find(symbol);
    if (name_it == symbol_name_to_id_.end()) {
        return false;
    }
    auto sym_it = symbols_.find(name_it->second);
    if (sym_it == symbols_.end()) {
        return false;
    }
    sym_it->second.Select(select);
    return true;
}

std::vector<SymbolInfo> CTrade::symbols_get(std::optional<std::string> group) const noexcept {
    std::vector<SymbolInfo> out;
    out.reserve(symbols_.size());
    for (const auto& [_, sym] : symbols_) {
        if (group.has_value() && !group->empty() && !MatchGroupFilter(sym.Name(), *group)) {
            continue;
        }
        out.push_back(sym);
    }
    return out;
}

bool CTrade::history_order_set_state(uint64_t ticket, ENUM_ORDER_STATE state) noexcept {
    for (auto& ord : history_orders_) {
        if (ord.Ticket() == ticket) {
            ord.SetState(state);
            return true;
        }
    }

    auto it = orders_.find(ticket);
    if (it != orders_.end()) {
        it->second.SetState(state);
        return true;
    }
    return false;
}

bool CTrade::history_order_set_done_time(uint64_t ticket, int64_t time_sec, int64_t time_msc) noexcept {
    for (auto& ord : history_orders_) {
        if (ord.Ticket() == ticket) {
            ord.SetTimeDone(time_sec, time_msc);
            return true;
        }
    }
    return false;
}

// ===================================================================
// Symbol Management Implementation
// ===================================================================

void CTrade::UpdatePrices(const std::string& symbol,
                         double bid,
                         double ask,
                         int64_t timestamp) noexcept {
    // Update symbol prices first
    auto name_it = symbol_name_to_id_.find(symbol);
    if (name_it == symbol_name_to_id_.end()) return;

    auto sym_it = symbols_.find(name_it->second);
    if (sym_it == symbols_.end()) return;

    sym_it->second.UpdatePrice(bid, ask, timestamp);

    if (timestamp > 0) {
        current_time_us_ = timestamp;
    }

    // Update positions for this symbol
    for (auto& [ticket, pos] : positions_) {
        if (pos.Symbol() == symbol) {
            double current_price = (pos.PositionType() == ENUM_POSITION_TYPE::POSITION_TYPE_BUY)
                ? bid : ask;
            pos.UpdatePrice(current_price);
        }
    }

    UpdateEquity();
}

// ===================================================================
// Trailing Stop Implementation
// ===================================================================

bool CTrade::TrailingStopEnable(uint64_t ticket,
                               int32_t distance,
                               int32_t step) noexcept {
    auto it = positions_.find(ticket);
    if (it == positions_.end()) return false;

    PositionInfo& pos = it->second;
    pos.SetTrailingDistance(distance);
    pos.SetTrailingStep(step);
    pos.SetTrailingTrigger(pos.PriceCurrent());

    return true;
}

bool CTrade::TrailingStopDisable(uint64_t ticket) noexcept {
    auto it = positions_.find(ticket);
    if (it == positions_.end()) return false;

    PositionInfo& pos = it->second;
    pos.SetTrailingDistance(0);
    pos.SetTrailingStep(0);

    return true;
}

void CTrade::UpdateTrailingStops() noexcept {
    for (auto& [ticket, pos] : positions_) {
        int32_t distance = pos.GetTrailingDistance();
        if (distance == 0) continue;

        const SymbolInfo* info = GetSymbolInfo(pos.Symbol());
        if (!info) continue;

        double trail_distance = distance * info->Point();
        int32_t step = pos.GetTrailingStep();
        double current_price = pos.PriceCurrent();
        double current_sl = pos.StopLoss();

        if (pos.PositionType() == ENUM_POSITION_TYPE::POSITION_TYPE_BUY) {
            // Long position: trail SL below price
            double new_sl = current_price - trail_distance;

            if (current_sl == 0.0 || new_sl > current_sl) {
                // Check step
                if (step > 0) {
                    double step_distance = step * info->Point();
                    if (current_sl > 0.0) {
                        // SL already exists, check if movement is enough
                        if ((new_sl - current_sl) < step_distance) {
                            continue;
                        }
                    } else {
                        // No SL yet, check if price moved enough from trigger
                        double trigger_price = static_cast<double>(pos.GetTrailingTrigger()) /
                                              std::pow(10.0, static_cast<double>(info->Digits()));
                        if ((current_price - trigger_price) < step_distance) {
                            continue;
                        }
                    }
                }

                pos.SetStopLoss(new_sl);
                pos.SetTrailingTrigger(current_price);
            }
        } else {
            // Short position: trail SL above price
            double new_sl = current_price + trail_distance;

            if (current_sl == 0.0 || new_sl < current_sl) {
                // Check step
                if (step > 0) {
                    double step_distance = step * info->Point();
                    if (current_sl > 0.0) {
                        // SL already exists, check if movement is enough
                        if ((current_sl - new_sl) < step_distance) {
                            continue;
                        }
                    } else {
                        // No SL yet, check if price moved enough from trigger
                        double trigger_price = static_cast<double>(pos.GetTrailingTrigger()) /
                                              std::pow(10.0, static_cast<double>(info->Digits()));
                        if ((trigger_price - current_price) < step_distance) {
                            continue;
                        }
                    }
                }

                pos.SetStopLoss(new_sl);
                pos.SetTrailingTrigger(current_price);
            }
        }
    }
}

// ===================================================================
// Snapshot/Restore Implementation
// ===================================================================

CTrade::Snapshot CTrade::CreateSnapshot() const noexcept {
    Snapshot snap;
    snap.account = account_;
    snap.next_ticket = next_ticket_;
    snap.symbols = symbols_;

    snap.positions.reserve(positions_.size());
    for (const auto& [ticket, pos] : positions_) {
        snap.positions.push_back(pos);
    }

    snap.orders.reserve(orders_.size());
    for (const auto& [ticket, order] : orders_) {
        snap.orders.push_back(order);
    }

    snap.deals = deals_;
    snap.history_orders = history_orders_;

    return snap;
}

void CTrade::RestoreSnapshot(const Snapshot& snap) noexcept {
    account_ = snap.account;
    next_ticket_ = snap.next_ticket;
    symbols_ = snap.symbols;
    deals_ = snap.deals;
    history_orders_ = snap.history_orders;

    positions_.clear();
    for (const auto& pos : snap.positions) {
        positions_[pos.Ticket()] = pos;
    }

    orders_.clear();
    for (const auto& order : snap.orders) {
        orders_[order.Ticket()] = order;
    }
}

// ===================================================================
// Internal Helper Methods
// ===================================================================

void CTrade::UpdateEquity() noexcept {
    int64_t total_unrealized_pnl = 0;

    for (const auto& [ticket, pos] : positions_) {
        total_unrealized_pnl += static_cast<int64_t>(pos.Profit() * 1'000'000.0);
    }

    account_.UpdateEquity(total_unrealized_pnl);
}

double CTrade::CalculateMargin(double volume,
                              double price,
                              const SymbolInfo& info) const noexcept {
    double notional = volume * info.ContractSize() * price;
    return notional / account_.Leverage();
}

bool CTrade::CheckRequest(const MqlTradeRequest& request,
                         MqlTradeCheckResult& check) const noexcept {
    (void)request;
    check.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_DONE;
    check.balance = account_.Balance();
    check.equity = account_.Equity();
    check.margin = account_.Margin();
    check.margin_free = account_.FreeMargin();
    check.margin_level = account_.MarginLevel();
    check.comment = "Validated by gateway";
    return true;
}

bool CTrade::ExecuteRequest(const MqlTradeRequest& request,
                           MqlTradeResult& result) noexcept {
    result = MqlTradeResult();

    const SymbolInfo* info = GetSymbolInfo(request.symbol);
    if (!info) {
        result.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID;
        result.comment = "Symbol not found";
        return false;
    }

    result.bid = info->Bid();
    result.ask = info->Ask();

    switch (request.action) {
        case ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_DEAL: {
            // Market execution
            ENUM_POSITION_TYPE pos_type;
            double exec_price;

            if (request.type == ENUM_ORDER_TYPE::ORDER_TYPE_BUY) {
                pos_type = ENUM_POSITION_TYPE::POSITION_TYPE_BUY;
                exec_price = info->Ask();
            } else if (request.type == ENUM_ORDER_TYPE::ORDER_TYPE_SELL) {
                pos_type = ENUM_POSITION_TYPE::POSITION_TYPE_SELL;
                exec_price = info->Bid();
            } else {
                result.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID;
                result.comment = "Invalid order type for market execution";
                return false;
            }

            uint64_t ticket = InternalPositionOpen(
                request.symbol, pos_type, request.volume,
                exec_price, request.sl, request.tp, request.comment
            );

            if (ticket > 0) {
                result.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_DONE;
                result.order = ticket;
                result.volume = request.volume;
                result.price = exec_price;
                result.comment = "Position opened";
                return true;
            } else {
                result.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_ERROR;
                result.comment = "Failed to open position";
                return false;
            }
        }

        case ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_PENDING: {
            // Pending order
            uint64_t ticket = InternalOrderPlace(
                request.symbol, request.type, request.volume,
                request.price, request.stoplimit, request.sl, request.tp,
                request.type_time, request.expiration, request.comment
            );

            if (ticket > 0) {
                result.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_PLACED;
                result.order = ticket;
                result.volume = request.volume;
                result.price = request.price;
                result.comment = "Order placed";
                return true;
            } else {
                result.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_ERROR;
                result.comment = "Failed to place order";
                return false;
            }
        }

        default:
            result.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID;
            result.comment = "Unsupported action";
            return false;
    }
}

uint64_t CTrade::InternalPositionOpen(const std::string& symbol,
                                     ENUM_POSITION_TYPE type,
                                     double volume,
                                     double price,
                                     double sl,
                                     double tp,
                                     const std::string& comment) noexcept {
    const SymbolInfo* info = GetSymbolInfo(symbol);
    if (!info) return 0;

    uint64_t ticket = next_ticket_++;

    PositionInfo pos;
    pos.SetTicket(ticket);
    pos.SetIdentifier(ticket);
    pos.SetSymbol(symbol);
    pos.SetType(type);
    pos.SetVolume(volume);
    pos.SetPriceOpen(price);
    pos.SetPriceCurrent(price);
    pos.SetStopLoss(sl);
    pos.SetTakeProfit(tp);
    pos.SetCommission(0.0);
    pos.SetSwap(0.0);
    pos.SetTime(current_time_us_);
    pos.SetTimeUpdate(current_time_us_);
    pos.SetMagic(magic_number_);
    pos.SetComment(comment);

    // Set symbol properties for profit calculation
    pos.SetDigits(info->Digits());
    pos.SetPoint(info->Point());
    pos.SetContractSize(info->ContractSize());

    pos.RecalculateProfit();

    positions_[ticket] = pos;

    // Update margin
    double margin = CalculateMargin(volume, price, *info);
    account_.AddMargin(static_cast<int64_t>(margin * 1'000'000.0));

    UpdateEquity();

    return ticket;
}

bool CTrade::InternalPositionClose(uint64_t ticket,
                                  double volume,
                                  double price) noexcept {
    auto it = positions_.find(ticket);
    if (it == positions_.end()) return false;

    PositionInfo& pos = it->second;
    const SymbolInfo* info = GetSymbolInfo(pos.Symbol());
    if (!info) return false;

    // Update to final price
    pos.UpdatePrice(price);

    double close_volume = std::min(volume, pos.Volume());
    bool full_close = (close_volume >= pos.Volume());

    // Calculate profit for closed portion
    double profit_ratio = close_volume / pos.Volume();
    double realized_profit = pos.Profit() * profit_ratio;

    // Create deal
    DealInfo deal;
    deal.SetTicket(next_ticket_++);
    deal.SetPositionId(ticket);
    deal.SetOrder(0);
    deal.SetSymbol(pos.Symbol());

    ENUM_DEAL_TYPE deal_type = (pos.PositionType() == ENUM_POSITION_TYPE::POSITION_TYPE_BUY)
        ? ENUM_DEAL_TYPE::DEAL_TYPE_SELL : ENUM_DEAL_TYPE::DEAL_TYPE_BUY;
    deal.SetType(deal_type);
    deal.SetEntry(full_close ? ENUM_DEAL_ENTRY::DEAL_ENTRY_OUT : ENUM_DEAL_ENTRY::DEAL_ENTRY_OUT);

    deal.SetVolume(close_volume);
    deal.SetPrice(price);
    deal.SetProfit(realized_profit);
    deal.SetCommission(pos.Commission() * profit_ratio);
    deal.SetSwap(pos.Swap() * profit_ratio);
    deal.SetTime(current_time_us_);
    deal.SetMagic(pos.Magic());
    deal.SetComment(pos.Comment());
    deal.SetEntryPrice(pos.PriceOpen());
    deal.SetExitPrice(price);
    deal.SetEntryTime(pos.Time());
    deal.SetExitTime(current_time_us_);

    deals_.push_back(deal);

    // Update account
    int64_t realized_pnl_fp = static_cast<int64_t>(realized_profit * 1'000'000.0);
    int64_t commission_fp = static_cast<int64_t>(deal.Commission() * 1'000'000.0);
    int64_t swap_fp = static_cast<int64_t>(deal.Swap() * 1'000'000.0);
    account_.ApplyRealizedPnL(realized_pnl_fp, commission_fp, swap_fp);

    if (full_close) {
        // Release margin
        double margin = CalculateMargin(pos.Volume(), pos.PriceOpen(), *info);
        account_.SubtractMargin(static_cast<int64_t>(margin * 1'000'000.0));

        // Remove position
        positions_.erase(it);
    } else {
        // Reduce position volume
        pos.SetVolume(pos.Volume() - close_volume);
        pos.RecalculateProfit();

        // Adjust margin
        double old_margin = CalculateMargin(pos.Volume() + close_volume, pos.PriceOpen(), *info);
        double new_margin = CalculateMargin(pos.Volume(), pos.PriceOpen(), *info);
        account_.SubtractMargin(static_cast<int64_t>((old_margin - new_margin) * 1'000'000.0));
    }

    UpdateEquity();

    // Set result
    last_result_.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_DONE;
    last_result_.deal = deal.Ticket();
    last_result_.volume = close_volume;
    last_result_.price = price;
    last_result_.comment = full_close ? "Position closed" : "Position partially closed";

    return true;
}

uint64_t CTrade::InternalOrderPlace(const std::string& symbol,
                                   ENUM_ORDER_TYPE type,
                                   double volume,
                                   double price,
                                   double stop_limit,
                                   double sl,
                                   double tp,
                                   ENUM_ORDER_TYPE_TIME type_time,
                                   int64_t expiration,
                                   const std::string& comment) noexcept {
    const SymbolInfo* info = GetSymbolInfo(symbol);
    if (!info) return 0;

    uint64_t ticket = next_ticket_++;

    OrderInfo order;
    order.SetTicket(ticket);
    order.SetSymbol(symbol);
    order.SetOrderType(type);
    order.SetState(ENUM_ORDER_STATE::ORDER_STATE_PLACED);
    order.SetVolumeInitial(volume);
    order.SetVolumeCurrent(volume);
    order.SetPriceOpen(price);
    order.SetStopLoss(sl);
    order.SetTakeProfit(tp);
    order.SetPriceStopLimit(stop_limit);
    order.SetTypeFilling(type_filling_);
    order.SetTypeTime(type_time);
    order.SetTimeExpiration(expiration);
    order.SetTimeSetup(current_time_us_);
    order.SetTimeDone(0);
    order.SetMagic(magic_number_);
    order.SetComment(comment);

    orders_[ticket] = order;

    return ticket;
}

} // namespace haruquant

