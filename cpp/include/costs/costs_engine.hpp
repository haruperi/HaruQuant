/**
FILE: include\costs\costs_engine.hpp

PURPOSE:
Defines costs_engine.hpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in costs_engine.hpp.
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
#include "trading/order_info.hpp"
#include "costs/slippage_model.hpp"
#include "costs/commission_model.hpp"
#include "costs/swap_model.hpp"
#include "costs/spread_model.hpp"
#include <memory>
#include <vector>
#include <random>
#include <stdexcept>

namespace hqt {

/**
 * @brief Order execution result
 */
struct ExecutionResult {
    bool executed;              ///< Whether order was executed
    int64_t fill_price;         ///< Actual fill price (fixed-point)
    int64_t slippage;           ///< Slippage applied (fixed-point)
    int64_t commission;         ///< Commission charged (account currency, fixed-point)
    int64_t spread_cost;        ///< Cost due to spread (fixed-point)

    ExecutionResult() noexcept
        : executed(false), fill_price(0), slippage(0), commission(0), spread_cost(0) {}
};

/**
 * @brief Pending order representation
 */
struct PendingOrder {
    uint64_t ticket;            ///< Unique order ticket
    uint32_t symbol_id;         ///< Symbol identifier
    ENUM_ORDER_TYPE type;       ///< Order type (BUY_LIMIT, SELL_STOP, etc.)
    double volume;              ///< Order volume in lots
    int64_t price;              ///< Order trigger price (fixed-point)
    int64_t sl;                 ///< Stop loss (0 if none)
    int64_t tp;                 ///< Take profit (0 if none)
    int64_t timestamp_us;       ///< Order placement timestamp
};

/**
 * @brief Open position representation
 */
struct Position {
    uint64_t ticket;            ///< Position ticket
    uint32_t symbol_id;         ///< Symbol identifier
    ENUM_POSITION_TYPE type;    ///< Long (BUY) or short (SELL)
    double volume;              ///< Position volume in lots
    int64_t open_price;         ///< Entry price (fixed-point)
    int64_t sl;                 ///< Stop loss (0 if none)
    int64_t tp;                 ///< Take profit (0 if none)
    int64_t open_time_us;       ///< Position open timestamp
    int64_t commission;         ///< Commission paid (fixed-point)
    int64_t swap;               ///< Accumulated swap (fixed-point)
};

/**
 * @brief Execution costs engine with cost models
 *
 * Evaluates pending orders and open positions against new market data.
 * Calculates realistic fills using slippage, commission, and spread models.
 *
 * Example:
 * @code
 * CostsEngine engine(
 *     std::make_unique<FixedSlippage>(2),
 *     std::make_unique<FixedPerLot>(7.0),
 *     std::make_unique<StandardSwap>(-0.5, 0.3, SwapType::POINTS),
 *     std::make_unique<FixedSpread>(15)
 * );
 *
 * // Check if order triggers and execute
 * auto result = engine.evaluate_order(order, tick, symbol_info);
 * if (result.executed) {
 *     // Order filled at result.fill_price
 * }
 * @endcode
 */
class CostsEngine {
private:
    std::unique_ptr<ISlippageModel> slippage_model_;
    std::unique_ptr<ICommissionModel> commission_model_;
    std::unique_ptr<ISwapModel> swap_model_;
    std::unique_ptr<ISpreadModel> spread_model_;
    mutable std::mt19937_64 rng_;

    // Last known prices for gap detection
    struct LastPrice {
        int64_t bid;
        int64_t ask;
        int64_t timestamp_us;
    };
    mutable std::unordered_map<uint32_t, LastPrice> last_prices_;

public:
    /**
     * @brief Construct costs engine with execution models
     * @param slippage Slippage model
     * @param commission Commission model
     * @param swap Swap model
     * @param spread Spread model
     * @param seed Random seed for deterministic execution (default: 0)
     */
    CostsEngine(std::unique_ptr<ISlippageModel> slippage,
                std::unique_ptr<ICommissionModel> commission,
                std::unique_ptr<ISwapModel> swap,
                std::unique_ptr<ISpreadModel> spread,
                uint64_t seed = 0)
        : slippage_model_(std::move(slippage)),
          commission_model_(std::move(commission)),
          swap_model_(std::move(swap)),
          spread_model_(std::move(spread)),
          rng_(seed),
          last_prices_() {
        if (!slippage_model_ || !commission_model_ || !swap_model_ || !spread_model_) {
            throw std::invalid_argument("All execution models must be provided");
        }
    }

