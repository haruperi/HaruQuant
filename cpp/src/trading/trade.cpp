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

core::BacktestState::DictionaryMap::iterator find_position_iter(
    const std::shared_ptr<core::BacktestState>& state,
    const std::string& symbol,
    long ticket) {
  if (ticket > 0) {
    const std::string ticket_str = std::to_string(ticket);
    for (auto it = state->trading_deals.begin(); it != state->trading_deals.end(); ++it) {
      auto pos_ticket_it = it->second.find("ticket");
      auto entry_it = it->second.find("entry");
      const std::string entry = (entry_it != it->second.end()) ? entry_it->second : "0";
      if (pos_ticket_it != it->second.end() && pos_ticket_it->second == ticket_str && entry == "0") {
        return it;
      }
    }
  }

  if (!symbol.empty()) {
    for (auto it = state->trading_deals.begin(); it != state->trading_deals.end(); ++it) {
      auto sym_it = it->second.find("symbol");
      auto entry_it = it->second.find("entry");
      const std::string row_symbol = (sym_it != it->second.end()) ? sym_it->second : "";
      const std::string entry = (entry_it != it->second.end()) ? entry_it->second : "0";
      if (entry == "0" && row_symbol == symbol) {
        return it;
      }
    }
  }

  return state->trading_deals.end();
}

core::BacktestState::DictionaryMap::iterator find_order_iter(
    const std::shared_ptr<core::BacktestState>& state,
    long ticket) {
  if (!state || ticket <= 0) {
    return state ? state->trading_orders.end() : core::BacktestState::DictionaryMap::iterator{};
  }
  const std::string ticket_str = std::to_string(ticket);
  auto direct = state->trading_orders.find(ticket_str);
  if (direct != state->trading_orders.end()) {
    return direct;
  }
  for (auto it = state->trading_orders.begin(); it != state->trading_orders.end(); ++it) {
    auto order_ticket_it = it->second.find("ticket");
    if (order_ticket_it != it->second.end() && order_ticket_it->second == ticket_str) {
      return it;
    }
  }
  return state->trading_orders.end();
}

double read_row_double(const core::BacktestState::Dictionary& row,
                       const std::string& key,
                       double fallback = 0.0) {
  const auto it = row.find(key);
  if (it == row.end()) {
    return fallback;
  }
  try {
    return std::stod(it->second);
  } catch (...) {
    return fallback;
  }
}

