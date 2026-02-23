/**
FILE: include\costs\commission_model.hpp

PURPOSE:
Defines commission_model.hpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in commission_model.hpp.
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

#include "data/tick.hpp"
#include "trading/symbol_info.hpp"
#include "costs/slippage_model.hpp"
#include <cstdint>
#include <memory>

namespace hqt {

/**
 * @brief Commission model interface
 *
 * Calculates commission charged for a trade.
 * Returns commission in account currency as fixed-point.
 */
class ICommissionModel {
public:
    virtual ~ICommissionModel() = default;

    /**
     * @brief Calculate commission for a trade
     * @param side Buy or sell
     * @param volume Order volume in lots
     * @param fill_price Actual fill price (including slippage)
     * @param info Symbol information
     * @return Commission in account currency (fixed-point)
     */
    virtual int64_t calculate(ENUM_POSITION_TYPE side, double volume, int64_t fill_price,
                             const SymbolInfo& info) const = 0;
};

/**
 * @brief No commission (zero cost)
 *
 * Useful for comparing strategies without transaction costs.
 */
class ZeroCommission final : public ICommissionModel {
public:
    ZeroCommission() noexcept = default;

    int64_t calculate(ENUM_POSITION_TYPE /*side*/, double /*volume*/, int64_t /*fill_price*/,
                     const SymbolInfo& /*info*/) const override {
        return 0;
    }
};

/**
 * @brief Fixed commission per lot
 *
 * Charges a fixed amount per lot traded.
 * Example: $7 per lot on forex.
 */
class FixedPerLot final : public ICommissionModel {
private:
    int64_t commission_per_lot_;  // Fixed-point commission per lot

public:
    /**
     * @brief Construct with commission per lot
     * @param commission_per_lot Commission in account currency per lot (fixed-point)
     */
    explicit FixedPerLot(int64_t commission_per_lot) noexcept
        : commission_per_lot_(commission_per_lot) {}

    /**
     * @brief Convenience constructor from double
     * @param commission_per_lot_double Commission per lot as double
     */
    static FixedPerLot from_double(double commission_per_lot_double) {
        return FixedPerLot(static_cast<int64_t>(commission_per_lot_double * 1'000'000));
    }

    int64_t calculate(ENUM_POSITION_TYPE /*side*/, double volume, int64_t /*fill_price*/,
                     const SymbolInfo& /*info*/) const override {
        return static_cast<int64_t>(volume * commission_per_lot_);
    }
};

/**
 * @brief Fixed commission per trade
 *
 * Charges a fixed amount per trade regardless of volume.
 * Example: $10 flat fee per trade.
 */
class FixedPerTrade final : public ICommissionModel {
private:
    int64_t commission_per_trade_;  // Fixed-point commission per trade

public:
    /**
     * @brief Construct with commission per trade
     * @param commission_per_trade Commission in account currency per trade (fixed-point)
     */
    explicit FixedPerTrade(int64_t commission_per_trade) noexcept
        : commission_per_trade_(commission_per_trade) {}

    /**
     * @brief Convenience constructor from double
     * @param commission_per_trade_double Commission per trade as double
     */
    static FixedPerTrade from_double(double commission_per_trade_double) {
        return FixedPerTrade(static_cast<int64_t>(commission_per_trade_double * 1'000'000));
    }

    int64_t calculate(ENUM_POSITION_TYPE /*side*/, double /*volume*/, int64_t /*fill_price*/,
                     const SymbolInfo& /*info*/) const override {
        return commission_per_trade_;
    }
};

/**
 * @brief Commission as spread markup
 *
 * Broker widens the spread as their commission.
 * Example: Add 0.5 pips to both sides of the spread.
 */
class SpreadMarkup final : public ICommissionModel {
private:
    int32_t markup_points_;  // Spread markup in points

public:
    /**
     * @brief Construct with spread markup
     * @param markup_points Markup in points added to spread
     */
    explicit SpreadMarkup(int32_t markup_points) noexcept
        : markup_points_(markup_points) {}

    int64_t calculate(ENUM_POSITION_TYPE /*side*/, double volume, int64_t /*fill_price*/,
                     const SymbolInfo& info) const override {
        // Markup applied to each lot (convert points to fixed-point)
        int64_t markup_fp = static_cast<int64_t>(markup_points_ * info.Point() * 1'000'000.0);
        // notional_units * markup_in_fp = account_currency_in_fp
        int64_t commission = static_cast<int64_t>(volume * info.ContractSize()) * markup_fp;
        return commission;
    }
};

/**
 * @brief Commission as percentage of trade value
 *
 * Charges a percentage of the total trade notional value.
 * Example: 0.1% commission (10 basis points).
 */
class PercentageOfValue final : public ICommissionModel {
private:
    double percentage_;  // Commission as fraction (0.001 = 0.1%)

public:
    /**
     * @brief Construct with commission percentage
     * @param percentage Commission as fraction (e.g., 0.001 for 0.1%)
     */
    explicit PercentageOfValue(double percentage) noexcept
        : percentage_(percentage) {}

    int64_t calculate(ENUM_POSITION_TYPE /*side*/, double volume, int64_t fill_price,
                     const SymbolInfo& info) const override {
        // Trade value = volume * contract_size * price
        int64_t trade_value = static_cast<int64_t>(volume * info.ContractSize()) * fill_price;
        trade_value /= 1'000'000;  // Fixed-point adjustment

        // Apply percentage
        return static_cast<int64_t>(trade_value * percentage_);
    }
};

/**
 * @brief Tiered commission based on volume
 *
 * Lower commission rate for higher volumes.
 * Example: $7/lot for <10 lots, $5/lot for 10-50 lots, $3/lot for >50 lots.
 */
class TieredCommission final : public ICommissionModel {
private:
    struct Tier {
        double volume_threshold;
        int64_t commission_per_lot;
    };
    std::vector<Tier> tiers_;

public:
    /**
     * @brief Construct with tier thresholds and rates
     * @param tiers Vector of {volume_threshold, commission_per_lot} pairs (sorted ascending)
     */
    explicit TieredCommission(std::vector<std::pair<double, double>> tiers)
        : tiers_() {
        tiers_.reserve(tiers.size());
        for (const auto& [threshold, commission] : tiers) {
            tiers_.push_back({threshold, static_cast<int64_t>(commission * 1'000'000)});
        }
    }

    int64_t calculate(ENUM_POSITION_TYPE /*side*/, double volume, int64_t /*fill_price*/,
                     const SymbolInfo& /*info*/) const override {
        // Find applicable tier
        int64_t commission_per_lot = tiers_.front().commission_per_lot;
        for (const auto& tier : tiers_) {
            if (volume >= tier.volume_threshold) {
                commission_per_lot = tier.commission_per_lot;
            } else {
                break;
            }
        }

        return static_cast<int64_t>(volume * commission_per_lot);
    }
};

} // namespace hqt

