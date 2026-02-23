/**
FILE: include\trading\history_order_info.hpp

PURPOSE:
Defines history_order_info.hpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in history_order_info.hpp.
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

#include "order_info.hpp"
#include <cstdint>
#include <string>
#include <cmath>

namespace haruquant {

/**
 * @brief Historical order information class (mirrors MT5 CHistoryOrderInfo)
 *
 * Provides read-only access to historical order properties.
 * Represents orders that have been executed, canceled, or expired.
 * Inherits from OrderInfo but represents completed orders in history.
 */
class HistoryOrderInfo {
private:
    // Core identification
    uint64_t ticket_;
    std::string symbol_;
    uint32_t magic_;
    uint64_t position_id_;

    // Order type and state
    ENUM_ORDER_TYPE order_type_;
    ENUM_ORDER_STATE state_;

    // Volume
    double volume_initial_;
    double volume_current_;

    // Prices (fixed-point internally)
    int64_t price_open_;
    int64_t price_current_;
    int64_t price_stoplimit_;
    int64_t stop_loss_;
    int64_t take_profit_;

    // Time information
    int64_t time_setup_;          // Setup time (seconds)
    int64_t time_setup_msc_;      // Setup time (milliseconds)
    int64_t time_expiration_;     // Expiration time
    int64_t time_done_;           // Execution/cancellation time
    int64_t time_done_msc_;       // Execution/cancellation time (ms)

    // Order policies
    ENUM_ORDER_TYPE_FILLING type_filling_;
    ENUM_ORDER_TYPE_TIME type_time_;

    // Comment
    std::string comment_;

    // Symbol info (for price conversions)
    int32_t digits_;

public:
    /**
     * @brief Constructor
     */
    HistoryOrderInfo()
        : ticket_(0),
          symbol_(""),
          magic_(0),
          position_id_(0),
          order_type_(ENUM_ORDER_TYPE::ORDER_TYPE_BUY),
          state_(ENUM_ORDER_STATE::ORDER_STATE_FILLED),
          volume_initial_(0.0),
          volume_current_(0.0),
          price_open_(0),
          price_current_(0),
          price_stoplimit_(0),
          stop_loss_(0),
          take_profit_(0),
          time_setup_(0),
          time_setup_msc_(0),
          time_expiration_(0),
          time_done_(0),
          time_done_msc_(0),
          type_filling_(ENUM_ORDER_TYPE_FILLING::ORDER_FILLING_FOK),
          type_time_(ENUM_ORDER_TYPE_TIME::ORDER_TIME_GTC),
          comment_(""),
          digits_(5) {}

    /**
     * @brief Construct from OrderInfo (when order moves to history)
     * @param order Active order that moved to history
     */
    explicit HistoryOrderInfo(const OrderInfo& order)
        : ticket_(order.Ticket()),
          symbol_(order.Symbol()),
          magic_(order.Magic()),
          position_id_(order.PositionId()),
          order_type_(order.OrderType()),
          state_(order.State()),
          volume_initial_(order.VolumeInitial()),
          volume_current_(order.VolumeCurrent()),
          time_setup_(order.TimeSetup()),
          time_setup_msc_(order.TimeSetupMsc()),
          time_expiration_(order.TimeExpiration()),
          time_done_(order.TimeDone()),
          time_done_msc_(order.TimeDoneMsc()),
          type_filling_(order.TypeFilling()),
          type_time_(order.TypeTime()),
          comment_(order.Comment()),
          digits_(5) {
        // Copy prices from OrderInfo via public double accessors, converting to fixed-point
        double multiplier = std::pow(10.0, static_cast<double>(digits_));
        price_open_ = static_cast<int64_t>(order.PriceOpen() * multiplier + 0.5);
        price_current_ = static_cast<int64_t>(order.PriceCurrent() * multiplier + 0.5);
        price_stoplimit_ = static_cast<int64_t>(order.PriceStopLimit() * multiplier + 0.5);
        stop_loss_ = static_cast<int64_t>(order.StopLoss() * multiplier + 0.5);
        take_profit_ = static_cast<int64_t>(order.TakeProfit() * multiplier + 0.5);
    }

    // --- Integer Property Accessors (MT5 API) ---

    /**
     * @brief Get order ticket number
     * @return Order ticket
     */
    uint64_t Ticket() const noexcept { return ticket_; }

