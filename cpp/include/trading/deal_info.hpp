/**
 * @file deal_info.hpp
 * @brief Deal information class (mirrors MT5 CDealInfo)
 *
 * Provides access to completed deal (trade history) properties.
 * Mirrors MQL5's CDealInfo from Trade.mqh standard library.
 * See: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/cdealinfo
 */

#pragma once

#include <cstdint>
#include <string>
#include <cmath>

namespace hqt {

/**
 * @brief Deal type (MT5-compatible)
 */
enum class ENUM_DEAL_TYPE {
    DEAL_TYPE_BUY = 0,                ///< Buy deal
    DEAL_TYPE_SELL = 1,               ///< Sell deal
    DEAL_TYPE_BALANCE = 2,            ///< Balance operation
    DEAL_TYPE_CREDIT = 3,             ///< Credit operation
    DEAL_TYPE_CHARGE = 4,             ///< Additional charge
    DEAL_TYPE_CORRECTION = 5,         ///< Correction
    DEAL_TYPE_BONUS = 6,              ///< Bonus
    DEAL_TYPE_COMMISSION = 7,         ///< Additional commission
    DEAL_TYPE_COMMISSION_DAILY = 8,   ///< Daily commission
    DEAL_TYPE_COMMISSION_MONTHLY = 9, ///< Monthly commission
    DEAL_TYPE_COMMISSION_AGENT_DAILY = 10,   ///< Daily agent commission
    DEAL_TYPE_COMMISSION_AGENT_MONTHLY = 11, ///< Monthly agent commission
    DEAL_TYPE_INTEREST = 12,          ///< Interest rate
    DEAL_TYPE_BUY_CANCELED = 13,      ///< Canceled buy deal
    DEAL_TYPE_SELL_CANCELED = 14,     ///< Canceled sell deal
    DEAL_DIVIDEND = 15,               ///< Dividend
    DEAL_DIVIDEND_FRANKED = 16,       ///< Franked dividend
    DEAL_TAX = 17                     ///< Tax
};

/**
 * @brief Deal entry type (direction)
 */
enum class ENUM_DEAL_ENTRY {
    DEAL_ENTRY_IN = 0,     ///< Entry into market (open position)
    DEAL_ENTRY_OUT = 1,    ///< Exit from market (close position)
    DEAL_ENTRY_INOUT = 2,  ///< Reverse position (close and open opposite)
    DEAL_ENTRY_OUT_BY = 3  ///< Close position by opposite position
};

/**
 * @brief Deal information class (mirrors MT5 CDealInfo)
 *
 * Provides access to completed deal properties.
 * All price and monetary values stored internally as fixed-point for precision.
 */
class DealInfo {
private:
    // Core identification
    uint64_t ticket_;           ///< Deal ticket
    uint64_t order_;            ///< Order that generated this deal
    uint64_t position_id_;      ///< Position identifier
    std::string symbol_;        ///< Symbol name
    uint32_t magic_;            ///< Magic number

    // Deal classification
    ENUM_DEAL_TYPE type_;       ///< Deal type
    ENUM_DEAL_ENTRY entry_;     ///< Deal entry direction

    // Volume and price (fixed-point internally)
    double volume_;             ///< Deal volume in lots
    int64_t price_;             ///< Deal execution price

    // Financial data (fixed-point internally)
    int64_t profit_;            ///< Profit/loss
    int64_t commission_;        ///< Commission
    int64_t swap_;              ///< Swap

    // Time information
    int64_t time_;              ///< Deal time (seconds since epoch)
    int64_t time_msc_;          ///< Deal time (milliseconds since epoch)

    // Comment
    std::string comment_;       ///< Deal comment

    // Symbol info (for conversions)
    int32_t digits_;

    // Extended info (for backtesting, not in MT5 CDealInfo)
    int64_t entry_price_;       ///< Position entry price (for analysis)
    int64_t exit_price_;        ///< Position exit price (for analysis)
    int64_t entry_time_;        ///< Position open time
    int64_t exit_time_;         ///< Position close time

public:
    /**
     * @brief Constructor
     */
    DealInfo()
        : ticket_(0),
          order_(0),
          position_id_(0),
          symbol_(""),
          magic_(0),
          type_(ENUM_DEAL_TYPE::DEAL_TYPE_BUY),
          entry_(ENUM_DEAL_ENTRY::DEAL_ENTRY_IN),
          volume_(0.0),
          price_(0),
          profit_(0),
          commission_(0),
          swap_(0),
          time_(0),
          time_msc_(0),
          comment_(""),
          digits_(5),
          entry_price_(0),
          exit_price_(0),
          entry_time_(0),
          exit_time_(0) {}

