#pragma once

#include "core/state.hpp"
#include <string>

namespace haruquant::trading {

class OrderInfo {
private:
  const core::BacktestState *m_state;
  std::string m_ticket;

protected:
  long GetInteger(const std::string &prop) const;
  double GetDouble(const std::string &prop) const;
  std::string GetString(const std::string &prop) const;

public:
  OrderInfo();
  explicit OrderInfo(const core::BacktestState *state);
  virtual ~OrderInfo() = default;

  void SetState(const core::BacktestState *state);
  const core::BacktestState *GetState() const { return m_state; }

  bool Select(const long ticket);
  bool SelectByIndex(const int index);

  //--- Integer properties
  long Ticket() const;
  long TimeSetup() const;
  long TimeSetupMsc() const;
  long TimeDone() const;
  long TimeDoneMsc() const;
  long TimeExpiration() const;
  long Type() const;
  long TypeTime() const;
  long TypeFilling() const;
  long State() const;
  long Magic() const;
  long Reason() const;
  long PositionId() const;
  long PositionById() const;

  //--- Double properties
  double VolumeInitial() const;
  double VolumeCurrent() const;
  double PriceOpen() const;
  double Sl() const;
  double Tp() const;
  double PriceCurrent() const;
  double PriceStopLimit() const;

  //--- String properties
  std::string Symbol() const;
  std::string Comment() const;
  std::string ExternalId() const;
};

} // namespace haruquant::trading
