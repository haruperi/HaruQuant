/**
 * @file models.cpp
 * @brief Unified engine models compilation unit.
 */

#include "engine/engine.hpp"

#include <sstream>

namespace hqt::sim {

namespace {

template <typename T>
std::string to_string_num(T value) {
    std::ostringstream oss;
    oss << value;
    return oss.str();
}

}  // namespace

Dict SymbolTickData::to_dict() const {
    return {
        {"time", to_string_num(time)},
        {"bid", to_string_num(bid)},
        {"ask", to_string_num(ask)},
        {"last", to_string_num(last)},
        {"volume", to_string_num(volume)},
        {"time_msc", to_string_num(time_msc)},
        {"flags", to_string_num(flags)},
        {"volume_real", to_string_num(volume_real)},
    };
}

Dict TradeRecordData::to_dict() const {
    return {
        {"ticket", to_string_num(ticket)},
        {"order", to_string_num(order)},
        {"time", to_string_num(time)},
        {"time_msc", to_string_num(time_msc)},
        {"expiration", to_string_num(expiration)},
        {"type", to_string_num(type)},
        {"type_time", to_string_num(type_time)},
        {"magic", to_string_num(magic)},
        {"identifier", to_string_num(identifier)},
        {"reason", to_string_num(reason)},
        {"volume", to_string_num(volume)},
        {"price_open", to_string_num(price_open)},
        {"sl", to_string_num(sl)},
        {"tp", to_string_num(tp)},
        {"price_current", to_string_num(price_current)},
        {"swap", to_string_num(swap)},
        {"profit", to_string_num(profit)},
        {"symbol", symbol},
        {"comment", comment},
    };
}

void SimulatorState::reset() noexcept {
    running = false;
    paused = false;
    current_time_us = 0;
    current_bar_index = 0;
    processed_events = 0;
}

}  // namespace hqt::sim
