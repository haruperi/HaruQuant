#pragma once

#include "core/state.hpp"
#include <string>

namespace haruquant::trading {

class DealInfo {
private:
  const core::BacktestState *m_state;
  std::string m_ticket;

protected:
  long GetInteger(const std::string &prop) const;
  double GetDouble(const std::string &prop) const;
  std::string GetString(const std::string &prop) const;

public:
  DealInfo();
  explicit DealInfo(const core::BacktestState *state);
  virtual ~DealInfo() = default;

  void SetState(const core::BacktestState *state);
  const core::BacktestState *GetState() const { return m_state; }

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
};

} // namespace haruquant::trading