    /**
     * @brief Update market prices (for gap detection)
     * @param symbol_id Symbol identifier
     * @param tick Current tick
     */
    void update_market(uint32_t symbol_id, const Tick& tick) {
        last_prices_[symbol_id] = {tick.bid, tick.ask, tick.timestamp_us};
    }

    /**
     * @brief Check if order should trigger and execute
     * @param order Pending order
     * @param tick Current market tick
     * @param info Symbol information
     * @return Execution result
     */
    ExecutionResult evaluate_order(const PendingOrder& order, const Tick& tick,
                                   const SymbolInfo& info) {
        ExecutionResult result;

        // Check if order triggers
        bool triggers = false;
        int64_t trigger_price = 0;
        bool is_buy = (order.type == ENUM_ORDER_TYPE::ORDER_TYPE_BUY ||
                      order.type == ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT ||
                      order.type == ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP ||
                      order.type == ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP_LIMIT);

        switch (order.type) {
            case ENUM_ORDER_TYPE::ORDER_TYPE_BUY:
            case ENUM_ORDER_TYPE::ORDER_TYPE_SELL:
                // Market orders always execute immediately
                triggers = true;
                trigger_price = is_buy ? tick.ask : tick.bid;
                break;

            case ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT:
                // Limit buy triggers when ask <= limit price
                if (tick.ask <= order.price) {
                    triggers = true;
                    trigger_price = order.price;  // Fill at limit price (or better)
                }
                break;

            case ENUM_ORDER_TYPE::ORDER_TYPE_SELL_LIMIT:
                // Limit sell triggers when bid >= limit price
                if (tick.bid >= order.price) {
                    triggers = true;
                    trigger_price = order.price;
                }
                break;

            case ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP:
                // Stop buy triggers when ask >= stop price
                if (tick.ask >= order.price) {
                    triggers = true;
                    trigger_price = tick.ask;  // Fill at market price (gap scenario)
                }
                break;

            case ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP:
                // Stop sell triggers when bid <= stop price
                if (tick.bid <= order.price) {
                    triggers = true;
                    trigger_price = tick.bid;
                }
                break;

            case ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP_LIMIT:
                // Stop-limit buy triggers like stop but becomes limit order
                if (tick.ask >= order.price) {
                    triggers = true;
                    trigger_price = std::min(tick.ask, order.price);
                }
                break;

            case ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP_LIMIT:
                // Stop-limit sell triggers like stop but becomes limit order
                if (tick.bid <= order.price) {
                    triggers = true;
                    trigger_price = std::max(tick.bid, order.price);
                }
                break;
        }

        if (!triggers) {
            return result;  // Order did not trigger
        }

        // Convert to position type for slippage/commission calculation
        ENUM_POSITION_TYPE pos_type = is_buy ? ENUM_POSITION_TYPE::POSITION_TYPE_BUY
                                              : ENUM_POSITION_TYPE::POSITION_TYPE_SELL;

        // Calculate execution price with slippage and spread
        result.executed = true;
        result.slippage = slippage_model_->calculate(pos_type, order.volume, tick, info, rng_);
        result.spread_cost = spread_model_->calculate(tick, info, tick.timestamp_us, rng_);

        // Apply slippage to trigger price
        if (is_buy) {
            result.fill_price = trigger_price + result.slippage;
        } else {
            result.fill_price = trigger_price - result.slippage;
        }

        // Calculate commission
        result.commission = commission_model_->calculate(pos_type, order.volume,
                                                        result.fill_price, info);

        return result;
    }

