/**
 * @file trading.cpp
 * @brief Unified engine trading compilation unit.
 */

#include "engine/engine.hpp"
#include "util/error.hpp"
#include "util/logger.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <optional>
#include <sstream>
#include <string>

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

PositionTotals AccountMonitor::monitor_positions(
    const TradeSimulator& client,
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

hqt::AccountInfo AccountMonitor::monitor_account(
    const hqt::AccountInfo& base,
    const PositionTotals& totals) const {
    hqt::AccountInfo updated = base;
    const auto margin_fp = static_cast<int64_t>(std::llround(totals.margin * 1'000'000.0));
    const auto profit_fp = static_cast<int64_t>(std::llround(totals.profit * 1'000'000.0));
    updated.SetMargin(margin_fp);
    updated.UpdateEquity(profit_fp);
    return updated;
}

void TradeRecordTracker::reset() {
    open_.clear();
    completed_.clear();
}

bool TradeRecordTracker::has_open(uint64_t ticket) const {
    return open_.find(ticket) != open_.end();
}

void TradeRecordTracker::on_open(
    uint64_t ticket,
    const std::string& symbol,
    bool is_buy,
    double volume,
    double open_price,
    double sl,
    double tp,
    int64_t open_time_msc,
    double initial_risk_usd) {
    if (ticket == 0 || has_open(ticket)) {
        return;
    }

    OpenTradeState state;
    state.record.ticket = ticket;
    state.record.symbol = symbol;
    state.record.is_buy = is_buy;
    state.record.volume = volume;
    state.record.open_price = open_price;
    state.record.stop_loss = sl;
    state.record.take_profit = tp;
    state.record.open_time_msc = open_time_msc;
    state.record.initial_risk_usd = initial_risk_usd;
    open_[ticket] = state;
}

void TradeRecordTracker::on_update(uint64_t ticket, double profit_usd) {
    const auto it = open_.find(ticket);
    if (it == open_.end()) {
        return;
    }

    OpenTradeState& state = it->second;
    state.record.bars_in_trade += 1;
    if (profit_usd > state.mfe_usd) {
        state.mfe_usd = profit_usd;
    }
    if (profit_usd < state.mae_usd) {
        state.mae_usd = profit_usd;
    }
}

bool TradeRecordTracker::on_close(
    uint64_t ticket,
    int64_t close_time_msc,
    double close_price,
    double profit_loss_usd) {
    const auto it = open_.find(ticket);
    if (it == open_.end()) {
        return false;
    }

    TradeRecord record = it->second.record;
    record.close_time_msc = close_time_msc;
    record.close_price = close_price;
    record.time_in_trade_seconds = static_cast<double>(record.close_time_msc - record.open_time_msc) / 1000.0;
    record.profit_loss = profit_loss_usd;
    record.mfe_usd = it->second.mfe_usd;
    record.mae_usd = std::abs(it->second.mae_usd);
    if (record.initial_risk_usd > 0.0) {
        record.r_multiple = record.profit_loss / record.initial_risk_usd;
    }

    completed_.push_back(record);
    open_.erase(it);
    return true;
}

const std::vector<TradeRecord>& TradeRecordTracker::completed_trades() const noexcept {
    return completed_;
}

namespace {

TradeResult invalid_result(const std::string& comment, int retcode = 10013) {
    util::warning("TradeGateway invalid request: " + comment + " (retcode=" + std::to_string(retcode) + ")");
    TradeResult result;
    result.retcode = retcode;
    result.comment = comment;
    return result;
}

}  // namespace

TradeGateway::TradeGateway(const hqt::AccountInfo& account)
    : trade_(account.Balance(), account.Currency(), static_cast<uint32_t>(account.Leverage())) {}

void TradeGateway::register_symbol(const hqt::SymbolInfo& symbol) {
    symbols_[symbol.Name()] = symbol;
    trade_.RegisterSymbol(symbol);
}

TradeResult TradeGateway::order_send(const TradeRequest& request, const SymbolTickData* tick) {
    bool ok = false;

    if (request.action == 1 || request.action == 5) {
        if (request.symbol.empty()) {
            return invalid_result("Invalid request: missing symbol", 10013);
        }
        if (request.volume <= 0.0) {
            return invalid_result("Invalid volume", 10014);
        }

        const auto sym_it = symbols_.find(request.symbol);
        if (sym_it == symbols_.end()) {
            return invalid_result("No quotes to process the request", 10021);
        }

        const double bid = tick ? tick->bid : sym_it->second.Bid();
        const double ask = tick ? tick->ask : sym_it->second.Ask();
        if (bid <= 0.0 || ask <= 0.0) {
            return invalid_result("No quotes to process the request", 10021);
        }
        trade_.UpdatePrices(request.symbol, bid, ask, tick ? (tick->time_msc * 1000) : 0);

        if (request.action == 1) {
            if (request.type == 0) {  // BUY
                ok = trade_.Buy(
                    request.volume,
                    request.symbol,
                    request.price,
                    request.sl,
                    request.tp,
                    request.comment);
            } else if (request.type == 1) {  // SELL
                ok = trade_.Sell(
                    request.volume,
                    request.symbol,
                    request.price,
                    request.sl,
                    request.tp,
                    request.comment);
            } else {
                return invalid_result("Invalid order type for market execution", 10013);
            }
        } else {
            // Pending place flow
            using OT = hqt::ENUM_ORDER_TYPE;
            OT order_type;
            switch (request.type) {
                case 2: order_type = OT::ORDER_TYPE_BUY_LIMIT; break;
                case 3: order_type = OT::ORDER_TYPE_SELL_LIMIT; break;
                case 4: order_type = OT::ORDER_TYPE_BUY_STOP; break;
                case 5: order_type = OT::ORDER_TYPE_SELL_STOP; break;
                case 6: order_type = OT::ORDER_TYPE_BUY_STOP_LIMIT; break;
                case 7: order_type = OT::ORDER_TYPE_SELL_STOP_LIMIT; break;
                default:
                    return invalid_result("Invalid pending order type", 10013);
            }

            ok = trade_.OrderOpen(
                request.symbol,
                order_type,
                request.volume,
                request.price,
                request.stoplimit,
                request.sl,
                request.tp,
                static_cast<hqt::ENUM_ORDER_TYPE_TIME>(request.type_time),
                request.expiration,
                request.comment);
        }
    } else if (request.action == 7) {
        if (request.order == 0) {
            return invalid_result("Invalid request: missing order", 10013);
        }
        ok = trade_.OrderModify(
            request.order,
            request.price,
            request.sl,
            request.tp,
            request.stoplimit,
            request.expiration);
    } else if (request.action == 8) {
        if (request.order == 0) {
            return invalid_result("Invalid request: missing order", 10013);
        }
        ok = trade_.OrderDelete(request.order);
    } else {
        return invalid_result("Invalid request: missing or unsupported action", 10013);
    }

    TradeResult result;
    result.retcode = static_cast<int>(trade_.ResultRetcode());
    result.deal = trade_.ResultDeal();
    result.order = trade_.ResultOrder();
    result.volume = trade_.ResultVolume();
    result.price = trade_.ResultPrice();
    result.bid = trade_.ResultBid();
    result.ask = trade_.ResultAsk();
    result.comment = trade_.ResultComment();

    if (!ok && result.retcode == 0) {
        result.retcode = 10011;
    }
    if (!ok) {
        util::warning("TradeGateway order_send failed: " + result.comment +
                      " (retcode=" + std::to_string(result.retcode) + ")");
    }
    return result;
}

TradeSimulator::TradeSimulator(hqt::AccountInfo account)
    : account_info_(std::move(account)),
      trade_gateway_(account_info_) {}

const hqt::AccountInfo& TradeSimulator::account_info() const noexcept {
    return account_info_;
}

const hqt::SymbolInfo* TradeSimulator::symbol_info(const std::string& symbol) const noexcept {
    const auto it = symbols_data_.find(symbol);
    return it == symbols_data_.end() ? nullptr : &it->second;
}

const SymbolTickData* TradeSimulator::symbol_info_tick(const std::string& symbol) const noexcept {
    const auto it = ticks_data_.find(symbol);
    return it == ticks_data_.end() ? nullptr : &it->second;
}

std::vector<TradeRecordData> TradeSimulator::positions_get(
    std::optional<uint64_t> ticket,
    std::optional<std::string_view> symbol) const {
    return collect_records(positions_data_, ticket, symbol);
}

std::vector<TradeRecordData> TradeSimulator::orders_get(
    std::optional<uint64_t> ticket,
    std::optional<std::string_view> symbol) const {
    return collect_records(orders_data_, ticket, symbol);
}

std::vector<TradeRecordData> TradeSimulator::history_orders_get(
    std::optional<uint64_t> ticket) const {
    return collect_records(history_orders_data_, ticket, std::nullopt);
}

std::vector<TradeRecordData> TradeSimulator::history_deals_get(
    std::optional<uint64_t> ticket) const {
    return collect_records(deals_data_, ticket, std::nullopt);
}

std::pair<int, std::string> TradeSimulator::last_error() const {
    return {last_error_code_, last_error_message_};
}

std::string TradeSimulator::trade_retcode_description(int retcode) const {
    return util::error_from_retcode(retcode).message;
}

double TradeSimulator::order_calc_margin(
    int action,
    const std::string& symbol,
    double volume,
    double price) const {
    (void)action;
    const auto* info = symbol_info(symbol);
    if (info == nullptr) {
        util::warning("TradeSimulator::order_calc_margin unknown symbol: " + symbol);
        return 0.0;
    }
    return calc_margin(
        static_cast<int>(info->TradeCalcMode()),
        volume,
        price,
        info->ContractSize(),
        static_cast<double>(account_info_.Leverage()),
        info->TickSize() > 0.0 ? info->TickSize() : info->Point(),
        info->TickValue(),
        info->MarginInitial());
}

double TradeSimulator::order_calc_profit(
    int action,
    const std::string& symbol,
    double volume,
    double price_open,
    double price_close) const {
    const auto* info = symbol_info(symbol);
    if (info == nullptr) {
        util::warning("TradeSimulator::order_calc_profit unknown symbol: " + symbol);
        return 0.0;
    }
    return calc_profit(
        action,
        volume,
        price_open,
        price_close,
        info->TickSize() > 0.0 ? info->TickSize() : info->Point(),
        info->TickValue(),
        info->ContractSize());
}

TradeResult TradeSimulator::order_send(const TradeRequest& request) {
    const bool is_submission = (request.action == 1 || request.action == 5);
    const std::string client_order_id = request.client_order_id;
    const std::string fingerprint = submission_fingerprint(request);
    if (is_submission && !client_order_id.empty()) {
        const auto idem_it = idempotency_by_client_order_id_.find(client_order_id);
        if (idem_it != idempotency_by_client_order_id_.end()) {
            if (idem_it->second.fingerprint != fingerprint) {
                return invalid_result("Duplicate client_order_id with different payload", 10013);
            }
            return idem_it->second.result;
        }
    }

    const SymbolTickData* tick = symbol_info_tick(request.symbol);
    TradeResult result = trade_gateway_.order_send(request, tick);
    if (result.retcode == 10008 || result.retcode == 10009 || result.retcode == 10010) {
        sync_state_from_trade();
        util::debug("TradeSimulator::order_send success retcode=" + std::to_string(result.retcode));
    } else {
        util::warning("TradeSimulator::order_send failed retcode=" + std::to_string(result.retcode) +
                      " comment=" + result.comment);
    }

    if (is_submission && !client_order_id.empty()) {
        if (result.retcode == 10008 || result.retcode == 10009 || result.retcode == 10010) {
            idempotency_by_client_order_id_[client_order_id] = IdempotencyEntry{fingerprint, result};
        }
    }

    if (request.action == 1 || request.action == 5) {
        if (result.order > 0) {
            set_order_state(result.order, OmsOrderState::New);
            if (result.retcode == 10008 || result.retcode == 10009 || result.retcode == 10010) {
                set_order_state(result.order, OmsOrderState::Accepted);
                if (request.action == 1) {
                    if (result.retcode == 10010) {
                        set_order_state(result.order, OmsOrderState::PartiallyFilled);
                    } else if (result.retcode == 10009) {
                        set_order_state(result.order, OmsOrderState::Filled);
                    }
                }
            } else {
                set_order_state(result.order, OmsOrderState::Rejected);
            }
        }
    } else if (request.action == 8 && request.order > 0 &&
               (result.retcode == 10009 || result.retcode == 10010)) {
        set_order_state(request.order, OmsOrderState::Canceled);
    }

    return result;
}

TradeResult TradeSimulator::close_position(uint64_t ticket) {
    if (ticket == 0) {
        util::warning("TradeSimulator::close_position called with ticket=0");
        TradeResult invalid;
        invalid.retcode = 10013;
        invalid.comment = "Invalid request: missing position ticket";
        return invalid;
    }

    std::string symbol;
    const auto pos_it = positions_data_.find(ticket);
    if (pos_it != positions_data_.end()) {
        symbol = pos_it->second.symbol;
    }

    if (!symbol.empty()) {
        const auto tick_it = ticks_data_.find(symbol);
        if (tick_it != ticks_data_.end()) {
            const auto& tick = tick_it->second;
            trade_gateway_.trade().UpdatePrices(symbol, tick.bid, tick.ask, tick.time_msc * 1000);
        }
    }

    const bool ok = trade_gateway_.trade().PositionClose(ticket);

    TradeResult result;
    result.retcode = static_cast<int>(trade_gateway_.trade().ResultRetcode());
    result.deal = trade_gateway_.trade().ResultDeal();
    result.order = trade_gateway_.trade().ResultOrder();
    result.volume = trade_gateway_.trade().ResultVolume();
    result.price = trade_gateway_.trade().ResultPrice();
    result.bid = trade_gateway_.trade().ResultBid();
    result.ask = trade_gateway_.trade().ResultAsk();
    result.comment = trade_gateway_.trade().ResultComment();

    if (ok && (result.retcode == 10009 || result.retcode == 10010)) {
        sync_state_from_trade();
        util::debug("TradeSimulator::close_position success ticket=" + std::to_string(ticket));
    } else if (!ok && result.retcode == 0) {
        result.retcode = 10011;
        util::warning("TradeSimulator::close_position failed ticket=" + std::to_string(ticket));
    }

    return result;
}

bool TradeSimulator::set_history_order_state(uint64_t ticket, uint64_t state) {
    const auto hist_it = history_orders_data_.find(ticket);
    if (hist_it != history_orders_data_.end()) {
        hist_it->second.reason = state;
        set_order_state(ticket, map_order_state(state));
        return true;
    }

    const auto active_it = orders_data_.find(ticket);
    if (active_it != orders_data_.end()) {
        active_it->second.reason = state;
        set_order_state(ticket, map_order_state(state));
        return true;
    }

    return false;
}

bool TradeSimulator::set_history_order_done_time(uint64_t ticket, int64_t time_sec, int64_t time_msc) {
    const auto it = history_orders_data_.find(ticket);
    if (it == history_orders_data_.end()) {
        return false;
    }
    it->second.time = time_sec;
    it->second.time_msc = time_msc;
    return true;
}

void TradeSimulator::set_account_info(const hqt::AccountInfo& data) {
    account_info_ = data;
    trade_gateway_ = TradeGateway(account_info_);
    for (const auto& [_, symbol] : symbols_data_) {
        trade_gateway_.register_symbol(symbol);
    }
}

void TradeSimulator::set_symbol_info(const hqt::SymbolInfo& data) {
    symbols_data_[data.Name()] = data;
    trade_gateway_.register_symbol(data);
    util::debug("TradeSimulator::set_symbol_info symbol=" + data.Name());
}

void TradeSimulator::set_symbol_tick(const std::string& symbol, const SymbolTickData& tick) {
    ticks_data_[symbol] = tick;
}

void TradeSimulator::upsert_position(const TradeRecordData& data) {
    positions_data_[data.ticket] = data;
}

void TradeSimulator::upsert_order(const TradeRecordData& data) {
    orders_data_[data.ticket] = data;
}

void TradeSimulator::upsert_history_order(const TradeRecordData& data) {
    history_orders_data_[data.ticket] = data;
}

void TradeSimulator::upsert_deal(const TradeRecordData& data) {
    deals_data_[data.ticket] = data;
}

void TradeSimulator::set_last_error(int code, const std::string& message) {
    last_error_code_ = code;
    last_error_message_ = message;
    util::warning("TradeSimulator::set_last_error code=" + std::to_string(code) + " message=" + message);
}

OmsOrderState TradeSimulator::order_state(uint64_t ticket) const {
    const auto it = order_states_.find(ticket);
    if (it == order_states_.end()) {
        return OmsOrderState::Unknown;
    }
    return it->second;
}

std::string TradeSimulator::order_state_name(uint64_t ticket) const {
    return order_state_label(order_state(ticket));
}

std::size_t TradeSimulator::idempotency_cache_size() const noexcept {
    return idempotency_by_client_order_id_.size();
}

std::string TradeSimulator::submission_fingerprint(const TradeRequest& request) {
    std::ostringstream oss;
    oss << request.action << '|'
        << request.type << '|'
        << request.symbol << '|'
        << request.volume << '|'
        << request.price << '|'
        << request.stoplimit << '|'
        << request.sl << '|'
        << request.tp << '|'
        << request.type_time << '|'
        << request.expiration << '|'
        << request.comment;
    return oss.str();
}

OmsOrderState TradeSimulator::map_order_state(uint64_t raw_state) noexcept {
    switch (raw_state) {
        case 0: return OmsOrderState::New;
        case 1: return OmsOrderState::Accepted;
        case 2: return OmsOrderState::Canceled;
        case 3: return OmsOrderState::PartiallyFilled;
        case 4: return OmsOrderState::Filled;
        case 5: return OmsOrderState::Rejected;
        case 6: return OmsOrderState::Expired;
        default: return OmsOrderState::Unknown;
    }
}

std::string TradeSimulator::order_state_label(OmsOrderState state) {
    switch (state) {
        case OmsOrderState::New: return "NEW";
        case OmsOrderState::Accepted: return "ACCEPTED";
        case OmsOrderState::PartiallyFilled: return "PARTIALLY_FILLED";
        case OmsOrderState::Filled: return "FILLED";
        case OmsOrderState::Canceled: return "CANCELED";
        case OmsOrderState::Expired: return "EXPIRED";
        case OmsOrderState::Rejected: return "REJECTED";
        default: return "UNKNOWN";
    }
}

void TradeSimulator::set_order_state(uint64_t ticket, OmsOrderState state) {
    if (ticket == 0) {
        return;
    }
    order_states_[ticket] = state;
}

void TradeSimulator::rebuild_order_states_from_snapshots() {
    for (const auto& [ticket, record] : orders_data_) {
        order_states_[ticket] = map_order_state(record.reason);
    }
    for (const auto& [ticket, record] : history_orders_data_) {
        order_states_[ticket] = map_order_state(record.reason);
    }
}

void TradeSimulator::sync_state_from_trade() {
    positions_data_.clear();
    orders_data_.clear();
    deals_data_.clear();
    history_orders_data_.clear();

    const auto& trade = trade_gateway_.trade();
    const auto& account = trade.Account();

    account_info_ = account;

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
        data.expiration = ord.TimeExpiration();
        data.type_time = static_cast<uint64_t>(ord.TypeTime());
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
        data.expiration = hist.TimeExpiration();
        data.type_time = static_cast<uint64_t>(hist.TypeTime());
        data.volume = hist.VolumeCurrent();
        data.price_open = hist.PriceOpen();
        data.sl = hist.StopLoss();
        data.tp = hist.TakeProfit();
        data.comment = hist.Comment();
        history_orders_data_[data.ticket] = data;
    }

    util::debug(
        "TradeSimulator::sync_state_from_trade positions=" + std::to_string(positions_data_.size()) +
        " orders=" + std::to_string(orders_data_.size()) +
        " deals=" + std::to_string(deals_data_.size()) +
        " history_orders=" + std::to_string(history_orders_data_.size()));
    rebuild_order_states_from_snapshots();
}