    /**
     * @brief Get order placement time
     * @return Time in seconds since epoch
     */
    int64_t TimeSetup() const noexcept { return time_setup_; }

    /**
     * @brief Get order placement time in milliseconds
     * @return Time in milliseconds since epoch
     */
    int64_t TimeSetupMsc() const noexcept { return time_setup_msc_; }

    /**
     * @brief Get order type
     * @return Order type
     */
    ENUM_ORDER_TYPE OrderType() const noexcept { return order_type_; }

    /**
     * @brief Get order type as string
     * @return Order type description
     */
    std::string OrderTypeDescription() const noexcept {
        switch (order_type_) {
            case ENUM_ORDER_TYPE::ORDER_TYPE_BUY: return "Buy";
            case ENUM_ORDER_TYPE::ORDER_TYPE_SELL: return "Sell";
            case ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT: return "Buy Limit";
            case ENUM_ORDER_TYPE::ORDER_TYPE_SELL_LIMIT: return "Sell Limit";
            case ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP: return "Buy Stop";
            case ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP: return "Sell Stop";
            case ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP_LIMIT: return "Buy Stop Limit";
            case ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP_LIMIT: return "Sell Stop Limit";
            default: return "Unknown";
        }
    }

    /**
     * @brief Get order state
     * @return Final state
     */
    ENUM_ORDER_STATE State() const noexcept { return state_; }

    /**
     * @brief Get order state as string
     * @return State description
     */
    std::string StateDescription() const noexcept {
        switch (state_) {
            case ENUM_ORDER_STATE::ORDER_STATE_STARTED: return "Started";
            case ENUM_ORDER_STATE::ORDER_STATE_PLACED: return "Placed";
            case ENUM_ORDER_STATE::ORDER_STATE_CANCELED: return "Canceled";
            case ENUM_ORDER_STATE::ORDER_STATE_PARTIAL: return "Partial";
            case ENUM_ORDER_STATE::ORDER_STATE_FILLED: return "Filled";
            case ENUM_ORDER_STATE::ORDER_STATE_REJECTED: return "Rejected";
            case ENUM_ORDER_STATE::ORDER_STATE_EXPIRED: return "Expired";
            case ENUM_ORDER_STATE::ORDER_STATE_REQUEST_ADD: return "Request Add";
            case ENUM_ORDER_STATE::ORDER_STATE_REQUEST_MODIFY: return "Request Modify";
            case ENUM_ORDER_STATE::ORDER_STATE_REQUEST_CANCEL: return "Request Cancel";
            default: return "Unknown";
        }
    }

    /**
     * @brief Get order expiration time
     * @return Expiration time (seconds since epoch)
     */
    int64_t TimeExpiration() const noexcept { return time_expiration_; }

    /**
     * @brief Get order execution/cancellation time
     * @return Done time (seconds since epoch)
     */
    int64_t TimeDone() const noexcept { return time_done_; }

    /**
     * @brief Get order execution/cancellation time in milliseconds
     * @return Done time (milliseconds since epoch)
     */
    int64_t TimeDoneMsc() const noexcept { return time_done_msc_; }

    /**
     * @brief Get filling type
     * @return Order filling mode
     */
    ENUM_ORDER_TYPE_FILLING TypeFilling() const noexcept { return type_filling_; }

    /**
     * @brief Get filling type as string
     * @return Filling mode description
     */
    std::string TypeFillingDescription() const noexcept {
        switch (type_filling_) {
            case ENUM_ORDER_TYPE_FILLING::ORDER_FILLING_FOK: return "Fill or Kill";
            case ENUM_ORDER_TYPE_FILLING::ORDER_FILLING_IOC: return "Immediate or Cancel";
            case ENUM_ORDER_TYPE_FILLING::ORDER_FILLING_RETURN: return "Return";
            default: return "Unknown";
        }
    }

    /**
     * @brief Get expiration type
     * @return Order time mode
     */
    ENUM_ORDER_TYPE_TIME TypeTime() const noexcept { return type_time_; }

