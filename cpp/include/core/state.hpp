#pragma once

#include <string>
#include <unordered_map>

namespace haruquant::core {

struct BacktestState {
  using Dictionary = std::unordered_map<std::string, std::string>;
  using DictionaryMap = std::unordered_map<std::string, Dictionary>;

  Dictionary trading_account{};
  DictionaryMap trading_symbols{};
  DictionaryMap trading_deals{};
  DictionaryMap trading_history_deals{};
  DictionaryMap trading_orders{};
  DictionaryMap trading_history_orders{};
  DictionaryMap trading_symbol_ticks{};
  Dictionary terminal_info{};
};

} // namespace haruquant::core
