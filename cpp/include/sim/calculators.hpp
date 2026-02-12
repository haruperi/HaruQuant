/**
 * @file calculators.hpp
 * @brief Margin and profit calculators for simulator parity.
 */

#pragma once

namespace hqt::sim {

/**
 * @brief Calculate required margin using MT5-like calc mode semantics.
 */
double calc_margin(
    int trade_calc_mode,
    double volume,
    double price,
    double contract_size,
    double leverage,
    double tick_size,
    double tick_value,
    double margin_initial);

/**
 * @brief Calculate profit for BUY/SELL actions.
 *
 * @param action 0 = BUY, 1 = SELL
 */
double calc_profit(
    int action,
    double volume,
    double price_open,
    double price_close,
    double tick_size,
    double tick_value,
    double contract_size);

}  // namespace hqt::sim

