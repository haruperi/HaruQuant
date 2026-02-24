#pragma once

#include "core/state.hpp"
#include <memory>
#include <string>

namespace haruquant::trading {

class HistoryOrderInfo {
private:
  std::shared_ptr<core::BacktestState> m_state;
  std::string m_ticket;
  core::BacktestState &EnsureState();
  core::BacktestState::Dictionary &EnsureRow();

protected:
  long GetInteger(const std::string &prop) const;
  double GetDouble(const std::string &prop) const;
  std::string GetString(const std::string &prop) const;

public:
  HistoryOrderInfo();
  explicit HistoryOrderInfo(std::shared_ptr<core::BacktestState> state);
  virtual ~HistoryOrderInfo() = default;

  void SetState(std::shared_ptr<core::BacktestState> state);
  const core::BacktestState *GetState() const { return m_state.get(); }
  const std::shared_ptr<core::BacktestState> &GetSharedState() const {
    return m_state;
  }

  bool Ticket(const long ticket);

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

  //--- Setters
  void SetTicket(long value);
  void SetTimeSetup(long value);
  void SetTimeSetupMsc(long value);
  void SetTimeDone(long value);
  void SetTimeDoneMsc(long value);
  void SetTimeExpiration(long value);
  void SetType(long value);
  void SetTypeTime(long value);
  void SetTypeFilling(long value);
  void SetStateValue(long value);
  void SetMagic(long value);
  void SetReason(long value);
  void SetPositionId(long value);

  void SetVolumeInitial(double value);
  void SetVolumeCurrent(double value);
  void SetPriceOpen(double value);
  void SetSl(double value);
  void SetTp(double value);
  void SetPriceCurrent(double value);
  void SetPriceStopLimit(double value);

  void SetSymbol(const std::string &value);
  void SetComment(const std::string &value);
  void SetExternalId(const std::string &value);
};

} // namespace haruquant::trading
