/**
 * @file spread_model.hpp
 * @brief Spread models for bid-ask spread simulation
 *
 * Models the bid-ask spread which affects execution prices.
 * Spreads widen during low liquidity periods and narrow during high liquidity.
 */

#pragma once

#include "data/tick.hpp"
#include "trading/symbol_info.hpp"
#include "util/timestamp.hpp"
#include <cstdint>
#include <memory>
#include <random>

namespace hqt {

/**
 * @brief Spread model interface
 *
 * Calculates the bid-ask spread to use for order fills.
 * Returns spread in fixed-point (1/1,000,000 units).
 */
class ISpreadModel {
public:
    virtual ~ISpreadModel() = default;

    /**
     * @brief Calculate spread for current market conditions
     * @param tick Current market tick (may contain actual spread)
     * @param info Symbol information
     * @param timestamp_us Current timestamp in microseconds
     * @param rng Random number generator
     * @return Spread in fixed-point
     */
    virtual int64_t calculate(const Tick& tick, const SymbolInfo& info,
                             int64_t timestamp_us, std::mt19937_64& rng) const = 0;
};

/**
 * @brief Fixed spread (constant)
 *
 * Uses a constant spread regardless of market conditions.
 * Simplest model for backtesting.
 */
class FixedSpread final : public ISpreadModel {
private:
    int32_t spread_points_;

public:
    /**
     * @brief Construct with fixed spread
     * @param spread_points Spread in points (e.g., 15 points = 1.5 pips on EURUSD)
     */
    explicit FixedSpread(int32_t spread_points) noexcept
        : spread_points_(spread_points) {}

    int64_t calculate(const Tick& /*tick*/, const SymbolInfo& info,
                     int64_t /*timestamp_us*/, std::mt19937_64& /*rng*/) const override {
        return static_cast<int64_t>(spread_points_ * info.Point() * 1'000'000.0);
    }
};

/**
 * @brief Historical spread (use actual tick data)
 *
 * Uses the spread from actual market data.
 * Most realistic but requires tick data with bid/ask.
 */
class HistoricalSpread final : public ISpreadModel {
private:
    int32_t min_spread_points_;  // Minimum spread floor

public:
    /**
     * @brief Construct with minimum spread constraint
     * @param min_spread_points Minimum spread in points (prevents unrealistic tights)
     */
    explicit HistoricalSpread(int32_t min_spread_points = 0) noexcept
        : min_spread_points_(min_spread_points) {}

    int64_t calculate(const Tick& tick, const SymbolInfo& info,
                     int64_t /*timestamp_us*/, std::mt19937_64& /*rng*/) const override {
        int64_t actual_spread = tick.ask - tick.bid;

        // Apply minimum spread floor (convert points to fixed-point)
        int64_t min_spread = static_cast<int64_t>(min_spread_points_ * info.Point() * 1'000'000.0);
        return std::max(actual_spread, min_spread);
    }
};

/**
 * @brief Time-of-day varying spread
 *
 * Spreads widen during low liquidity periods and narrow during high liquidity.
 * Models typical forex market sessions (London, NY, Asian).
 */
class TimeOfDaySpread final : public ISpreadModel {
private:
    int32_t base_spread_points_;
    double asian_multiplier_;    // Multiplier during Asian session (typically wider)
    double london_multiplier_;   // Multiplier during London session (typically tighter)
    double ny_multiplier_;       // Multiplier during NY session (typically tighter)
    double overlap_multiplier_;  // Multiplier during London-NY overlap (tightest)

public:
    /**
     * @brief Construct time-of-day spread model
     * @param base_spread_points Base spread in points
     * @param asian_multiplier Asian session multiplier (default: 1.5 = 50% wider)
     * @param london_multiplier London session multiplier (default: 0.8)
     * @param ny_multiplier NY session multiplier (default: 0.9)
     * @param overlap_multiplier London-NY overlap multiplier (default: 0.7 = 30% tighter)
     */
    TimeOfDaySpread(int32_t base_spread_points,
                    double asian_multiplier = 1.5,
                    double london_multiplier = 0.8,
                    double ny_multiplier = 0.9,
                    double overlap_multiplier = 0.7) noexcept
        : base_spread_points_(base_spread_points),
          asian_multiplier_(asian_multiplier),
          london_multiplier_(london_multiplier),
          ny_multiplier_(ny_multiplier),
          overlap_multiplier_(overlap_multiplier) {}

