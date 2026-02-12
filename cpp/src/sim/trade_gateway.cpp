#include "sim/trade_gateway.hpp"

namespace hqt::sim {

namespace {

TradeResult invalid_result(const std::string& comment, int retcode = 10013) {
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
    if (request.action != 1) {
        return invalid_result("Invalid request: missing or unsupported action", 10013);
    }
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

    bool ok = false;
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

}  // namespace hqt::sim