    // --- Integer Property Accessors (MT5 API) ---

    /**
     * @brief Get deal ticket
     * @return Deal ticket number
     */
    uint64_t Ticket() const noexcept { return ticket_; }

    /**
     * @brief Get order ticket
     * @return Order that generated this deal
     */
    uint64_t Order() const noexcept { return order_; }

    /**
     * @brief Get deal execution time
     * @return Time in seconds since epoch
     */
    int64_t Time() const noexcept { return time_; }

    /**
     * @brief Get deal execution time in milliseconds
     * @return Time in milliseconds since epoch
     */
    int64_t TimeMsc() const noexcept { return time_msc_; }

    /**
     * @brief Get deal type
     * @return Deal type (buy, sell, balance, etc.)
     */
    ENUM_DEAL_TYPE DealType() const noexcept { return type_; }

    /**
     * @brief Get deal type as string
     * @return Deal type description
     */
    std::string TypeDescription() const noexcept {
        switch (type_) {
            case ENUM_DEAL_TYPE::DEAL_TYPE_BUY: return "Buy";
            case ENUM_DEAL_TYPE::DEAL_TYPE_SELL: return "Sell";
            case ENUM_DEAL_TYPE::DEAL_TYPE_BALANCE: return "Balance";
            case ENUM_DEAL_TYPE::DEAL_TYPE_CREDIT: return "Credit";
            case ENUM_DEAL_TYPE::DEAL_TYPE_CHARGE: return "Charge";
            case ENUM_DEAL_TYPE::DEAL_TYPE_CORRECTION: return "Correction";
            case ENUM_DEAL_TYPE::DEAL_TYPE_BONUS: return "Bonus";
            case ENUM_DEAL_TYPE::DEAL_TYPE_COMMISSION: return "Commission";
            case ENUM_DEAL_TYPE::DEAL_TYPE_COMMISSION_DAILY: return "Daily Commission";
            case ENUM_DEAL_TYPE::DEAL_TYPE_COMMISSION_MONTHLY: return "Monthly Commission";
            case ENUM_DEAL_TYPE::DEAL_TYPE_COMMISSION_AGENT_DAILY: return "Agent Daily Commission";
            case ENUM_DEAL_TYPE::DEAL_TYPE_COMMISSION_AGENT_MONTHLY: return "Agent Monthly Commission";
            case ENUM_DEAL_TYPE::DEAL_TYPE_INTEREST: return "Interest";
            case ENUM_DEAL_TYPE::DEAL_TYPE_BUY_CANCELED: return "Buy Canceled";
            case ENUM_DEAL_TYPE::DEAL_TYPE_SELL_CANCELED: return "Sell Canceled";
            case ENUM_DEAL_TYPE::DEAL_DIVIDEND: return "Dividend";
            case ENUM_DEAL_TYPE::DEAL_DIVIDEND_FRANKED: return "Franked Dividend";
            case ENUM_DEAL_TYPE::DEAL_TAX: return "Tax";
            default: return "Unknown";
        }
    }

    /**
     * @brief Get deal entry direction
     * @return Entry type (in, out, inout, out_by)
     */
    ENUM_DEAL_ENTRY Entry() const noexcept { return entry_; }

    /**
     * @brief Get deal entry as string
     * @return Entry description
     */
    std::string EntryDescription() const noexcept {
        switch (entry_) {
            case ENUM_DEAL_ENTRY::DEAL_ENTRY_IN: return "Entry In";
            case ENUM_DEAL_ENTRY::DEAL_ENTRY_OUT: return "Entry Out";
            case ENUM_DEAL_ENTRY::DEAL_ENTRY_INOUT: return "Entry InOut";
            case ENUM_DEAL_ENTRY::DEAL_ENTRY_OUT_BY: return "Entry Out By";
            default: return "Unknown";
        }
    }

    /**
     * @brief Get magic number
     * @return Expert Advisor identifier
     */
    uint32_t Magic() const noexcept { return magic_; }

    /**
     * @brief Get position identifier
     * @return Position ID
     */
    uint64_t PositionId() const noexcept { return position_id_; }

    // --- Double Property Accessors (MT5 API) ---

