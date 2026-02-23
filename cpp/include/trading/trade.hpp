#pragma once

#include "core/state.hpp"
#include <climits>
#include <string>


namespace haruquant::trading {

class Trade {
private:
  core::BacktestState *m_state;
  long m_magic;
  double m_deviation;
  long m_type_filling;
  long m_log_level;
  std::string m_symbol;

  // Last result values
  long m_result_deal;
  long m_result_order;
  long m_result_retcode;
  std::string m_result_comment;

public:
  Trade();
  explicit Trade(core::BacktestState *state);
  virtual ~Trade() = default;

  void SetState(core::BacktestState *state);
  core::BacktestState *GetState() const { return m_state; }

  // Configuration
  void LogLevel(const long log_level) { m_log_level = log_level; }
  void RequestMagic(const long magic) { m_magic = magic; }
  void RequestDeviation(const double deviation) { m_deviation = deviation; }
  void RequestTypeFilling(const long type) { m_type_filling = type; }
  void RequestSymbol(const std::string &symbol) { m_symbol = symbol; }

  long RequestMagic() const { return m_magic; }
  double RequestDeviation() const { return m_deviation; }
  long RequestTypeFilling() const { return m_type_filling; }
  std::string RequestSymbol() const { return m_symbol; }

  // Trading methods analogous to MQL5 standard CTrade
  bool PositionOpen(const std::string &symbol, const long order_type,
                    const double volume, const double price, const double sl,
                    const double tp, const std::string &comment = "");
  bool PositionModify(const std::string &symbol, const double sl,
                      const double tp);
  bool PositionModify(const long ticket, const double sl, const double tp);
  bool PositionClose(const std::string &symbol,
                     const double deviation = ULONG_MAX);
  bool PositionClose(const long ticket, const double deviation = ULONG_MAX);
  bool PositionClosePartial(const std::string &symbol, const double volume,
                            const double deviation = ULONG_MAX);
  bool PositionClosePartial(const long ticket, const double volume,
                            const double deviation = ULONG_MAX);

  bool Buy(const double volume, const std::string &symbol = "",
           const double price = 0.0, const double sl = 0.0,
           const double tp = 0.0, const std::string &comment = "");
  bool Sell(const double volume, const std::string &symbol = "",
            const double price = 0.0, const double sl = 0.0,
            const double tp = 0.0, const std::string &comment = "");

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
