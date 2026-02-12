/**
 * @file account_info.hpp
 * @brief Account information class (mirrors MT5 CAccountInfo)
 *
 * Provides access to account properties and state.
 * Mirrors MQL5's CAccountInfo from Trade.mqh standard library.
 * See: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/caccountinfo
 */

#pragma once

#include <cstdint>
#include <string>

namespace hqt {

/**
 * @brief Account trade mode
 */
enum class ENUM_ACCOUNT_TRADE_MODE {
    ACCOUNT_TRADE_MODE_DEMO = 0,    ///< Demo account
    ACCOUNT_TRADE_MODE_CONTEST = 1, ///< Contest account
    ACCOUNT_TRADE_MODE_REAL = 2     ///< Real account
};

/**
 * @brief Account stop out mode
 */
enum class ENUM_ACCOUNT_STOPOUT_MODE {
    ACCOUNT_STOPOUT_MODE_PERCENT = 0, ///< Stop out calculated as percentage
    ACCOUNT_STOPOUT_MODE_MONEY = 1    ///< Stop out calculated as money
};

/**
 * @brief Account margin calculation mode
 */
enum class ENUM_ACCOUNT_MARGIN_MODE {
    ACCOUNT_MARGIN_MODE_RETAIL_NETTING = 0,  ///< Netting mode for retail accounts
    ACCOUNT_MARGIN_MODE_EXCHANGE = 1,        ///< Exchange mode
    ACCOUNT_MARGIN_MODE_RETAIL_HEDGING = 2   ///< Hedging mode for retail accounts
};

/**
 * @brief Account information class (mirrors MT5 CAccountInfo)
 *
 * Provides access to account properties and calculations.
 * All monetary values stored in fixed-point (1/1,000,000 units) internally,
 * but exposed as doubles for MT5 compatibility.
 */
class AccountInfo {
private:
    // Internal state (fixed-point for precision)
    int64_t balance_;           ///< Account balance (fixed-point)
    int64_t equity_;            ///< Current equity (fixed-point)
    int64_t margin_;            ///< Margin used (fixed-point)
    int64_t margin_free_;       ///< Free margin (fixed-point)
    int64_t profit_;            ///< Current profit (fixed-point)
    int64_t credit_;            ///< Credit facility (fixed-point)
    double margin_level_;       ///< Margin level percentage
    double margin_so_call_;     ///< Margin call level
    double margin_so_so_;       ///< Stop out level

    // Account properties
    int login_;                 ///< Account number
    std::string name_;          ///< Client name
    std::string server_;        ///< Trade server name
    std::string currency_;      ///< Account currency
    std::string company_;       ///< Broker company name
    int leverage_;              ///< Account leverage
    int limit_orders_;          ///< Max pending orders

    // Flags
    ENUM_ACCOUNT_TRADE_MODE trade_mode_;
    ENUM_ACCOUNT_STOPOUT_MODE stopout_mode_;
    ENUM_ACCOUNT_MARGIN_MODE margin_mode_;
    bool trade_allowed_;        ///< Trade permission
    bool trade_expert_;         ///< Expert Advisor permission

