#include "trading/trade.hpp"
#include <iostream>

namespace haruquant::trading {

Trade::Trade()
    : m_state(nullptr), m_magic(0), m_deviation(10), m_type_filling(0),
      m_log_level(0), m_symbol(""), m_result_deal(0), m_result_order(0),
      m_result_retcode(0), m_result_comment("") {}

Trade::Trade(core::BacktestState *state)
    : m_state(state), m_magic(0), m_deviation(10), m_type_filling(0),
      m_log_level(0), m_symbol(""), m_result_deal(0), m_result_order(0),
      m_result_retcode(0), m_result_comment("") {}

void Trade::SetState(core::BacktestState *state) { m_state = state; }

std::string Trade::ResultRetcodeDescription() const {
  if (m_result_retcode == 10009)
    return "TRADE_RETCODE_DONE";
  if (m_result_retcode == 10008)
    return "TRADE_RETCODE_PLACED";
  if (m_result_retcode == 10013)
    return "TRADE_RETCODE_INVALID";
  return "UNKNOWN_RETCODE_" + std::to_string(m_result_retcode);
}

// Below are placeholder implementations meant to be integrated with the
// backtesting engine. They mimic MQL5 API surface. A real engine hook would
// create order requests in m_state.

bool Trade::PositionOpen(const std::string &symbol, const long order_type,
                         const double volume, const double price,
                         const double sl, const double tp,
                         const std::string &comment) {
  if (!m_state) {
    m_result_retcode = 10013; // Invalid request
    return false;
  }
  std::string sym = symbol.empty() ? m_symbol : symbol;

  // Engine integration: append action to state queue
  m_state->trading_orders["new_order_" + std::to_string(time(nullptr))] = {
      {"symbol", sym},
      {"type", std::to_string(order_type)},
      {"volume", std::to_string(volume)},
      {"price", std::to_string(price)},
      {"sl", std::to_string(sl)},
      {"tp", std::to_string(tp)},
      {"comment", comment},
      {"action", "position_open"}};

  m_result_retcode = 10009; // DONE
  m_result_order = 1;       // Fake order ticket
  return true;
}

bool Trade::PositionModify(const std::string &symbol, const double sl,
                           const double tp) {
  if (!m_state)
    return false;
  m_result_retcode = 10009;
  return true;
}

bool Trade::PositionModify(const long ticket, const double sl,
                           const double tp) {
  if (!m_state)
    return false;
  m_result_retcode = 10009;
  return true;
}

bool Trade::PositionClose(const std::string &symbol, const double deviation) {
  if (!m_state)
    return false;
  m_result_retcode = 10009;
  return true;
}

bool Trade::PositionClose(const long ticket, const double deviation) {
  if (!m_state)
    return false;
  m_result_retcode = 10009;
  return true;
}

bool Trade::PositionClosePartial(const std::string &symbol, const double volume,
                                 const double deviation) {
  if (!m_state)
    return false;
  m_result_retcode = 10009;
  return true;
}

bool Trade::PositionClosePartial(const long ticket, const double volume,
                                 const double deviation) {
  if (!m_state)
    return false;
  m_result_retcode = 10009;
  return true;
}

bool Trade::Buy(const double volume, const std::string &symbol,
                const double price, const double sl, const double tp,
                const std::string &comment) {
  return PositionOpen(symbol, 0 /* ORDER_TYPE_BUY */, volume, price, sl, tp,
                      comment);
}

bool Trade::Sell(const double volume, const std::string &symbol,
                 const double price, const double sl, const double tp,
                 const std::string &comment) {
  return PositionOpen(symbol, 1 /* ORDER_TYPE_SELL */, volume, price, sl, tp,
                      comment);
}

bool Trade::OrderOpen(const std::string &symbol, const long order_type,
                      const double volume, const double limit_price,
                      const double price, const double sl, const double tp,
                      const long type_time, const long expiration,
                      const std::string &comment) {
  if (!m_state) {
    m_result_retcode = 10013;
    return false;
  }
  m_result_retcode = 10009;
  return true;
}

bool Trade::OrderModify(const long ticket, const double price, const double sl,
                        const double tp, const long type_time,
                        const long expiration, const double stoplimit_price) {
  if (!m_state)
    return false;
  m_result_retcode = 10009;
  return true;
}

bool Trade::OrderDelete(const long ticket) {
  if (!m_state)
    return false;
  m_result_retcode = 10009;
  return true;
}

} // namespace haruquant::trading
