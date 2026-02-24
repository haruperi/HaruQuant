#include "trading/account_info.hpp"
#include <sstream>
#include <string>

namespace haruquant::trading {

AccountInfo::AccountInfo() : m_state(std::make_shared<core::BacktestState>()) {}

AccountInfo::AccountInfo(std::shared_ptr<core::BacktestState> state)
    : m_state(std::move(state)) {
  EnsureState();
}

void AccountInfo::SetState(std::shared_ptr<core::BacktestState> state) {
  m_state = std::move(state);
  EnsureState();
}

core::BacktestState &AccountInfo::EnsureState() {
  if (!m_state) {
    m_state = std::make_shared<core::BacktestState>();
  }
  return *m_state;
}

long AccountInfo::GetInteger(const std::string &prop) const {
  if (!m_state) return 0;
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
  if (!m_state) return 0.0;
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
  if (!m_state) return "";
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

namespace {
template <typename T>
std::string to_string_value(T value) {
  std::ostringstream oss;
  oss << value;
  return oss.str();
}
} // namespace

void AccountInfo::SetLogin(long value) {
  EnsureState().trading_account["login"] = to_string_value(value);
}
void AccountInfo::SetTradeMode(long value) {
  EnsureState().trading_account["trade_mode"] = to_string_value(value);
}
void AccountInfo::SetLeverage(int value) {
  EnsureState().trading_account["leverage"] = to_string_value(value);
}
void AccountInfo::SetLimitOrders(int value) {
  EnsureState().trading_account["limit_orders"] = to_string_value(value);
}
void AccountInfo::SetMarginMode(long value) {
  EnsureState().trading_account["margin_mode"] = to_string_value(value);
}
void AccountInfo::SetTradeAllowed(bool value) {
  EnsureState().trading_account["trade_allowed"] = value ? "1" : "0";
}
void AccountInfo::SetTradeExpert(bool value) {
  EnsureState().trading_account["trade_expert"] = value ? "1" : "0";
}

void AccountInfo::SetBalance(double value) {
  EnsureState().trading_account["balance"] = to_string_value(value);
}
void AccountInfo::SetCredit(double value) {
  EnsureState().trading_account["credit"] = to_string_value(value);
}
void AccountInfo::SetProfit(double value) {
  EnsureState().trading_account["profit"] = to_string_value(value);
}
void AccountInfo::SetEquity(double value) {
  EnsureState().trading_account["equity"] = to_string_value(value);
}
void AccountInfo::SetMargin(double value) {
  EnsureState().trading_account["margin"] = to_string_value(value);
}
void AccountInfo::SetMarginFree(double value) {
  EnsureState().trading_account["margin_free"] = to_string_value(value);
}
void AccountInfo::SetMarginLevel(double value) {
  EnsureState().trading_account["margin_level"] = to_string_value(value);
}
void AccountInfo::SetMarginCall(double value) {
  EnsureState().trading_account["margin_call"] = to_string_value(value);
}
void AccountInfo::SetMarginStopOut(double value) {
  EnsureState().trading_account["margin_stop_out"] = to_string_value(value);
}

void AccountInfo::SetName(const std::string &value) {
  EnsureState().trading_account["name"] = value;
}
void AccountInfo::SetServer(const std::string &value) {
  EnsureState().trading_account["server"] = value;
}
void AccountInfo::SetCurrency(const std::string &value) {
  EnsureState().trading_account["currency"] = value;
}
void AccountInfo::SetCompany(const std::string &value) {
  EnsureState().trading_account["company"] = value;
}

} // namespace haruquant::trading
