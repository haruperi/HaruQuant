#include "sim/simulator_client.hpp"

namespace hqt::sim {

SimulatorClient::SimulatorClient(AccountInfoData account_data)
    : account_data_(std::move(account_data)) {}

const AccountInfoData& SimulatorClient::account_info() const noexcept {
    return account_data_;
}

const SymbolInfoData* SimulatorClient::symbol_info(const std::string& symbol) const noexcept {
    const auto it = symbols_data_.find(symbol);
    return it == symbols_data_.end() ? nullptr : &it->second;
}

const SymbolTickData* SimulatorClient::symbol_info_tick(const std::string& symbol) const noexcept {
    const auto it = ticks_data_.find(symbol);
    return it == ticks_data_.end() ? nullptr : &it->second;
}

std::vector<TradeRecordData> SimulatorClient::positions_get(
    std::optional<uint64_t> ticket,
    std::optional<std::string_view> symbol) const {
    return collect_records(positions_data_, ticket, symbol);
}

std::vector<TradeRecordData> SimulatorClient::orders_get(
    std::optional<uint64_t> ticket,
    std::optional<std::string_view> symbol) const {
    return collect_records(orders_data_, ticket, symbol);
}

std::vector<TradeRecordData> SimulatorClient::history_orders_get(
    std::optional<uint64_t> ticket) const {
    return collect_records(history_orders_data_, ticket, std::nullopt);
}

std::vector<TradeRecordData> SimulatorClient::history_deals_get(
    std::optional<uint64_t> ticket) const {
    return collect_records(deals_data_, ticket, std::nullopt);
}

std::pair<int, std::string> SimulatorClient::last_error() const {
    return {last_error_code_, last_error_message_};
}

std::string SimulatorClient::trade_retcode_description(int retcode) const {
    switch (retcode) {
        case 10008: return "Order placed";
        case 10009: return "Request completed";
        case 10010: return "Request partially completed";
        case 10013: return "Invalid request";
        case 10014: return "Invalid volume";
        case 10015: return "Invalid price";
        case 10016: return "Invalid stops";
        case 10017: return "Trade disabled";
        case 10018: return "Market closed";
        case 10019: return "No money";
        case 10021: return "No quotes";
        default: return "Unknown retcode";
    }
}

void SimulatorClient::set_account_info(const AccountInfoData& data) {
    account_data_ = data;
}

void SimulatorClient::set_symbol_info(const SymbolInfoData& data) {
    symbols_data_[data.symbol] = data;
}

void SimulatorClient::set_symbol_tick(const std::string& symbol, const SymbolTickData& tick) {
    ticks_data_[symbol] = tick;
}

void SimulatorClient::upsert_position(const TradeRecordData& data) {
    positions_data_[data.ticket] = data;
}

void SimulatorClient::upsert_order(const TradeRecordData& data) {
    orders_data_[data.ticket] = data;
}

void SimulatorClient::upsert_history_order(const TradeRecordData& data) {
    history_orders_data_[data.ticket] = data;
}

void SimulatorClient::upsert_deal(const TradeRecordData& data) {
    deals_data_[data.ticket] = data;
}

void SimulatorClient::set_last_error(int code, const std::string& message) {
    last_error_code_ = code;
    last_error_message_ = message;
}

template <typename Container>
std::vector<TradeRecordData> SimulatorClient::collect_records(
    const Container& records,
    std::optional<uint64_t> ticket,
    std::optional<std::string_view> symbol) {
    std::vector<TradeRecordData> out;

    if (ticket.has_value()) {
        const auto it = records.find(*ticket);
        if (it != records.end()) {
            if (!symbol.has_value() || it->second.symbol == *symbol) {
                out.push_back(it->second);
            }
        }
        return out;
    }

    out.reserve(records.size());
    for (const auto& [_, record] : records) {
        if (symbol.has_value() && record.symbol != *symbol) {
            continue;
        }
        out.push_back(record);
    }

    return out;
}

}  // namespace hqt::sim

