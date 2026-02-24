#pragma once

#include "core/state.hpp"
#include <memory>
#include <string>

namespace haruquant::trading {

class PositionInfo {
private:
  std::shared_ptr<core::BacktestState> m_state;
  std::string m_symbol;
  core::BacktestState &EnsureState();
  core::BacktestState::Dictionary &EnsureRow();

protected:
  long GetInteger(const std::string &prop) const;
  double GetDouble(const std::string &prop) const;
  std::string GetString(const std::string &prop) const;

public:
  PositionInfo();
  explicit PositionInfo(std::shared_ptr<core::BacktestState> state);
  virtual ~PositionInfo() = default;

  void SetState(std::shared_ptr<core::BacktestState> state);
  const core::BacktestState *GetState() const { return m_state.get(); }
  const std::shared_ptr<core::BacktestState> &GetSharedState() const {
    return m_state;
  }

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

  //--- Setters
  void SetTicket(long value);
  void SetTime(long value);
  void SetTimeMsc(long value);
  void SetTimeUpdate(long value);
  void SetTimeUpdateMsc(long value);
  void SetType(long value);
  void SetMagic(long value);
  void SetIdentifier(long value);
  void SetReason(long value);

  void SetVolume(double value);
  void SetPriceOpen(double value);
  void SetSl(double value);
  void SetTp(double value);
  void SetPriceCurrent(double value);
  void SetSwap(double value);
  void SetProfit(double value);

  void SetSymbol(const std::string &value);
  void SetComment(const std::string &value);
  void SetExternalId(const std::string &value);
};

} // namespace haruquant::trading
