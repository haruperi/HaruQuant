/**
FILE: include\trading\symbol_info.hpp

PURPOSE:
Defines symbol_info.hpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in symbol_info.hpp.
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

#include <cstdint>
#include <string>
#include <cmath>

namespace hqt {

/**
 * @brief Simple swap type (for backward compatibility with existing code)
 */
enum class SwapType : uint8_t {
    POINTS      = 0,  ///< Swap in points
    PERCENTAGE  = 1,  ///< Swap as percentage of contract value
    MONEY       = 2   ///< Swap in account currency
};

/**
 * @brief Simple trade mode (for backward compatibility)
 */
enum class TradeMode : uint8_t {
    DISABLED    = 0,  ///< Trading disabled
    LONG_ONLY   = 1,  ///< Long positions only
    SHORT_ONLY  = 2,  ///< Short positions only
    CLOSE_ONLY  = 3,  ///< Close only, no new positions
    FULL        = 4   ///< Full trading enabled
};

/**
 * @brief Swap calculation mode (MT5-compatible)
 */
enum class ENUM_SYMBOL_SWAP_MODE {
    SYMBOL_SWAP_MODE_DISABLED = 0,          ///< Swaps disabled
    SYMBOL_SWAP_MODE_POINTS = 1,            ///< Swaps in points
    SYMBOL_SWAP_MODE_CURRENCY_SYMBOL = 2,   ///< Swaps in symbol base currency
    SYMBOL_SWAP_MODE_CURRENCY_MARGIN = 3,   ///< Swaps in margin currency
    SYMBOL_SWAP_MODE_CURRENCY_DEPOSIT = 4,  ///< Swaps in account currency
    SYMBOL_SWAP_MODE_INTEREST_CURRENT = 5,  ///< Interest on current prices
    SYMBOL_SWAP_MODE_INTEREST_OPEN = 6,     ///< Interest on open prices
    SYMBOL_SWAP_MODE_REOPEN_CURRENT = 7,    ///< Reopen by current prices
    SYMBOL_SWAP_MODE_REOPEN_BID = 8         ///< Reopen by bid prices
};

/**
 * @brief Day of week for triple swap
 */
enum class ENUM_DAY_OF_WEEK {
    SUNDAY = 0,
    MONDAY = 1,
    TUESDAY = 2,
    WEDNESDAY = 3,
    THURSDAY = 4,
    FRIDAY = 5,
    SATURDAY = 6
};

/**
 * @brief Trade mode for symbol
 */
enum class ENUM_SYMBOL_TRADE_MODE {
    SYMBOL_TRADE_MODE_DISABLED = 0,   ///< Trade disabled
    SYMBOL_TRADE_MODE_LONGONLY = 1,   ///< Long only
    SYMBOL_TRADE_MODE_SHORTONLY = 2,  ///< Short only
    SYMBOL_TRADE_MODE_CLOSEONLY = 3,  ///< Close only
    SYMBOL_TRADE_MODE_FULL = 4        ///< No restrictions
};

/**
 * @brief Trade execution mode
 */
enum class ENUM_SYMBOL_TRADE_EXECUTION {
    SYMBOL_TRADE_EXECUTION_REQUEST = 0,  ///< Execution by request
    SYMBOL_TRADE_EXECUTION_INSTANT = 1,  ///< Instant execution
    SYMBOL_TRADE_EXECUTION_MARKET = 2,   ///< Market execution
    SYMBOL_TRADE_EXECUTION_EXCHANGE = 3  ///< Exchange execution
};

/**
 * @brief Margin calculation mode
 */
