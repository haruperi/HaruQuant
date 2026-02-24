#include "trading/deal_info.hpp"
#include <sstream>
#include <string>

namespace haruquant::trading {

DealInfo::DealInfo() : m_state(std::make_shared<core::BacktestState>()), m_ticket("") {}

DealInfo::DealInfo(std::shared_ptr<core::BacktestState> state)
    : m_state(std::move(state)), m_ticket("") {
  EnsureState();
}

void DealInfo::SetState(std::shared_ptr<core::BacktestState> state) {
  m_state = std::move(state);
  EnsureState();
}

core::BacktestState &DealInfo::EnsureState() {
  if (!m_state) {
    m_state = std::make_shared<core::BacktestState>();
  }
  return *m_state;
}

core::BacktestState::Dictionary &DealInfo::EnsureDealRow() {
  auto &state = EnsureState();
  if (m_ticket.empty()) {
    m_ticket = "0";
  }
  return state.trading_deals[m_ticket];
}

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

namespace {
template <typename T>
std::string to_string_value(T value) {
  std::ostringstream oss;
  oss << value;
  return oss.str();
}
} // namespace

void DealInfo::SetTicket(long value) {
  m_ticket = std::to_string(value);
  EnsureDealRow()["ticket"] = m_ticket;
}
void DealInfo::SetOrder(long value) {
  EnsureDealRow()["order"] = to_string_value(value);
}
void DealInfo::SetTime(long value) {
  EnsureDealRow()["time"] = to_string_value(value);
}
void DealInfo::SetTimeMsc(long value) {
  EnsureDealRow()["time_msc"] = to_string_value(value);
}
void DealInfo::SetType(long value) {
  EnsureDealRow()["type"] = to_string_value(value);
}
void DealInfo::SetEntry(long value) {
  EnsureDealRow()["entry"] = to_string_value(value);
}
void DealInfo::SetMagic(long value) {
  EnsureDealRow()["magic"] = to_string_value(value);
}
void DealInfo::SetReason(long value) {
  EnsureDealRow()["reason"] = to_string_value(value);
}
void DealInfo::SetPositionId(long value) {
  EnsureDealRow()["position_id"] = to_string_value(value);
}

void DealInfo::SetVolume(double value) {
  EnsureDealRow()["volume"] = to_string_value(value);
}
void DealInfo::SetPrice(double value) {
  EnsureDealRow()["price"] = to_string_value(value);
}
void DealInfo::SetCommission(double value) {
  EnsureDealRow()["commission"] = to_string_value(value);
}
void DealInfo::SetSwap(double value) {
  EnsureDealRow()["swap"] = to_string_value(value);
}
void DealInfo::SetProfit(double value) {
  EnsureDealRow()["profit"] = to_string_value(value);
}
void DealInfo::SetFee(double value) {
  EnsureDealRow()["fee"] = to_string_value(value);
}

void DealInfo::SetSymbol(const std::string &value) {
  EnsureDealRow()["symbol"] = value;
}
void DealInfo::SetComment(const std::string &value) {
  EnsureDealRow()["comment"] = value;
}
void DealInfo::SetExternalId(const std::string &value) {
  EnsureDealRow()["external_id"] = value;
}

} // namespace haruquant::trading
