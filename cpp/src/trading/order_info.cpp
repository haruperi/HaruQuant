#include "trading/order_info.hpp"
#include <sstream>
#include <string>

namespace haruquant::trading {

OrderInfo::OrderInfo() : m_state(std::make_shared<core::BacktestState>()), m_ticket("") {}

OrderInfo::OrderInfo(std::shared_ptr<core::BacktestState> state)
    : m_state(std::move(state)), m_ticket("") {
  EnsureState();
}

void OrderInfo::SetState(std::shared_ptr<core::BacktestState> state) {
  m_state = std::move(state);
  EnsureState();
}

core::BacktestState &OrderInfo::EnsureState() {
  if (!m_state) {
    m_state = std::make_shared<core::BacktestState>();
  }
  return *m_state;
}

core::BacktestState::Dictionary &OrderInfo::EnsureRow() {
  auto &state = EnsureState();
  if (m_ticket.empty()) {
    m_ticket = "0";
  }
  return state.trading_orders[m_ticket];
}

bool OrderInfo::Select(const long ticket) {
  if (!m_state)
    return false;
  std::string t_str = std::to_string(ticket);
  auto it = m_state->trading_orders.find(t_str);
  if (it != m_state->trading_orders.end()) {
    m_ticket = t_str;
    return true;
  }
  return false;
}

bool OrderInfo::SelectByIndex(const int index) {
  // Requires a sorted or indexable array. In unordered_map this is
  // non-deterministic unless iterating, but standard map ordering is arbitrary.
  // If indices are exactly 0..N-1 we could iterate, but it's an O(N) operation
  // and arbitrary. Implement loosely as N-th item in iteration for
  // compatibility, but recommend Select()
  if (!m_state || index < 0)
    return false;

  int i = 0;
  for (const auto &kv : m_state->trading_orders) {
    if (i == index) {
      m_ticket = kv.first;
      return true;
    }
    i++;
  }
  return false;
}

long OrderInfo::GetInteger(const std::string &prop) const {
  if (!m_state || m_ticket.empty())
    return 0;

  auto t_it = m_state->trading_orders.find(m_ticket);
  if (t_it != m_state->trading_orders.end()) {
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

double OrderInfo::GetDouble(const std::string &prop) const {
  if (!m_state || m_ticket.empty())
    return 0.0;

  auto t_it = m_state->trading_orders.find(m_ticket);
  if (t_it != m_state->trading_orders.end()) {
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

std::string OrderInfo::GetString(const std::string &prop) const {
  if (!m_state || m_ticket.empty())
    return "";

  auto t_it = m_state->trading_orders.find(m_ticket);
  if (t_it != m_state->trading_orders.end()) {
    auto p_it = t_it->second.find(prop);
    if (p_it != t_it->second.end()) {
      return p_it->second;
    }
  }
  return "";
}

//--- Integer properties
long OrderInfo::Ticket() const { return GetInteger("ticket"); }
long OrderInfo::TimeSetup() const { return GetInteger("time_setup"); }
long OrderInfo::TimeSetupMsc() const { return GetInteger("time_setup_msc"); }
long OrderInfo::TimeDone() const { return GetInteger("time_done"); }
long OrderInfo::TimeDoneMsc() const { return GetInteger("time_done_msc"); }
long OrderInfo::TimeExpiration() const { return GetInteger("time_expiration"); }
long OrderInfo::Type() const { return GetInteger("type"); }
long OrderInfo::TypeTime() const { return GetInteger("type_time"); }
long OrderInfo::TypeFilling() const { return GetInteger("type_filling"); }
long OrderInfo::State() const { return GetInteger("state"); }
long OrderInfo::Magic() const { return GetInteger("magic"); }
long OrderInfo::Reason() const { return GetInteger("reason"); }
long OrderInfo::PositionId() const { return GetInteger("position_id"); }
long OrderInfo::PositionById() const { return GetInteger("position_by_id"); }

//--- Double properties
double OrderInfo::VolumeInitial() const { return GetDouble("volume_initial"); }
double OrderInfo::VolumeCurrent() const { return GetDouble("volume_current"); }
double OrderInfo::PriceOpen() const { return GetDouble("price_open"); }
double OrderInfo::Sl() const { return GetDouble("sl"); }
double OrderInfo::Tp() const { return GetDouble("tp"); }
double OrderInfo::PriceCurrent() const { return GetDouble("price_current"); }
double OrderInfo::PriceStopLimit() const {
  return GetDouble("price_stoplimit");
}

//--- String properties
std::string OrderInfo::Symbol() const { return GetString("symbol"); }
std::string OrderInfo::Comment() const { return GetString("comment"); }
std::string OrderInfo::ExternalId() const { return GetString("external_id"); }

namespace {
template <typename T>
std::string to_string_value(T value) {
  std::ostringstream oss;
  oss << value;
  return oss.str();
}
} // namespace

void OrderInfo::SetTicket(long value) {
  m_ticket = std::to_string(value);
  EnsureRow()["ticket"] = m_ticket;
}
void OrderInfo::SetTimeSetup(long value) {
  EnsureRow()["time_setup"] = to_string_value(value);
}
void OrderInfo::SetTimeSetupMsc(long value) {
  EnsureRow()["time_setup_msc"] = to_string_value(value);
}
void OrderInfo::SetTimeDone(long value) {
  EnsureRow()["time_done"] = to_string_value(value);
}
void OrderInfo::SetTimeDoneMsc(long value) {
  EnsureRow()["time_done_msc"] = to_string_value(value);
}
void OrderInfo::SetTimeExpiration(long value) {
  EnsureRow()["time_expiration"] = to_string_value(value);
}
void OrderInfo::SetType(long value) {
  EnsureRow()["type"] = to_string_value(value);
}
void OrderInfo::SetTypeTime(long value) {
  EnsureRow()["type_time"] = to_string_value(value);
}
void OrderInfo::SetTypeFilling(long value) {
  EnsureRow()["type_filling"] = to_string_value(value);
}
void OrderInfo::SetStateValue(long value) {
  EnsureRow()["state"] = to_string_value(value);
}
void OrderInfo::SetMagic(long value) {
  EnsureRow()["magic"] = to_string_value(value);
}
void OrderInfo::SetReason(long value) {
  EnsureRow()["reason"] = to_string_value(value);
}
void OrderInfo::SetPositionId(long value) {
  EnsureRow()["position_id"] = to_string_value(value);
}
void OrderInfo::SetPositionById(long value) {
  EnsureRow()["position_by_id"] = to_string_value(value);
}

void OrderInfo::SetVolumeInitial(double value) {
  EnsureRow()["volume_initial"] = to_string_value(value);
}
void OrderInfo::SetVolumeCurrent(double value) {
  EnsureRow()["volume_current"] = to_string_value(value);
}
void OrderInfo::SetPriceOpen(double value) {
  EnsureRow()["price_open"] = to_string_value(value);
}
void OrderInfo::SetSl(double value) {
  EnsureRow()["sl"] = to_string_value(value);
}
void OrderInfo::SetTp(double value) {
  EnsureRow()["tp"] = to_string_value(value);
}
void OrderInfo::SetPriceCurrent(double value) {
  EnsureRow()["price_current"] = to_string_value(value);
}
void OrderInfo::SetPriceStopLimit(double value) {
  EnsureRow()["price_stoplimit"] = to_string_value(value);
}

void OrderInfo::SetSymbol(const std::string &value) {
  EnsureRow()["symbol"] = value;
}
void OrderInfo::SetComment(const std::string &value) {
  EnsureRow()["comment"] = value;
}
void OrderInfo::SetExternalId(const std::string &value) {
  EnsureRow()["external_id"] = value;
}

} // namespace haruquant::trading
