#include "sim/account_monitor.hpp"

#include <optional>

namespace hqt::sim {

PositionTotals AccountMonitor::monitor_positions(
    const SimulatorClient& client,
    const std::string& symbol,
    double bid,
    double ask) const {
    PositionTotals totals;
    if (bid <= 0.0 || ask <= 0.0) {
        return totals;
    }

    const auto positions = client.positions_get(std::nullopt, symbol);
    for (const auto& pos : positions) {
        const bool is_buy = (pos.type == 0U);
        const int action = is_buy ? 0 : 1;
        const double close_price = is_buy ? bid : ask;

        totals.profit += client.order_calc_profit(
            action,
            symbol,
            pos.volume,
            pos.price_open,
            close_price);
        totals.margin += client.order_calc_margin(
            action,
            symbol,
            pos.volume,
            pos.price_open);
        totals.commission += 0.0;
        totals.fee += 0.0;
        totals.swap += pos.swap;
    }

    return totals;
}

AccountInfoData AccountMonitor::monitor_account(
    const AccountInfoData& base,
    const PositionTotals& totals) const {
    AccountInfoData updated = base;
    updated.profit = totals.profit;
    updated.margin = totals.margin;
    updated.commission_blocked = totals.commission + totals.fee;
    updated.equity = updated.balance + updated.credit + totals.profit +
        totals.commission + totals.fee + totals.swap;
    updated.margin_free = updated.equity - totals.margin;
    updated.margin_level = (updated.margin > 0.0)
        ? ((updated.equity / updated.margin) * 100.0)
        : 0.0;
    return updated;
}

}  // namespace hqt::sim

