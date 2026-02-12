/**
 * @file margin_calculator.hpp
 * @brief Margin calculation and stop-out enforcement
 *
 * Calculates required margin, margin level, and enforces stop-out rules.
 * Supports both hedging and netting modes.
 */

#pragma once

#include "trading/account_info.hpp"
#include "trading/position_info.hpp"
#include "trading/symbol_info.hpp"
#include "util/currency_converter.hpp"
#include <vector>
#include <algorithm>
#include <cmath>

namespace hqt {

/**
 * @brief Margin calculation modes
 */
enum class MarginMode : uint8_t {
    FOREX = 0,      ///< Forex calculation (leverage-based)
    CFD = 1,        ///< CFD calculation
    FUTURES = 2,    ///< Futures calculation
    EXCHANGE = 3    ///< Exchange stocks calculation
};

/**
 * @brief Margin calculator with stop-out enforcement
 *
 * Calculates margin requirements for positions and enforces
 * stop-out rules when margin level falls below threshold.
 *
 * Example:
 * @code
 * MarginCalculator calc(converter);
 *
 * // Calculate required margin for new position
 * double margin = calc.required_margin(
 *     symbol, POSITION_TYPE_BUY, 1.0, 1.10000, 100
 * );
 *
 * // Check if account has sufficient margin
 * if (calc.has_sufficient_margin(account, positions, margin)) {
 *     // Open position
 * }
 *
 * // Check for stop-out condition
 * if (calc.should_stop_out(account, positions, 20.0)) {
 *     // Close largest losing position
 * }
 * @endcode
 */
class MarginCalculator {
public:
    /**
     * @brief Construct margin calculator
     * @param converter Currency converter for cross-currency calculations
     */
    explicit MarginCalculator(const CurrencyConverter& converter)
        : converter_(converter) {}

    /**
     * @brief Calculate required margin for a position
     * @param symbol Symbol information
     * @param type Position type (BUY or SELL)
     * @param volume Position volume in lots
     * @param price Open price
     * @param leverage Account leverage
     * @return Required margin in account currency
     *
     * Formula (Forex): margin = (volume * contract_size * price) / leverage
     */
    double required_margin(const SymbolInfo& symbol,
                          ENUM_POSITION_TYPE type,
                          double volume,
                          double price,
                          int leverage) const noexcept {
        (void)type;  // Unused parameter (may be used for different margin modes)
        if (leverage <= 0) leverage = 1;

        // Basic forex calculation
        double contract_value = volume * symbol.ContractSize() * price;
        double margin = contract_value / static_cast<double>(leverage);

        return margin;
    }

    /**
     * @brief Calculate total margin used by all positions
     * @param positions Vector of open positions
     * @param symbols Map of symbol name -> SymbolInfo
     * @param leverage Account leverage
     * @param account_currency Account currency (for conversion)
     * @return Total margin in account currency
     */
    double total_margin(const std::vector<PositionInfo>& positions,
                       const std::unordered_map<std::string, SymbolInfo>& symbols,
                       int leverage,
                       const std::string& account_currency = "USD") const {
        double total = 0.0;

        for (const auto& pos : positions) {
            auto sym_it = symbols.find(pos.Symbol());
            if (sym_it == symbols.end()) continue;

            const SymbolInfo& symbol = sym_it->second;

            // Calculate margin for this position
            double margin = required_margin(
                symbol,
                pos.PositionType(),
                pos.Volume(),
                pos.PriceOpen(),
                leverage
            );

            // Convert to account currency if needed
            std::string pos_currency = symbol.CurrencyProfit();
            if (pos_currency != account_currency) {
                try {
                    margin = converter_.convert(margin, pos_currency, account_currency);
                } catch (const ConversionPathError&) {
                    // If conversion fails, use margin as-is
                }
            }

            total += margin;
        }

        return total;
    }

    /**
     * @brief Calculate margin level percentage
     * @param equity Current account equity
     * @param margin Total margin used
     * @return Margin level as percentage (equity / margin * 100)
     *
     * Margin level = (Equity / Margin) * 100%
     * - Above 100%: Safe
     * - Below 100%: Warning
     * - Below stop-out level: Forced position closure
     */
    double margin_level(double equity, double margin) const noexcept {
        if (margin <= 0.0) return INFINITY;
        return (equity / margin) * 100.0;
    }

    /**
     * @brief Calculate free margin (available for new positions)
     * @param equity Current equity
     * @param margin Used margin
     * @return Free margin amount
     *
     * Free margin = Equity - Margin
     */
    double free_margin(double equity, double margin) const noexcept {
        return equity - margin;
    }