    // Additional statistics (not in MT5 CAccountInfo but useful for backtesting)
    int64_t total_profit_;      ///< Cumulative realized profit
    int64_t total_loss_;        ///< Cumulative realized loss
    int64_t total_commission_;  ///< Total commission paid
    int64_t total_swap_;        ///< Total swap charged/credited
    uint32_t total_trades_;     ///< Total closed trades
    uint32_t winning_trades_;   ///< Number of winners
    uint32_t losing_trades_;    ///< Number of losers
    uint32_t daily_trades_;     ///< Trades today
    int64_t daily_profit_;      ///< Profit today
    int64_t daily_high_equity_; ///< Daily high equity
    int64_t daily_low_equity_;  ///< Daily low equity

public:
    /**
     * @brief Constructor
     * @param initial_balance Initial account balance
     * @param currency Account currency (e.g., "USD")
     * @param leverage Account leverage (e.g., 100 for 1:100)
     */
    explicit AccountInfo(double initial_balance = 10000.0,
                        const std::string& currency = "USD",
                        int leverage = 100) noexcept
        : balance_(static_cast<int64_t>(initial_balance * 1'000'000)),
          equity_(static_cast<int64_t>(initial_balance * 1'000'000)),
          margin_(0),
          margin_free_(static_cast<int64_t>(initial_balance * 1'000'000)),
          profit_(0),
          credit_(0),
          margin_level_(0.0),
          margin_so_call_(100.0),
          margin_so_so_(50.0),
          login_(0),
          name_(""),
          server_(""),
          currency_(currency),
          company_("HQT Backtester"),
          leverage_(leverage),
          limit_orders_(200),
          trade_mode_(ENUM_ACCOUNT_TRADE_MODE::ACCOUNT_TRADE_MODE_DEMO),
          stopout_mode_(ENUM_ACCOUNT_STOPOUT_MODE::ACCOUNT_STOPOUT_MODE_PERCENT),
          margin_mode_(ENUM_ACCOUNT_MARGIN_MODE::ACCOUNT_MARGIN_MODE_RETAIL_NETTING),
          trade_allowed_(true),
          trade_expert_(true),
          total_profit_(0),
          total_loss_(0),
          total_commission_(0),
          total_swap_(0),
          total_trades_(0),
          winning_trades_(0),
          losing_trades_(0),
          daily_trades_(0),
          daily_profit_(0),
          daily_high_equity_(static_cast<int64_t>(initial_balance * 1'000'000)),
          daily_low_equity_(static_cast<int64_t>(initial_balance * 1'000'000)) {}

    // --- Integer Property Accessors (MT5 API) ---

    /**
     * @brief Get account number
     * @return Account login number
     */
    int Login() const noexcept { return login_; }

    /**
     * @brief Get trade mode
     * @return Trade mode (demo/contest/real)
     */
    ENUM_ACCOUNT_TRADE_MODE TradeMode() const noexcept { return trade_mode_; }

    /**
     * @brief Get trade mode as string
     * @return Trade mode description
     */
    std::string TradeModeDescription() const noexcept {
        switch (trade_mode_) {
            case ENUM_ACCOUNT_TRADE_MODE::ACCOUNT_TRADE_MODE_DEMO: return "Demo";
            case ENUM_ACCOUNT_TRADE_MODE::ACCOUNT_TRADE_MODE_CONTEST: return "Contest";
            case ENUM_ACCOUNT_TRADE_MODE::ACCOUNT_TRADE_MODE_REAL: return "Real";
            default: return "Unknown";
        }
    }

    /**
     * @brief Get account leverage
     * @return Leverage (e.g., 100 for 1:100)
     */
    int Leverage() const noexcept { return leverage_; }

    /**
     * @brief Get stop out mode
     * @return Stop out mode (percent or money)
     */
    ENUM_ACCOUNT_STOPOUT_MODE StopoutMode() const noexcept { return stopout_mode_; }

    /**
     * @brief Get stop out mode as string
     * @return Stop out mode description
     */
    std::string StopoutModeDescription() const noexcept {
        switch (stopout_mode_) {
            case ENUM_ACCOUNT_STOPOUT_MODE::ACCOUNT_STOPOUT_MODE_PERCENT: return "Percent";
            case ENUM_ACCOUNT_STOPOUT_MODE::ACCOUNT_STOPOUT_MODE_MONEY: return "Money";
            default: return "Unknown";
        }
    }

    /**
     * @brief Get margin calculation mode
     * @return Margin mode (netting/exchange/hedging)
     */
    ENUM_ACCOUNT_MARGIN_MODE MarginMode() const noexcept { return margin_mode_; }

    /**
     * @brief Get margin mode as string
     * @return Margin mode description
     */
    std::string MarginModeDescription() const noexcept {
        switch (margin_mode_) {
            case ENUM_ACCOUNT_MARGIN_MODE::ACCOUNT_MARGIN_MODE_RETAIL_NETTING: return "Retail Netting";
            case ENUM_ACCOUNT_MARGIN_MODE::ACCOUNT_MARGIN_MODE_EXCHANGE: return "Exchange";
            case ENUM_ACCOUNT_MARGIN_MODE::ACCOUNT_MARGIN_MODE_RETAIL_HEDGING: return "Retail Hedging";
            default: return "Unknown";
        }
    }

