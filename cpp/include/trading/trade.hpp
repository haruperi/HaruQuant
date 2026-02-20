/**
 * @file trade.hpp
 * @brief Trade management class mirroring MT5's CTrade
 *
 * Provides complete trade execution and state management for backtesting.
 * Mirrors MQL5's CTrade class while adding backtesting-specific functionality.
 * Combines order/position/deal management with account state tracking.
 */

#pragma once

#include "account_info.hpp"
#include "position_info.hpp"
#include "order_info.hpp"
#include "deal_info.hpp"
#include "history_order_info.hpp"
#include "symbol_info.hpp"
#include <unordered_map>
#include <vector>
#include <string>
#include <cstdint>
#include <optional>

namespace hqt {

/**
 * @brief Trade request action enumeration
 */
enum class ENUM_TRADE_REQUEST_ACTIONS {
    TRADE_ACTION_DEAL = 1,        // Place order for immediate execution
    TRADE_ACTION_PENDING = 5,     // Place pending order
    TRADE_ACTION_SLTP = 6,        // Modify SL/TP
    TRADE_ACTION_MODIFY = 7,      // Modify order
    TRADE_ACTION_REMOVE = 8,      // Delete pending order
    TRADE_ACTION_CLOSE_BY = 10    // Close position by opposite
};

/**
 * @brief Trade result codes (subset of MT5 codes)
 */
enum class ENUM_TRADE_RETCODE {
    TRADE_RETCODE_DONE = 10009,           // Request completed
    TRADE_RETCODE_PLACED = 10008,         // Order placed
    TRADE_RETCODE_DONE_PARTIAL = 10010,   // Partial fill
    TRADE_RETCODE_ERROR = 10011,          // Request error
    TRADE_RETCODE_TIMEOUT = 10012,        // Request timeout
    TRADE_RETCODE_INVALID = 10013,        // Invalid request
    TRADE_RETCODE_INVALID_VOLUME = 10014, // Invalid volume
    TRADE_RETCODE_INVALID_PRICE = 10015,  // Invalid price
    TRADE_RETCODE_INVALID_STOPS = 10016,  // Invalid SL/TP
    TRADE_RETCODE_TRADE_DISABLED = 10017, // Trading disabled
    TRADE_RETCODE_MARKET_CLOSED = 10018,  // Market closed
    TRADE_RETCODE_NO_MONEY = 10019,       // Insufficient funds
    TRADE_RETCODE_PRICE_CHANGED = 10020,  // Price changed
    TRADE_RETCODE_PRICE_OFF = 10021,      // No quotes
    TRADE_RETCODE_INVALID_EXPIRATION = 10022, // Invalid expiration
    TRADE_RETCODE_ORDER_CHANGED = 10023,  // Order changed
    TRADE_RETCODE_TOO_MANY_REQUESTS = 10024, // Too many requests
    TRADE_RETCODE_NO_CHANGES = 10025,     // No changes
    TRADE_RETCODE_REJECT = 10026,         // Request rejected
    TRADE_RETCODE_CANCEL = 10027,         // Request cancelled
    TRADE_RETCODE_FROZEN = 10029,         // Trading frozen
    TRADE_RETCODE_INVALID_FILL = 10030,   // Invalid filling type
    TRADE_RETCODE_CONNECTION = 10031,     // No connection
    TRADE_RETCODE_ONLY_REAL = 10032,      // Only real allowed
    TRADE_RETCODE_LIMIT_ORDERS = 10033,   // Order limit reached
    TRADE_RETCODE_LIMIT_VOLUME = 10034,   // Volume limit reached
    TRADE_RETCODE_INVALID_ORDER = 10035,  // Invalid order
    TRADE_RETCODE_POSITION_CLOSED = 10036 // Position already closed
};

/**
 * @brief Trade request structure
 */
struct MqlTradeRequest {
    ENUM_TRADE_REQUEST_ACTIONS action;
    uint64_t magic;
    uint64_t order;
    std::string symbol;
    double volume;
    double price;
    double stoplimit;
    double sl;
    double tp;
    uint64_t deviation;
    ENUM_ORDER_TYPE type;
    ENUM_ORDER_TYPE_FILLING type_filling;
    ENUM_ORDER_TYPE_TIME type_time;
    int64_t expiration;
    std::string comment;
    uint64_t position;
    uint64_t position_by;