template <typename Container>
std::vector<TradeRecordData> TradeSimulator::collect_records(
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

MockBroker::MockBroker(TradeSimulator client)
    : client_(std::move(client)) {}

void MockBroker::set_partial_fill_ratio(double ratio) {
    partial_fill_ratio_ = std::clamp(ratio, 0.0, 1.0);
}

void MockBroker::set_deterministic_price(double price) {
    if (price > 0.0) {
        deterministic_price_ = price;
    }
}

void MockBroker::clear_deterministic_price() {
    deterministic_price_.reset();
}

bool MockBroker::connect() {
    connected_ = true;
    return true;
}

TradeResult MockBroker::submit(const TradeRequest& request) {
    if (!connected_) {
        TradeResult out;
        out.retcode = 10031;
        out.comment = "MockBroker not connected";
        return out;
    }

    TradeRequest effective = scaled_request(request, partial_fill_ratio_);
    if (deterministic_price_.has_value()) {
        effective.price = *deterministic_price_;
    }
    TradeResult out = client_.order_send(effective);
    if (request.volume > 0.0 && effective.volume > 0.0 && effective.volume < request.volume &&
        hqt::util::is_success_retcode(out.retcode)) {
        out.retcode = 10010;
        out.volume = effective.volume;
        if (out.comment.empty()) {
            out.comment = "Partial fill (mock ratio)";
        }
    }
    return out;
}

TradeResult MockBroker::cancel(uint64_t order_id) {
    if (!connected_) {
        TradeResult out;
        out.retcode = 10031;
        out.comment = "MockBroker not connected";
        return out;
    }
    TradeRequest req;
    req.action = 8;
    req.order = order_id;
    return client_.order_send(req);
}

BrokerSnapshot MockBroker::fetch_state() const {
    BrokerSnapshot snapshot;
    snapshot.account = client_.account_info();
    snapshot.positions = aggregate_positions();
    return snapshot;
}

TradeRequest MockBroker::scaled_request(const TradeRequest& request, double ratio) {
    TradeRequest out = request;
    if (out.volume > 0.0) {
        out.volume = std::max(0.0, out.volume * std::clamp(ratio, 0.0, 1.0));
    }
    return out;
}

std::unordered_map<std::string, PositionAggregate> MockBroker::aggregate_positions() const {
    std::unordered_map<std::string, PositionAggregate> out;
    for (const auto& pos : client_.positions_get()) {
        auto& agg = out[pos.symbol];
        const bool is_buy = (pos.type == 0U);
        if (is_buy) {
            agg.long_volume += pos.volume;
            agg.net_volume += pos.volume;
        } else {
            agg.short_volume += pos.volume;
            agg.net_volume -= pos.volume;
        }
    }
    return out;
}

PaperTradingEngine::PaperTradingEngine(std::shared_ptr<BrokerAdapter> adapter)
    : adapter_(std::move(adapter)) {}

bool PaperTradingEngine::connect() {
    if (!adapter_) {
        return false;
    }
    return adapter_->connect();
}

TradeResult PaperTradingEngine::submit_order(const TradeRequest& request) {
    if (!adapter_) {
        TradeResult out;
        out.retcode = 10031;
        out.comment = "PaperTradingEngine adapter missing";
        return out;
    }
    return adapter_->submit(request);
}

TradeResult PaperTradingEngine::cancel_order(uint64_t order_id) {
    if (!adapter_) {
        TradeResult out;
        out.retcode = 10031;
        out.comment = "PaperTradingEngine adapter missing";
        return out;
    }
    return adapter_->cancel(order_id);
}

BrokerSnapshot PaperTradingEngine::snapshot_state() const {
    if (!adapter_) {
        return {};
    }
    return adapter_->fetch_state();
}

std::vector<ExecutionSlice> ExecutionAlgoTWAP::build_schedule(
    const double total_volume,
    const int64_t start_time_ms,
    const int64_t end_time_ms,
    const std::size_t slices) {
    std::vector<ExecutionSlice> out;
    if (total_volume <= 0.0 || slices == 0U || end_time_ms < start_time_ms) {
        return out;
    }
    out.reserve(slices);

    const double slice_volume = total_volume / static_cast<double>(slices);
    const int64_t span = end_time_ms - start_time_ms;
    const int64_t step = (slices > 1U) ? (span / static_cast<int64_t>(slices - 1U)) : 0;
    double assigned = 0.0;

    for (std::size_t i = 0; i < slices; ++i) {
        ExecutionSlice s{};
        s.scheduled_time_ms = start_time_ms + (step * static_cast<int64_t>(i));
        s.weight = 1.0 / static_cast<double>(slices);
        s.volume = (i + 1U == slices) ? (total_volume - assigned) : slice_volume;
        assigned += s.volume;
        out.push_back(s);
    }
    return out;
}

std::vector<ExecutionSlice> ExecutionAlgoVWAP::build_schedule(
    const double total_volume,
    const int64_t start_time_ms,
    const int64_t end_time_ms,
    const std::vector<double>& market_volume_profile) {
    std::vector<ExecutionSlice> out;
    const std::size_t slices = market_volume_profile.size();
    if (total_volume <= 0.0 || slices == 0U || end_time_ms < start_time_ms) {
        return out;
    }
    out.reserve(slices);

    double weight_sum = 0.0;
    for (const double v : market_volume_profile) {
        if (v > 0.0) {
            weight_sum += v;
        }
    }
    if (weight_sum <= 0.0) {
        return ExecutionAlgoTWAP::build_schedule(total_volume, start_time_ms, end_time_ms, slices);
    }

    const int64_t span = end_time_ms - start_time_ms;
    const int64_t step = (slices > 1U) ? (span / static_cast<int64_t>(slices - 1U)) : 0;
    double assigned = 0.0;

    for (std::size_t i = 0; i < slices; ++i) {
        const double raw = std::max(0.0, market_volume_profile[i]);
        const double weight = raw / weight_sum;
        ExecutionSlice s{};
        s.scheduled_time_ms = start_time_ms + (step * static_cast<int64_t>(i));
        s.weight = weight;
        s.volume = (i + 1U == slices) ? (total_volume - assigned) : (total_volume * weight);
        assigned += s.volume;
        out.push_back(s);
    }
    return out;
}

ExecutionRouter::ExecutionRouter(
    std::shared_ptr<BrokerAdapter> adapter,
    ExecutionPolicy policy)
    : adapter_(std::move(adapter)),
      policy_(policy) {}

bool ExecutionRouter::connect() {
    if (!adapter_) {
        return false;
    }
    connected_ = adapter_->connect();
    return connected_;
}

void ExecutionRouter::set_policy(const ExecutionPolicy& policy) {
    std::scoped_lock lock(mutex_);
    policy_ = policy;
}

ExecutionPolicy ExecutionRouter::policy() const {
    std::scoped_lock lock(mutex_);
    return policy_;
}

void ExecutionRouter::set_risk_account_state(
    const double equity,
    const double peak_equity,
    const double gross_exposure,
    const double net_exposure) {
    std::scoped_lock lock(mutex_);
    risk_state_.equity = equity;
    risk_state_.peak_equity = peak_equity;
    risk_state_.gross_exposure = gross_exposure;
    risk_state_.net_exposure = net_exposure;
}

std::size_t ExecutionRouter::consecutive_failures() const {
    std::scoped_lock lock(mutex_);
    return consecutive_failures_;
}

ExecutionRouteResult ExecutionRouter::submit(
    const TradeRequest& request,
    const double candidate_gross_add,
    const double candidate_net_delta,
    const double margin_required,
    const double free_margin,
    const bool live_mode) {
    ExecutionRouteResult out;
    if (!adapter_ || !connected_) {
        out.result.retcode = 10031;
        out.result.comment = "ExecutionRouter adapter unavailable";
        out.policy_code = "CONNECTION";
        out.reason = "adapter_unavailable";
        return out;
    }

    hqt::risk::RiskAccountState risk_state{};
    {
        std::scoped_lock lock(mutex_);
        risk_state = risk_state_;
    }
    const auto mode = live_mode ? hqt::risk::RiskMode::Live : hqt::risk::RiskMode::Backtest;
    const auto risk_decision = governor_.can_trade_with_mode(
        risk_state,
        request.volume,
        candidate_gross_add,
        candidate_net_delta,
        margin_required,
        free_margin,
        mode);
    if (!risk_decision.allowed) {
        out.risk_blocked = true;
        out.policy_code = risk_decision.policy_code;
        out.reason = risk_decision.reason;
        out.result.retcode = 10006;
        out.result.comment = "Risk gate rejected order";
        return out;
    }

    const auto now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                            std::chrono::steady_clock::now().time_since_epoch())
                            .count();
    {
        std::scoped_lock lock(mutex_);
        if (!check_rate_limit_unlocked(now_ms)) {
            out.rate_limited = true;
            out.policy_code = "RATE_LIMIT";
            out.reason = "too_many_requests";
            out.result.retcode = 10024;
            out.result.comment = "Order spam prevention triggered";
            return out;
        }
        recent_submissions_ms_.push_back(now_ms);
    }

    const auto start_ts = std::chrono::steady_clock::now();
    const int max_attempts = std::max(1, policy().max_retries + 1);
    for (int attempt = 1; attempt <= max_attempts; ++attempt) {
        out.attempts = attempt;
        out.result = adapter_->submit(request);
        if (hqt::util::is_success_retcode(out.result.retcode)) {
            std::scoped_lock lock(mutex_);
            consecutive_failures_ = 0;
            out.retried = (attempt > 1);
            break;
        }

        const auto error_info = hqt::util::error_from_retcode(out.result.retcode);
        const bool can_retry = error_info.retryable && attempt < max_attempts;
        if (!can_retry) {
            break;
        }
    }

    if (!hqt::util::is_success_retcode(out.result.retcode)) {
        out.retried = out.attempts > 1;
        {
            std::scoped_lock lock(mutex_);
            ++consecutive_failures_;
            if (consecutive_failures_ >= policy_.escalation_after_failures) {
                out.escalated = true;
                out.escalation_reason = "bounded_failure_threshold_reached";
            }
        }
        out.policy_code = "EXECUTION_FAILED";
        out.reason = "execution_retry_exhausted";
    }

    const auto end_ts = std::chrono::steady_clock::now();
    const double latency_ms = std::chrono::duration_cast<std::chrono::microseconds>(
                                  end_ts - start_ts)
                                  .count() /
        1000.0;
    {
        std::scoped_lock lock(mutex_);
        latencies_ms_.push_back(latency_ms);
        latency_sum_ms_ += latency_ms;
        ++quality_samples_;

        const bool partial_fill = (out.result.retcode == 10010) ||
            (request.volume > 0.0 && out.result.volume > 0.0 && out.result.volume < request.volume);
        if (partial_fill) {
            ++partial_fill_count_;
        }

        const bool is_buy = (request.type == 0 || request.type == 2 || request.type == 4 || request.type == 6);
        const double spread = std::max(0.0, out.result.ask - out.result.bid);
        spread_sum_ += spread;

        double expected_price = request.price;
        if (request.action == 1 && expected_price <= 0.0) {
            expected_price = is_buy ? out.result.ask : out.result.bid;
        }
        if (expected_price > 0.0 && out.result.price > 0.0) {
            const double slippage = is_buy
                ? std::max(0.0, out.result.price - expected_price)
                : std::max(0.0, expected_price - out.result.price);
            slippage_sum_ += slippage;
        }
    }
    return out;
}