enum class ENUM_SYMBOL_CALC_MODE {
    SYMBOL_CALC_MODE_FOREX = 0,           ///< Forex mode
    SYMBOL_CALC_MODE_FUTURES = 1,         ///< Futures mode
    SYMBOL_CALC_MODE_CFD = 2,             ///< CFD mode
    SYMBOL_CALC_MODE_CFDINDEX = 3,        ///< CFD on index
    SYMBOL_CALC_MODE_CFDLEVERAGE = 4,     ///< CFD with leverage
    SYMBOL_CALC_MODE_EXCH_STOCKS = 5,     ///< Exchange stocks
    SYMBOL_CALC_MODE_EXCH_FUTURES = 6,    ///< Exchange futures
    SYMBOL_CALC_MODE_EXCH_OPTIONS = 7,    ///< Exchange options
    SYMBOL_CALC_MODE_EXCH_BONDS = 8       ///< Exchange bonds
};

/**
 * @brief Symbol information class (mirrors MT5 CSymbolInfo)
 *
 * Provides access to symbol properties and market data.
 * All price values stored internally as fixed-point for precision.
 */
class SymbolInfo {
private:
    // Core identification
    std::string name_;
    std::string description_;
    std::string path_;
    uint32_t symbol_id_;

    // Price data (fixed-point: value * 10^digits)
    int64_t bid_;
    int64_t bid_high_;
    int64_t bid_low_;
    int64_t ask_;
    int64_t ask_high_;
    int64_t ask_low_;
    int64_t last_;
    int64_t last_high_;
    int64_t last_low_;
    int64_t volume_real_;
    int64_t volume_high_;
    int64_t volume_low_;
    int64_t time_;  // Timestamp of last quote

    // Price formatting
    int32_t digits_;
    double point_;
    int32_t spread_;
    bool spread_float_;

    // Contract specifications
    double tick_value_;
    double tick_size_;
    double tick_value_profit_;
    double tick_value_loss_;
    double contract_size_;

    // Volume constraints
    double volume_min_;
    double volume_max_;
    double volume_step_;
    double volume_limit_;

    // Margin requirements
    double margin_initial_;
    double margin_maintenance_;
    double margin_long_;
    double margin_short_;
    double margin_limit_;
    double margin_stop_;
    double margin_stop_limit_;

    // Swap rates
    double swap_long_;
    double swap_short_;
    ENUM_SYMBOL_SWAP_MODE swap_mode_;
    ENUM_DAY_OF_WEEK swap_rollover3days_;

    // Trading parameters
    ENUM_SYMBOL_TRADE_MODE trade_mode_;
    ENUM_SYMBOL_TRADE_EXECUTION trade_execution_;
    ENUM_SYMBOL_CALC_MODE trade_calc_mode_;
    int32_t stops_level_;
    int32_t freeze_level_;

    // Currency information
    std::string currency_base_;
    std::string currency_profit_;
    std::string currency_margin_;

    // Session data
    int64_t session_deals_;
    int64_t session_buy_orders_;
    int64_t session_sell_orders_;
    double session_turnover_;
    double session_interest_;
    double session_buy_orders_volume_;
    double session_sell_orders_volume_;

    // Flags
    bool selected_;

public:
    /**
     * @brief Constructor
     */
    SymbolInfo()
        : name_(""),
          description_(""),
          path_(""),
          symbol_id_(0),
          bid_(0), bid_high_(0), bid_low_(0),
          ask_(0), ask_high_(0), ask_low_(0),
          last_(0), last_high_(0), last_low_(0),
          volume_real_(0), volume_high_(0), volume_low_(0),
          time_(0),
          digits_(0),
          point_(0.0),
          spread_(0),
          spread_float_(false),
          tick_value_(0.0),
          tick_size_(0.0),
          tick_value_profit_(0.0),
          tick_value_loss_(0.0),
          contract_size_(0.0),
          volume_min_(0.0),
          volume_max_(0.0),
          volume_step_(0.0),
          volume_limit_(0.0),
          margin_initial_(0.0),
          margin_maintenance_(0.0),
          margin_long_(0.0),
          margin_short_(0.0),
          margin_limit_(0.0),
          margin_stop_(0.0),
          margin_stop_limit_(0.0),
          swap_long_(0.0),
          swap_short_(0.0),
          swap_mode_(ENUM_SYMBOL_SWAP_MODE::SYMBOL_SWAP_MODE_POINTS),
          swap_rollover3days_(ENUM_DAY_OF_WEEK::WEDNESDAY),
          trade_mode_(ENUM_SYMBOL_TRADE_MODE::SYMBOL_TRADE_MODE_FULL),
          trade_execution_(ENUM_SYMBOL_TRADE_EXECUTION::SYMBOL_TRADE_EXECUTION_INSTANT),
          trade_calc_mode_(ENUM_SYMBOL_CALC_MODE::SYMBOL_CALC_MODE_FOREX),
          stops_level_(0),
          freeze_level_(0),
          currency_base_(""),
          currency_profit_(""),
          currency_margin_(""),
          session_deals_(0),
          session_buy_orders_(0),
          session_sell_orders_(0),
          session_turnover_(0.0),
          session_interest_(0.0),
          session_buy_orders_volume_(0.0),
          session_sell_orders_volume_(0.0),
          selected_(false) {}