    /**
     * @brief Check if trading is allowed
     * @return True if trading is permitted
     */
    bool TradeAllowed() const noexcept { return trade_allowed_; }

    /**
     * @brief Check if Expert Advisors are allowed
     * @return True if EAs are permitted
     */
    bool TradeExpert() const noexcept { return trade_expert_; }

    /**
     * @brief Get maximum pending orders limit
     * @return Max number of pending orders
     */
    int LimitOrders() const noexcept { return limit_orders_; }

    // --- Double Property Accessors (MT5 API) ---

    /**
     * @brief Get account balance
     * @return Balance in account currency
     */
    double Balance() const noexcept {
        return static_cast<double>(balance_) / 1'000'000.0;
    }

    /**
     * @brief Get credit amount
     * @return Credit in account currency
     */
    double Credit() const noexcept {
        return static_cast<double>(credit_) / 1'000'000.0;
    }

    /**
     * @brief Get current profit
     * @return Floating profit/loss in account currency
     */
    double Profit() const noexcept {
        return static_cast<double>(profit_) / 1'000'000.0;
    }

    /**
     * @brief Get current equity
     * @return Equity (balance + floating profit) in account currency
     */
    double Equity() const noexcept {
        return static_cast<double>(equity_) / 1'000'000.0;
    }

    /**
     * @brief Get used margin
     * @return Margin used by open positions
     */
    double Margin() const noexcept {
        return static_cast<double>(margin_) / 1'000'000.0;
    }

    /**
     * @brief Get free margin
     * @return Available margin for new trades
     */
    double FreeMargin() const noexcept {
        return static_cast<double>(margin_free_) / 1'000'000.0;
    }

    /**
     * @brief Get margin level
     * @return Margin level percentage (equity / margin * 100)
     */
    double MarginLevel() const noexcept {
        return margin_level_;
    }

    /**
     * @brief Get margin call level
     * @return Margin call threshold percentage
     */
    double MarginCall() const noexcept {
        return margin_so_call_;
    }

    /**
     * @brief Get stop out level
     * @return Stop out threshold percentage
     */
    double MarginStopOut() const noexcept {
        return margin_so_so_;
    }

    // --- String Property Accessors (MT5 API) ---

    /**
     * @brief Get client name
     * @return Account holder name
     */
    std::string Name() const noexcept { return name_; }

    /**
     * @brief Get trade server name
     * @return Server address
     */
    std::string Server() const noexcept { return server_; }

    /**
     * @brief Get account currency
     * @return Currency code (e.g., "USD")
     */
    std::string Currency() const noexcept { return currency_; }

    /**
     * @brief Get broker company name
     * @return Company name
     */
    std::string Company() const noexcept { return company_; }

    // --- Internal Update Methods (Not in MT5 API) ---

    /**
     * @brief Add to used margin (internal use)
     * @param amount Amount to add (fixed-point)
     */
    void AddMargin(int64_t amount) noexcept {
        margin_ += amount;
        UpdateEquity(profit_);
    }

    /**
     * @brief Subtract from used margin (internal use)
     * @param amount Amount to subtract (fixed-point)
     */
    void SubtractMargin(int64_t amount) noexcept {
        margin_ -= amount;
        UpdateEquity(profit_);
    }

    /**
     * @brief Add to balance (internal use, for commission)
     * @param amount Amount to add/subtract (fixed-point)
     */
    void AddBalance(int64_t amount) noexcept {
        balance_ += amount;
        UpdateEquity(profit_);
    }

    /**
     * @brief Add to total commission (internal use)
     * @param amount Commission amount (fixed-point)
     */
    void AddCommission(int64_t amount) noexcept {
        total_commission_ += amount;
    }

    /**
     * @brief Update equity from unrealized PnL
     * @param total_unrealized_pnl Sum of all open position PnL (fixed-point)
     */
    void UpdateEquity(int64_t total_unrealized_pnl) noexcept {
        profit_ = total_unrealized_pnl;
        equity_ = balance_ + total_unrealized_pnl;

        // Update margin level
        if (margin_ > 0) {
            margin_level_ = (static_cast<double>(equity_) / static_cast<double>(margin_)) * 100.0;
        } else {
            margin_level_ = 0.0;
        }

        margin_free_ = equity_ - margin_;

        // Update daily high/low
        if (equity_ > daily_high_equity_) {
            daily_high_equity_ = equity_;
        }
        if (equity_ < daily_low_equity_ || daily_low_equity_ == 0) {
            daily_low_equity_ = equity_;
        }
    }