    /**
     * @brief Check if position stop loss or take profit triggers
     * @param position Open position
     * @param tick Current market tick
     * @param info Symbol information
     * @return Execution result (executed=true if SL/TP hit)
     */
    ExecutionResult evaluate_position(const Position& position, const Tick& tick,
                                     const SymbolInfo& info) {
        ExecutionResult result;

        bool triggers = false;
        int64_t trigger_price = 0;
        ENUM_POSITION_TYPE close_type = (position.type == ENUM_POSITION_TYPE::POSITION_TYPE_BUY)
            ? ENUM_POSITION_TYPE::POSITION_TYPE_SELL
            : ENUM_POSITION_TYPE::POSITION_TYPE_BUY;

        if (position.type == ENUM_POSITION_TYPE::POSITION_TYPE_BUY) {
            // Long position: check SL (below) and TP (above)
            if (position.sl > 0 && tick.bid <= position.sl) {
                // Stop loss hit
                triggers = true;
                trigger_price = std::min(tick.bid, position.sl);  // Gap scenario
            } else if (position.tp > 0 && tick.bid >= position.tp) {
                // Take profit hit
                triggers = true;
                trigger_price = std::max(tick.bid, position.tp);  // Gap scenario
            }
        } else {
            // Short position: check SL (above) and TP (below)
            if (position.sl > 0 && tick.ask >= position.sl) {
                // Stop loss hit
                triggers = true;
                trigger_price = std::max(tick.ask, position.sl);  // Gap scenario
            } else if (position.tp > 0 && tick.ask <= position.tp) {
                // Take profit hit
                triggers = true;
                trigger_price = std::min(tick.ask, position.tp);  // Gap scenario
            }
        }

        if (!triggers) {
            return result;  // Position exits not triggered
        }

        // Calculate close execution
        result.executed = true;
        result.slippage = slippage_model_->calculate(close_type, position.volume, tick, info, rng_);
        result.spread_cost = spread_model_->calculate(tick, info, tick.timestamp_us, rng_);

        // Apply slippage to trigger price
        if (close_type == ENUM_POSITION_TYPE::POSITION_TYPE_BUY) {
            result.fill_price = trigger_price + result.slippage;
        } else {
            result.fill_price = trigger_price - result.slippage;
        }

        // Calculate commission on close
        result.commission = commission_model_->calculate(close_type, position.volume,
                                                        result.fill_price, info);

        return result;
    }

    /**
     * @brief Execute market order immediately
     * @param type Position type (BUY or SELL)
     * @param volume Order volume in lots
     * @param tick Current market tick
     * @param info Symbol information
     * @return Execution result
     */
    ExecutionResult execute_market_order(ENUM_POSITION_TYPE type, double volume, const Tick& tick,
                                        const SymbolInfo& info) {
        PendingOrder order{};
        order.type = (type == ENUM_POSITION_TYPE::POSITION_TYPE_BUY)
            ? ENUM_ORDER_TYPE::ORDER_TYPE_BUY
            : ENUM_ORDER_TYPE::ORDER_TYPE_SELL;
        order.volume = volume;
        order.timestamp_us = tick.timestamp_us;

        return evaluate_order(order, tick, info);
    }

    /**
     * @brief Calculate daily swap charges for position
     * @param position Open position
     * @param current_price Current market price
     * @param info Symbol information
     * @param timestamp_us Current timestamp
     * @return Swap charges in account currency (fixed-point)
     */
    int64_t calculate_swap(const Position& position, int64_t current_price,
                          const SymbolInfo& info, int64_t timestamp_us) const {
        if (!swap_model_->should_apply(timestamp_us)) {
            return 0;
        }

        // Calculate days held
        int64_t duration_us = timestamp_us - position.open_time_us;
        int days_held = static_cast<int>(duration_us / (24LL * 3600LL * 1'000'000LL));

        if (days_held == 0) {
            return 0;
        }

        // Apply swap multiplier (3x on Wednesday)
        int multiplier = swap_model_->get_multiplier(timestamp_us);

        int64_t swap = swap_model_->calculate(position.type, position.volume,
                                             position.open_price, current_price,
                                             info, days_held);

        return swap * multiplier;
    }

    /**
     * @brief Reset RNG seed for deterministic execution
     * @param seed New random seed
     */
    void set_seed(uint64_t seed) {
        rng_.seed(seed);
    }
};

} // namespace hqt