    // --- Basic Properties (MT5 API) ---

    /**
     * @brief Get symbol name
     * @return Symbol name (e.g., "EURUSD")
     */
    std::string Name() const noexcept { return name_; }

    /**
     * @brief Set symbol name
     * @param name Symbol name
     */
    void Name(const std::string& name) noexcept { name_ = name; }

    /**
     * @brief Get internal symbol ID
     * @return Symbol ID
     */
    uint32_t SymbolId() const noexcept { return symbol_id_; }

    /**
     * @brief Get symbol description
     * @return Human-readable description
     */
    std::string Description() const noexcept { return description_; }

    /**
     * @brief Get symbol path
     * @return Symbol path in symbol tree
     */
    std::string Path() const noexcept { return path_; }

    /**
     * @brief Check if symbol is selected in Market Watch
     * @return True if selected
     */
    bool Select() const noexcept { return selected_; }

    /**
     * @brief Set Market Watch selection
     * @param selected Selection state
     */
    void Select(bool selected) noexcept { selected_ = selected; }

    // --- Price Information (MT5 API) ---

    /**
     * @brief Get current bid price
     * @return Bid price
     */
    double Bid() const noexcept {
        return static_cast<double>(bid_) / pow(10.0, digits_);
    }

    /**
     * @brief Get highest bid for day
     * @return High bid price
     */
    double BidHigh() const noexcept {
        return static_cast<double>(bid_high_) / pow(10.0, digits_);
    }

    /**
     * @brief Get lowest bid for day
     * @return Low bid price
     */
    double BidLow() const noexcept {
        return static_cast<double>(bid_low_) / pow(10.0, digits_);
    }

    /**
     * @brief Get current ask price
     * @return Ask price
     */
    double Ask() const noexcept {
        return static_cast<double>(ask_) / pow(10.0, digits_);
    }

    /**
     * @brief Get highest ask for day
     * @return High ask price
     */
    double AskHigh() const noexcept {
        return static_cast<double>(ask_high_) / pow(10.0, digits_);
    }

    /**
     * @brief Get lowest ask for day
     * @return Low ask price
     */
    double AskLow() const noexcept {
        return static_cast<double>(ask_low_) / pow(10.0, digits_);
    }

    /**
     * @brief Get last deal price
     * @return Last price
     */
    double Last() const noexcept {
        return static_cast<double>(last_) / pow(10.0, digits_);
    }

    /**
     * @brief Get spread in points
     * @return Current spread
     */
    int32_t Spread() const noexcept { return spread_; }

    /**
     * @brief Check if spread is floating
     * @return True if spread is floating
     */
    bool SpreadFloat() const noexcept { return spread_float_; }

    /**
     * @brief Get time of last quote
     * @return Timestamp (seconds since epoch)
     */
    int64_t Time() const noexcept { return time_; }

    // --- Volume Information (MT5 API) ---

    /**
     * @brief Get last deal volume
     * @return Volume
     */
    int64_t Volume() const noexcept { return volume_real_; }

