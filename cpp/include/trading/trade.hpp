#pragma once

#include "core/state.hpp"
#include <climits>
#include <unordered_map>
#include <memory>
#include <string>


namespace haruquant::trading {

class Trade {
private:
  std::shared_ptr<core::BacktestState> m_state;
  long m_magic;
  double m_deviation;
  long m_type_filling;
  long m_type_time;
  bool m_async_mode;
  long m_margin_mode;
  long m_log_level;
  std::string m_symbol;
  std::unordered_map<std::string, long> m_type_filling_by_symbol;

  // Last result values
  long m_result_deal;
  long m_result_order;
  long m_result_retcode;
  std::string m_result_comment;

public:
  Trade();
  explicit Trade(std::shared_ptr<core::BacktestState> state);
  virtual ~Trade() = default;

  void SetState(std::shared_ptr<core::BacktestState> state);
  const core::BacktestState *GetState() const { return m_state.get(); }
  const std::shared_ptr<core::BacktestState> &GetSharedState() const {
    return m_state;
  }

  // Configuration
  void LogLevel(const long log_level) { m_log_level = log_level; }
  void SetAsyncMode(bool async_mode) { m_async_mode = async_mode; }
  void SetExpertMagicNumber(const long magic) { m_magic = magic; }
  void SetDeviationInPoints(const double deviation) { m_deviation = deviation; }
  void SetTypeFilling(const long type) { m_type_filling = type; }
  void SetTypeTime(const long type_time) { m_type_time = type_time; }
  bool SetTypeFillingBySymbol(const std::string &symbol);
  void SetMarginMode(const long margin_mode) { m_margin_mode = margin_mode; }

  // Trading methods analogous to MQL5 standard CTrade
  bool PositionOpen(const std::string &symbol, const long order_type,
                    const double volume, const double price, const double sl,
                    const double tp, const std::string &comment = "");
  bool PositionModify(const std::string &symbol = "", const long ticket = 0,
                      const double sl = 0.0, const double tp = 0.0);
  bool PositionClose(const std::string &symbol = "", const long ticket = 0,
                     const double deviation = ULONG_MAX);
  bool PositionClosePartial(const std::string &symbol = "",
                            const long ticket = 0, const double volume = 0.0,
                            const double deviation = ULONG_MAX);

  bool OrderOpen(const std::string &symbol, const long order_type,
                 const double volume, const double limit_price,
                 const double price, const double sl, const double tp,
                 const long type_time = 0, const long expiration = 0,
                 const std::string &comment = "");
  bool OrderModify(const long ticket, const double price, const double sl,
                   const double tp, const long type_time, const long expiration,
                   const double stoplimit_price = 0.0);
  bool OrderDelete(const long ticket);

  // Result properties
  long ResultDeal() const { return m_result_deal; }
  long ResultOrder() const { return m_result_order; }
  long ResultRetcode() const { return m_result_retcode; }
  std::string ResultRetcodeDescription() const;
  std::string ResultComment() const { return m_result_comment; }
};

} // namespace haruquant::trading
