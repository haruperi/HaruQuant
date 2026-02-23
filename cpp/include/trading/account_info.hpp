#pragma once

#include "core/state.hpp"
#include <string>

namespace haruquant::trading {

class AccountInfo {
private:
  const core::BacktestState *m_state;

protected:
  long GetInteger(const std::string &prop) const;
  double GetDouble(const std::string &prop) const;
  std::string GetString(const std::string &prop) const;

public:
  AccountInfo();
  explicit AccountInfo(const core::BacktestState *state);
  virtual ~AccountInfo() = default;

  void SetState(const core::BacktestState *state);
  const core::BacktestState *GetState() const { return m_state; }

  //--- Integer properties
  long Login() const;
  long TradeMode() const;
  long Leverage() const;
  long LimitOrders() const;
  long MarginMode() const;
  long MarginSoMode() const;
  bool TradeAllowed() const;
  bool TradeExpert() const;
  int MarginInitial() const;     // Typically integer enum in some contexts, but
                                 // usually double in MT5
  int MarginMaintenance() const; // Usually double, but checking MT5 API - they
                                 // are doubles. I will use them as double down
                                 // below to match MT5 ENUM_ACCOUNT_INFO_DOUBLE.

  //--- Double properties
  double Balance() const;
  double Credit() const;
  double Profit() const;
  double Equity() const;
  double Margin() const;
  double MarginFree() const;
  double MarginLevel() const;
  double MarginCall() const;
  double MarginStopOut() const;
  double
  MarginInitialDouble() const; // AccountInfoDouble(ACCOUNT_MARGIN_INITIAL)
  double MarginMaintenanceDouble()
      const; // AccountInfoDouble(ACCOUNT_MARGIN_MAINTENANCE)
  double Assets() const;
  double Liabilities() const;
  double Commissions() const;
  double Blocked() const;

  //--- String properties
  std::string Name() const;
  std::string Server() const;
  std::string Currency() const;
  std::string Company() const;
};

} // namespace haruquant::trading