    /**
     * @brief Get highest volume for day
     * @return High volume
     */
    int64_t VolumeHigh() const noexcept { return volume_high_; }

    /**
     * @brief Get lowest volume for day
     * @return Low volume
     */
    int64_t VolumeLow() const noexcept { return volume_low_; }

    // --- Contract Specifications (MT5 API) ---

    /**
     * @brief Get number of decimal places
     * @return Digits (e.g., 5 for EURUSD)
     */
    int32_t Digits() const noexcept { return digits_; }

    /**
     * @brief Get point value
     * @return Point (e.g., 0.00001 for 5-digit EURUSD)
     */
    double Point() const noexcept { return point_; }

    /**
     * @brief Get tick value
     * @return Tick value
     */
    double TickValue() const noexcept { return tick_value_; }

    /**
     * @brief Get tick size
     * @return Tick size
     */
    double TickSize() const noexcept { return tick_size_; }

    /**
     * @brief Get tick value for profit calculation
     * @return Tick value profit
     */
    double TickValueProfit() const noexcept { return tick_value_profit_; }

    /**
     * @brief Get tick value for loss calculation
     * @return Tick value loss
     */
    double TickValueLoss() const noexcept { return tick_value_loss_; }

    /**
     * @brief Get contract size
     * @return Contract size (e.g., 100000 for standard lot)
     */
    double ContractSize() const noexcept { return contract_size_; }

    // --- Volume Constraints (MT5 API) ---

    /**
     * @brief Get minimum volume
     * @return Minimum lots
     */
    double LotsMin() const noexcept { return volume_min_; }

    /**
     * @brief Get maximum volume
     * @return Maximum lots
     */
    double LotsMax() const noexcept { return volume_max_; }

    /**
     * @brief Get volume step
     * @return Lot increment
     */
    double LotsStep() const noexcept { return volume_step_; }

    /**
     * @brief Get maximum volume for all positions
     * @return Maximum total volume
     */
    double LotsLimit() const noexcept { return volume_limit_; }

    // --- Margin Requirements (MT5 API) ---

    /**
     * @brief Get initial margin requirement
     * @return Initial margin
     */
    double MarginInitial() const noexcept { return margin_initial_; }

    /**
     * @brief Get maintenance margin requirement
     * @return Maintenance margin
     */
    double MarginMaintenance() const noexcept { return margin_maintenance_; }

    /**
     * @brief Get margin for long positions
     * @return Long margin
     */
    double MarginLong() const noexcept { return margin_long_; }

    /**
     * @brief Get margin for short positions
     * @return Short margin
     */
    double MarginShort() const noexcept { return margin_short_; }

    /**
     * @brief Get margin for limit orders
     * @return Limit margin
     */
    double MarginLimit() const noexcept { return margin_limit_; }

    /**
     * @brief Get margin for stop orders
     * @return Stop margin
     */
    double MarginStop() const noexcept { return margin_stop_; }

    /**
     * @brief Get margin for stop-limit orders
     * @return Stop-limit margin
     */
    double MarginStopLimit() const noexcept { return margin_stop_limit_; }

    // --- Swap Information (MT5 API) ---

    /**
     * @brief Get swap for long positions
     * @return Long swap rate
     */
    double SwapLong() const noexcept { return swap_long_; }

    /**
     * @brief Get swap for short positions
     * @return Short swap rate
     */
    double SwapShort() const noexcept { return swap_short_; }

    /**
     * @brief Get swap calculation mode
     * @return Swap mode
     */
    ENUM_SYMBOL_SWAP_MODE SwapMode() const noexcept { return swap_mode_; }

