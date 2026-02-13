/**
 * @file trade.cpp
 * @brief Implementation of CTrade class
 */

#include "trading/trade.hpp"
#include "util/logger.hpp"
#include <sstream>
#include <iomanip>
#include <cmath>

namespace hqt {

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

    // Check request
    if (!CheckRequest(last_request_, last_check_)) {
        last_result_.retcode = last_check_.retcode;
        last_result_.comment = last_check_.comment;
        return false;
    }

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

    // Check request
    if (!CheckRequest(last_request_, last_check_)) {
        last_result_.retcode = last_check_.retcode;
        last_result_.comment = last_check_.comment;
        return false;
    }

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
    check.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_DONE;
    check.balance = account_.Balance();
    check.equity = account_.Equity();
    check.margin = account_.Margin();
    check.margin_free = account_.FreeMargin();
    check.margin_level = account_.MarginLevel();

    // Validate symbol
    const SymbolInfo* info = GetSymbolInfo(request.symbol);
    if (!info) {
        check.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID;
        check.comment = "Unknown symbol";
        return false;
    }

    // Validate volume
    if (request.volume <= 0.0) {
        check.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID_VOLUME;
        check.comment = "Invalid volume";
        return false;
    }

    if (request.volume < info->LotsMin() || request.volume > info->LotsMax()) {
        check.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID_VOLUME;
        check.comment = "Volume out of range";
        return false;
    }

    // Check margin requirements for new positions
    if (request.action == ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_DEAL ||
        request.action == ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_PENDING) {

        double price = (request.price > 0.0) ? request.price :
            ((request.type == ENUM_ORDER_TYPE::ORDER_TYPE_BUY) ? info->Ask() : info->Bid());

        double required_margin = CalculateMargin(request.volume, price, *info);
        check.margin += required_margin;
        check.margin_free = check.equity - check.margin;

        if (check.margin_free < 0.0) {
            check.retcode = ENUM_TRADE_RETCODE::TRADE_RETCODE_NO_MONEY;
            check.comment = "Insufficient margin";
            return false;
        }

        check.margin_level = (check.margin > 0.0) ? (check.equity / check.margin * 100.0) : 0.0;
    }

    check.comment = "Request valid";
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

} // namespace hqt