    /**
     * @brief Get deal volume
     * @return Volume in lots
     */
    double Volume() const noexcept { return volume_; }

    /**
     * @brief Get deal price
     * @return Execution price
     */
    double Price() const noexcept {
        return static_cast<double>(price_) / std::pow(10.0, digits_);
    }

    /**
     * @brief Get commission (note: typo in MT5 API is "Commision", we use correct spelling)
     * @return Commission amount
     */
    double Commission() const noexcept {
        return static_cast<double>(commission_) / 1'000'000.0;
    }

    /**
     * @brief MT5 API compatibility (with typo)
     * @return Commission amount
     */
    double Commision() const noexcept {
        return Commission();  // Redirect to correct spelling
    }

    /**
     * @brief Get swap
     * @return Swap/rollover charges
     */
    double Swap() const noexcept {
        return static_cast<double>(swap_) / 1'000'000.0;
    }

    /**
     * @brief Get profit
     * @return Financial result
     */
    double Profit() const noexcept {
        return static_cast<double>(profit_) / 1'000'000.0;
    }

    // --- String Property Accessors (MT5 API) ---

    /**
     * @brief Get symbol name
     * @return Symbol
     */
    std::string Symbol() const noexcept { return symbol_; }

    /**
     * @brief Get deal comment
     * @return Comment string
     */
    std::string Comment() const noexcept { return comment_; }

    // --- Selection Methods (MT5 API) ---

    /**
     * @brief Select deal by ticket (placeholder for backtesting)
     * @param ticket Deal ticket
     * @return True if deal exists
     */
    bool Select(uint64_t ticket) noexcept {
        // In backtesting, deals are managed by CTrade
        // This is a placeholder for MT5 API compatibility
        ticket_ = ticket;
        return true;
    }

    /**
     * @brief Select deal by index (placeholder for backtesting)
     * @param index Deal index in history
     * @return True if deal exists
     */
    bool SelectByIndex(int index) noexcept {
        // Placeholder for MT5 API compatibility
        (void)index;
        return false;
    }

    // --- Internal Setters (for backtesting engine) ---

    void SetTicket(uint64_t ticket) noexcept { ticket_ = ticket; }
    void SetOrder(uint64_t order) noexcept { order_ = order; }
    void SetPositionId(uint64_t id) noexcept { position_id_ = id; }
    void SetSymbol(const std::string& symbol) noexcept { symbol_ = symbol; }
    void SetMagic(uint32_t magic) noexcept { magic_ = magic; }
    void SetType(ENUM_DEAL_TYPE type) noexcept { type_ = type; }
    void SetEntry(ENUM_DEAL_ENTRY entry) noexcept { entry_ = entry; }
    void SetVolume(double volume) noexcept { volume_ = volume; }
    void SetComment(const std::string& comment) noexcept { comment_ = comment; }
    void SetDigits(int32_t digits) noexcept { digits_ = digits; }

    void SetTime(int64_t time_sec, int64_t time_msc = 0) noexcept {
        time_ = time_sec;
        time_msc_ = (time_msc > 0) ? time_msc : (time_sec * 1000);
    }

    void SetPrice(double price) noexcept {
        price_ = static_cast<int64_t>((price) * std::pow(10.0, static_cast<double>(digits_)) + 0.5);
    }

    void SetProfit(double profit) noexcept {
        profit_ = static_cast<int64_t>(profit * 1'000'000.0);
    }

    void SetCommission(double commission) noexcept {
        commission_ = static_cast<int64_t>(commission * 1'000'000.0);
    }

    void SetSwap(double swap) noexcept {
        swap_ = static_cast<int64_t>(swap * 1'000'000.0);
    }

    // --- Extended Setters (for backtesting analytics) ---

    void SetEntryPrice(double price) noexcept {
        entry_price_ = static_cast<int64_t>((price) * std::pow(10.0, static_cast<double>(digits_)) + 0.5);
    }

    void SetExitPrice(double price) noexcept {
        exit_price_ = static_cast<int64_t>((price) * std::pow(10.0, static_cast<double>(digits_)) + 0.5);
    }

    void SetEntryTime(int64_t time) noexcept { entry_time_ = time; }
    void SetExitTime(int64_t time) noexcept { exit_time_ = time; }

    // --- Utility Methods (backtesting helpers, not in MT5 API) ---

    /**
     * @brief Get net profit including commission and swap
     * @return Net profit/loss
     */
    double NetProfit() const noexcept {
        return Profit() + Swap() - Commission();
    }