    /**
     * @brief Get swap mode as string
     * @return Swap mode description
     */
    std::string SwapModeDescription() const noexcept {
        switch (swap_mode_) {
            case ENUM_SYMBOL_SWAP_MODE::SYMBOL_SWAP_MODE_DISABLED: return "Disabled";
            case ENUM_SYMBOL_SWAP_MODE::SYMBOL_SWAP_MODE_POINTS: return "Points";
            case ENUM_SYMBOL_SWAP_MODE::SYMBOL_SWAP_MODE_CURRENCY_SYMBOL: return "Currency Symbol";
            case ENUM_SYMBOL_SWAP_MODE::SYMBOL_SWAP_MODE_CURRENCY_MARGIN: return "Currency Margin";
            case ENUM_SYMBOL_SWAP_MODE::SYMBOL_SWAP_MODE_CURRENCY_DEPOSIT: return "Currency Deposit";
            case ENUM_SYMBOL_SWAP_MODE::SYMBOL_SWAP_MODE_INTEREST_CURRENT: return "Interest Current";
            case ENUM_SYMBOL_SWAP_MODE::SYMBOL_SWAP_MODE_INTEREST_OPEN: return "Interest Open";
            case ENUM_SYMBOL_SWAP_MODE::SYMBOL_SWAP_MODE_REOPEN_CURRENT: return "Reopen Current";
            case ENUM_SYMBOL_SWAP_MODE::SYMBOL_SWAP_MODE_REOPEN_BID: return "Reopen Bid";
            default: return "Unknown";
        }
    }

    /**
     * @brief Get day of week for triple swap
     * @return Day of week (0=Sunday, 3=Wednesday, etc.)
     */
    ENUM_DAY_OF_WEEK SwapRollover3days() const noexcept { return swap_rollover3days_; }

    /**
     * @brief Get triple swap day as string
     * @return Day name
     */
    std::string SwapRollover3daysDescription() const noexcept {
        switch (swap_rollover3days_) {
            case ENUM_DAY_OF_WEEK::SUNDAY: return "Sunday";
            case ENUM_DAY_OF_WEEK::MONDAY: return "Monday";
            case ENUM_DAY_OF_WEEK::TUESDAY: return "Tuesday";
            case ENUM_DAY_OF_WEEK::WEDNESDAY: return "Wednesday";
            case ENUM_DAY_OF_WEEK::THURSDAY: return "Thursday";
            case ENUM_DAY_OF_WEEK::FRIDAY: return "Friday";
            case ENUM_DAY_OF_WEEK::SATURDAY: return "Saturday";
            default: return "Unknown";
        }
    }

    // --- Trading Parameters (MT5 API) ---

    /**
     * @brief Get trade mode
     * @return Trade mode
     */
    ENUM_SYMBOL_TRADE_MODE TradeMode() const noexcept { return trade_mode_; }

    /**
     * @brief Get trade mode as string
     * @return Trade mode description
     */
    std::string TradeModeDescription() const noexcept {
        switch (trade_mode_) {
            case ENUM_SYMBOL_TRADE_MODE::SYMBOL_TRADE_MODE_DISABLED: return "Disabled";
            case ENUM_SYMBOL_TRADE_MODE::SYMBOL_TRADE_MODE_LONGONLY: return "Long Only";
            case ENUM_SYMBOL_TRADE_MODE::SYMBOL_TRADE_MODE_SHORTONLY: return "Short Only";
            case ENUM_SYMBOL_TRADE_MODE::SYMBOL_TRADE_MODE_CLOSEONLY: return "Close Only";
            case ENUM_SYMBOL_TRADE_MODE::SYMBOL_TRADE_MODE_FULL: return "Full";
            default: return "Unknown";
        }
    }

    /**
     * @brief Get trade execution mode
     * @return Execution mode
     */
    ENUM_SYMBOL_TRADE_EXECUTION TradeExecution() const noexcept { return trade_execution_; }

