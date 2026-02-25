#include "trading/trade.hpp"
#include "core/backtest_simulator.hpp"
#include "util/error.hpp"
#include "util/validators.hpp"
#include "trading/symbol_info.hpp"
#include <algorithm>
#include <cctype>
#include <ctime>

namespace haruquant::trading {

namespace {
std::string resolve_symbol_key(const std::shared_ptr<core::BacktestState>& state,
                               const std::string& symbol) {
  if (!state || symbol.empty()) {
    return symbol;
  }
  auto exact = state->trading_symbols.find(symbol);
  if (exact != state->trading_symbols.end()) {
    return symbol;
  }
  std::string target = symbol;
  std::transform(target.begin(), target.end(), target.begin(),
                 [](unsigned char c) { return static_cast<char>(std::toupper(c)); });
  for (const auto& kv : state->trading_symbols) {
    std::string key = kv.first;
    std::transform(key.begin(), key.end(), key.begin(),
                   [](unsigned char c) { return static_cast<char>(std::toupper(c)); });
    if (key == target) {
      return kv.first;
    }
  }
  return symbol;
}
}  // namespace

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

  const std::string resolved_sym = resolve_symbol_key(m_state, sym);
  const auto symbol_it = m_state->trading_symbols.find(resolved_sym);
  SymbolInfo symbol_info(m_state);
  const SymbolInfo* symbol_ptr = nullptr;
  if (symbol_it != m_state->trading_symbols.end()) {
    symbol_info.Name(resolved_sym);
    symbol_ptr = &symbol_info;
  }

  haruquant::MqlTradeRequest validation_request;
  validation_request.action =
      static_cast<int>(haruquant::ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_DEAL);
  validation_request.symbol = resolved_sym;
  validation_request.volume = volume;
  validation_request.type = static_cast<int>(order_type);
  validation_request.price = price;
  validation_request.sl = sl;
  validation_request.tp = tp;
  validation_request.deviation = static_cast<int>(m_deviation);

  const AccountInfo account_snapshot(m_state);
  const auto validation =
      haruquant::util::open_position_validations(validation_request, account_snapshot, symbol_ptr);
  if (!validation.ok) {
    m_result_retcode = validation.retcode;
    m_result_comment = validation.comment;
    return false;
  }

  core::TradeRequest request;
  request.action = 1;  // TRADE_ACTION_DEAL
  request.magic = m_magic;
  request.symbol = resolved_sym;
  request.volume = volume;
  request.type = order_type;
  request.price = price;
  request.sl = sl;
  request.tp = tp;
  request.type_filling = type_filling;
  request.type_time = m_type_time;
  request.comment = comment;

  core::BacktestSimulator simulator(account_snapshot);
  const core::TradeResult result = simulator.order_send(request);
  m_result_retcode = result.retcode;
  m_result_order = result.order;
  m_result_deal = result.deal;
  m_result_comment = result.comment;
  return haruquant::util::is_success_retcode(static_cast<int>(m_result_retcode));
}

bool Trade::PositionModify(const std::string &symbol, const long ticket,
                           const double sl, const double tp) {
  if (!m_state) {
    m_result_retcode = 10013;
    return false;
  }

  const std::string sym = symbol.empty() ? m_symbol : symbol;
  const auto validation = haruquant::util::modify_position_validations(sym, ticket, m_state.get());
  if (!validation.ok) {
    m_result_retcode = validation.retcode;
    m_result_comment = validation.comment;
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

  const std::string sym = symbol.empty() ? m_symbol : symbol;
  const auto validation = haruquant::util::close_position_validations(sym, ticket, m_state.get());
  if (!validation.ok) {
    m_result_retcode = validation.retcode;
    m_result_comment = validation.comment;
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

  const std::string sym = symbol.empty() ? m_symbol : symbol;
  const auto validation =
      haruquant::util::close_partial_position_validations(sym, ticket, volume, m_state.get());
  if (!validation.ok) {
    m_result_retcode = validation.retcode;
    m_result_comment = validation.comment;
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
  const std::string resolved_sym = resolve_symbol_key(m_state, symbol);
  const auto symbol_it = m_state->trading_symbols.find(resolved_sym);
  SymbolInfo symbol_info(m_state);
  const SymbolInfo* symbol_ptr = nullptr;
  if (symbol_it != m_state->trading_symbols.end()) {
    symbol_info.Name(resolved_sym);
    symbol_ptr = &symbol_info;
  }

  haruquant::MqlTradeRequest validation_request;
  validation_request.action =
      static_cast<int>(haruquant::ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_PENDING);
  validation_request.symbol = resolved_sym;
  validation_request.volume = volume;
  validation_request.type = static_cast<int>(order_type);
  validation_request.price = (limit_price > 0.0) ? limit_price : price;
  validation_request.sl = sl;
  validation_request.tp = tp;
  validation_request.expiration = expiration;

  const AccountInfo account_snapshot(m_state);
  const auto validation =
      haruquant::util::open_pending_order_validations(validation_request, account_snapshot, symbol_ptr);
  if (!validation.ok) {
    m_result_retcode = validation.retcode;
    m_result_comment = validation.comment;
    return false;
  }

  std::string sym_upper = resolved_sym;
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
      {"symbol", resolved_sym},
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
  if (!m_state) {
    m_result_retcode = 10013;
    return false;
  }
  const auto order_it = m_state->trading_orders.find(std::to_string(ticket));
  SymbolInfo symbol_info(m_state);
  const SymbolInfo* symbol_ptr = nullptr;
  if (order_it != m_state->trading_orders.end()) {
    auto sym_it = order_it->second.find("symbol");
    if (sym_it != order_it->second.end() && !sym_it->second.empty()) {
      symbol_info.Name(sym_it->second);
      symbol_ptr = &symbol_info;
    }
  }
  const auto validation =
      haruquant::util::modify_pending_order_validations(
          ticket, price, sl, tp, expiration, m_state.get(), symbol_ptr);
  if (!validation.ok) {
    m_result_retcode = validation.retcode;
    m_result_comment = validation.comment;
    return false;
  }
  m_result_retcode = 10009;
  return true;
}

bool Trade::OrderDelete(const long ticket) {
  if (!m_state) {
    m_result_retcode = 10013;
    return false;
  }
  const auto validation =
      haruquant::util::delete_pending_order_validations(ticket, m_state.get());
  if (!validation.ok) {
    m_result_retcode = validation.retcode;
    m_result_comment = validation.comment;
    return false;
  }
  m_result_retcode = 10009;
  return true;
}

} // namespace haruquant::trading
