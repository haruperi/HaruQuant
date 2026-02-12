/**
 * @file sim_data.hpp
 * @brief MT5-like simulation data transfer objects.
 *
 * PR-002 scope: core data containers mirroring Python simulator data objects.
 */

#pragma once

#include <cstdint>
#include <string>
#include <unordered_map>

namespace hqt::sim {

using Dict = std::unordered_map<std::string, std::string>;

/**
 * @brief Simulated account info container.
 */
struct AccountInfoData {
    int64_t login{12345678};
    int32_t leverage{100};
    int32_t margin_mode{0};
    bool trade_allowed{true};
    bool trade_expert{true};

    double balance{10000.0};
    double credit{0.0};
    double profit{0.0};
    double equity{0.0};
    double margin{0.0};
    double margin_free{10000.0};
    double margin_level{0.0};
    double commission_blocked{0.0};

    std::string name{"Simulated Trader"};
    std::string server{"Sim-Server"};
    std::string currency{"USD"};
    std::string company{"Simulated Company"};

    [[nodiscard]] Dict to_dict() const;
};

/**
 * @brief Simulated symbol tick container.
 */
struct SymbolTickData {
    int64_t time{0};
    double bid{0.0};
    double ask{0.0};
    double last{0.0};
    int64_t volume{0};
    int64_t time_msc{0};
    int32_t flags{0};
    double volume_real{0.0};

    [[nodiscard]] Dict to_dict() const;
};

/**
 * @brief Simulated symbol metadata container.
 */
struct SymbolInfoData {
    std::string symbol{"EURUSD"};

    int32_t digits{5};
    int32_t spread{10};
    bool spread_float{true};
    double point{0.00001};

    int32_t trade_calc_mode{0};
    int32_t trade_mode{4};
    int32_t trade_stops_level{0};
    int32_t trade_freeze_level{0};
    int32_t trade_exemode{1};

    double volume_min{0.01};
    double volume_max{100.0};
    double volume_step{0.01};
    double volume_limit{0.0};

    double trade_tick_value{1.0};
    double trade_tick_value_profit{1.0};
    double trade_tick_value_loss{1.0};
    double trade_tick_size{0.00001};
    double trade_contract_size{100000.0};

    int32_t swap_mode{1};
    double swap_long{-1.0};
    double swap_short{-1.0};
    int32_t swap_rollover3days{3};

    double bid{0.0};
    double ask{0.0};
    double last{0.0};

    bool select{true};
    bool visible{true};

    [[nodiscard]] Dict to_dict() const;
};

/**
 * @brief Base record container used by simulated positions/orders/deals.
 */
struct TradeRecordData {
    uint64_t ticket{0};
    uint64_t order{0};
    int64_t time{0};
    int64_t time_msc{0};
    uint64_t type{0};
    uint64_t magic{0};
    uint64_t identifier{0};
    uint64_t reason{0};
    double volume{0.0};
    double price_open{0.0};
    double sl{0.0};
    double tp{0.0};
    double price_current{0.0};
    double swap{0.0};
    double profit{0.0};
    std::string symbol{};
    std::string comment{};

    [[nodiscard]] Dict to_dict() const;
};

}  // namespace hqt::sim