    MqlTradeRequest() noexcept
        : action(ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_DEAL),
          magic(0), order(0), volume(0.0), price(0.0), stoplimit(0.0),
          sl(0.0), tp(0.0), deviation(0),
          type(ENUM_ORDER_TYPE::ORDER_TYPE_BUY),
          type_filling(ENUM_ORDER_TYPE_FILLING::ORDER_FILLING_FOK),
          type_time(ENUM_ORDER_TYPE_TIME::ORDER_TIME_GTC),
          expiration(0), position(0), position_by(0) {}
};

/**
 * @brief Trade result structure
 */
struct MqlTradeResult {
    ENUM_TRADE_RETCODE retcode;
    uint64_t deal;
    uint64_t order;
    double volume;
    double price;
    double bid;
    double ask;
    std::string comment;
    uint32_t request_id;
    uint32_t retcode_external;

    MqlTradeResult() noexcept
        : retcode(ENUM_TRADE_RETCODE::TRADE_RETCODE_ERROR),
          deal(0), order(0), volume(0.0), price(0.0),
          bid(0.0), ask(0.0), request_id(0), retcode_external(0) {}
};

/**
 * @brief Trade check result structure
 */
struct MqlTradeCheckResult {
    ENUM_TRADE_RETCODE retcode;
    double balance;
    double equity;
    double profit;
    double margin;
    double margin_free;
    double margin_level;
    std::string comment;

    MqlTradeCheckResult() noexcept
        : retcode(ENUM_TRADE_RETCODE::TRADE_RETCODE_DONE),
          balance(0.0), equity(0.0), profit(0.0),
          margin(0.0), margin_free(0.0), margin_level(0.0) {}
};

/**
 * @brief Trade class mirroring MT5's CTrade
 *
 * Provides complete trade execution and state management for backtesting.
 * Maintains account state, positions, orders, deals, and history.
 */
class CTrade {
private:
    // Account and state
    AccountInfo account_;
    std::unordered_map<uint64_t, PositionInfo> positions_;
    std::unordered_map<uint64_t, OrderInfo> orders_;
    std::vector<DealInfo> deals_;
    std::vector<HistoryOrderInfo> history_orders_;
    uint64_t next_ticket_;

    // Symbol cache
    std::unordered_map<uint32_t, SymbolInfo> symbols_;
    std::unordered_map<std::string, uint32_t> symbol_name_to_id_;

    // Trade settings
    uint32_t magic_number_;
    uint64_t deviation_;
    ENUM_ORDER_TYPE_FILLING type_filling_;
    bool async_mode_;
    int log_level_;

    // Last request and result
    MqlTradeRequest last_request_;
    MqlTradeResult last_result_;
    MqlTradeCheckResult last_check_;

    // Current timestamp (for backtesting)
    int64_t current_time_us_;

public:
    /**
     * @brief Construct trade manager
     * @param initial_balance Starting balance in account currency
     * @param currency Account currency (e.g., "USD")
     * @param leverage Account leverage (e.g., 100 for 1:100)
     */
    explicit CTrade(double initial_balance = 10000.0,
                    const std::string& currency = "USD",
                    uint32_t leverage = 100) noexcept
        : account_(initial_balance, currency, leverage),
          next_ticket_(1000),
          magic_number_(0),
          deviation_(10),
          type_filling_(ENUM_ORDER_TYPE_FILLING::ORDER_FILLING_FOK),
          async_mode_(false),
          log_level_(0),
          current_time_us_(0) {}

    // ===================================================================
    // MT5 CTrade API - Configuration Methods
    // ===================================================================