    /**
     * @brief Check if account has sufficient margin for new position
     * @param account Account information
     * @param current_positions Currently open positions
     * @param symbols Map of symbols
     * @param additional_margin Margin required for new position
     * @param min_margin_level Minimum margin level to maintain (default: 100%)
     * @return True if sufficient margin available
     */
    bool has_sufficient_margin(const AccountInfo& account,
                              const std::vector<PositionInfo>& current_positions,
                              const std::unordered_map<std::string, SymbolInfo>& symbols,
                              double additional_margin,
                              double min_margin_level = 100.0) const {
        // Calculate current margin usage
        double current_margin = total_margin(
            current_positions,
            symbols,
            account.Leverage(),
            account.Currency()
        );

        // Calculate what margin level would be after opening position
        double new_margin = current_margin + additional_margin;
        double equity = account.Equity();

        if (new_margin <= 0.0) return true;

        double new_margin_level = margin_level(equity, new_margin);

        return new_margin_level >= min_margin_level;
    }

    /**
     * @brief Check if stop-out should be triggered
     * @param account Account information
     * @param positions Open positions
     * @param symbols Map of symbols
     * @param stop_out_level Stop-out threshold percentage (default: 20%)
     * @return True if margin level is below stop-out threshold
     *
     * When margin level falls below stop_out_level, the broker will
     * automatically close positions starting with the largest loser.
     */
    bool should_stop_out(const AccountInfo& account,
                        const std::vector<PositionInfo>& positions,
                        const std::unordered_map<std::string, SymbolInfo>& symbols,
                        double stop_out_level = 20.0) const {
        if (positions.empty()) return false;

        double margin = total_margin(
            positions,
            symbols,
            account.Leverage(),
            account.Currency()
        );

        if (margin <= 0.0) return false;

        double level = margin_level(account.Equity(), margin);
        return level < stop_out_level;
    }

    /**
     * @brief Find largest losing position for stop-out
     * @param positions Open positions
     * @return Index of largest losing position (-1 if none losing)
     *
     * Used to determine which position to close during stop-out.
     * Returns position with largest negative P&L.
     */
    int find_largest_loser(const std::vector<PositionInfo>& positions) const noexcept {
        if (positions.empty()) return -1;

        int worst_idx = -1;
        double worst_profit = 0.0;

        for (size_t i = 0; i < positions.size(); ++i) {
            double profit = positions[i].Profit();
            if (profit < worst_profit) {
                worst_profit = profit;
                worst_idx = static_cast<int>(i);
            }
        }

        return worst_idx;
    }

    /**
     * @brief Calculate margin call level
     * @param equity Current equity
     * @param margin Used margin
     * @param margin_call_level Margin call threshold (default: 80%)
     * @return True if margin call should be issued
     *
     * Margin call is a warning issued before stop-out.
     */
    bool is_margin_call(double equity,
                       double margin,
                       double margin_call_level = 80.0) const noexcept {
        if (margin <= 0.0) return false;
        double level = margin_level(equity, margin);
        return level < margin_call_level;
    }

    /**
     * @brief Calculate maximum volume that can be opened
     * @param symbol Symbol information
     * @param type Position type
     * @param price Open price
     * @param available_margin Free margin available
     * @param leverage Account leverage
     * @return Maximum volume in lots
     */
    double max_volume(const SymbolInfo& symbol,
                     ENUM_POSITION_TYPE type,
                     double price,
                     double available_margin,
                     int leverage) const noexcept {
        (void)type;  // Unused parameter
        if (leverage <= 0) leverage = 1;
        if (price <= 0.0) return 0.0;

        // margin = (volume * contract_size * price) / leverage
        // volume = (margin * leverage) / (contract_size * price)
        double max_vol = (available_margin * leverage) /
                        (symbol.ContractSize() * price);

        // Round down to nearest step
        double step = symbol.LotsStep();
        if (step > 0.0) {
            max_vol = std::floor(max_vol / step) * step;
        }

        // Clamp to symbol limits
        max_vol = std::max(symbol.LotsMin(), max_vol);
        max_vol = std::min(symbol.LotsMax(), max_vol);

        return max_vol;
    }

    /**
     * @brief Set hedging mode
     * @param enabled True to allow hedging (multiple positions per symbol)
     *
     * In hedging mode, long and short positions on the same symbol
     * both require margin. In netting mode, they offset each other.
     */
    void set_hedging_mode(bool enabled) noexcept {
        hedging_mode_ = enabled;
    }

    /**
     * @brief Check if hedging mode is enabled
     */
    bool is_hedging_mode() const noexcept {
        return hedging_mode_;
    }

private:
    const CurrencyConverter& converter_;
    bool hedging_mode_ = true;  ///< Hedging mode (true) vs netting mode (false)
};

} // namespace hqt
