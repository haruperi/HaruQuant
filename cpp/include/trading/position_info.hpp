/**
 * @file position_info.hpp
 * @brief Position information class (mirrors MT5 CPositionInfo)
 *
 * Provides access to open position properties.
 * Mirrors MQL5's CPositionInfo from Trade.mqh standard library.
 * See: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/cpositioninfo
 */

#pragma once

#include <cstdint>
#include <string>
#include <cmath>

namespace hqt {

/**
 * @brief Position type (MT5-compatible)
 */
enum class ENUM_POSITION_TYPE {
    POSITION_TYPE_BUY = 0,   ///< Long position
    POSITION_TYPE_SELL = 1   ///< Short position
};

/**
 * @brief Trailing stop mode (backtesting extension)
 */
enum class TrailingMode : uint8_t {
    NONE = 0,        ///< No trailing
    FIXED = 1,       ///< Fixed distance trailing (in points)
    ATR = 2,         ///< ATR-based trailing
    STEP = 3         ///< Step trailing (move in increments)
};

/**
 * @brief Position information class (mirrors MT5 CPositionInfo)
 *
 * Provides access to open position properties.
 * All price values stored internally as fixed-point for precision.
 */
class PositionInfo {
private:
    // Core identification
    uint64_t ticket_;           ///< Position ticket (for backward compatibility)
    uint64_t identifier_;       ///< Unique position identifier (MT5)
    std::string symbol_;        ///< Symbol name
    uint32_t magic_;            ///< Magic number
    ENUM_POSITION_TYPE type_;   ///< Position type (buy/sell)

    // Volume
    double volume_;             ///< Position volume in lots

    // Prices (fixed-point internally)
    int64_t price_open_;        ///< Entry price
    int64_t price_current_;     ///< Current market price
    int64_t stop_loss_;         ///< Stop loss level
    int64_t take_profit_;       ///< Take profit level

    // Financial data (fixed-point internally)
    int64_t profit_;            ///< Unrealized profit/loss
    int64_t commission_;        ///< Commission paid
    int64_t swap_;              ///< Swap/rollover charges

    // Time information
    int64_t time_;              ///< Open time (seconds since epoch)
    int64_t time_msc_;          ///< Open time (milliseconds since epoch)
    int64_t time_update_;       ///< Last update time (seconds)
    int64_t time_update_msc_;   ///< Last update time (milliseconds)

    // Comment
    std::string comment_;       ///< Position comment

    // Trailing stop (backtesting specific, not in MT5)
    TrailingMode trailing_mode_;
    int32_t trailing_distance_;
    int32_t trailing_step_;
    int64_t trailing_trigger_;

    // Cached state (for CheckState)
    bool has_stored_state_;
    double stored_volume_;
    int64_t stored_stop_loss_;
    int64_t stored_take_profit_;
    int64_t stored_profit_;

    // Symbol info (for conversions)
    int32_t digits_;
    double point_;
    double contract_size_;

public:
    /**
     * @brief Constructor
     */
    PositionInfo()
        : ticket_(0),
          identifier_(0),
          symbol_(""),
          magic_(0),
          type_(ENUM_POSITION_TYPE::POSITION_TYPE_BUY),
          volume_(0.0),
          price_open_(0),
          price_current_(0),
          stop_loss_(0),
          take_profit_(0),
          profit_(0),
          commission_(0),
          swap_(0),
          time_(0),
          time_msc_(0),
          time_update_(0),
          time_update_msc_(0),
          comment_(""),
          trailing_mode_(TrailingMode::NONE),
          trailing_distance_(0),
          trailing_step_(0),
          trailing_trigger_(0),
          has_stored_state_(false),
          stored_volume_(0.0),
          stored_stop_loss_(0),
          stored_take_profit_(0),
          stored_profit_(0),
          digits_(5),
          point_(0.00001),
          contract_size_(100000.0) {}

    // --- Integer Property Accessors (MT5 API) ---

    /**
     * @brief Get position opening time
     * @return Time in seconds since epoch
     */
    int64_t Time() const noexcept { return time_; }

    /**
     * @brief Get position opening time in milliseconds
     * @return Time in milliseconds since epoch
     */
    int64_t TimeMsc() const noexcept { return time_msc_; }