    /**
     * @brief Set logging level
     * @param log_level Logging level (0 = none, 1 = errors, 2 = all)
     */
    void LogLevel(int log_level) noexcept {
        log_level_ = log_level;
    }

    /**
     * @brief Get logging level
     */
    int LogLevel() const noexcept {
        return log_level_;
    }

    /**
     * @brief Set expert magic number
     * @param magic Magic number for all operations
     */
    void SetExpertMagicNumber(uint32_t magic) noexcept {
        magic_number_ = magic;
    }

    /**
     * @brief Get expert magic number
     */
    uint32_t ExpertMagicNumber() const noexcept {
        return magic_number_;
    }

    /**
     * @brief Set allowed price deviation in points
     * @param deviation Deviation in points
     */
    void SetDeviationInPoints(uint64_t deviation) noexcept {
        deviation_ = deviation;
    }

    /**
     * @brief Get allowed price deviation
     */
    uint64_t DeviationInPoints() const noexcept {
        return deviation_;
    }

    /**
     * @brief Set order filling type
     * @param filling Filling type
     */
    void SetTypeFilling(ENUM_ORDER_TYPE_FILLING filling) noexcept {
        type_filling_ = filling;
    }

    /**
     * @brief Set filling type from symbol properties
     * @param symbol Symbol name
     * @return True if successful
     */
    bool SetTypeFillingBySymbol(const std::string& symbol) noexcept {
        const SymbolInfo* info = GetSymbolInfo(symbol);
        if (!info) return false;

        // Symbol registered successfully (type_filling_ keeps current value)
        return true;
    }

    /**
     * @brief Enable/disable asynchronous mode
     * @param mode True for async mode
     */
    void SetAsyncMode(bool mode) noexcept {
        async_mode_ = mode;
    }

    /**
     * @brief Get async mode status
     */
    bool AsyncMode() const noexcept {
        return async_mode_;
    }

    /**
     * @brief Set margin calculation mode (placeholder for backtesting)
     */
    void SetMarginMode() noexcept {
        // In backtesting, margin mode is always aligned with account
    }

    // ===================================================================
    // MT5 CTrade API - Position Management
    // ===================================================================

    /**
     * @brief Open position
     * @param symbol Symbol name
     * @param order_type ORDER_TYPE_BUY or ORDER_TYPE_SELL
     * @param volume Volume in lots
     * @param price Entry price (0 = market)
     * @param sl Stop loss (0 = none)
     * @param tp Take profit (0 = none)
     * @param comment Comment
     * @return True if successful
     */
    bool PositionOpen(const std::string& symbol,
                     ENUM_ORDER_TYPE order_type,
                     double volume,
                     double price = 0.0,
                     double sl = 0.0,
                     double tp = 0.0,
                     const std::string& comment = "") noexcept;

    /**
     * @brief Modify position by symbol
     * @param symbol Symbol name
     * @param sl New stop loss
     * @param tp New take profit
     * @return True if successful
     */
    bool PositionModify(const std::string& symbol,
                       double sl,
                       double tp) noexcept;

    /**
     * @brief Modify position by ticket
     * @param ticket Position ticket
     * @param sl New stop loss
     * @param tp New take profit
     * @return True if successful
     */
    bool PositionModify(uint64_t ticket,
                       double sl,
                       double tp) noexcept;

    /**
     * @brief Close position by symbol
     * @param symbol Symbol name
     * @param deviation Allowed slippage in points (0 = use default)
     * @return True if successful
     */
    bool PositionClose(const std::string& symbol,
                      uint64_t deviation = 0) noexcept;

    /**
     * @brief Close position by ticket
     * @param ticket Position ticket
     * @param deviation Allowed slippage in points (0 = use default)
     * @return True if successful
     */
    bool PositionClose(uint64_t ticket,
                      uint64_t deviation = 0) noexcept;