    int64_t calculate(const Tick& /*tick*/, const SymbolInfo& info,
                     int64_t timestamp_us, std::mt19937_64& /*rng*/) const override {
        // Extract hour from timestamp (simplified)
        int64_t seconds = timestamp_us / 1'000'000;
        int64_t hours_since_epoch = seconds / 3600;
        int hour_utc = static_cast<int>(hours_since_epoch % 24);

        double multiplier = 1.0;

        // Determine session and apply multiplier
        // Asian: 00:00-08:00 UTC
        // London: 08:00-16:00 UTC
        // NY: 13:00-22:00 UTC
        // Overlap: 13:00-16:00 UTC

        if (hour_utc >= 13 && hour_utc < 16) {
            // London-NY overlap (tightest)
            multiplier = overlap_multiplier_;
        } else if (hour_utc >= 8 && hour_utc < 16) {
            // London session
            multiplier = london_multiplier_;
        } else if (hour_utc >= 13 && hour_utc < 22) {
            // NY session (after overlap)
            multiplier = ny_multiplier_;
        } else {
            // Asian session (lowest liquidity)
            multiplier = asian_multiplier_;
        }

        int32_t adjusted_spread = static_cast<int32_t>(base_spread_points_ * multiplier);
        return static_cast<int64_t>(adjusted_spread * info.Point() * 1'000'000.0);
    }
};

/**
 * @brief Random spread with normal distribution
 *
 * Spreads vary randomly around a mean with specified standard deviation.
 * Models unpredictable liquidity conditions.
 */
class RandomSpread final : public ISpreadModel {
private:
    int32_t mean_spread_points_;
    int32_t stddev_points_;
    int32_t min_spread_points_;

public:
    /**
     * @brief Construct random spread model
     * @param mean_spread_points Mean spread in points
     * @param stddev_points Standard deviation in points
     * @param min_spread_points Minimum spread floor (default: 0)
     */
    RandomSpread(int32_t mean_spread_points, int32_t stddev_points,
                 int32_t min_spread_points = 0) noexcept
        : mean_spread_points_(mean_spread_points),
          stddev_points_(stddev_points),
          min_spread_points_(min_spread_points) {}

    int64_t calculate(const Tick& /*tick*/, const SymbolInfo& info,
                     int64_t /*timestamp_us*/, std::mt19937_64& rng) const override {
        std::normal_distribution<double> dist(mean_spread_points_, stddev_points_);
        int32_t spread_points = static_cast<int32_t>(std::max(
            static_cast<double>(min_spread_points_),
            std::abs(dist(rng))
        ));

        return static_cast<int64_t>(spread_points * info.Point() * 1'000'000.0);
    }
};

/**
 * @brief Volatility-adjusted spread
 *
 * Spreads widen during high volatility (captured by recent price movement).
 * Uses simple ATR-like calculation.
 */
class VolatilitySpread final : public ISpreadModel {
private:
    int32_t base_spread_points_;
    double volatility_multiplier_;
    mutable int64_t last_price_;
    mutable double running_volatility_;
    mutable int sample_count_;
    int lookback_samples_;

public:
    /**
     * @brief Construct volatility-adjusted spread model
     * @param base_spread_points Base spread in points
     * @param volatility_multiplier How much volatility affects spread (default: 0.5)
     * @param lookback_samples Number of samples for volatility calculation (default: 100)
     */
    VolatilitySpread(int32_t base_spread_points, double volatility_multiplier = 0.5,
                     int lookback_samples = 100) noexcept
        : base_spread_points_(base_spread_points),
          volatility_multiplier_(volatility_multiplier),
          last_price_(0),
          running_volatility_(0.0),
          sample_count_(0),
          lookback_samples_(lookback_samples) {}

    int64_t calculate(const Tick& tick, const SymbolInfo& info,
                     int64_t /*timestamp_us*/, std::mt19937_64& /*rng*/) const override {
        int64_t mid_price = (tick.bid + tick.ask) / 2;

        if (last_price_ != 0 && sample_count_ < lookback_samples_) {
            // Update running volatility estimate
            double price_change = std::abs(static_cast<double>(mid_price - last_price_));
            running_volatility_ = (running_volatility_ * sample_count_ + price_change) / (sample_count_ + 1);
            ++sample_count_;
        }

        last_price_ = mid_price;

        // Adjust spread based on volatility
        // volatility is in fixed-point units, convert to points by dividing by fp-per-point
        double fp_per_point = info.Point() * 1'000'000.0;
        double volatility_adjustment = running_volatility_ * volatility_multiplier_;
        int32_t adjusted_spread = base_spread_points_ + static_cast<int32_t>(volatility_adjustment / fp_per_point);

        return static_cast<int64_t>(adjusted_spread * fp_per_point);
    }
};

} // namespace hqt

