#pragma once

#include "core/state.hpp"
#include <memory>
#include <string>

namespace haruquant::trading {

class AccountInfo {
private:
  std::shared_ptr<core::BacktestState> m_state;
  core::BacktestState &EnsureState();

protected:
  long GetInteger(const std::string &prop) const;
  double GetDouble(const std::string &prop) const;
  std::string GetString(const std::string &prop) const;

public:
  AccountInfo();
  explicit AccountInfo(std::shared_ptr<core::BacktestState> state);
  virtual ~AccountInfo() = default;

  void SetState(std::shared_ptr<core::BacktestState> state);
  const core::BacktestState *GetState() const { return m_state.get(); }
  const std::shared_ptr<core::BacktestState> &GetSharedState() const {
    return m_state;
  }

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

  //--- Setters for snapshot-style initialization from Python/bridge.
  void SetLogin(long value);
  void SetTradeMode(long value);
  void SetLeverage(int value);
  void SetLimitOrders(int value);
  void SetMarginMode(long value);
  void SetTradeAllowed(bool value);
  void SetTradeExpert(bool value);

  void SetBalance(double value);
  void SetCredit(double value);
  void SetProfit(double value);
  void SetEquity(double value);
  void SetMargin(double value);
  void SetMarginFree(double value);
  void SetMarginLevel(double value);
  void SetMarginCall(double value);
  void SetMarginStopOut(double value);

  void SetName(const std::string &value);
  void SetServer(const std::string &value);
  void SetCurrency(const std::string &value);
  void SetCompany(const std::string &value);
};

} // namespace haruquant::trading
