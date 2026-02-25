#include "trading/symbol_info.hpp"
#include <cmath>
#include <sstream>
#include <string>

namespace haruquant::trading {

SymbolInfo::SymbolInfo() : m_state(std::make_shared<core::BacktestState>()), m_name("") {}

SymbolInfo::SymbolInfo(std::shared_ptr<core::BacktestState> state)
    : m_state(std::move(state)), m_name("") {
  EnsureState();
}

void SymbolInfo::SetState(std::shared_ptr<core::BacktestState> state) {
  m_state = std::move(state);
  EnsureState();
}

core::BacktestState &SymbolInfo::EnsureState() {
  if (!m_state) {
    m_state = std::make_shared<core::BacktestState>();
  }
  return *m_state;
}

core::BacktestState::Dictionary &SymbolInfo::EnsureRow() {
  auto &state = EnsureState();
  if (m_name.empty()) {
    m_name = "UNKNOWN";
  }
  return state.trading_symbols[m_name];
}

void SymbolInfo::SetIntegerProperty(const std::string &prop, long value) {
  std::ostringstream oss;
  oss << value;
  EnsureRow()[prop] = oss.str();
}

void SymbolInfo::SetDoubleProperty(const std::string &prop, double value) {
  std::ostringstream oss;
  oss << value;
  EnsureRow()[prop] = oss.str();
}

void SymbolInfo::SetStringProperty(const std::string &prop,
                                   const std::string &value) {
  EnsureRow()[prop] = value;
}

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
  const_cast<SymbolInfo *>(this)->SetSelect(select);
  return Select();
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

bool SymbolInfo::AddSymbol(const SymbolInfo &source) {
  const std::string source_name = source.Name();
  const auto *source_state = source.GetState();
  if (!source_state || source_name.empty()) {
    return false;
  }

  const auto it = source_state->trading_symbols.find(source_name);
  if (it == source_state->trading_symbols.end()) {
    return false;
  }

  m_name = source_name;
  EnsureState().trading_symbols[source_name] = it->second;
  return true;
}

//--- Setters
void SymbolInfo::SetSelect(bool value) {
  SetIntegerProperty("select", value ? 1 : 0);
}
void SymbolInfo::SetVisible(bool value) {
  SetIntegerProperty("visible", value ? 1 : 0);
}
void SymbolInfo::SetVolume(long value) { SetIntegerProperty("volume", value); }
void SymbolInfo::SetVolumeHigh(long value) {
  SetIntegerProperty("volume_high", value);
}
void SymbolInfo::SetVolumeLow(long value) {
  SetIntegerProperty("volume_low", value);
}
void SymbolInfo::SetTime(long value) { SetIntegerProperty("time", value); }
void SymbolInfo::SetDigits(long value) { SetIntegerProperty("digits", value); }
void SymbolInfo::SetSpread(long value) { SetIntegerProperty("spread", value); }
void SymbolInfo::SetSpreadFloat(bool value) {
  SetIntegerProperty("spread_float", value ? 1 : 0);
}
void SymbolInfo::SetTradeCalcMode(long value) {
  SetIntegerProperty("trade_calc_mode", value);
}
void SymbolInfo::SetTradeMode(long value) {
  SetIntegerProperty("trade_mode", value);
}
void SymbolInfo::SetTradeExemode(long value) {
  SetIntegerProperty("trade_exemode", value);
}
void SymbolInfo::SetTradeStopsLevel(long value) {
  SetIntegerProperty("trade_stops_level", value);
}
void SymbolInfo::SetTradeFreezeLevel(long value) {
  SetIntegerProperty("trade_freeze_level", value);
}
void SymbolInfo::SetSwapMode(long value) {
  SetIntegerProperty("swap_mode", value);
}
void SymbolInfo::SetSwapRollover3days(long value) {
  SetIntegerProperty("swap_rollover3days", value);
}

void SymbolInfo::SetBid(double value) { SetDoubleProperty("bid", value); }
void SymbolInfo::SetBidHigh(double value) { SetDoubleProperty("bid_high", value); }
void SymbolInfo::SetBidLow(double value) { SetDoubleProperty("bid_low", value); }
void SymbolInfo::SetAsk(double value) { SetDoubleProperty("ask", value); }
void SymbolInfo::SetAskHigh(double value) { SetDoubleProperty("ask_high", value); }
void SymbolInfo::SetAskLow(double value) { SetDoubleProperty("ask_low", value); }
void SymbolInfo::SetLast(double value) { SetDoubleProperty("last", value); }
void SymbolInfo::SetLastHigh(double value) { SetDoubleProperty("last_high", value); }
void SymbolInfo::SetLastLow(double value) { SetDoubleProperty("last_low", value); }
void SymbolInfo::SetPoint(double value) { SetDoubleProperty("point", value); }
void SymbolInfo::SetTradeTickValue(double value) {
  SetDoubleProperty("trade_tick_value", value);
}
void SymbolInfo::SetTradeTickValueProfit(double value) {
  SetDoubleProperty("trade_tick_value_profit", value);
}
void SymbolInfo::SetTradeTickValueLoss(double value) {
  SetDoubleProperty("trade_tick_value_loss", value);
}
void SymbolInfo::SetTradeTickSize(double value) {
  SetDoubleProperty("trade_tick_size", value);
}
void SymbolInfo::SetTradeContractSize(double value) {
  SetDoubleProperty("trade_contract_size", value);
}
void SymbolInfo::SetVolumeMin(double value) {
  SetDoubleProperty("volume_min", value);
}
void SymbolInfo::SetVolumeMax(double value) {
  SetDoubleProperty("volume_max", value);
}
void SymbolInfo::SetVolumeStep(double value) {
  SetDoubleProperty("volume_step", value);
}
void SymbolInfo::SetVolumeLimit(double value) {
  SetDoubleProperty("volume_limit", value);
}
void SymbolInfo::SetSwapLong(double value) {
  SetDoubleProperty("swap_long", value);
}
void SymbolInfo::SetSwapShort(double value) {
  SetDoubleProperty("swap_short", value);
}
void SymbolInfo::SetMarginInitial(double value) {
  SetDoubleProperty("margin_initial", value);
}
void SymbolInfo::SetMarginMaintenance(double value) {
  SetDoubleProperty("margin_maintenance", value);
}

void SymbolInfo::SetPath(const std::string &value) {
  SetStringProperty("path", value);
}
void SymbolInfo::SetDescription(const std::string &value) {
  SetStringProperty("description", value);
}
void SymbolInfo::SetCurrencyBase(const std::string &value) {
  SetStringProperty("currency_base", value);
}
void SymbolInfo::SetCurrencyProfit(const std::string &value) {
  SetStringProperty("currency_profit", value);
}
void SymbolInfo::SetCurrencyMargin(const std::string &value) {
  SetStringProperty("currency_margin", value);
}

} // namespace haruquant::trading