TradeResult ExecutionRouter::cancel(const uint64_t order_id) {
    if (!adapter_ || !connected_) {
        TradeResult out;
        out.retcode = 10031;
        out.comment = "ExecutionRouter adapter unavailable";
        return out;
    }
    return adapter_->cancel(order_id);
}

bool ExecutionRouter::check_rate_limit_unlocked(const int64_t now_ms) {
    const int64_t window_ms = std::max<int64_t>(1, policy_.rate_limit_window_ms);
    while (!recent_submissions_ms_.empty() &&
           (now_ms - recent_submissions_ms_.front()) > window_ms) {
        recent_submissions_ms_.pop_front();
    }
    return recent_submissions_ms_.size() < policy_.max_orders_per_window;
}

void ExecutionRouter::reset_quality_metrics() {
    std::scoped_lock lock(mutex_);
    latencies_ms_.clear();
    latency_sum_ms_ = 0.0;
    slippage_sum_ = 0.0;
    spread_sum_ = 0.0;
    quality_samples_ = 0U;
    partial_fill_count_ = 0U;
}

ExecutionQualitySummary ExecutionRouter::quality_summary() const {
    std::scoped_lock lock(mutex_);
    ExecutionQualitySummary out{};
    out.samples = quality_samples_;
    out.partial_fill_count = partial_fill_count_;
    if (quality_samples_ == 0U) {
        return out;
    }

    out.partial_fill_rate = static_cast<double>(partial_fill_count_) / static_cast<double>(quality_samples_);
    out.avg_latency_ms = latency_sum_ms_ / static_cast<double>(quality_samples_);
    out.avg_slippage = slippage_sum_ / static_cast<double>(quality_samples_);
    out.avg_spread = spread_sum_ / static_cast<double>(quality_samples_);

    std::vector<double> sorted = latencies_ms_;
    std::sort(sorted.begin(), sorted.end());
    const std::size_t idx = static_cast<std::size_t>(
        std::ceil(0.99 * static_cast<double>(sorted.size()))) - 1U;
    out.p99_latency_ms = sorted[std::min(idx, sorted.size() - 1U)];
    return out;
}

}  // namespace hqt::sim


