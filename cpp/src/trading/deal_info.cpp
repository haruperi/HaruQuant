#include "trading/deal_info.hpp"
#include <stdexcept>
#include <string>

namespace haruquant::trading {

DealInfo::DealInfo() : m_state(nullptr), m_ticket("") {}

DealInfo::DealInfo(const core::BacktestState *state)
    : m_state(state), m_ticket("") {}

void DealInfo::SetState(const core::BacktestState *state) { m_state = state; }

bool DealInfo::Ticket(const long ticket) {
  if (!m_state)
    return false;
  std::string t_str = std::to_string(ticket);
  auto it = m_state->trading_deals.find(t_str);
  if (it != m_state->trading_deals.end()) {
    m_ticket = t_str;
    return true;
  }
  return false;
}

long DealInfo::GetInteger(const std::string &prop) const {
  if (!m_state || m_ticket.empty())
    return 0;

  auto t_it = m_state->trading_deals.find(m_ticket);
  if (t_it != m_state->trading_deals.end()) {
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

double DealInfo::GetDouble(const std::string &prop) const {
  if (!m_state || m_ticket.empty())
    return 0.0;

  auto t_it = m_state->trading_deals.find(m_ticket);
  if (t_it != m_state->trading_deals.end()) {
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

std::string DealInfo::GetString(const std::string &prop) const {
  if (!m_state || m_ticket.empty())
    return "";

  auto t_it = m_state->trading_deals.find(m_ticket);
  if (t_it != m_state->trading_deals.end()) {
    auto p_it = t_it->second.find(prop);
    if (p_it != t_it->second.end()) {
      return p_it->second;
    }
  }
  return "";
}

//--- Integer properties
long DealInfo::Ticket() const { return GetInteger("ticket"); }
long DealInfo::Order() const { return GetInteger("order"); }
long DealInfo::Time() const { return GetInteger("time"); }
long DealInfo::TimeMsc() const { return GetInteger("time_msc"); }
long DealInfo::Type() const { return GetInteger("type"); }
long DealInfo::Entry() const { return GetInteger("entry"); }
long DealInfo::Magic() const { return GetInteger("magic"); }
long DealInfo::Reason() const { return GetInteger("reason"); }
long DealInfo::PositionId() const { return GetInteger("position_id"); }

//--- Double properties
double DealInfo::Volume() const { return GetDouble("volume"); }
double DealInfo::Price() const { return GetDouble("price"); }
double DealInfo::Commission() const { return GetDouble("commission"); }
double DealInfo::Swap() const { return GetDouble("swap"); }
double DealInfo::Profit() const { return GetDouble("profit"); }
double DealInfo::Fee() const { return GetDouble("fee"); }

//--- String properties
std::string DealInfo::Symbol() const { return GetString("symbol"); }
std::string DealInfo::Comment() const { return GetString("comment"); }
std::string DealInfo::ExternalId() const { return GetString("external_id"); }

} // namespace haruquant::trading
