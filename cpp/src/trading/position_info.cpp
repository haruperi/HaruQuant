#include "trading/position_info.hpp"
#include <stdexcept>
#include <string>

namespace haruquant::trading {

PositionInfo::PositionInfo() : m_state(nullptr), m_symbol("") {}

PositionInfo::PositionInfo(const core::BacktestState *state)
    : m_state(state), m_symbol("") {}

void PositionInfo::SetState(const core::BacktestState *state) {
  m_state = state;
}

bool PositionInfo::Select(const std::string &symbol) {
  if (!m_state)
    return false;
  auto it = m_state->trading_positions.find(symbol);
  if (it != m_state->trading_positions.end()) {
    m_symbol = symbol;
    return true;
  }
  return false;
}

bool PositionInfo::SelectByTicket(const long ticket) {
  if (!m_state)
    return false;
  std::string t_str = std::to_string(ticket);
  for (const auto &kv : m_state->trading_positions) {
    auto it = kv.second.find("ticket");
    if (it != kv.second.end() && it->second == t_str) {
      m_symbol =
          kv.first; // Dictionary key is typically symbol, but MT5 supports
                    // multiple positions per symbol in hedged mode. Assuming
                    // symbol as key for now based on context.
      return true;
    }
  }
  return false;
}

bool PositionInfo::SelectByIndex(const int index) {
  if (!m_state || index < 0)
    return false;

  int i = 0;
  for (const auto &kv : m_state->trading_positions) {
    if (i == index) {
      m_symbol = kv.first;
      return true;
    }
    i++;
  }
  return false;
}

long PositionInfo::GetInteger(const std::string &prop) const {
  if (!m_state || m_symbol.empty())
    return 0;

  auto t_it = m_state->trading_positions.find(m_symbol);
  if (t_it != m_state->trading_positions.end()) {
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

double PositionInfo::GetDouble(const std::string &prop) const {
  if (!m_state || m_symbol.empty())
    return 0.0;

  auto t_it = m_state->trading_positions.find(m_symbol);
  if (t_it != m_state->trading_positions.end()) {
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

std::string PositionInfo::GetString(const std::string &prop) const {
  if (!m_state || m_symbol.empty())
    return "";

  auto t_it = m_state->trading_positions.find(m_symbol);
  if (t_it != m_state->trading_positions.end()) {
    auto p_it = t_it->second.find(prop);
    if (p_it != t_it->second.end()) {
      return p_it->second;
    }
  }
  return "";
}

//--- Integer properties
long PositionInfo::Ticket() const { return GetInteger("ticket"); }
long PositionInfo::Time() const { return GetInteger("time"); }
long PositionInfo::TimeMsc() const { return GetInteger("time_msc"); }
long PositionInfo::TimeUpdate() const { return GetInteger("time_update"); }
long PositionInfo::TimeUpdateMsc() const {
  return GetInteger("time_update_msc");
}
long PositionInfo::Type() const { return GetInteger("type"); }
long PositionInfo::Magic() const { return GetInteger("magic"); }
long PositionInfo::Identifier() const { return GetInteger("identifier"); }
long PositionInfo::Reason() const { return GetInteger("reason"); }

//--- Double properties
double PositionInfo::Volume() const { return GetDouble("volume"); }
double PositionInfo::PriceOpen() const { return GetDouble("price_open"); }
double PositionInfo::Sl() const { return GetDouble("sl"); }
double PositionInfo::Tp() const { return GetDouble("tp"); }
double PositionInfo::PriceCurrent() const { return GetDouble("price_current"); }
double PositionInfo::Swap() const { return GetDouble("swap"); }
double PositionInfo::Profit() const { return GetDouble("profit"); }

//--- String properties
std::string PositionInfo::Symbol() const { return GetString("symbol"); }
std::string PositionInfo::Comment() const { return GetString("comment"); }
std::string PositionInfo::ExternalId() const {
  return GetString("external_id");
}

} // namespace haruquant::trading
