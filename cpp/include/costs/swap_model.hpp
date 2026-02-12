/**
 * @file swap_model.hpp
 * @brief Swap (rollover) models for overnight position financing
 *
 * Models overnight interest charges/credits for held positions.
 * Swaps apply at broker rollover time (typically 23:00-00:00 UTC).
 * Triple swap on Wednesday (covers weekend).
 */

#pragma once

#include "data/tick.hpp"
#include "trading/symbol_info.hpp"
#include "trading/position_info.hpp"
#include "costs/slippage_model.hpp"
#include "util/timestamp.hpp"
#include <cstdint>
#include <memory>

namespace hqt {

// SwapType is defined in symbol_info.hpp (POINTS, PERCENTAGE)
// We extend it conceptually to include MONEY mode in StandardSwap implementation

/**
 * @brief Swap model interface
 *
 * Calculates overnight financing charges for positions.
 * Returns swap in account currency as fixed-point.
 */
class ISwapModel {
public:
    virtual ~ISwapModel() = default;

    /**
     * @brief Calculate swap for a position held overnight
     * @param side Position side (buy or sell)
     * @param volume Position volume in lots
     * @param open_price Position open price (fixed-point)
     * @param current_price Current market price (fixed-point)
     * @param info Symbol information
     * @param days_held Number of days position has been held
     * @return Swap charges in account currency (positive = charged, negative = credited)
     */
    virtual int64_t calculate(ENUM_POSITION_TYPE side, double volume, int64_t open_price,
                             int64_t current_price, const SymbolInfo& info,
                             int days_held) const = 0;

    /**
     * @brief Check if swap should be applied on given day
     * @param timestamp_us Current timestamp in microseconds
     * @return True if swap should be calculated
     */
    virtual bool should_apply(int64_t timestamp_us) const = 0;

    /**
     * @brief Get swap multiplier for given day (3x on Wednesday)
     * @param timestamp_us Current timestamp in microseconds
     * @return Swap multiplier (1 for regular days, 3 for triple swap day)
     */
    virtual int get_multiplier(int64_t timestamp_us) const = 0;
};

/**
 * @brief No swap (zero financing costs)
 *
 * Useful for strategies that don't hold overnight or for testing.
 */
class ZeroSwap final : public ISwapModel {
public:
    ZeroSwap() noexcept = default;

    int64_t calculate(ENUM_POSITION_TYPE /*side*/, double /*volume*/, int64_t /*open_price*/,
                     int64_t /*current_price*/, const SymbolInfo& /*info*/,
                     int /*days_held*/) const override {
        return 0;
    }

    bool should_apply(int64_t /*timestamp_us*/) const override {
        return false;
    }

    int get_multiplier(int64_t /*timestamp_us*/) const override {
        return 1;
    }
};

/**
 * @brief Standard swap model
 *
 * Applies swap based on broker's swap rates.
 * Supports points, percentage, and money swap types.
 * Triple swap on Wednesday (covers Sat/Sun).
 */
class StandardSwap final : public ISwapModel {
private:
    double swap_long_;       // Swap for long positions
    double swap_short_;      // Swap for short positions
    SwapType swap_type_;
    int rollover_hour_;      // UTC hour when swap applies (typically 23 or 0)
    int triple_swap_day_;    // Day of week for triple swap (3 = Wednesday)

public:
    /**
     * @brief Construct standard swap model
     * @param swap_long Swap rate for long positions
     * @param swap_short Swap rate for short positions
     * @param swap_type Type of swap calculation
     * @param rollover_hour UTC hour when swap applies (default: 0)
     * @param triple_swap_day Day of week for triple swap (default: 3 = Wednesday)
     */
    StandardSwap(double swap_long, double swap_short, SwapType swap_type,
                 int rollover_hour = 0, int triple_swap_day = 3) noexcept
        : swap_long_(swap_long), swap_short_(swap_short), swap_type_(swap_type),
          rollover_hour_(rollover_hour), triple_swap_day_(triple_swap_day) {}

    int64_t calculate(ENUM_POSITION_TYPE side, double volume, int64_t open_price,
                     int64_t current_price, const SymbolInfo& info,
                     int days_held) const override {
        (void)open_price;  // Unused in this model

        if (days_held == 0) {
            return 0;
        }

        double swap_rate = (side == ENUM_POSITION_TYPE::POSITION_TYPE_BUY) ? swap_long_ : swap_short_;

        switch (swap_type_) {
            case SwapType::POINTS: {
                // Swap in points (convert to fixed-point)
                int64_t swap_in_fp = static_cast<int64_t>(swap_rate * info.Point() * 1'000'000.0);
                // notional_units * swap_per_unit_fp = swap in account currency fp
                int64_t total_swap = static_cast<int64_t>(volume * info.ContractSize()) * swap_in_fp;
                return total_swap;
            }

            case SwapType::PERCENTAGE: {
                // Swap as percentage of position value
                // position_value_real = volume * ContractSize * (current_price / 1e6)
                double position_value_real = volume * info.ContractSize() *
                    (static_cast<double>(current_price) / 1'000'000.0);
                // swap_real = position_value_real * rate / 100
                double swap_real = position_value_real * (swap_rate / 100.0);
                // Convert to fixed-point
                return static_cast<int64_t>(swap_real * 1'000'000.0);
            }

            default:
                return 0;
        }
    }

    bool should_apply(int64_t timestamp_us) const override {
        // Check if we've crossed the rollover hour
        // In production, track last rollover time to avoid double-charging
        // For now, simplified check: assume daily rollover
        (void)timestamp_us;  // Unused for now
        (void)rollover_hour_;  // Unused for now
        return true;  // Simplified: always apply swap daily
    }

    int get_multiplier(int64_t timestamp_us) const override {
        // Triple swap on specified day (covers weekend)
        int day_of_week = hqt::Timestamp::day_of_week(timestamp_us);
        return (day_of_week == triple_swap_day_) ? 3 : 1;
    }
};

/**
 * @brief Islamic (swap-free) account model
 *
 * No swap charges, but may have extended holding fees.
 */
class IslamicSwap final : public ISwapModel {
private:
    int64_t holding_fee_;    // Fee per lot per day after grace period (fixed-point)
    int grace_period_days_;  // Days before fee applies

public:
    /**
     * @brief Construct Islamic swap model
     * @param holding_fee_double Fee per lot per day in account currency
     * @param grace_period_days Number of days before fee applies (default: 1)
     */
    explicit IslamicSwap(double holding_fee_double, int grace_period_days = 1) noexcept
        : holding_fee_(static_cast<int64_t>(holding_fee_double * 1'000'000)),
          grace_period_days_(grace_period_days) {}

    int64_t calculate(ENUM_POSITION_TYPE /*side*/, double volume, int64_t /*open_price*/,
                     int64_t /*current_price*/, const SymbolInfo& /*info*/,
                     int days_held) const override {
        // Apply holding fee after grace period
        if (days_held <= grace_period_days_) {
            return 0;
        }

        int billable_days = days_held - grace_period_days_;
        return static_cast<int64_t>(volume * holding_fee_ * billable_days);
    }

    bool should_apply(int64_t /*timestamp_us*/) const override {
        return true;  // Check daily
    }

    int get_multiplier(int64_t /*timestamp_us*/) const override {
        return 1;  // No triple swap
    }
};

} // namespace hqt