    /**
     * @brief Get execution mode as string
     * @return Execution mode description
     */
    std::string TradeExecutionDescription() const noexcept {
        switch (trade_execution_) {
            case ENUM_SYMBOL_TRADE_EXECUTION::SYMBOL_TRADE_EXECUTION_REQUEST: return "Request";
            case ENUM_SYMBOL_TRADE_EXECUTION::SYMBOL_TRADE_EXECUTION_INSTANT: return "Instant";
            case ENUM_SYMBOL_TRADE_EXECUTION::SYMBOL_TRADE_EXECUTION_MARKET: return "Market";
            case ENUM_SYMBOL_TRADE_EXECUTION::SYMBOL_TRADE_EXECUTION_EXCHANGE: return "Exchange";
            default: return "Unknown";
        }
    }

    /**
     * @brief Get margin calculation mode
     * @return Calculation mode
     */
    ENUM_SYMBOL_CALC_MODE TradeCalcMode() const noexcept { return trade_calc_mode_; }

    /**
     * @brief Get calculation mode as string
     * @return Calculation mode description
     */
    std::string TradeCalcModeDescription() const noexcept {
        switch (trade_calc_mode_) {
            case ENUM_SYMBOL_CALC_MODE::SYMBOL_CALC_MODE_FOREX: return "Forex";
            case ENUM_SYMBOL_CALC_MODE::SYMBOL_CALC_MODE_FUTURES: return "Futures";
            case ENUM_SYMBOL_CALC_MODE::SYMBOL_CALC_MODE_CFD: return "CFD";
            case ENUM_SYMBOL_CALC_MODE::SYMBOL_CALC_MODE_CFDINDEX: return "CFD Index";
            case ENUM_SYMBOL_CALC_MODE::SYMBOL_CALC_MODE_CFDLEVERAGE: return "CFD Leverage";
            case ENUM_SYMBOL_CALC_MODE::SYMBOL_CALC_MODE_EXCH_STOCKS: return "Exchange Stocks";
            case ENUM_SYMBOL_CALC_MODE::SYMBOL_CALC_MODE_EXCH_FUTURES: return "Exchange Futures";
            case ENUM_SYMBOL_CALC_MODE::SYMBOL_CALC_MODE_EXCH_OPTIONS: return "Exchange Options";
            case ENUM_SYMBOL_CALC_MODE::SYMBOL_CALC_MODE_EXCH_BONDS: return "Exchange Bonds";
            default: return "Unknown";
        }
    }

    /**
     * @brief Get minimal stop level (distance from price)
     * @return Stops level in points
     */
    int32_t StopsLevel() const noexcept { return stops_level_; }

    /**
     * @brief Get freeze level (order modification freeze distance)
     * @return Freeze level in points
     */
    int32_t FreezeLevel() const noexcept { return freeze_level_; }

    // --- Currency Information (MT5 API) ---

    /**
     * @brief Get base currency
     * @return Base currency code (e.g., "EUR" in EURUSD)
     */
    std::string CurrencyBase() const noexcept { return currency_base_; }

    /**
     * @brief Get profit currency
     * @return Profit currency code (e.g., "USD" in EURUSD)
     */
    std::string CurrencyProfit() const noexcept { return currency_profit_; }

    /**
     * @brief Get margin currency
     * @return Margin currency code
     */
    std::string CurrencyMargin() const noexcept { return currency_margin_; }

    // --- Utility Methods (MT5 API) ---

    /**
     * @brief Normalize price according to symbol properties
     * @param price Price to normalize
     * @return Normalized price
     */
    double NormalizePrice(double price) const noexcept {
        if (digits_ > 0) {
            double multiplier = pow(10.0, digits_);
            return std::round(price * multiplier) / multiplier;
        }
        return price;
    }

    /**
     * @brief Refresh symbol data (placeholder for backtesting)
     * @return True (always succeeds in backtesting)
     */
    bool Refresh() noexcept {
        return true;  // In backtesting, data is pushed to us
    }

    /**
     * @brief Refresh rates (placeholder for backtesting)
     * @return True (always succeeds in backtesting)
     */
    bool RefreshRates() noexcept {
        return true;  // In backtesting, rates are updated via UpdatePrice()
    }

    // --- Internal Setters (for backtesting engine) ---

