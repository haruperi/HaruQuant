#include "trading/symbol_info.hpp"
#include <cmath>
#include <stdexcept>
#include <string>

namespace haruquant::trading {

SymbolInfo::SymbolInfo() : m_state(nullptr), m_name("") {}

SymbolInfo::SymbolInfo(const core::BacktestState *state)
    : m_state(state), m_name("") {}

void SymbolInfo::SetState(const core::BacktestState *state) { m_state = state; }

bool SymbolInfo::Name(const std::string &name) {
  m_name = name;
  return true;
}

void SymbolInfo::Refresh() {
  // If we wanted to parse current ticks from state directly here we could,
  // but typically m_state will just update under the hood in a backtester.
}

void SymbolInfo::RefreshRates() { Refresh(); }

long SymbolInfo::GetInteger(const std::string &prop) const {
  if (!m_state || m_name.empty())
    return 0;

  auto sym_it = m_state->trading_symbols.find(m_name);
  if (sym_it != m_state->trading_symbols.end()) {
    auto prop_it = sym_it->second.find(prop);
    if (prop_it != sym_it->second.end()) {
      try {
        return static_cast<long>(std::stoll(prop_it->second));
      } catch (...) {
        return 0;
      }
    }
  }
  return 0;
}

double SymbolInfo::GetDouble(const std::string &prop) const {
  if (!m_state || m_name.empty())
    return 0.0;

  auto sym_it = m_state->trading_symbols.find(m_name);
  if (sym_it != m_state->trading_symbols.end()) {
    auto prop_it = sym_it->second.find(prop);
    if (prop_it != sym_it->second.end()) {
      try {
        return std::stod(prop_it->second);
      } catch (...) {
        return 0.0;
      }
    }
  }
  return 0.0;
}

std::string SymbolInfo::GetString(const std::string &prop) const {
  if (!m_state || m_name.empty())
    return "";

  auto sym_it = m_state->trading_symbols.find(m_name);
  if (sym_it != m_state->trading_symbols.end()) {
    auto prop_it = sym_it->second.find(prop);
    if (prop_it != sym_it->second.end()) {
      return prop_it->second;
    }
  }
  return "";
}

//--- Integer properties
long SymbolInfo::Select() const { return GetInteger("select"); }
long SymbolInfo::Select(const bool select) {
  (void)select;
  return 0; /* In MT5 selects MarketWatch */
}
long SymbolInfo::Visible() const { return GetInteger("visible"); }
long SymbolInfo::SessionDeals() const { return GetInteger("session_deals"); }
long SymbolInfo::SessionBuyOrders() const {
  return GetInteger("session_buy_orders");
}
long SymbolInfo::SessionSellOrders() const {
  return GetInteger("session_sell_orders");
}
long SymbolInfo::Volume() const { return GetInteger("volume"); }
long SymbolInfo::VolumeHigh() const { return GetInteger("volume_high"); }
long SymbolInfo::VolumeLow() const { return GetInteger("volume_low"); }
long SymbolInfo::Time() const { return GetInteger("time"); }
long SymbolInfo::Digits() const { return GetInteger("digits"); }
long SymbolInfo::Spread() const { return GetInteger("spread"); }
long SymbolInfo::SpreadFloat() const { return GetInteger("spread_float"); }
long SymbolInfo::TicksBookDepth() const {
  return GetInteger("ticks_book_depth");
}
long SymbolInfo::TradeCalcMode() const { return GetInteger("trade_calc_mode"); }
long SymbolInfo::TradeMode() const { return GetInteger("trade_mode"); }
long SymbolInfo::StartTime() const { return GetInteger("start_time"); }
long SymbolInfo::ExpirationTime() const {
  return GetInteger("expiration_time");
}
long SymbolInfo::TradeStopsLevel() const {
  return GetInteger("trade_stops_level");
}
long SymbolInfo::TradeFreezeLevel() const {
  return GetInteger("trade_freeze_level");
}
long SymbolInfo::TradeExemode() const { return GetInteger("trade_exemode"); }
long SymbolInfo::SwapMode() const { return GetInteger("swap_mode"); }
long SymbolInfo::SwapRollover3days() const {
  return GetInteger("swap_rollover3days");
}
long SymbolInfo::MarginHedgedUseLeg() const {
  return GetInteger("margin_hedged_use_leg");
}
long SymbolInfo::ExpirationMode() const {
  return GetInteger("expiration_mode");
}
long SymbolInfo::FillingMode() const { return GetInteger("filling_mode"); }
long SymbolInfo::OrderMode() const { return GetInteger("order_mode"); }

//--- Double properties
double SymbolInfo::Bid() const { return GetDouble("bid"); }
double SymbolInfo::BidHigh() const { return GetDouble("bid_high"); }
double SymbolInfo::BidLow() const { return GetDouble("bid_low"); }
double SymbolInfo::Ask() const { return GetDouble("ask"); }
double SymbolInfo::AskHigh() const { return GetDouble("ask_high"); }
double SymbolInfo::AskLow() const { return GetDouble("ask_low"); }
double SymbolInfo::Last() const { return GetDouble("last"); }
double SymbolInfo::LastHigh() const { return GetDouble("last_high"); }
double SymbolInfo::LastLow() const { return GetDouble("last_low"); }
double SymbolInfo::Point() const { return GetDouble("point"); }
double SymbolInfo::TradeTickValue() const {
  return GetDouble("trade_tick_value");
}
double SymbolInfo::TradeTickValueProfit() const {
  return GetDouble("trade_tick_value_profit");
}
double SymbolInfo::TradeTickValueLoss() const {
  return GetDouble("trade_tick_value_loss");
}
double SymbolInfo::TradeTickSize() const {
  return GetDouble("trade_tick_size");
}
double SymbolInfo::TradeContractSize() const {
  return GetDouble("trade_contract_size");
}
double SymbolInfo::TradeAccruedInterest() const {
  return GetDouble("trade_accrued_interest");
}
double SymbolInfo::TradeFaceValue() const {
  return GetDouble("trade_face_value");
}
double SymbolInfo::TradeLiquidityRate() const {
  return GetDouble("trade_liquidity_rate");
}
double SymbolInfo::VolumeMin() const { return GetDouble("volume_min"); }
double SymbolInfo::VolumeMax() const { return GetDouble("volume_max"); }
double SymbolInfo::VolumeStep() const { return GetDouble("volume_step"); }
double SymbolInfo::VolumeLimit() const { return GetDouble("volume_limit"); }
double SymbolInfo::SwapLong() const { return GetDouble("swap_long"); }
double SymbolInfo::SwapShort() const { return GetDouble("swap_short"); }
double SymbolInfo::MarginInitial() const { return GetDouble("margin_initial"); }
double SymbolInfo::MarginMaintenance() const {
  return GetDouble("margin_maintenance");
}
double SymbolInfo::SessionVolume() const { return GetDouble("session_volume"); }
double SymbolInfo::SessionTurnover() const {
  return GetDouble("session_turnover");
}
double SymbolInfo::SessionInterest() const {
  return GetDouble("session_interest");
}
double SymbolInfo::SessionBuyOrdersVolume() const {
  return GetDouble("session_buy_orders_volume");
}
double SymbolInfo::SessionSellOrdersVolume() const {
  return GetDouble("session_sell_orders_volume");
}
double SymbolInfo::SessionOpen() const { return GetDouble("session_open"); }
double SymbolInfo::SessionClose() const { return GetDouble("session_close"); }
double SymbolInfo::SessionAw() const { return GetDouble("session_aw"); }
double SymbolInfo::SessionPriceSettlement() const {
  return GetDouble("session_price_settlement");
}
double SymbolInfo::SessionPriceLimitMin() const {
  return GetDouble("session_price_limit_min");
}
double SymbolInfo::SessionPriceLimitMax() const {
  return GetDouble("session_price_limit_max");
}
double SymbolInfo::MarginHedged() const { return GetDouble("margin_hedged"); }

//--- String properties
std::string SymbolInfo::Path() const { return GetString("path"); }
std::string SymbolInfo::Description() const { return GetString("description"); }
std::string SymbolInfo::Isin() const { return GetString("isin"); }
std::string SymbolInfo::Page() const { return GetString("page"); }
std::string SymbolInfo::CurrencyBase() const {
  return GetString("currency_base");
}
std::string SymbolInfo::CurrencyProfit() const {
  return GetString("currency_profit");
}
std::string SymbolInfo::CurrencyMargin() const {
  return GetString("currency_margin");
}
std::string SymbolInfo::Bank() const { return GetString("bank"); }

//--- Normalized property methods
double SymbolInfo::NormalizePrice(const double price) const {
  long digits = Digits();
  if (digits == 0)
    return price;
  double pt = std::pow(10.0, digits);
  return std::round(price * pt) / pt;
}

} // namespace haruquant::trading