    /**
     * @brief Get expiration type as string
     * @return Time mode description
     */
    std::string TypeTimeDescription() const noexcept {
        switch (type_time_) {
            case ENUM_ORDER_TYPE_TIME::ORDER_TIME_GTC: return "Good Till Canceled";
            case ENUM_ORDER_TYPE_TIME::ORDER_TIME_DAY: return "Good Till Day";
            case ENUM_ORDER_TYPE_TIME::ORDER_TIME_SPECIFIED: return "Good Till Specified";
            case ENUM_ORDER_TYPE_TIME::ORDER_TIME_SPECIFIED_DAY: return "Good Till Specified Day";
            default: return "Unknown";
        }
    }

    /**
     * @brief Get magic number
     * @return Expert Advisor ID
     */
    uint32_t Magic() const noexcept { return magic_; }

    /**
     * @brief Get position ID
     * @return Position identifier
     */
    uint64_t PositionId() const noexcept { return position_id_; }

    // --- Double Property Accessors (MT5 API) ---

    /**
     * @brief Get initial order volume
     * @return Initial volume in lots
     */
    double VolumeInitial() const noexcept { return volume_initial_; }

    /**
     * @brief Get current (unfilled) volume at time of completion
     * @return Current volume in lots
     */
    double VolumeCurrent() const noexcept { return volume_current_; }

    /**
     * @brief Get order price
     * @return Order price
     */
    double PriceOpen() const noexcept {
        return static_cast<double>(price_open_) / std::pow(10.0, digits_);
    }

    /**
     * @brief Get stop loss price
     * @return Stop loss
     */
    double StopLoss() const noexcept {
        return static_cast<double>(stop_loss_) / std::pow(10.0, digits_);
    }

    /**
     * @brief Get take profit price
     * @return Take profit
     */
    double TakeProfit() const noexcept {
        return static_cast<double>(take_profit_) / std::pow(10.0, digits_);
    }

    /**
     * @brief Get current price at time of completion
     * @return Current price
     */
    double PriceCurrent() const noexcept {
        return static_cast<double>(price_current_) / std::pow(10.0, digits_);
    }

    /**
     * @brief Get stop-limit price
     * @return Stop-limit price
     */
    double PriceStopLimit() const noexcept {
        return static_cast<double>(price_stoplimit_) / std::pow(10.0, digits_);
    }

    // --- String Property Accessors (MT5 API) ---

    /**
     * @brief Get order symbol name
     * @return Symbol name
     */
    std::string Symbol() const noexcept { return symbol_; }

    /**
     * @brief Get order comment
     * @return Comment string
     */
    std::string Comment() const noexcept { return comment_; }

    // --- Selection Methods (MT5 API) ---

    /**
     * @brief Select historical order by ticket (placeholder for backtesting)
     * @param ticket Order ticket to select
     * @return True if order exists in history
     */
    bool Select(uint64_t ticket) noexcept {
        // In backtesting, historical orders are managed by CTrade
        // This is a placeholder for MT5 API compatibility
        ticket_ = ticket;
        return true;
    }

    /**
     * @brief Select historical order by index (placeholder for backtesting)
     * @param index Order index in history
     * @return True if order exists
     */
    bool SelectByIndex(int index) noexcept {
        // Placeholder for MT5 API compatibility
        (void)index;
        return false;
    }

    // --- Internal Setters (for backtesting engine) ---

    void SetTicket(uint64_t ticket) noexcept { ticket_ = ticket; }
    void SetSymbol(const std::string& symbol) noexcept { symbol_ = symbol; }
    void SetMagic(uint32_t magic) noexcept { magic_ = magic; }
    void SetPositionId(uint64_t id) noexcept { position_id_ = id; }
    void SetOrderType(ENUM_ORDER_TYPE type) noexcept { order_type_ = type; }
    void SetState(ENUM_ORDER_STATE state) noexcept { state_ = state; }
    void SetVolumeInitial(double volume) noexcept { volume_initial_ = volume; }
    void SetVolumeCurrent(double volume) noexcept { volume_current_ = volume; }
    void SetTimeSetup(int64_t time_sec, int64_t time_msc = 0) noexcept {
        time_setup_ = time_sec;
        time_setup_msc_ = (time_msc > 0) ? time_msc : (time_sec * 1000);
    }
    void SetTimeExpiration(int64_t time) noexcept { time_expiration_ = time; }
    void SetTimeDone(int64_t time_sec, int64_t time_msc = 0) noexcept {
        time_done_ = time_sec;
        time_done_msc_ = (time_msc > 0) ? time_msc : (time_sec * 1000);
    }
    void SetTypeFilling(ENUM_ORDER_TYPE_FILLING filling) noexcept { type_filling_ = filling; }
    void SetTypeTime(ENUM_ORDER_TYPE_TIME time_type) noexcept { type_time_ = time_type; }
    void SetComment(const std::string& comment) noexcept { comment_ = comment; }
    void SetDigits(int32_t digits) noexcept { digits_ = digits; }

