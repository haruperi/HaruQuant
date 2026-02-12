#include "sim/simulator_client.hpp"
#include "sim/calculators.hpp"

namespace hqt::sim {

SimulatorClient::SimulatorClient(AccountInfoData account_data)
    : account_data_(std::move(account_data)),
      trade_gateway_(account_data_) {}

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

double SimulatorClient::order_calc_margin(
    int action,
    const std::string& symbol,
    double volume,
    double price) const {
    (void)action;
    const auto* info = symbol_info(symbol);
    if (info == nullptr) {
        return 0.0;
    }
    return calc_margin(
        info->trade_calc_mode,
        volume,
        price,
        info->trade_contract_size,
        static_cast<double>(account_data_.leverage),
        info->trade_tick_size > 0.0 ? info->trade_tick_size : info->point,
        info->trade_tick_value,
        info->margin_initial);
}

double SimulatorClient::order_calc_profit(
    int action,
    const std::string& symbol,
    double volume,
    double price_open,
    double price_close) const {
    const auto* info = symbol_info(symbol);
    if (info == nullptr) {
        return 0.0;
    }
    return calc_profit(
        action,
        volume,
        price_open,
        price_close,
        info->trade_tick_size > 0.0 ? info->trade_tick_size : info->point,
        info->trade_tick_value,
        info->trade_contract_size);
}

TradeResult SimulatorClient::order_send(const TradeRequest& request) {
    const SymbolTickData* tick = symbol_info_tick(request.symbol);
    TradeResult result = trade_gateway_.order_send(request, tick);
    if (result.retcode == 10008 || result.retcode == 10009 || result.retcode == 10010) {
        sync_state_from_trade();
    }
    return result;
}

void SimulatorClient::set_account_info(const AccountInfoData& data) {
    account_data_ = data;
    trade_gateway_ = TradeGateway(account_data_);
    for (const auto& [_, symbol] : symbols_data_) {
        trade_gateway_.register_symbol(symbol);
    }
}

void SimulatorClient::set_symbol_info(const SymbolInfoData& data) {
    symbols_data_[data.symbol] = data;
    trade_gateway_.register_symbol(data);
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

void SimulatorClient::sync_state_from_trade() {
    positions_data_.clear();
    orders_data_.clear();
    deals_data_.clear();
    history_orders_data_.clear();

    const auto& trade = trade_gateway_.trade();

    for (const auto& pos : trade.GetPositions()) {
        TradeRecordData data;
        data.ticket = pos.Ticket();
        data.identifier = pos.Identifier();
        data.symbol = pos.Symbol();
        data.magic = pos.Magic();
        data.type = static_cast<uint64_t>(pos.PositionType());
        data.time = pos.Time();
        data.time_msc = pos.TimeMsc();
        data.volume = pos.Volume();
        data.price_open = pos.PriceOpen();
        data.price_current = pos.PriceCurrent();
        data.sl = pos.StopLoss();
        data.tp = pos.TakeProfit();
        data.profit = pos.Profit();
        data.comment = pos.Comment();
        positions_data_[data.ticket] = data;
    }

    for (const auto& ord : trade.GetOrders()) {
        TradeRecordData data;
        data.ticket = ord.Ticket();
        data.symbol = ord.Symbol();
        data.magic = ord.Magic();
        data.type = static_cast<uint64_t>(ord.OrderType());
        data.reason = static_cast<uint64_t>(ord.State());
        data.time = ord.TimeSetup();
        data.time_msc = ord.TimeSetupMsc();
        data.volume = ord.VolumeCurrent();
        data.price_open = ord.PriceOpen();
        data.price_current = ord.PriceCurrent();
        data.sl = ord.StopLoss();
        data.tp = ord.TakeProfit();
        data.comment = ord.Comment();
        orders_data_[data.ticket] = data;
    }

    for (const auto& deal : trade.GetDeals()) {
        TradeRecordData data;
        data.ticket = deal.Ticket();
        data.order = deal.Order();
        data.identifier = deal.PositionId();
        data.symbol = deal.Symbol();
        data.magic = deal.Magic();
        data.type = static_cast<uint64_t>(deal.DealType());
        data.reason = static_cast<uint64_t>(deal.Entry());
        data.time = deal.Time();
        data.time_msc = deal.TimeMsc();
        data.volume = deal.Volume();
        data.price_open = deal.Price();
        data.profit = deal.Profit();
        data.comment = deal.Comment();
        deals_data_[data.ticket] = data;
    }

    for (const auto& hist : trade.GetHistoryOrders()) {
        TradeRecordData data;
        data.ticket = hist.Ticket();
        data.symbol = hist.Symbol();
        data.type = static_cast<uint64_t>(hist.OrderType());
        data.reason = static_cast<uint64_t>(hist.State());
        data.time = hist.TimeSetup();
        data.time_msc = hist.TimeSetupMsc();
        data.volume = hist.VolumeCurrent();
        data.price_open = hist.PriceOpen();
        data.sl = hist.StopLoss();
        data.tp = hist.TakeProfit();
        data.comment = hist.Comment();
        history_orders_data_[data.ticket] = data;
    }
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
