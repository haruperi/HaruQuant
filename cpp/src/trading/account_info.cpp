#include "trading/account_info.hpp"
#include <stdexcept>
#include <string>

namespace haruquant::trading {

AccountInfo::AccountInfo() : m_state(nullptr) {}

AccountInfo::AccountInfo(const core::BacktestState *state) : m_state(state) {}

void AccountInfo::SetState(const core::BacktestState *state) {
  m_state = state;
}

long AccountInfo::GetInteger(const std::string &prop) const {
  if (!m_state)
    return 0;
  auto it = m_state->trading_account.find(prop);
  if (it != m_state->trading_account.end()) {
    try {
      return static_cast<long>(std::stoll(it->second));
    } catch (...) {
      return 0;
    }
  }
  return 0;
}

double AccountInfo::GetDouble(const std::string &prop) const {
  if (!m_state)
    return 0.0;
  auto it = m_state->trading_account.find(prop);
  if (it != m_state->trading_account.end()) {
    try {
      return std::stod(it->second);
    } catch (...) {
      return 0.0;
    }
  }
  return 0.0;
}

std::string AccountInfo::GetString(const std::string &prop) const {
  if (!m_state)
    return "";
  auto it = m_state->trading_account.find(prop);
  if (it != m_state->trading_account.end()) {
    return it->second;
  }
  return "";
}

//--- Integer properties
long AccountInfo::Login() const { return GetInteger("login"); }
long AccountInfo::TradeMode() const { return GetInteger("trade_mode"); }
long AccountInfo::Leverage() const { return GetInteger("leverage"); }
long AccountInfo::LimitOrders() const { return GetInteger("limit_orders"); }
long AccountInfo::MarginMode() const { return GetInteger("margin_mode"); }
long AccountInfo::MarginSoMode() const { return GetInteger("margin_so_mode"); }
bool AccountInfo::TradeAllowed() const {
  return GetInteger("trade_allowed") != 0;
}
bool AccountInfo::TradeExpert() const {
  return GetInteger("trade_expert") != 0;
}

//--- Double properties
double AccountInfo::Balance() const { return GetDouble("balance"); }
double AccountInfo::Credit() const { return GetDouble("credit"); }
double AccountInfo::Profit() const { return GetDouble("profit"); }
double AccountInfo::Equity() const { return GetDouble("equity"); }
double AccountInfo::Margin() const { return GetDouble("margin"); }
double AccountInfo::MarginFree() const { return GetDouble("margin_free"); }
double AccountInfo::MarginLevel() const { return GetDouble("margin_level"); }
double AccountInfo::MarginCall() const { return GetDouble("margin_call"); }
double AccountInfo::MarginStopOut() const {
  return GetDouble("margin_stop_out");
}
double AccountInfo::MarginInitialDouble() const {
  return GetDouble("margin_initial");
}
double AccountInfo::MarginMaintenanceDouble() const {
  return GetDouble("margin_maintenance");
}
double AccountInfo::Assets() const { return GetDouble("assets"); }
double AccountInfo::Liabilities() const { return GetDouble("liabilities"); }
double AccountInfo::Commissions() const { return GetDouble("commissions"); }
double AccountInfo::Blocked() const { return GetDouble("blocked"); }

//--- String properties
std::string AccountInfo::Name() const { return GetString("name"); }
std::string AccountInfo::Server() const { return GetString("server"); }
std::string AccountInfo::Currency() const { return GetString("currency"); }
std::string AccountInfo::Company() const { return GetString("company"); }

} // namespace haruquant::trading
