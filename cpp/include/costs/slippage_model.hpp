/**
FILE: include\costs\slippage_model.hpp

PURPOSE:
Defines slippage_model.hpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in slippage_model.hpp.
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
#include "trading/position_info.hpp"
#include <random>
#include <cstdint>
#include <memory>
#include <cmath>

namespace haruquant {

/**
 * @brief Slippage model interface
 *
 * Calculates price slippage in fixed-point (1/1,000,000 units).
 * Positive slippage = worse fill (higher for buy, lower for sell).
 * Negative slippage = price improvement (rare in backtesting).
 */
class ISlippageModel {
public:
    virtual ~ISlippageModel() = default;

    /**
     * @brief Calculate slippage for an order fill
     * @param side Buy or sell
     * @param volume Order volume in lots
     * @param tick Current market tick
     * @param info Symbol information
     * @param rng Random number generator
     * @return Slippage in fixed-point (positive = worse fill)
     */
    virtual int64_t calculate(ENUM_POSITION_TYPE side, double volume, const Tick& tick,
                              const SymbolInfo& info, std::mt19937_64& rng) const = 0;
};

/**
 * @brief Zero slippage (ideal execution)
 *
 * Orders fill at exact bid/ask with no degradation.
 * Useful for comparing strategies without execution costs.
 */
class ZeroSlippage final : public ISlippageModel {
public:
    ZeroSlippage() noexcept = default;

    int64_t calculate(ENUM_POSITION_TYPE /*side*/, double /*volume*/, const Tick& /*tick*/,
                     const SymbolInfo& /*info*/, std::mt19937_64& /*rng*/) const override {
        return 0;
    }
};

/**
 * @brief Fixed slippage in points
 *
 * Constant slippage regardless of market conditions.
 * Example: 2 points slippage on EURUSD = 0.00002 price degradation.
 */
class FixedSlippage final : public ISlippageModel {
private:
    int32_t slippage_points_;

public:
    /**
     * @brief Construct with fixed slippage
     * @param slippage_points Slippage in points (e.g., 2 points = 0.2 pips)
     */
    explicit FixedSlippage(int32_t slippage_points) noexcept
        : slippage_points_(slippage_points) {}

    int64_t calculate(ENUM_POSITION_TYPE /*side*/, double /*volume*/, const Tick& /*tick*/,
                     const SymbolInfo& info, std::mt19937_64& /*rng*/) const override {
        // Convert points to fixed-point price (Point() * 1e6 = fixed-point units per point)
        return static_cast<int64_t>(slippage_points_ * info.Point() * 1'000'000.0);
    }
};

/**
 * @brief Random slippage with uniform distribution
 *
 * Slippage varies randomly between min and max points.
 * Models unpredictable execution quality.
 */
class RandomSlippage final : public ISlippageModel {
private:
    int32_t min_points_;
    int32_t max_points_;

public:
    /**
     * @brief Construct with slippage range
     * @param min_points Minimum slippage in points
     * @param max_points Maximum slippage in points
     */
    RandomSlippage(int32_t min_points, int32_t max_points) noexcept
        : min_points_(min_points), max_points_(max_points) {}

    int64_t calculate(ENUM_POSITION_TYPE /*side*/, double /*volume*/, const Tick& /*tick*/,
                     const SymbolInfo& info, std::mt19937_64& rng) const override {
        std::uniform_int_distribution<int32_t> dist(min_points_, max_points_);
        int32_t slippage_points = dist(rng);
        return static_cast<int64_t>(slippage_points * info.Point() * 1'000'000.0);
    }
};

/**
 * @brief Volume-dependent slippage
 *
 * Larger orders experience more slippage due to market impact.
 * Slippage = base + (volume * multiplier).
 */
class VolumeSlippage final : public ISlippageModel {
private:
    int32_t base_points_;
    double volume_multiplier_;  // Points per lot

public:
    /**
     * @brief Construct with base slippage and volume multiplier
     * @param base_points Base slippage in points
     * @param volume_multiplier Additional points per lot
     */
    VolumeSlippage(int32_t base_points, double volume_multiplier) noexcept
        : base_points_(base_points), volume_multiplier_(volume_multiplier) {}

    int64_t calculate(ENUM_POSITION_TYPE /*side*/, double volume, const Tick& /*tick*/,
                     const SymbolInfo& info, std::mt19937_64& /*rng*/) const override {
        double total_points = base_points_ + (volume * volume_multiplier_);
        return static_cast<int64_t>(std::round(total_points) * info.Point() * 1'000'000.0);
    }
};

/**
 * @brief Latency-based slippage profile
 *
 * Models execution delay causing price movement.
 * Slippage increases with spread and volatility.
 */
class LatencyProfileSlippage final : public ISlippageModel {
private:
    double latency_ms_;          // Execution latency in milliseconds
    double spread_multiplier_;   // Multiplier applied to spread

public:
    /**
     * @brief Construct with latency profile
     * @param latency_ms Execution latency in milliseconds (typical: 10-100ms)
     * @param spread_multiplier Slippage as fraction of spread (typical: 0.3-0.5)
     */
    LatencyProfileSlippage(double latency_ms, double spread_multiplier) noexcept
        : latency_ms_(latency_ms), spread_multiplier_(spread_multiplier) {}

    int64_t calculate(ENUM_POSITION_TYPE /*side*/, double /*volume*/, const Tick& tick,
                     const SymbolInfo& info, std::mt19937_64& rng) const override {
        // Base slippage from spread (already in fixed-point)
        int64_t spread = tick.ask - tick.bid;
        double base_slippage = spread * spread_multiplier_;

        // Add random component based on latency (simulate price movement during delay)
        std::normal_distribution<double> dist(0.0, latency_ms_ / 100.0);
        double latency_component = std::abs(dist(rng)) * info.Point() * 1'000'000.0;

        return static_cast<int64_t>(base_slippage + latency_component);
    }
};

} // namespace haruquant

