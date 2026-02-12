#include "sim/calculators.hpp"

namespace hqt::sim {

double calc_margin(
    int trade_calc_mode,
    double volume,
    double price,
    double contract_size,
    double leverage,
    double tick_size,
    double tick_value,
    double margin_initial) {
    const double lv = leverage > 0.0 ? leverage : 1.0;

    switch (trade_calc_mode) {
        case 0:  // FOREX
            return (volume * contract_size) / lv;
        case 1:  // FOREX_NO_LEVERAGE
            return volume * contract_size;
        case 2:  // CFD
            return volume * contract_size * price;
        case 3:  // CFDLEVERAGE
            return (volume * contract_size * price) / lv;
        case 4:  // CFDINDEX
            if (tick_size > 0.0) {
                return volume * contract_size * price * tick_value / tick_size;
            }
            break;
        case 5:  // EXCH_STOCKS
        case 6:  // EXCH_STOCKS_MOEX
            return volume * contract_size * price;
        case 7:  // FUTURES
        case 8:  // EXCH_FUTURES
            return volume * margin_initial;
        default:
            break;
    }

    return (volume * contract_size * price) / lv;
}

double calc_profit(
    int action,
    double volume,
    double price_open,
    double price_close,
    double tick_size,
    double tick_value,
    double contract_size) {
    const double direction = (action == 0) ? 1.0 : -1.0;
    const double price_delta = (price_close - price_open) * direction;

    if (tick_size > 0.0 && tick_value > 0.0) {
        return (price_delta / tick_size) * tick_value * volume;
    }
    if (contract_size > 0.0) {
        return price_delta * contract_size * volume;
    }
    return 0.0;
}

}  // namespace hqt::sim