    /**
     * @brief Set used margin
     * @param margin Margin amount (fixed-point)
     */
    void SetMargin(int64_t margin) noexcept {
        margin_ = margin;
        UpdateEquity(profit_);  // Recalculate margin level
    }

    /**
     * @brief Apply realized profit/loss to balance
     * @param realized_pnl Realized profit (positive) or loss (negative)
     * @param commission Commission charged
     * @param swap Swap charged or credited
     */
    void ApplyRealizedPnL(int64_t realized_pnl, int64_t commission, int64_t swap) noexcept {
        int64_t net_pnl = realized_pnl - commission + swap;

        balance_ += net_pnl;
        total_commission_ += commission;
        total_swap_ += swap;
        total_trades_++;

        if (realized_pnl > 0) {
            total_profit_ += realized_pnl;
            winning_trades_++;
        } else if (realized_pnl < 0) {
            total_loss_ += (-realized_pnl);
            losing_trades_++;
        }

        daily_trades_++;
        daily_profit_ += net_pnl;
    }

    /**
     * @brief Reset daily statistics
     */
    void ResetDailyStats() noexcept {
        daily_trades_ = 0;
        daily_profit_ = 0;
        daily_high_equity_ = equity_;
        daily_low_equity_ = equity_;
    }

    /**
     * @brief Check if margin call level is breached
     * @return True if below margin call level
     */
    bool IsMarginCall() const noexcept {
        return margin_ > 0 && margin_level_ < margin_so_call_;
    }

    /**
     * @brief Check if stop out level is breached
     * @return True if below stop out level
     */
    bool IsStopOut() const noexcept {
        return margin_ > 0 && margin_level_ < margin_so_so_;
    }

    // --- Setters (for initialization) ---

    void SetLogin(int login) noexcept { login_ = login; }
    void SetName(const std::string& name) noexcept { name_ = name; }
    void SetServer(const std::string& server) noexcept { server_ = server; }
    void SetCompany(const std::string& company) noexcept { company_ = company; }
    void SetLeverage(int leverage) noexcept { leverage_ = leverage; }
    void SetTradeMode(ENUM_ACCOUNT_TRADE_MODE mode) noexcept { trade_mode_ = mode; }
    void SetStopoutMode(ENUM_ACCOUNT_STOPOUT_MODE mode) noexcept { stopout_mode_ = mode; }
    void SetMarginMode(ENUM_ACCOUNT_MARGIN_MODE mode) noexcept { margin_mode_ = mode; }
    void SetMarginCall(double level) noexcept { margin_so_call_ = level; }
    void SetMarginStopOut(double level) noexcept { margin_so_so_ = level; }
    void SetTradeAllowed(bool allowed) noexcept { trade_allowed_ = allowed; }
    void SetTradeExpert(bool allowed) noexcept { trade_expert_ = allowed; }
    void SetLimitOrders(int limit) noexcept { limit_orders_ = limit; }

    // --- Additional Statistics (Backtesting specific) ---

    uint32_t TotalTrades() const noexcept { return total_trades_; }
    uint32_t WinningTrades() const noexcept { return winning_trades_; }
    uint32_t LosingTrades() const noexcept { return losing_trades_; }
    double TotalProfit() const noexcept { return static_cast<double>(total_profit_) / 1'000'000.0; }
    double TotalLoss() const noexcept { return static_cast<double>(total_loss_) / 1'000'000.0; }
    double TotalCommission() const noexcept { return static_cast<double>(total_commission_) / 1'000'000.0; }
    double TotalSwap() const noexcept { return static_cast<double>(total_swap_) / 1'000'000.0; }
    uint32_t DailyTrades() const noexcept { return daily_trades_; }
    double DailyProfit() const noexcept { return static_cast<double>(daily_profit_) / 1'000'000.0; }
};

} // namespace hqt