    /**
     * @brief Partially close position
     * @param symbol Symbol name
     * @param volume Volume to close
     * @param deviation Allowed slippage in points (0 = use default)
     * @return True if successful
     */
    bool PositionClosePartial(const std::string& symbol,
                             double volume,
                             uint64_t deviation = 0) noexcept;

    /**
     * @brief Partially close position by ticket
     * @param ticket Position ticket
     * @param volume Volume to close
     * @param deviation Allowed slippage in points (0 = use default)
     * @return True if successful
     */
    bool PositionClosePartial(uint64_t ticket,
                             double volume,
                             uint64_t deviation = 0) noexcept;

    /**
     * @brief Close position by opposite position
     * @param ticket Position to close
     * @param ticket_by Opposite position
     * @return True if successful
     */
    bool PositionCloseBy(uint64_t ticket,
                        uint64_t ticket_by) noexcept;

    // ===================================================================
    // MT5 CTrade API - Order Management
    // ===================================================================

    /**
     * @brief Open pending order
     * @param symbol Symbol name
     * @param order_type Order type (LIMIT, STOP, etc.)
     * @param volume Volume in lots
     * @param limit_price Limit price
     * @param stop_price Stop price (for STOP_LIMIT)
     * @param sl Stop loss
     * @param tp Take profit
     * @param type_time Time in force
     * @param expiration Expiration time
     * @param comment Comment
     * @return True if successful
     */
    bool OrderOpen(const std::string& symbol,
                  ENUM_ORDER_TYPE order_type,
                  double volume,
                  double limit_price,
                  double stop_price = 0.0,
                  double sl = 0.0,
                  double tp = 0.0,
                  ENUM_ORDER_TYPE_TIME type_time = ENUM_ORDER_TYPE_TIME::ORDER_TIME_GTC,
                  int64_t expiration = 0,
                  const std::string& comment = "") noexcept;

    /**
     * @brief Modify pending order
     * @param ticket Order ticket
     * @param price New price
     * @param sl New stop loss
     * @param tp New take profit
     * @param stop_limit New stop limit (for STOP_LIMIT orders)
     * @param expiration New expiration
     * @return True if successful
     */
    bool OrderModify(uint64_t ticket,
                    double price,
                    double sl,
                    double tp,
                    double stop_limit = 0.0,
                    int64_t expiration = 0) noexcept;

    /**
     * @brief Delete pending order
     * @param ticket Order ticket
     * @return True if successful
     */
    bool OrderDelete(uint64_t ticket) noexcept;

    // ===================================================================
    // MT5 CTrade API - Quick Trade Methods
    // ===================================================================

    /**
     * @brief Open BUY position at market
     * @param volume Volume in lots
     * @param symbol Symbol name (empty = current)
     * @param price Entry price (0 = market)
     * @param sl Stop loss
     * @param tp Take profit
     * @param comment Comment
     * @return True if successful
     */
    bool Buy(double volume,
            const std::string& symbol = "",
            double price = 0.0,
            double sl = 0.0,
            double tp = 0.0,
            const std::string& comment = "") noexcept {
        return PositionOpen(symbol, ENUM_ORDER_TYPE::ORDER_TYPE_BUY,
                          volume, price, sl, tp, comment);
    }

    /**
     * @brief Open SELL position at market
     * @param volume Volume in lots
     * @param symbol Symbol name (empty = current)
     * @param price Entry price (0 = market)
     * @param sl Stop loss
     * @param tp Take profit
     * @param comment Comment
     * @return True if successful
     */
    bool Sell(double volume,
             const std::string& symbol = "",
             double price = 0.0,
             double sl = 0.0,
             double tp = 0.0,
             const std::string& comment = "") noexcept {
        return PositionOpen(symbol, ENUM_ORDER_TYPE::ORDER_TYPE_SELL,
                          volume, price, sl, tp, comment);
    }

