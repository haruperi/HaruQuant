/**
 * @file trading.cpp
 * @brief Unified engine trading compilation unit.
 */

#include "engine/engine.hpp"
#include "util/error.hpp"
#include "util/logger.hpp"

#include <algorithm>
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

TradeGateway::TradeGateway(const AccountInfoData& account)
    : trade_(account.balance, account.currency, static_cast<uint32_t>(account.leverage)) {}

void TradeGateway::register_symbol(const SymbolInfoData& symbol) {
    symbols_[symbol.symbol] = symbol;
    trade_.RegisterSymbol(to_symbol_info(symbol));
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

        const double bid = tick ? tick->bid : sym_it->second.bid;
        const double ask = tick ? tick->ask : sym_it->second.ask;
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

hqt::SymbolInfo TradeGateway::to_symbol_info(const SymbolInfoData& data) {
    hqt::SymbolInfo info;
    info.Name(data.symbol);
    info.SetSymbolId(static_cast<uint32_t>(std::hash<std::string>{}(data.symbol) & 0x7fffffff));
    info.SetDigits(data.digits);
    info.SetPoint(data.point);
    info.SetSpread(data.spread);
    info.SetSpreadFloat(data.spread_float);
    info.SetTradeCalcMode(static_cast<hqt::ENUM_SYMBOL_CALC_MODE>(data.trade_calc_mode));
    info.SetTradeMode(static_cast<hqt::ENUM_SYMBOL_TRADE_MODE>(data.trade_mode));
    info.SetStopsLevel(data.trade_stops_level);
    info.SetFreezeLevel(data.trade_freeze_level);
    info.SetVolumeMin(data.volume_min);
    info.SetVolumeMax(data.volume_max);
    info.SetVolumeStep(data.volume_step);
    info.SetVolumeLimit(data.volume_limit);
    info.SetTickValue(data.trade_tick_value);
    info.SetTickValueProfit(data.trade_tick_value_profit);
    info.SetTickValueLoss(data.trade_tick_value_loss);
    info.SetTickSize(data.trade_tick_size);
    info.SetContractSize(data.trade_contract_size);
    info.SetMarginInitial(data.margin_initial);
    info.SetSwapLong(data.swap_long);
    info.SetSwapShort(data.swap_short);
    info.SetSwapMode(static_cast<hqt::ENUM_SYMBOL_SWAP_MODE>(data.swap_mode));
    info.SetSwapRollover3days(static_cast<hqt::ENUM_DAY_OF_WEEK>(data.swap_rollover3days));
    if (data.bid > 0.0 && data.ask > 0.0) {
        info.UpdatePrice(data.bid, data.ask, 0);
    }
    return info;
}

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
    return util::error_from_retcode(retcode).message;
}

double SimulatorClient::order_calc_margin(
    int action,
    const std::string& symbol,
    double volume,
    double price) const {
    (void)action;
    const auto* info = symbol_info(symbol);
    if (info == nullptr) {
        util::warning("SimulatorClient::order_calc_margin unknown symbol: " + symbol);
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
        util::warning("SimulatorClient::order_calc_profit unknown symbol: " + symbol);
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
        util::debug("SimulatorClient::order_send success retcode=" + std::to_string(result.retcode));
    } else {
        util::warning("SimulatorClient::order_send failed retcode=" + std::to_string(result.retcode) +
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

TradeResult SimulatorClient::close_position(uint64_t ticket) {
    if (ticket == 0) {
        util::warning("SimulatorClient::close_position called with ticket=0");
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
        util::debug("SimulatorClient::close_position success ticket=" + std::to_string(ticket));
    } else if (!ok && result.retcode == 0) {
        result.retcode = 10011;
        util::warning("SimulatorClient::close_position failed ticket=" + std::to_string(ticket));
    }

    return result;
}

bool SimulatorClient::set_history_order_state(uint64_t ticket, uint64_t state) {
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

bool SimulatorClient::set_history_order_done_time(uint64_t ticket, int64_t time_sec, int64_t time_msc) {
    const auto it = history_orders_data_.find(ticket);
    if (it == history_orders_data_.end()) {
        return false;
    }
    it->second.time = time_sec;
    it->second.time_msc = time_msc;
    return true;
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
    util::debug("SimulatorClient::set_symbol_info symbol=" + data.symbol);
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
    util::warning("SimulatorClient::set_last_error code=" + std::to_string(code) + " message=" + message);
}

OmsOrderState SimulatorClient::order_state(uint64_t ticket) const {
    const auto it = order_states_.find(ticket);
    if (it == order_states_.end()) {
        return OmsOrderState::Unknown;
    }
    return it->second;
}

std::string SimulatorClient::order_state_name(uint64_t ticket) const {
    return order_state_label(order_state(ticket));
}

std::size_t SimulatorClient::idempotency_cache_size() const noexcept {
    return idempotency_by_client_order_id_.size();
}

std::string SimulatorClient::submission_fingerprint(const TradeRequest& request) {
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

OmsOrderState SimulatorClient::map_order_state(uint64_t raw_state) noexcept {
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

std::string SimulatorClient::order_state_label(OmsOrderState state) {
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

void SimulatorClient::set_order_state(uint64_t ticket, OmsOrderState state) {
    if (ticket == 0) {
        return;
    }
    order_states_[ticket] = state;
}

void SimulatorClient::rebuild_order_states_from_snapshots() {
    for (const auto& [ticket, record] : orders_data_) {
        order_states_[ticket] = map_order_state(record.reason);
    }
    for (const auto& [ticket, record] : history_orders_data_) {
        order_states_[ticket] = map_order_state(record.reason);
    }
}

void SimulatorClient::sync_state_from_trade() {
    positions_data_.clear();
    orders_data_.clear();
    deals_data_.clear();
    history_orders_data_.clear();

    const auto& trade = trade_gateway_.trade();
    const auto& account = trade.Account();

    account_data_.balance = account.Balance();
    account_data_.credit = account.Credit();
    account_data_.profit = account.Profit();
    account_data_.equity = account.Equity();
    account_data_.margin = account.Margin();
    account_data_.margin_free = account.FreeMargin();
    account_data_.margin_level = account.MarginLevel();

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
        "SimulatorClient::sync_state_from_trade positions=" + std::to_string(positions_data_.size()) +
        " orders=" + std::to_string(orders_data_.size()) +
        " deals=" + std::to_string(deals_data_.size()) +
        " history_orders=" + std::to_string(history_orders_data_.size()));
    rebuild_order_states_from_snapshots();
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

MockBroker::MockBroker(SimulatorClient client)
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
    return client_.order_send(effective);
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

}  // namespace hqt::sim
