#pragma once

#include "core/state.hpp"
#include <memory>
#include <string>

namespace haruquant::trading {

class SymbolInfo {
private:
  std::shared_ptr<core::BacktestState> m_state;
  std::string m_name;
  core::BacktestState &EnsureState();
  core::BacktestState::Dictionary &EnsureRow();
  void SetIntegerProperty(const std::string &prop, long value);
  void SetDoubleProperty(const std::string &prop, double value);
  void SetStringProperty(const std::string &prop, const std::string &value);

protected:
  long GetInteger(const std::string &prop) const;
  double GetDouble(const std::string &prop) const;
  std::string GetString(const std::string &prop) const;

public:
  SymbolInfo();
  explicit SymbolInfo(std::shared_ptr<core::BacktestState> state);
  virtual ~SymbolInfo() = default;

  void SetState(std::shared_ptr<core::BacktestState> state);
  const core::BacktestState *GetState() const { return m_state.get(); }
  const std::shared_ptr<core::BacktestState> &GetSharedState() const {
    return m_state;
  }

  bool Name(const std::string &name);
  std::string Name() const { return m_name; }

  void Refresh(); // Normally refreshes rates, we can leave empty or hook to
                  // state later
  void RefreshRates(); // Same as above

  //--- Integer properties
  long Select() const;
  long Select(const bool select);
  long Visible() const;
  long SessionDeals() const;
  long SessionBuyOrders() const;
  long SessionSellOrders() const;
  long Volume() const;
  long VolumeHigh() const;
  long VolumeLow() const;
  long Time() const;
  long Digits() const;
  long Spread() const;
  long SpreadFloat() const;
  long TicksBookDepth() const;
  long TradeCalcMode() const;
  long TradeMode() const;
  long StartTime() const;
  long ExpirationTime() const;
  long TradeStopsLevel() const;
  long TradeFreezeLevel() const;
  long TradeExemode() const;
  long SwapMode() const;
  long SwapRollover3days() const;
  long MarginHedgedUseLeg() const;
  long ExpirationMode() const;
  long FillingMode() const;
  long OrderMode() const;

  //--- Double properties
  double Bid() const;
  double BidHigh() const;
  double BidLow() const;
  double Ask() const;
  double AskHigh() const;
  double AskLow() const;
  double Last() const;
  double LastHigh() const;
  double LastLow() const;
  double Point() const;
  double TradeTickValue() const;
  double TradeTickValueProfit() const;
  double TradeTickValueLoss() const;
  double TradeTickSize() const;
  double TradeContractSize() const;
  double TradeAccruedInterest() const;
  double TradeFaceValue() const;
  double TradeLiquidityRate() const;
  double VolumeMin() const;
  double VolumeMax() const;
  double VolumeStep() const;
  double VolumeLimit() const;
  double SwapLong() const;
  double SwapShort() const;
  double MarginInitial() const;
  double MarginMaintenance() const;
  double SessionVolume() const;
  double SessionTurnover() const;
  double SessionInterest() const;
  double SessionBuyOrdersVolume() const;
  double SessionSellOrdersVolume() const;
  double SessionOpen() const;
  double SessionClose() const;
  double SessionAw() const;
  double SessionPriceSettlement() const;
  double SessionPriceLimitMin() const;
  double SessionPriceLimitMax() const;
  double MarginHedged() const;

  //--- String properties
  std::string Path() const;
  std::string Description() const;
  std::string Isin() const;
  std::string Page() const;
  std::string CurrencyBase() const;
  std::string CurrencyProfit() const;
  std::string CurrencyMargin() const;
  std::string Bank() const;

  //--- Normalized property methods
  double NormalizePrice(const double price) const;

  //--- Setters
  void SetSelect(bool value);
  void SetVisible(bool value);
  void SetVolume(long value);
  void SetVolumeHigh(long value);
  void SetVolumeLow(long value);
  void SetTime(long value);
  void SetDigits(long value);
  void SetSpread(long value);
  void SetSpreadFloat(bool value);
  void SetTradeCalcMode(long value);
  void SetTradeMode(long value);
  void SetTradeExemode(long value);
  void SetTradeStopsLevel(long value);
  void SetTradeFreezeLevel(long value);
  void SetSwapMode(long value);
  void SetSwapRollover3days(long value);

  void SetBid(double value);
  void SetBidHigh(double value);
  void SetBidLow(double value);
  void SetAsk(double value);
  void SetAskHigh(double value);
  void SetAskLow(double value);
  void SetLast(double value);
  void SetLastHigh(double value);
  void SetLastLow(double value);
  void SetPoint(double value);
  void SetTradeTickValue(double value);
  void SetTradeTickValueProfit(double value);
  void SetTradeTickValueLoss(double value);
  void SetTradeTickSize(double value);
  void SetTradeContractSize(double value);
  void SetVolumeMin(double value);
  void SetVolumeMax(double value);
  void SetVolumeStep(double value);
  void SetVolumeLimit(double value);
  void SetSwapLong(double value);
  void SetSwapShort(double value);
  void SetMarginInitial(double value);
  void SetMarginMaintenance(double value);

  void SetPath(const std::string &value);
  void SetDescription(const std::string &value);
  void SetCurrencyBase(const std::string &value);
  void SetCurrencyProfit(const std::string &value);
  void SetCurrencyMargin(const std::string &value);
};

} // namespace haruquant::trading
