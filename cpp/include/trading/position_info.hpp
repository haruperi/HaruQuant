#pragma once

#include "core/state.hpp"
#include <string>

namespace haruquant::trading {

class PositionInfo {
private:
  const core::BacktestState *m_state;
  std::string m_symbol;

protected:
  long GetInteger(const std::string &prop) const;
  double GetDouble(const std::string &prop) const;
  std::string GetString(const std::string &prop) const;

public:
  PositionInfo();
  explicit PositionInfo(const core::BacktestState *state);
  virtual ~PositionInfo() = default;

  void SetState(const core::BacktestState *state);
  const core::BacktestState *GetState() const { return m_state; }

  bool Select(const std::string &symbol);
  bool SelectByTicket(const long ticket);
  bool SelectByIndex(const int index);

  //--- Integer properties
  long Ticket() const;
  long Time() const;
  long TimeMsc() const;
  long TimeUpdate() const;
  long TimeUpdateMsc() const;
  long Type() const;
  long Magic() const;
  long Identifier() const;
  long Reason() const;

  //--- Double properties
  double Volume() const;
  double PriceOpen() const;
  double Sl() const;
  double Tp() const;
  double PriceCurrent() const;
  double Swap() const;
  double Profit() const;

  //--- String properties
  std::string Symbol() const;
  std::string Comment() const;
  std::string ExternalId() const;
};

} // namespace haruquant::trading
