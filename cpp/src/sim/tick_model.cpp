#include "sim/tick_model.hpp"

#include <algorithm>

namespace hqt::sim {

std::vector<ModelTick> TickModel::generate_m1_ohlc(
    const std::vector<TickModelBar>& bars,
    double point,
    double spread_default_points) {
    std::vector<ModelTick> out;
    out.reserve(bars.size() * 4);

    for (const auto& bar : bars) {
        const double spread_points = (bar.spread_points >= 0.0) ? bar.spread_points : spread_default_points;
        const bool bullish = bar.close >= bar.open;

        const double p0 = bar.open;
        const double p1 = bullish ? bar.low : bar.high;
        const double p2 = bullish ? bar.high : bar.low;
        const double p3 = bar.close;
        const double prices[4]{p0, p1, p2, p3};

        for (int i = 0; i < 4; ++i) {
            const double bid = prices[i];
            out.push_back(ModelTick{
                bar.time_msc + i,
                bid,
                bid + (spread_points * point),
                bid,
            });
        }
    }

    return out;
}

std::vector<ModelTick> TickModel::generate_synthetic_ticks(
    const std::vector<TickModelBar>& bars,
    double point,
    double spread_default_points,
    int support_points) {
    std::vector<ModelTick> out;
    const int clamped_support = std::max(0, support_points);

    for (const auto& bar : bars) {
        const double spread_points = (bar.spread_points >= 0.0) ? bar.spread_points : spread_default_points;
        const bool bullish = bar.close >= bar.open;

        const double p0 = bar.open;
        const double p1 = bullish ? bar.low : bar.high;
        const double p2 = bullish ? bar.high : bar.low;
        const double p3 = bar.close;

        const std::vector<double> s01 = support_point_split(p0, p1, clamped_support);
        const std::vector<double> s12 = support_point_split(p1, p2, clamped_support);
        const std::vector<double> s23 = support_point_split(p2, p3, clamped_support);

        int64_t offset = 0;
        const auto append_prices = [&](const std::vector<double>& prices, bool skip_first) {
            const std::size_t begin = skip_first ? 1U : 0U;
            for (std::size_t i = begin; i < prices.size(); ++i) {
                const double bid = prices[i];
                out.push_back(ModelTick{
                    bar.time_msc + offset,
                    bid,
                    bid + (spread_points * point),
                    bid,
                });
                ++offset;
            }
        };

        append_prices(s01, false);
        append_prices(s12, true);
        append_prices(s23, true);
    }

    return out;
}

std::vector<ModelTick> TickModel::passthrough_real_ticks(const std::vector<ModelTick>& ticks) {
    return ticks;
}

std::vector<double> TickModel::support_point_split(
    double start,
    double end,
    int support_points) {
    std::vector<double> out;
    const int points = std::max(0, support_points);
    out.reserve(static_cast<std::size_t>(points + 2));
    out.push_back(start);

    const double step = (end - start) / static_cast<double>(points + 1);
    for (int i = 1; i <= points; ++i) {
        out.push_back(start + (step * static_cast<double>(i)));
    }
    out.push_back(end);
    return out;
}

}  // namespace hqt::sim