    void SetPriceOpen(double price) noexcept {
        price_open_ = static_cast<int64_t>((price) * std::pow(10.0, static_cast<double>(digits_)) + 0.5);
    }

    void SetPriceCurrent(double price) noexcept {
        price_current_ = static_cast<int64_t>((price) * std::pow(10.0, static_cast<double>(digits_)) + 0.5);
    }

    void SetPriceStopLimit(double price) noexcept {
        price_stoplimit_ = static_cast<int64_t>((price) * std::pow(10.0, static_cast<double>(digits_)) + 0.5);
    }

    void SetStopLoss(double sl) noexcept {
        stop_loss_ = static_cast<int64_t>((sl) * std::pow(10.0, static_cast<double>(digits_)) + 0.5);
    }

    void SetTakeProfit(double tp) noexcept {
        take_profit_ = static_cast<int64_t>((tp) * std::pow(10.0, static_cast<double>(digits_)) + 0.5);
    }

    // --- Utility Methods (backtesting helpers) ---

    /**
     * @brief Get order lifetime in seconds
     * @return Duration from setup to done
     */
    int64_t Lifetime() const noexcept {
        if (time_done_ == 0) return 0;
        return time_done_ - time_setup_;
    }

    /**
     * @brief Check if order was filled
     * @return True if fully filled
     */
    bool WasFilled() const noexcept {
        return state_ == ENUM_ORDER_STATE::ORDER_STATE_FILLED;
    }

    /**
     * @brief Check if order was canceled
     * @return True if canceled
     */
    bool WasCanceled() const noexcept {
        return state_ == ENUM_ORDER_STATE::ORDER_STATE_CANCELED;
    }

    /**
     * @brief Check if order was rejected
     * @return True if rejected
     */
    bool WasRejected() const noexcept {
        return state_ == ENUM_ORDER_STATE::ORDER_STATE_REJECTED;
    }

    /**
     * @brief Check if order expired
     * @return True if expired
     */
    bool WasExpired() const noexcept {
        return state_ == ENUM_ORDER_STATE::ORDER_STATE_EXPIRED;
    }

    /**
     * @brief Check if order was partially filled
     * @return True if partial fill
     */
    bool WasPartiallyFilled() const noexcept {
        return state_ == ENUM_ORDER_STATE::ORDER_STATE_PARTIAL;
    }

    /**
     * @brief Get filled volume
     * @return Volume that was executed
     */
    double VolumeFilled() const noexcept {
        return volume_initial_ - volume_current_;
    }

    /**
     * @brief Get fill ratio
     * @return Percentage of order filled (0.0 to 1.0)
     */
    double FillRatio() const noexcept {
        if (volume_initial_ == 0.0) return 0.0;
        return VolumeFilled() / volume_initial_;
    }

    /**
     * @brief Check if this is a buy order
     * @return True if buy order
     */
    bool IsBuy() const noexcept {
        return order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_BUY ||
               order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT ||
               order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP ||
               order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP_LIMIT;
    }

    /**
     * @brief Check if this is a sell order
     * @return True if sell order
     */
    bool IsSell() const noexcept {
        return order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_SELL ||
               order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_SELL_LIMIT ||
               order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP ||
               order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP_LIMIT;
    }

    /**
     * @brief Check if this was a market order
     * @return True if market order
     */
    bool IsMarket() const noexcept {
        return order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_BUY ||
               order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_SELL;
    }

    /**
     * @brief Check if this was a limit order
     * @return True if limit order
     */
    bool IsLimit() const noexcept {
        return order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT ||
               order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_SELL_LIMIT ||
               order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP_LIMIT ||
               order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP_LIMIT;
    }

    /**
     * @brief Check if this was a stop order
     * @return True if stop order
     */
    bool IsStop() const noexcept {
        return order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP ||
               order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP ||
               order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP_LIMIT ||
               order_type_ == ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP_LIMIT;
    }
};

} // namespace haruquant