double compute_realized_profit(const std::shared_ptr<core::BacktestState>& state,
                               const core::BacktestState::Dictionary& pos_row) {
  if (!state) {
    return 0.0;
  }

  const std::string symbol_raw = pos_row.count("symbol") ? pos_row.at("symbol") : "";
  const std::string symbol = resolve_symbol_key(state, symbol_raw);
  const long order_type = static_cast<long>(read_row_double(pos_row, "type", -1.0));
  const bool is_buy = (order_type == 0);
  const bool is_sell = (order_type == 1);
  if (!is_buy && !is_sell) {
    return read_row_double(pos_row, "profit", 0.0);
  }

  const double volume = read_row_double(pos_row, "volume", 0.0);
  const double entry_price = read_row_double(pos_row, "price_open", read_row_double(pos_row, "price", 0.0));
  if (!(volume > 0.0) || !(entry_price > 0.0) || symbol.empty()) {
    return read_row_double(pos_row, "profit", 0.0);
  }

  const auto sym_it = state->trading_symbols.find(symbol);
  if (sym_it == state->trading_symbols.end()) {
    return read_row_double(pos_row, "profit", 0.0);
  }
  const double bid = read_row_double(sym_it->second, "bid", 0.0);
  const double ask = read_row_double(sym_it->second, "ask", 0.0);
  const double exit_price = is_buy ? bid : ask;
  if (!(exit_price > 0.0)) {
    return read_row_double(pos_row, "profit", 0.0);
  }

  try {
    const AccountInfo account_snapshot(state);
    const core::BacktestSimulator simulator(account_snapshot);
    return simulator.order_calc_profit(is_buy ? "BUY" : "SELL", symbol, volume, entry_price, exit_price);
  } catch (...) {
    return read_row_double(pos_row, "profit", 0.0);
  }
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

  auto pos_it = find_position_iter(m_state, sym, ticket);
  if (pos_it == m_state->trading_deals.end()) {
    m_result_retcode = 10036;
    m_result_comment = "Position not found";
    return false;
  }

  auto& target_position = pos_it->second;
  target_position["sl"] = std::to_string(sl);
  target_position["tp"] = std::to_string(tp);
  const long now = static_cast<long>(time(nullptr));
  target_position["time_update"] = std::to_string(now);
  target_position["time_update_msc"] = std::to_string(now * 1000);

  m_state->trading_orders["modify_position_" + std::to_string(time(nullptr))] = {
      {"action", "position_modify"},
      {"symbol", sym},
      {"ticket", std::to_string(ticket)},
      {"sl", std::to_string(sl)},
      {"tp", std::to_string(tp)}};

  m_result_retcode = 10009;
  m_result_comment = "Position modified";
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

  auto pos_it = find_position_iter(m_state, sym, ticket);
  if (pos_it == m_state->trading_deals.end()) {
    m_result_retcode = 10036;
    m_result_comment = "Position not found";
    return false;
  }

  const std::string closed_symbol = pos_it->second.count("symbol") ? pos_it->second.at("symbol") : pos_it->first;
  const std::string closed_ticket = pos_it->second.count("ticket") ? pos_it->second.at("ticket")
                                                                    : std::to_string(ticket);
  auto closed_row = pos_it->second;

  // Realize P/L into account balance on full close.
  const double realized_profit = compute_realized_profit(m_state, closed_row);
  const double current_balance = read_row_double(m_state->trading_account, "balance", 0.0);
  m_state->trading_account["balance"] = std::to_string(current_balance + realized_profit);
  closed_row["profit"] = std::to_string(realized_profit);

  closed_row["entry"] = "1";
  closed_row["time_update"] = std::to_string(static_cast<long>(time(nullptr)));
  m_state->trading_history_deals[closed_ticket] = closed_row;
  m_state->trading_deals.erase(pos_it);

  m_state->trading_orders["close_position_" + std::to_string(time(nullptr))] = {
      {"action", "position_close"},
      {"symbol", closed_symbol},
      {"ticket", closed_ticket},
      {"deviation", std::to_string(deviation)}};

  m_result_retcode = 10009;
  m_result_comment = "Position closed";
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

  auto pos_it = find_position_iter(m_state, sym, ticket);
  if (pos_it == m_state->trading_deals.end()) {
    m_result_retcode = 10036;
    m_result_comment = "Position not found";
    return false;
  }

  auto& pos_row = pos_it->second;
  const std::string selected_symbol = pos_it->first;
  const std::string selected_ticket = pos_row.count("ticket") ? pos_row.at("ticket")
                                                               : std::to_string(ticket);
  const double current_volume = read_row_double(pos_row, "volume", 0.0);
  if (current_volume <= 0.0) {
    m_result_retcode = 10014;
    m_result_comment = "Position volume is invalid";
    return false;
  }

  const double remaining_volume = current_volume - volume;
  const long now = static_cast<long>(time(nullptr));
  const double current_profit = compute_realized_profit(m_state, pos_row);
  const double realized_profit = (current_volume > 0.0) ? (current_profit * (volume / current_volume)) : 0.0;
  const double current_balance = read_row_double(m_state->trading_account, "balance", 0.0);
  m_state->trading_account["balance"] = std::to_string(current_balance + realized_profit);

  if (remaining_volume <= 1e-12) {
    auto closed_row = pos_row;
    closed_row["profit"] = std::to_string(current_profit);
    closed_row["entry"] = "1";
    closed_row["time_update"] = std::to_string(now);
    m_state->trading_history_deals[selected_ticket] = closed_row;
    m_state->trading_deals.erase(pos_it);
  } else {
    pos_row["volume"] = std::to_string(remaining_volume);
    pos_row["profit"] = std::to_string(current_profit - realized_profit);
    pos_row["time_update"] = std::to_string(now);
    pos_row["time_update_msc"] = std::to_string(now * 1000);
  }

  m_state->trading_orders["partial_close_position_" + std::to_string(time(nullptr))] = {
      {"action", "position_close_partial"},
      {"symbol", selected_symbol},
      {"ticket", selected_ticket},
      {"volume", std::to_string(volume)},
      {"deviation", std::to_string(deviation)}};

  m_result_retcode = 10009;
  m_result_comment = "Position partially closed";
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

  const bool supported_pending_type =
      order_type == static_cast<long>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT) ||
      order_type == static_cast<long>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP) ||
      order_type == static_cast<long>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_LIMIT) ||
      order_type == static_cast<long>(haruquant::ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP);
  if (!supported_pending_type) {
    m_result_retcode = 10013;
    m_result_comment = "Only BUY_LIMIT/BUY_STOP/SELL_LIMIT/SELL_STOP are supported";
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

  core::TradeRequest request;
  request.action =
      static_cast<long>(haruquant::ENUM_TRADE_REQUEST_ACTIONS::TRADE_ACTION_PENDING);
  request.magic = m_magic;
  request.symbol = resolved_sym;
  request.volume = volume;
  request.type = order_type;
  request.price = (limit_price > 0.0) ? limit_price : price;
  request.sl = sl;
  request.tp = tp;
  request.type_filling = type_filling;
  request.type_time = resolved_type_time;
  request.expiration = expiration;
  request.comment = comment;

  core::BacktestSimulator simulator(account_snapshot);
  const core::TradeResult result = simulator.order_send(request);
  m_result_retcode = result.retcode;
  m_result_order = result.order;
  m_result_deal = result.deal;
  m_result_comment = result.comment;
  return haruquant::util::is_success_retcode(static_cast<int>(m_result_retcode));
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

  auto row_it = find_order_iter(m_state, ticket);
  if (row_it == m_state->trading_orders.end()) {
    m_result_retcode = 10035;
    m_result_comment = "Order not found";
    return false;
  }

  auto& row = row_it->second;
  if (price > 0.0) {
    const std::string p = std::to_string(price);
    row["price"] = p;
    row["price_open"] = p;
    row["price_current"] = p;
  }
  if (stoplimit_price > 0.0) {
    row["price_stoplimit"] = std::to_string(stoplimit_price);
  }
  row["sl"] = std::to_string(sl);
  row["tp"] = std::to_string(tp);
  if (type_time >= 0) {
    row["type_time"] = std::to_string(type_time);
  }
  if (expiration >= 0) {
    row["time_expiration"] = std::to_string(expiration);
  }

  m_result_retcode = 10009;
  m_result_comment = "Order modified";
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

  auto row_it = find_order_iter(m_state, ticket);
  if (row_it == m_state->trading_orders.end()) {
    m_result_retcode = 10035;
    m_result_comment = "Order not found";
    return false;
  }

  m_state->trading_orders.erase(row_it);
  m_result_retcode = 10009;
  m_result_comment = "Order deleted";
  return true;
}

} // namespace haruquant::trading