    /**
     * @brief Get position last update time
     * @return Update time in seconds since epoch
     */
    int64_t TimeUpdate() const noexcept { return time_update_; }

    /**
     * @brief Get position last update time in milliseconds
     * @return Update time in milliseconds since epoch
     */
    int64_t TimeUpdateMsc() const noexcept { return time_update_msc_; }

    /**
     * @brief Get position type
     * @return Position type (buy/sell)
     */
    ENUM_POSITION_TYPE PositionType() const noexcept { return type_; }

    /**
     * @brief Get position type as string
     * @return Position type description
     */
    std::string TypeDescription() const noexcept {
        return (type_ == ENUM_POSITION_TYPE::POSITION_TYPE_BUY) ? "Buy" : "Sell";
    }

    /**
     * @brief Get magic number
     * @return Expert Advisor identifier
     */
    uint32_t Magic() const noexcept { return magic_; }

    /**
     * @brief Get position identifier
     * @return Unique position ID
     */
    uint64_t Identifier() const noexcept { return identifier_; }

    /**
     * @brief Get position ticket (backward compatibility)
     * @return Position ticket
     */
    uint64_t Ticket() const noexcept { return ticket_; }

    // --- Double Property Accessors (MT5 API) ---

    /**
     * @brief Get position volume
     * @return Volume in lots
     */
    double Volume() const noexcept { return volume_; }

    /**
     * @brief Get entry price
     * @return Opening price
     */
    double PriceOpen() const noexcept {
        return static_cast<double>(price_open_) / std::pow(10.0, digits_);
    }

    /**
     * @brief Get stop loss price
     * @return Stop loss level
     */
    double StopLoss() const noexcept {
        return static_cast<double>(stop_loss_) / std::pow(10.0, digits_);
    }

    /**
     * @brief Get take profit price
     * @return Take profit level
     */
    double TakeProfit() const noexcept {
        return static_cast<double>(take_profit_) / std::pow(10.0, digits_);
    }

    /**
     * @brief Get current market price
     * @return Current price for position symbol
     */
    double PriceCurrent() const noexcept {
        return static_cast<double>(price_current_) / std::pow(10.0, digits_);
    }

    /**
     * @brief Get commission
     * @return Commission paid
     */
    double Commission() const noexcept {
        return static_cast<double>(commission_) / 1'000'000.0;
    }

    /**
     * @brief Get swap
     * @return Swap/rollover charges
     */
    double Swap() const noexcept {
        return static_cast<double>(swap_) / 1'000'000.0;
    }

    /**
     * @brief Get unrealized profit
     * @return Current profit/loss
     */
    double Profit() const noexcept {
        return static_cast<double>(profit_) / 1'000'000.0;
    }

    // --- String Property Accessors (MT5 API) ---

    /**
     * @brief Get position symbol
     * @return Symbol name
     */
    std::string Symbol() const noexcept { return symbol_; }

    /**
     * @brief Get position comment
     * @return Comment string
     */
    std::string Comment() const noexcept { return comment_; }

    // --- State Management (MT5 API) ---

    /**
     * @brief Store current position state
     *
     * Saves volume, SL, TP, and profit for later comparison
     */
    void StoreState() noexcept {
        has_stored_state_ = true;
        stored_volume_ = volume_;
        stored_stop_loss_ = stop_loss_;
        stored_take_profit_ = take_profit_;
        stored_profit_ = profit_;
    }

    /**
     * @brief Check if state has changed since StoreState()
     * @return True if any tracked field has changed
     */
    bool CheckState() const noexcept {
        if (!has_stored_state_) return false;
        return (std::abs(volume_ - stored_volume_) > 1e-9) ||
               (stop_loss_ != stored_stop_loss_) ||
               (take_profit_ != stored_take_profit_) ||
               (profit_ != stored_profit_);
    }

    // --- Selection Methods (MT5 API) ---

    /**
     * @brief Select position by ticket (placeholder for backtesting)
     * @param ticket Position ticket
     * @return True if position exists
     */
    bool Select(uint64_t ticket) noexcept {
        // In backtesting, positions are managed by CTrade
        // This is a placeholder for MT5 API compatibility
        ticket_ = ticket;
        identifier_ = ticket;
        return true;
    }