    void SetSymbolId(uint32_t id) noexcept { symbol_id_ = id; }
    void SetDescription(const std::string& desc) noexcept { description_ = desc; }
    void SetPath(const std::string& path) noexcept { path_ = path; }
    void SetDigits(int32_t digits) noexcept { digits_ = digits; }
    void SetPoint(double point) noexcept { point_ = point; }
    void SetSpread(int32_t spread) noexcept { spread_ = spread; }
    void SetSpreadFloat(bool floating) noexcept { spread_float_ = floating; }
    void SetTickValue(double value) noexcept { tick_value_ = value; }
    void SetTickSize(double size) noexcept { tick_size_ = size; }
    void SetTickValueProfit(double value) noexcept { tick_value_profit_ = value; }
    void SetTickValueLoss(double value) noexcept { tick_value_loss_ = value; }
    void SetContractSize(double size) noexcept { contract_size_ = size; }
    void SetVolumeMin(double min) noexcept { volume_min_ = min; }
    void SetVolumeMax(double max) noexcept { volume_max_ = max; }
    void SetVolumeStep(double step) noexcept { volume_step_ = step; }
    void SetVolumeLimit(double limit) noexcept { volume_limit_ = limit; }
    void SetMarginInitial(double margin) noexcept { margin_initial_ = margin; }
    void SetMarginMaintenance(double margin) noexcept { margin_maintenance_ = margin; }
    void SetMarginLong(double margin) noexcept { margin_long_ = margin; }
    void SetMarginShort(double margin) noexcept { margin_short_ = margin; }
    void SetSwapLong(double swap) noexcept { swap_long_ = swap; }
    void SetSwapShort(double swap) noexcept { swap_short_ = swap; }
    void SetSwapMode(ENUM_SYMBOL_SWAP_MODE mode) noexcept { swap_mode_ = mode; }
    void SetSwapRollover3days(ENUM_DAY_OF_WEEK day) noexcept { swap_rollover3days_ = day; }
    void SetTradeMode(ENUM_SYMBOL_TRADE_MODE mode) noexcept { trade_mode_ = mode; }
    void SetTradeExecution(ENUM_SYMBOL_TRADE_EXECUTION mode) noexcept { trade_execution_ = mode; }
    void SetTradeCalcMode(ENUM_SYMBOL_CALC_MODE mode) noexcept { trade_calc_mode_ = mode; }
    void SetStopsLevel(int32_t level) noexcept { stops_level_ = level; }
    void SetFreezeLevel(int32_t level) noexcept { freeze_level_ = level; }
    void SetCurrencyBase(const std::string& currency) noexcept { currency_base_ = currency; }
    void SetCurrencyProfit(const std::string& currency) noexcept { currency_profit_ = currency; }
    void SetCurrencyMargin(const std::string& currency) noexcept { currency_margin_ = currency; }

    /**
     * @brief Update current price data
     * @param bid Current bid price
     * @param ask Current ask price
     * @param timestamp Quote timestamp (seconds)
     */
    void UpdatePrice(double bid, double ask, int64_t timestamp = 0) noexcept {
        double multiplier = pow(10.0, digits_);
        bid_ = static_cast<int64_t>(bid * multiplier + 0.5);
        ask_ = static_cast<int64_t>(ask * multiplier + 0.5);
        double fp_per_point = point_ * pow(10.0, digits_);
        spread_ = (fp_per_point > 0.0) ? static_cast<int32_t>((ask_ - bid_) / fp_per_point) : 0;
        time_ = timestamp;

        // Update high/low
        if (bid_ > bid_high_ || bid_high_ == 0) bid_high_ = bid_;
        if (bid_ < bid_low_ || bid_low_ == 0) bid_low_ = bid_;
        if (ask_ > ask_high_ || ask_high_ == 0) ask_high_ = ask_;
        if (ask_ < ask_low_ || ask_low_ == 0) ask_low_ = ask_;
    }
};

} // namespace hqt