    /**
     * @brief Place BUY LIMIT order
     */
    bool BuyLimit(double volume,
                 double price,
                 const std::string& symbol = "",
                 double sl = 0.0,
                 double tp = 0.0,
                 ENUM_ORDER_TYPE_TIME type_time = ENUM_ORDER_TYPE_TIME::ORDER_TIME_GTC,
                 int64_t expiration = 0,
                 const std::string& comment = "") noexcept {
        return OrderOpen(symbol, ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT,
                       volume, price, 0.0, sl, tp, type_time, expiration, comment);
    }

    /**
     * @brief Place BUY STOP order
     */
    bool BuyStop(double volume,
                double price,
                const std::string& symbol = "",
                double sl = 0.0,
                double tp = 0.0,
                ENUM_ORDER_TYPE_TIME type_time = ENUM_ORDER_TYPE_TIME::ORDER_TIME_GTC,
                int64_t expiration = 0,
                const std::string& comment = "") noexcept {
        return OrderOpen(symbol, ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP,
                       volume, price, 0.0, sl, tp, type_time, expiration, comment);
    }

    /**
     * @brief Place SELL LIMIT order
     */
    bool SellLimit(double volume,
                  double price,
                  const std::string& symbol = "",
                  double sl = 0.0,
                  double tp = 0.0,
                  ENUM_ORDER_TYPE_TIME type_time = ENUM_ORDER_TYPE_TIME::ORDER_TIME_GTC,
                  int64_t expiration = 0,
                  const std::string& comment = "") noexcept {
        return OrderOpen(symbol, ENUM_ORDER_TYPE::ORDER_TYPE_SELL_LIMIT,
                       volume, price, 0.0, sl, tp, type_time, expiration, comment);
    }

    /**
     * @brief Place SELL STOP order
     */
    bool SellStop(double volume,
                 double price,
                 const std::string& symbol = "",
                 double sl = 0.0,
                 double tp = 0.0,
                 ENUM_ORDER_TYPE_TIME type_time = ENUM_ORDER_TYPE_TIME::ORDER_TIME_GTC,
                 int64_t expiration = 0,
                 const std::string& comment = "") noexcept {
        return OrderOpen(symbol, ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP,
                       volume, price, 0.0, sl, tp, type_time, expiration, comment);
    }

    // ===================================================================
    // MT5 CTrade API - Request Access
    // ===================================================================

    /**
     * @brief Get last trade request
     */
    const MqlTradeRequest& Request() const noexcept {
        return last_request_;
    }

    ENUM_TRADE_REQUEST_ACTIONS RequestAction() const noexcept {
        return last_request_.action;
    }

    uint64_t RequestMagic() const noexcept {
        return last_request_.magic;
    }

    uint64_t RequestOrder() const noexcept {
        return last_request_.order;
    }

    std::string RequestSymbol() const noexcept {
        return last_request_.symbol;
    }

    double RequestVolume() const noexcept {
        return last_request_.volume;
    }

    double RequestPrice() const noexcept {
        return last_request_.price;
    }

    double RequestStopLimit() const noexcept {
        return last_request_.stoplimit;
    }

    double RequestSL() const noexcept {
        return last_request_.sl;
    }

    double RequestTP() const noexcept {
        return last_request_.tp;
    }

    uint64_t RequestDeviation() const noexcept {
        return last_request_.deviation;
    }

    ENUM_ORDER_TYPE RequestType() const noexcept {
        return last_request_.type;
    }

    ENUM_ORDER_TYPE_FILLING RequestTypeFilling() const noexcept {
        return last_request_.type_filling;
    }

    ENUM_ORDER_TYPE_TIME RequestTypeTime() const noexcept {
        return last_request_.type_time;
    }

    int64_t RequestExpiration() const noexcept {
        return last_request_.expiration;
    }

    std::string RequestComment() const noexcept {
        return last_request_.comment;
    }

    uint64_t RequestPosition() const noexcept {
        return last_request_.position;
    }

    uint64_t RequestPositionBy() const noexcept {
        return last_request_.position_by;
    }

    // ===================================================================
    // MT5 CTrade API - Result Access
    // ===================================================================

    /**
     * @brief Get last trade result
     */
    const MqlTradeResult& Result() const noexcept {
        return last_result_;
    }