    /**
     * @brief Select position by symbol (placeholder for backtesting)
     * @param symbol Symbol name
     * @return True if position exists
     */
    bool Select(const std::string& symbol) noexcept {
        // Placeholder for MT5 API compatibility
        symbol_ = symbol;
        return false;
    }

    /**
     * @brief Select position by index (placeholder for backtesting)
     * @param index Position index
     * @return True if position exists
     */
    bool SelectByIndex(int index) noexcept {
        // Placeholder for MT5 API compatibility
        (void)index;
        return false;
    }

    /**
     * @brief Select position by magic number and symbol
     * @param symbol Symbol name
     * @param magic Magic number
     * @return True if position exists
     */
    bool SelectByMagic(const std::string& symbol, uint32_t magic) noexcept {
        // Placeholder for MT5 API compatibility
        symbol_ = symbol;
        magic_ = magic;
        return false;
    }

    /**
     * @brief Select position by ticket number
     * @param ticket Position ticket
     * @return True if position exists
     */
    bool SelectByTicket(uint64_t ticket) noexcept {
        // Placeholder for MT5 API compatibility
        ticket_ = ticket;
        identifier_ = ticket;
        return true;
    }

    // --- Internal Setters (for backtesting engine) ---

    void SetTicket(uint64_t ticket) noexcept {
        ticket_ = ticket;
        identifier_ = ticket;  // Use ticket as identifier
    }
    void SetIdentifier(uint64_t id) noexcept { identifier_ = id; }
    void SetSymbol(const std::string& symbol) noexcept { symbol_ = symbol; }
    void SetMagic(uint32_t magic) noexcept { magic_ = magic; }
    void SetType(ENUM_POSITION_TYPE type) noexcept { type_ = type; }
    void SetVolume(double volume) noexcept { volume_ = volume; }
    void SetCommission(double commission) noexcept {
        commission_ = static_cast<int64_t>(commission * 1'000'000.0);
    }
    void SetSwap(double swap) noexcept {
        swap_ = static_cast<int64_t>(swap * 1'000'000.0);
    }
    void SetComment(const std::string& comment) noexcept { comment_ = comment; }
    void SetDigits(int32_t digits) noexcept { digits_ = digits; }
    void SetPoint(double point) noexcept { point_ = point; }
    void SetContractSize(double size) noexcept { contract_size_ = size; }

    void SetTime(int64_t time_sec, int64_t time_msc = 0) noexcept {
        time_ = time_sec;
        time_msc_ = (time_msc > 0) ? time_msc : (time_sec * 1000);
    }

    void SetTimeUpdate(int64_t time_sec, int64_t time_msc = 0) noexcept {
        time_update_ = time_sec;
        time_update_msc_ = (time_msc > 0) ? time_msc : static_cast<int64_t>(time_sec * 1000LL);
    }

    /**
     * @brief Set prices in double format (converts to fixed-point internally)
     */
    void SetPriceOpen(double price) noexcept {
        double scaled = price * std::pow(10.0, static_cast<double>(digits_)) + 0.5;
        price_open_ = static_cast<int64_t>(scaled);
    }

    void SetPriceCurrent(double price) noexcept {
        double scaled = price * std::pow(10.0, static_cast<double>(digits_)) + 0.5;
        price_current_ = static_cast<int64_t>(scaled);
    }

    void SetStopLoss(double sl) noexcept {
        double scaled = sl * std::pow(10.0, static_cast<double>(digits_)) + 0.5;
        stop_loss_ = static_cast<int64_t>(scaled);
        SetTimeUpdate(time_update_ > 0 ? time_update_ : time_);  // Update modification time
    }

    void SetTakeProfit(double tp) noexcept {
        double scaled = tp * std::pow(10.0, static_cast<double>(digits_)) + 0.5;
        take_profit_ = static_cast<int64_t>(scaled);
        SetTimeUpdate(time_update_ > 0 ? time_update_ : time_);  // Update modification time
    }

    // --- Trailing Stop Configuration (backtesting specific) ---

    void SetTrailingMode(TrailingMode mode) noexcept { trailing_mode_ = mode; }
    void SetTrailingDistance(int32_t distance) noexcept { trailing_distance_ = distance; }
    void SetTrailingStep(int32_t step) noexcept { trailing_step_ = step; }
    void SetTrailingTrigger(double trigger) noexcept {
        double scaled = trigger * std::pow(10.0, static_cast<double>(digits_)) + 0.5;
        trailing_trigger_ = static_cast<int64_t>(scaled);
    }

