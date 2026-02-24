#pragma once

#include "core/state.hpp"
#include <memory>
#include <string>

namespace haruquant::trading {

class DealInfo {
private:
  std::shared_ptr<core::BacktestState> m_state;
  std::string m_ticket;
  core::BacktestState &EnsureState();
  core::BacktestState::Dictionary &EnsureDealRow();

protected:
  long GetInteger(const std::string &prop) const;
  double GetDouble(const std::string &prop) const;
  std::string GetString(const std::string &prop) const;

public:
  DealInfo();
  explicit DealInfo(std::shared_ptr<core::BacktestState> state);
  virtual ~DealInfo() = default;

  void SetState(std::shared_ptr<core::BacktestState> state);
  const core::BacktestState *GetState() const { return m_state.get(); }
  const std::shared_ptr<core::BacktestState> &GetSharedState() const {
    return m_state;
  }

  bool Ticket(const long ticket);

  //--- Integer properties
  long Ticket() const;
  long Order() const;
  long Time() const;
  long TimeMsc() const;
  long Type() const;
  long Entry() const;
  long Magic() const;
  long Reason() const;
  long PositionId() const;

  //--- Double properties
  double Volume() const;
  double Price() const;
  double Commission() const;
  double Swap() const;
  double Profit() const;
  double Fee() const;

  //--- String properties
  std::string Symbol() const;
  std::string Comment() const;
  std::string ExternalId() const;

  //--- Setters
  void SetTicket(long value);
  void SetOrder(long value);
  void SetTime(long value);
  void SetTimeMsc(long value);
  void SetType(long value);
  void SetEntry(long value);
  void SetMagic(long value);
  void SetReason(long value);
  void SetPositionId(long value);

  void SetVolume(double value);
  void SetPrice(double value);
  void SetCommission(double value);
  void SetSwap(double value);
  void SetProfit(double value);
  void SetFee(double value);

  void SetSymbol(const std::string &value);
  void SetComment(const std::string &value);
  void SetExternalId(const std::string &value);
};

} // namespace haruquant::trading