    ENUM_TRADE_RETCODE ResultRetcode() const noexcept {
        return last_result_.retcode;
    }

    uint64_t ResultDeal() const noexcept {
        return last_result_.deal;
    }

    uint64_t ResultOrder() const noexcept {
        return last_result_.order;
    }

    double ResultVolume() const noexcept {
        return last_result_.volume;
    }

    double ResultPrice() const noexcept {
        return last_result_.price;
    }

    double ResultBid() const noexcept {
        return last_result_.bid;
    }

    double ResultAsk() const noexcept {
        return last_result_.ask;
    }

    std::string ResultComment() const noexcept {
        return last_result_.comment;
    }

    uint32_t ResultRetcodeExternal() const noexcept {
        return last_result_.retcode_external;
    }

    // ===================================================================
    // MT5 CTrade API - Check Result Access
    // ===================================================================

    /**
     * @brief Get last check result
     */
    const MqlTradeCheckResult& CheckResult() const noexcept {
        return last_check_;
    }

    ENUM_TRADE_RETCODE CheckResultRetcode() const noexcept {
        return last_check_.retcode;
    }

    double CheckResultBalance() const noexcept {
        return last_check_.balance;
    }

    double CheckResultEquity() const noexcept {
        return last_check_.equity;
    }

    double CheckResultProfit() const noexcept {
        return last_check_.profit;
    }

    double CheckResultMargin() const noexcept {
        return last_check_.margin;
    }

    double CheckResultMarginFree() const noexcept {
        return last_check_.margin_free;
    }

    double CheckResultMarginLevel() const noexcept {
        return last_check_.margin_level;
    }

    std::string CheckResultComment() const noexcept {
        return last_check_.comment;
    }

    bool OrderCheck(const MqlTradeRequest& request, MqlTradeCheckResult& check) const noexcept {
        return CheckRequest(request, check);
    }

    MqlTradeCheckResult OrderCheck(const MqlTradeRequest& request) const noexcept {
        MqlTradeCheckResult check;
        CheckRequest(request, check);
        return check;
    }

    // ===================================================================
    // MT5 CTrade API - Utility Methods
    // ===================================================================

    /**
     * @brief Print last request to log
     */
    void PrintRequest() const noexcept;

    /**
     * @brief Print last result to log
     */
    void PrintResult() const noexcept;

    /**
     * @brief Format request as string
     */
    std::string FormatRequest(const MqlTradeRequest& request) const noexcept;

    /**
     * @brief Format request result as string
     */
    std::string FormatRequestResult(const MqlTradeRequest& request,
                                   const MqlTradeResult& result) const noexcept;

    // ===================================================================
    // Backtesting Extensions - Symbol Management
    // ===================================================================

    /**
     * @brief Register symbol for trading
     * @param info Symbol information
     */
    void RegisterSymbol(const SymbolInfo& info) noexcept {
        uint32_t id = info.SymbolId();
        symbols_[id] = info;
        symbol_name_to_id_[info.Name()] = id;
    }

    /**
     * @brief Update symbol prices
     * @param symbol Symbol name
     * @param bid Bid price
     * @param ask Ask price
     * @param timestamp Timestamp in microseconds
     */
    void UpdatePrices(const std::string& symbol,
                     double bid,
                     double ask,
                     int64_t timestamp = 0) noexcept;

    /**
     * @brief Set current time for backtesting
     * @param timestamp_us Timestamp in microseconds
     */
    void SetCurrentTime(int64_t timestamp_us) noexcept {
        current_time_us_ = timestamp_us;
    }

    // ===================================================================
    // Backtesting Extensions - State Access
    // ===================================================================

    /**
     * @brief Get account info
     */
    const AccountInfo& Account() const noexcept {
        return account_;
    }

    /**
     * @brief Get mutable account info (for backtesting)
     */
    AccountInfo& Account() noexcept {
        return account_;
    }

