#include "trading/trade.hpp"
#include "util/error.hpp"
#include <algorithm>
#include <cctype>
#include <ctime>

namespace haruquant::trading {

Trade::Trade()
    : m_state(std::make_shared<core::BacktestState>()), m_magic(0),
      m_deviation(10), m_type_filling(0), m_type_time(0), m_async_mode(false),
      m_margin_mode(0), m_log_level(0), m_symbol(""), m_result_deal(0),
      m_result_order(0), m_result_retcode(0), m_result_comment("") {}

Trade::Trade(std::shared_ptr<core::BacktestState> state)
    : m_state(std::move(state)), m_magic(0), m_deviation(10),
      m_type_filling(0), m_type_time(0), m_async_mode(false), m_margin_mode(0), m_log_level(0),
      m_symbol(""), m_result_deal(0), m_result_order(0), m_result_retcode(0),
      m_result_comment("") {}

void Trade::SetState(std::shared_ptr<core::BacktestState> state) {
  m_state = std::move(state);
}

std::string Trade::ResultRetcodeDescription() const {
  const auto info = haruquant::util::error_from_retcode(static_cast<int>(m_result_retcode));
  return info.message;
}

bool Trade::SetTypeFillingBySymbol(const std::string &symbol) {
  if (symbol.empty()) {
    return false;
  }
  std::string key = symbol;
  std::transform(key.begin(), key.end(), key.begin(),
                 [](unsigned char c) { return static_cast<char>(std::toupper(c)); });
  m_type_filling_by_symbol[key] = m_type_filling;
  return true;
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
  m_symbol = sym;
  std::string sym_upper = sym;
  std::transform(sym_upper.begin(), sym_upper.end(), sym_upper.begin(),
                 [](unsigned char c) { return static_cast<char>(std::toupper(c)); });
  long type_filling = m_type_filling;
  auto it_fill = m_type_filling_by_symbol.find(sym_upper);
  if (it_fill != m_type_filling_by_symbol.end()) {
    type_filling = it_fill->second;
  }

  // Engine integration: append action to state queue
  m_state->trading_orders["new_order_" + std::to_string(time(nullptr))] = {
      {"symbol", sym},
      {"type", std::to_string(order_type)},
      {"type_filling", std::to_string(type_filling)},
      {"type_time", std::to_string(m_type_time)},
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

bool Trade::PositionModify(const std::string &symbol, const long ticket,
                           const double sl, const double tp) {
  if (!m_state) {
    m_result_retcode = 10013;
    return false;
  }

  const bool has_ticket = ticket > 0;
  const std::string sym = symbol.empty() ? m_symbol : symbol;
  const bool has_symbol = !sym.empty();
  if (!has_ticket && !has_symbol) {
    m_result_retcode = 10013;
    return false;
  }

  m_state->trading_orders["modify_position_" + std::to_string(time(nullptr))] = {
      {"action", "position_modify"},
      {"symbol", sym},
      {"ticket", std::to_string(ticket)},
      {"sl", std::to_string(sl)},
      {"tp", std::to_string(tp)}};

  m_result_retcode = 10009;
  return true;
}

bool Trade::PositionClose(const std::string &symbol, const long ticket,
                          const double deviation) {
  if (!m_state) {
    m_result_retcode = 10013;
    return false;
  }

  const bool has_ticket = ticket > 0;
  const std::string sym = symbol.empty() ? m_symbol : symbol;
  const bool has_symbol = !sym.empty();
  if (!has_ticket && !has_symbol) {
    m_result_retcode = 10013;
    return false;
  }

  m_state->trading_orders["close_position_" + std::to_string(time(nullptr))] = {
      {"action", "position_close"},
      {"symbol", sym},
      {"ticket", std::to_string(ticket)},
      {"deviation", std::to_string(deviation)}};

  m_result_retcode = 10009;
  return true;
}

bool Trade::PositionClosePartial(const std::string &symbol, const long ticket,
                                 const double volume,
                                 const double deviation) {
  if (!m_state) {
    m_result_retcode = 10013;
    return false;
  }

  const bool has_ticket = ticket > 0;
  const std::string sym = symbol.empty() ? m_symbol : symbol;
  const bool has_symbol = !sym.empty();
  if (!has_ticket && !has_symbol) {
    m_result_retcode = 10013;
    return false;
  }
  if (volume <= 0.0) {
    m_result_retcode = 10013;
    return false;
  }

  m_state->trading_orders["partial_close_position_" + std::to_string(time(nullptr))] = {
      {"action", "position_close_partial"},
      {"symbol", sym},
      {"ticket", std::to_string(ticket)},
      {"volume", std::to_string(volume)},
      {"deviation", std::to_string(deviation)}};

  m_result_retcode = 10009;
  return true;
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
  std::string sym_upper = symbol;
  std::transform(sym_upper.begin(), sym_upper.end(), sym_upper.begin(),
                 [](unsigned char c) { return static_cast<char>(std::toupper(c)); });
  long type_filling = m_type_filling;
  auto it_fill = m_type_filling_by_symbol.find(sym_upper);
  if (it_fill != m_type_filling_by_symbol.end()) {
    type_filling = it_fill->second;
  }
  const long resolved_type_time = (type_time == 0 ? m_type_time : type_time);
  m_state->trading_orders["open_order_" + std::to_string(time(nullptr))] = {
      {"action", "order_open"},
      {"symbol", symbol},
      {"type", std::to_string(order_type)},
      {"type_filling", std::to_string(type_filling)},
      {"type_time", std::to_string(resolved_type_time)},
      {"volume", std::to_string(volume)},
      {"limit_price", std::to_string(limit_price)},
      {"price", std::to_string(price)},
      {"sl", std::to_string(sl)},
      {"tp", std::to_string(tp)},
      {"expiration", std::to_string(expiration)},
      {"comment", comment}};

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
