/**
 * @file tick_model.hpp
 * @brief Deterministic tick modelling helpers for simulation.
 */

#pragma once

#include <cstdint>
#include <vector>

namespace hqt::sim {

struct TickModelBar {
    int64_t time_msc{0};
    double open{0.0};
    double high{0.0};
    double low{0.0};
    double close{0.0};
    double spread_points{-1.0};
};

struct ModelTick {
    int64_t time_msc{0};
    double bid{0.0};
    double ask{0.0};
    double last{0.0};

    friend bool operator==(const ModelTick& lhs, const ModelTick& rhs) {
        return lhs.time_msc == rhs.time_msc &&
            lhs.bid == rhs.bid &&
            lhs.ask == rhs.ask &&
            lhs.last == rhs.last;
    }
};

class TickModel {
public:
    [[nodiscard]] static std::vector<ModelTick> generate_m1_ohlc(
        const std::vector<TickModelBar>& bars,
        double point,
        double spread_default_points);

    [[nodiscard]] static std::vector<ModelTick> generate_synthetic_ticks(
        const std::vector<TickModelBar>& bars,
        double point,
        double spread_default_points,
        int support_points = 2);

    [[nodiscard]] static std::vector<ModelTick> passthrough_real_ticks(
        const std::vector<ModelTick>& ticks);

private:
    [[nodiscard]] static std::vector<double> support_point_split(
        double start,
        double end,
        int support_points);
};

}  // namespace hqt::sim