    /**
     * @brief Get position by ticket
     */
    const PositionInfo* GetPosition(uint64_t ticket) const noexcept {
        auto it = positions_.find(ticket);
        return (it != positions_.end()) ? &it->second : nullptr;
    }

    /**
     * @brief Get all positions
     */
    std::vector<PositionInfo> GetPositions() const noexcept {
        std::vector<PositionInfo> result;
        result.reserve(positions_.size());
        for (const auto& [ticket, pos] : positions_) {
            result.push_back(pos);
        }
        return result;
    }

    /**
     * @brief Get positions for symbol
     */
    std::vector<PositionInfo> GetPositions(const std::string& symbol) const noexcept {
        std::vector<PositionInfo> result;
        for (const auto& [ticket, pos] : positions_) {
            if (pos.Symbol() == symbol) {
                result.push_back(pos);
            }
        }
        return result;
    }

    /**
     * @brief Get order by ticket
     */
    const OrderInfo* GetOrder(uint64_t ticket) const noexcept {
        auto it = orders_.find(ticket);
        return (it != orders_.end()) ? &it->second : nullptr;
    }

    /**
     * @brief Get all pending orders
     */
    std::vector<OrderInfo> GetOrders() const noexcept {
        std::vector<OrderInfo> result;
        result.reserve(orders_.size());
        for (const auto& [ticket, order] : orders_) {
            result.push_back(order);
        }
        return result;
    }

    /**
     * @brief Get all deals
     */
    const std::vector<DealInfo>& GetDeals() const noexcept {
        return deals_;
    }

    /**
     * @brief Get all history orders
     */
    const std::vector<HistoryOrderInfo>& GetHistoryOrders() const noexcept {
        return history_orders_;
    }

    // ===================================================================
    // MT5 Python-style Query API
    // ===================================================================

    std::vector<PositionInfo> positions_get(
        std::optional<std::string> symbol = std::nullopt,
        std::optional<std::string> group = std::nullopt,
        std::optional<uint64_t> ticket = std::nullopt) const noexcept;

    void upsert_position(const PositionInfo& position) noexcept;

    size_t positions_total() const noexcept {
        return positions_.size();
    }

    std::vector<OrderInfo> orders_get(
        std::optional<std::string> symbol = std::nullopt,
        std::optional<std::string> group = std::nullopt,
        std::optional<uint64_t> ticket = std::nullopt) const noexcept;

    void upsert_active_order(const OrderInfo& order) noexcept;

    size_t orders_total() const noexcept {
        return orders_.size();
    }

    std::vector<HistoryOrderInfo> history_orders_get(
        std::optional<uint64_t> ticket = std::nullopt) const noexcept;

    std::vector<HistoryOrderInfo> history_orders_get(
        int64_t date_from_sec,
        int64_t date_to_sec,
        std::optional<std::string> group = std::nullopt,
        std::optional<uint64_t> ticket = std::nullopt) const noexcept;

    void upsert_history_order(const HistoryOrderInfo& order) noexcept;

    size_t history_orders_total() const noexcept {
        return history_orders_.size();
    }

    std::vector<DealInfo> history_deals_get(
        std::optional<uint64_t> ticket = std::nullopt) const noexcept;

    std::vector<DealInfo> history_deals_get(
        int64_t date_from_sec,
        int64_t date_to_sec,
        std::optional<std::string> group = std::nullopt,
        std::optional<uint64_t> ticket = std::nullopt) const noexcept;

    void upsert_history_deal(const DealInfo& deal) noexcept;

    size_t history_deals_total() const noexcept {
        return deals_.size();
    }

    bool symbol_select(const std::string& symbol, bool select = true) noexcept;

    std::vector<SymbolInfo> symbols_get(
        std::optional<std::string> group = std::nullopt) const noexcept;

    size_t symbols_total() const noexcept {
        return symbols_.size();
    }

    bool history_order_set_state(uint64_t ticket, ENUM_ORDER_STATE state) noexcept;
    bool history_order_set_done_time(uint64_t ticket, int64_t time_sec, int64_t time_msc) noexcept;