    TrailingMode GetTrailingMode() const noexcept { return trailing_mode_; }
    int32_t GetTrailingDistance() const noexcept { return trailing_distance_; }
    int32_t GetTrailingStep() const noexcept { return trailing_step_; }
    int64_t GetTrailingTrigger() const noexcept { return trailing_trigger_; }

    // --- Price Update and PnL Calculation ---

    /**
     * @brief Update current price and recalculate profit
     * @param new_price Current market price
     */
    void UpdatePrice(double new_price) noexcept {
        SetPriceCurrent(new_price);
        RecalculateProfit();
        SetTimeUpdate(time_update_ + 1);  // Increment update time
    }

    /**
     * @brief Recalculate profit based on current prices
     */
    void RecalculateProfit() noexcept {
        // Calculate PnL based on position type
        int64_t price_diff;
        if (type_ == ENUM_POSITION_TYPE::POSITION_TYPE_BUY) {
            price_diff = price_current_ - price_open_;
        } else {
            price_diff = price_open_ - price_current_;
        }

        // PnL = price_diff * volume * contract_size
        // Convert from fixed-point price difference to actual profit
        double price_diff_double = static_cast<double>(price_diff) / std::pow(10.0, digits_);
        profit_ = static_cast<int64_t>(price_diff_double * volume_ * contract_size_ * 1'000'000.0);
    }

    // --- Utility Methods (backtesting helpers, not in MT5 API) ---

    /**
     * @brief Check if stop loss is hit
     * @return True if SL level reached
     */
    bool IsStopLossHit() const noexcept {
        if (stop_loss_ == 0) return false;

        if (type_ == ENUM_POSITION_TYPE::POSITION_TYPE_BUY) {
            return price_current_ <= stop_loss_;
        } else {
            return price_current_ >= stop_loss_;
        }
    }

    /**
     * @brief Check if take profit is hit
     * @return True if TP level reached
     */
    bool IsTakeProfitHit() const noexcept {
        if (take_profit_ == 0) return false;

        if (type_ == ENUM_POSITION_TYPE::POSITION_TYPE_BUY) {
            return price_current_ >= take_profit_;
        } else {
            return price_current_ <= take_profit_;
        }
    }

    /**
     * @brief Get net profit including commission and swap
     * @return Net profit/loss
     */
    double NetProfit() const noexcept {
        return Profit() + Swap() - Commission();
    }

    /**
     * @brief Get distance from open price in points
     * @return Distance in points (positive = profit direction)
     */
    double DistanceInPoints() const noexcept {
        int64_t price_diff = (type_ == ENUM_POSITION_TYPE::POSITION_TYPE_BUY)
            ? (price_current_ - price_open_)
            : (price_open_ - price_current_);
        return static_cast<double>(price_diff) / (point_ * std::pow(10.0, digits_));
    }

    /**
     * @brief Check if this is a buy position
     * @return True if buy/long position
     */
    bool IsBuy() const noexcept {
        return type_ == ENUM_POSITION_TYPE::POSITION_TYPE_BUY;
    }

    /**
     * @brief Check if this is a sell position
     * @return True if sell/short position
     */
    bool IsSell() const noexcept {
        return type_ == ENUM_POSITION_TYPE::POSITION_TYPE_SELL;
    }

    // --- Internal Fixed-Point Accessors (for CTrade) ---

    int64_t GetPriceOpenFP() const noexcept { return price_open_; }
    int64_t GetPriceCurrentFP() const noexcept { return price_current_; }
    int64_t GetStopLossFP() const noexcept { return stop_loss_; }
    int64_t GetTakeProfitFP() const noexcept { return take_profit_; }
    int64_t GetProfitFP() const noexcept { return profit_; }
    int64_t GetCommissionFP() const noexcept { return commission_; }
    int64_t GetSwapFP() const noexcept { return swap_; }

    void SetProfitFP(int64_t profit) noexcept { profit_ = profit; }
    void AddCommissionFP(int64_t commission) noexcept { commission_ += commission; }
    void AddSwapFP(int64_t swap) noexcept { swap_ += swap; }
};

} // namespace hqt
