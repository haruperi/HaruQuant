#include "trading/history_order_info.hpp"
#include <sstream>
#include <string>

namespace haruquant::trading {

HistoryOrderInfo::HistoryOrderInfo()
    : m_state(std::make_shared<core::BacktestState>()), m_ticket("") {}

HistoryOrderInfo::HistoryOrderInfo(std::shared_ptr<core::BacktestState> state)
    : m_state(std::move(state)), m_ticket("") {
  EnsureState();
}

void HistoryOrderInfo::SetState(std::shared_ptr<core::BacktestState> state) {
  m_state = std::move(state);
  EnsureState();
}

core::BacktestState &HistoryOrderInfo::EnsureState() {
  if (!m_state) {
    m_state = std::make_shared<core::BacktestState>();
  }
  return *m_state;
}

core::BacktestState::Dictionary &HistoryOrderInfo::EnsureRow() {
  auto &state = EnsureState();
  if (m_ticket.empty()) {
    m_ticket = "0";
  }
  return state.trading_history_orders[m_ticket];
}

bool HistoryOrderInfo::Ticket(const long ticket) {
  if (!m_state)
    return false;
  std::string t_str = std::to_string(ticket);
  auto it = m_state->trading_history_orders.find(t_str);
  if (it != m_state->trading_history_orders.end()) {
    m_ticket = t_str;
    return true;
  }
  return false;
}

long HistoryOrderInfo::GetInteger(const std::string &prop) const {
  if (!m_state || m_ticket.empty())
    return 0;

  auto t_it = m_state->trading_history_orders.find(m_ticket);
  if (t_it != m_state->trading_history_orders.end()) {
    auto p_it = t_it->second.find(prop);
    if (p_it != t_it->second.end()) {
      try {
        return static_cast<long>(std::stoll(p_it->second));
      } catch (...) {
        return 0;
      }
    }
  }
  return 0;
}

double HistoryOrderInfo::GetDouble(const std::string &prop) const {
  if (!m_state || m_ticket.empty())
    return 0.0;

  auto t_it = m_state->trading_history_orders.find(m_ticket);
  if (t_it != m_state->trading_history_orders.end()) {
    auto p_it = t_it->second.find(prop);
    if (p_it != t_it->second.end()) {
      try {
        return std::stod(p_it->second);
      } catch (...) {
        return 0.0;
      }
    }
  }
  return 0.0;
}

std::string HistoryOrderInfo::GetString(const std::string &prop) const {
  if (!m_state || m_ticket.empty())
    return "";

  auto t_it = m_state->trading_history_orders.find(m_ticket);
  if (t_it != m_state->trading_history_orders.end()) {
    auto p_it = t_it->second.find(prop);
    if (p_it != t_it->second.end()) {
      return p_it->second;
    }
  }
  return "";
}

//--- Integer properties
long HistoryOrderInfo::Ticket() const { return GetInteger("ticket"); }
long HistoryOrderInfo::TimeSetup() const { return GetInteger("time_setup"); }
long HistoryOrderInfo::TimeSetupMsc() const {
  return GetInteger("time_setup_msc");
}
long HistoryOrderInfo::TimeDone() const { return GetInteger("time_done"); }
long HistoryOrderInfo::TimeDoneMsc() const {
  return GetInteger("time_done_msc");
}
long HistoryOrderInfo::TimeExpiration() const {
  return GetInteger("time_expiration");
}
long HistoryOrderInfo::Type() const { return GetInteger("type"); }
long HistoryOrderInfo::TypeTime() const { return GetInteger("type_time"); }
long HistoryOrderInfo::TypeFilling() const {
  return GetInteger("type_filling");
}
long HistoryOrderInfo::State() const { return GetInteger("state"); }
long HistoryOrderInfo::Magic() const { return GetInteger("magic"); }
long HistoryOrderInfo::Reason() const { return GetInteger("reason"); }
long HistoryOrderInfo::PositionId() const { return GetInteger("position_id"); }

//--- Double properties
double HistoryOrderInfo::VolumeInitial() const {
  return GetDouble("volume_initial");
}
double HistoryOrderInfo::VolumeCurrent() const {
  return GetDouble("volume_current");
}
double HistoryOrderInfo::PriceOpen() const { return GetDouble("price_open"); }
double HistoryOrderInfo::Sl() const { return GetDouble("sl"); }
double HistoryOrderInfo::Tp() const { return GetDouble("tp"); }
double HistoryOrderInfo::PriceCurrent() const {
  return GetDouble("price_current");
}
double HistoryOrderInfo::PriceStopLimit() const {
  return GetDouble("price_stoplimit");
}

//--- String properties
std::string HistoryOrderInfo::Symbol() const { return GetString("symbol"); }
std::string HistoryOrderInfo::Comment() const { return GetString("comment"); }
std::string HistoryOrderInfo::ExternalId() const {
  return GetString("external_id");
}

namespace {
template <typename T>
std::string to_string_value(T value) {
  std::ostringstream oss;
  oss << value;
  return oss.str();
}
} // namespace

void HistoryOrderInfo::SetTicket(long value) {
  m_ticket = std::to_string(value);
  EnsureRow()["ticket"] = m_ticket;
}
void HistoryOrderInfo::SetTimeSetup(long value) {
  EnsureRow()["time_setup"] = to_string_value(value);
}
void HistoryOrderInfo::SetTimeSetupMsc(long value) {
  EnsureRow()["time_setup_msc"] = to_string_value(value);
}
void HistoryOrderInfo::SetTimeDone(long value) {
  EnsureRow()["time_done"] = to_string_value(value);
}
void HistoryOrderInfo::SetTimeDoneMsc(long value) {
  EnsureRow()["time_done_msc"] = to_string_value(value);
}
void HistoryOrderInfo::SetTimeExpiration(long value) {
  EnsureRow()["time_expiration"] = to_string_value(value);
}
void HistoryOrderInfo::SetType(long value) {
  EnsureRow()["type"] = to_string_value(value);
}
void HistoryOrderInfo::SetTypeTime(long value) {
  EnsureRow()["type_time"] = to_string_value(value);
}
void HistoryOrderInfo::SetTypeFilling(long value) {
  EnsureRow()["type_filling"] = to_string_value(value);
}
void HistoryOrderInfo::SetStateValue(long value) {
  EnsureRow()["state"] = to_string_value(value);
}
void HistoryOrderInfo::SetMagic(long value) {
  EnsureRow()["magic"] = to_string_value(value);
}
void HistoryOrderInfo::SetReason(long value) {
  EnsureRow()["reason"] = to_string_value(value);
}
void HistoryOrderInfo::SetPositionId(long value) {
  EnsureRow()["position_id"] = to_string_value(value);
}

void HistoryOrderInfo::SetVolumeInitial(double value) {
  EnsureRow()["volume_initial"] = to_string_value(value);
}
void HistoryOrderInfo::SetVolumeCurrent(double value) {
  EnsureRow()["volume_current"] = to_string_value(value);
}
void HistoryOrderInfo::SetPriceOpen(double value) {
  EnsureRow()["price_open"] = to_string_value(value);
}
void HistoryOrderInfo::SetSl(double value) {
  EnsureRow()["sl"] = to_string_value(value);
}
void HistoryOrderInfo::SetTp(double value) {
  EnsureRow()["tp"] = to_string_value(value);
}
void HistoryOrderInfo::SetPriceCurrent(double value) {
  EnsureRow()["price_current"] = to_string_value(value);
}
void HistoryOrderInfo::SetPriceStopLimit(double value) {
  EnsureRow()["price_stoplimit"] = to_string_value(value);
}

void HistoryOrderInfo::SetSymbol(const std::string &value) {
  EnsureRow()["symbol"] = value;
}
void HistoryOrderInfo::SetComment(const std::string &value) {
  EnsureRow()["comment"] = value;
}
void HistoryOrderInfo::SetExternalId(const std::string &value) {
  EnsureRow()["external_id"] = value;
}

} // namespace haruquant::trading