    /**
     * @brief Get position holding time in seconds
     * @return Duration position was held
     */
    int64_t HoldingTime() const noexcept {
        if (entry_time_ == 0 || exit_time_ == 0) {
            return 0;
        }
        return exit_time_ - entry_time_;
    }

    /**
     * @brief Get position holding time in days
     * @return Duration in days
     */
    double HoldingTimeDays() const noexcept {
        return HoldingTime() / (24.0 * 3600.0);
    }

    /**
     * @brief Check if deal is a winning trade
     * @return True if net profit is positive
     */
    bool IsWinner() const noexcept {
        return NetProfit() > 0.0;
    }

    /**
     * @brief Check if deal is a losing trade
     * @return True if net profit is negative
     */
    bool IsLoser() const noexcept {
        return NetProfit() < 0.0;
    }

    /**
     * @brief Check if deal is a trade (not balance/credit/etc.)
     * @return True if buy or sell deal
     */
    bool IsTrade() const noexcept {
        return type_ == ENUM_DEAL_TYPE::DEAL_TYPE_BUY ||
               type_ == ENUM_DEAL_TYPE::DEAL_TYPE_SELL;
    }

    /**
     * @brief Check if this is a buy deal
     * @return True if buy deal
     */
    bool IsBuy() const noexcept {
        return type_ == ENUM_DEAL_TYPE::DEAL_TYPE_BUY;
    }

    /**
     * @brief Check if this is a sell deal
     * @return True if sell deal
     */
    bool IsSell() const noexcept {
        return type_ == ENUM_DEAL_TYPE::DEAL_TYPE_SELL;
    }

    /**
     * @brief Check if this is a position entry
     * @return True if entry deal
     */
    bool IsEntry() const noexcept {
        return entry_ == ENUM_DEAL_ENTRY::DEAL_ENTRY_IN;
    }

    /**
     * @brief Check if this is a position exit
     * @return True if exit deal
     */
    bool IsExit() const noexcept {
        return entry_ == ENUM_DEAL_ENTRY::DEAL_ENTRY_OUT ||
               entry_ == ENUM_DEAL_ENTRY::DEAL_ENTRY_INOUT ||
               entry_ == ENUM_DEAL_ENTRY::DEAL_ENTRY_OUT_BY;
    }

    /**
     * @brief Get price movement in points
     * @param point Symbol point value
     * @return Price movement (positive for profit direction)
     */
    double PriceMovementPoints(double point) const noexcept {
        if (!IsTrade() || point == 0.0 || entry_price_ == 0 || exit_price_ == 0) {
            return 0.0;
        }

        int64_t price_diff = IsBuy()
            ? (exit_price_ - entry_price_)
            : (entry_price_ - exit_price_);

        return static_cast<double>(price_diff) / (point * std::pow(10.0, digits_));
    }

    /**
     * @brief Get return on investment percentage
     * @param initial_margin Margin required for position
     * @return ROI as percentage
     */
    double ROIPercent(double initial_margin) const noexcept {
        if (initial_margin == 0.0) {
            return 0.0;
        }
        return (NetProfit() / initial_margin) * 100.0;
    }

    /**
     * @brief Get entry price (extended info)
     * @return Entry price
     */
    double EntryPrice() const noexcept {
        return static_cast<double>(entry_price_) / std::pow(10.0, digits_);
    }

    /**
     * @brief Get exit price (extended info)
     * @return Exit price
     */
    double ExitPrice() const noexcept {
        return static_cast<double>(exit_price_) / std::pow(10.0, digits_);
    }

    /**
     * @brief Get entry time (extended info)
     * @return Entry timestamp
     */
    int64_t EntryTime() const noexcept { return entry_time_; }

    /**
     * @brief Get exit time (extended info)
     * @return Exit timestamp
     */
    int64_t ExitTime() const noexcept { return exit_time_; }

    // --- Internal Fixed-Point Accessors (for CTrade) ---

    int64_t GetPriceFP() const noexcept { return price_; }
    int64_t GetProfitFP() const noexcept { return profit_; }
    int64_t GetCommissionFP() const noexcept { return commission_; }
    int64_t GetSwapFP() const noexcept { return swap_; }
    int64_t GetEntryPriceFP() const noexcept { return entry_price_; }
    int64_t GetExitPriceFP() const noexcept { return exit_price_; }
};

} // namespace hqt
