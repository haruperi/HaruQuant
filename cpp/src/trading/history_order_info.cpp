#include "trading/history_order_info.hpp"
#include <stdexcept>
#include <string>

namespace haruquant::trading {

HistoryOrderInfo::HistoryOrderInfo() : m_state(nullptr), m_ticket("") {}

HistoryOrderInfo::HistoryOrderInfo(const core::BacktestState *state)
    : m_state(state), m_ticket("") {}

void HistoryOrderInfo::SetState(const core::BacktestState *state) {
  m_state = state;
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

} // namespace haruquant::trading
