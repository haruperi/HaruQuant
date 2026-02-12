#include "sim/sim_data.hpp"

#include <sstream>

namespace hqt::sim {

namespace {

std::string to_string_bool(bool value) {
    return value ? "true" : "false";
}

template <typename T>
std::string to_string_num(T value) {
    std::ostringstream oss;
    oss << value;
    return oss.str();
}

}  // namespace

Dict AccountInfoData::to_dict() const {
    return {
        {"login", to_string_num(login)},
        {"leverage", to_string_num(leverage)},
        {"margin_mode", to_string_num(margin_mode)},
        {"trade_allowed", to_string_bool(trade_allowed)},
        {"trade_expert", to_string_bool(trade_expert)},
        {"balance", to_string_num(balance)},
        {"credit", to_string_num(credit)},
        {"profit", to_string_num(profit)},
        {"equity", to_string_num(equity)},
        {"margin", to_string_num(margin)},
        {"margin_free", to_string_num(margin_free)},
        {"margin_level", to_string_num(margin_level)},
        {"commission_blocked", to_string_num(commission_blocked)},
        {"name", name},
        {"server", server},
        {"currency", currency},
        {"company", company},
    };
}

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

Dict SymbolInfoData::to_dict() const {
    return {
        {"symbol", symbol},
        {"digits", to_string_num(digits)},
        {"spread", to_string_num(spread)},
        {"spread_float", to_string_bool(spread_float)},
        {"point", to_string_num(point)},
        {"trade_calc_mode", to_string_num(trade_calc_mode)},
        {"trade_mode", to_string_num(trade_mode)},
        {"trade_stops_level", to_string_num(trade_stops_level)},
        {"trade_freeze_level", to_string_num(trade_freeze_level)},
        {"trade_exemode", to_string_num(trade_exemode)},
        {"volume_min", to_string_num(volume_min)},
        {"volume_max", to_string_num(volume_max)},
        {"volume_step", to_string_num(volume_step)},
        {"volume_limit", to_string_num(volume_limit)},
        {"trade_tick_value", to_string_num(trade_tick_value)},
        {"trade_tick_value_profit", to_string_num(trade_tick_value_profit)},
        {"trade_tick_value_loss", to_string_num(trade_tick_value_loss)},
        {"trade_tick_size", to_string_num(trade_tick_size)},
        {"trade_contract_size", to_string_num(trade_contract_size)},
        {"swap_mode", to_string_num(swap_mode)},
        {"swap_long", to_string_num(swap_long)},
        {"swap_short", to_string_num(swap_short)},
        {"swap_rollover3days", to_string_num(swap_rollover3days)},
        {"bid", to_string_num(bid)},
        {"ask", to_string_num(ask)},
        {"last", to_string_num(last)},
        {"select", to_string_bool(select)},
        {"visible", to_string_bool(visible)},
    };
}

Dict TradeRecordData::to_dict() const {
    return {
        {"ticket", to_string_num(ticket)},
        {"order", to_string_num(order)},
        {"time", to_string_num(time)},
        {"time_msc", to_string_num(time_msc)},
        {"type", to_string_num(type)},
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

}  // namespace hqt::sim