    // ===================================================================
    // Backtesting Extensions - Trailing Stops
    // ===================================================================

    /**
     * @brief Enable trailing stop for position
     * @param ticket Position ticket
     * @param distance Trailing distance in points
     * @param step Step size in points (0 = continuous)
     * @return True if successful
     */
    bool TrailingStopEnable(uint64_t ticket,
                           int32_t distance,
                           int32_t step = 0) noexcept;

    /**
     * @brief Disable trailing stop
     * @param ticket Position ticket
     * @return True if successful
     */
    bool TrailingStopDisable(uint64_t ticket) noexcept;

    /**
     * @brief Update all trailing stops
     */
    void UpdateTrailingStops() noexcept;

    // ===================================================================
    // Backtesting Extensions - Snapshot/Restore
    // ===================================================================

    /**
     * @brief State snapshot
     */
    struct Snapshot {
        AccountInfo account;
        std::vector<PositionInfo> positions;
        std::vector<OrderInfo> orders;
        std::vector<DealInfo> deals;
        std::vector<HistoryOrderInfo> history_orders;
        uint64_t next_ticket;
        std::unordered_map<uint32_t, SymbolInfo> symbols;

        size_t EstimatedSize() const noexcept {
            return sizeof(AccountInfo) +
                   positions.size() * sizeof(PositionInfo) +
                   orders.size() * sizeof(OrderInfo) +
                   deals.size() * sizeof(DealInfo) +
                   history_orders.size() * sizeof(HistoryOrderInfo) +
                   symbols.size() * sizeof(SymbolInfo);
        }
    };

    /**
     * @brief Create snapshot
     */
    Snapshot CreateSnapshot() const noexcept;

    /**
     * @brief Restore from snapshot
     */
    void RestoreSnapshot(const Snapshot& snap) noexcept;

private:
    // ===================================================================
    // Internal Helper Methods
    // ===================================================================

    /**
     * @brief Get symbol info by name
     */
    const SymbolInfo* GetSymbolInfo(const std::string& symbol) const noexcept {
        auto it = symbol_name_to_id_.find(symbol);
        if (it == symbol_name_to_id_.end()) return nullptr;

        auto sym_it = symbols_.find(it->second);
        return (sym_it != symbols_.end()) ? &sym_it->second : nullptr;
    }

    /**
     * @brief Update equity from positions
     */
    void UpdateEquity() noexcept;

    /**
     * @brief Calculate margin for position
     */
    double CalculateMargin(double volume,
                          double price,
                          const SymbolInfo& info) const noexcept;

    /**
     * @brief Validate trade request
     */
    bool CheckRequest(const MqlTradeRequest& request,
                     MqlTradeCheckResult& check) const noexcept;

    /**
     * @brief Execute trade request
     */
    bool ExecuteRequest(const MqlTradeRequest& request,
                       MqlTradeResult& result) noexcept;

    /**
     * @brief Internal position open implementation
     */
    uint64_t InternalPositionOpen(const std::string& symbol,
                                 ENUM_POSITION_TYPE type,
                                 double volume,
                                 double price,
                                 double sl,
                                 double tp,
                                 const std::string& comment) noexcept;

    /**
     * @brief Internal position close implementation
     */
    bool InternalPositionClose(uint64_t ticket,
                              double volume,
                              double price) noexcept;

    /**
     * @brief Internal order place implementation
     */
    uint64_t InternalOrderPlace(const std::string& symbol,
                               ENUM_ORDER_TYPE type,
                               double volume,
                               double price,
                               double stop_limit,
                               double sl,
                               double tp,
                               ENUM_ORDER_TYPE_TIME type_time,
                               int64_t expiration,
                               const std::string& comment) noexcept;

    static bool MatchPattern(const std::string& value, const std::string& pattern) noexcept;
    static bool MatchGroupFilter(const std::string& value, const std::string& group) noexcept;
};

} // namespace hqt
