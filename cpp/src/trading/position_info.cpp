#include "trading/position_info.hpp"
#include <sstream>
#include <string>

namespace haruquant::trading {

namespace {
template <typename T>
std::string to_string_value(T value) {
  std::ostringstream oss;
  oss << value;
  return oss.str();
}
} // namespace

PositionInfo::PositionInfo() : m_state(std::make_shared<core::BacktestState>()), m_symbol("") {}

PositionInfo::PositionInfo(std::shared_ptr<core::BacktestState> state)
    : m_state(std::move(state)), m_symbol("") {
  EnsureState();
}

void PositionInfo::SetState(std::shared_ptr<core::BacktestState> state) {
  m_state = std::move(state);
  EnsureState();
}

core::BacktestState &PositionInfo::EnsureState() {
  if (!m_state) {
    m_state = std::make_shared<core::BacktestState>();
  }
  return *m_state;
}

core::BacktestState::Dictionary *FindSelectedRowMutable(
    const std::shared_ptr<core::BacktestState> &state,
    const std::string &symbol_selector) {
  if (!state || symbol_selector.empty()) {
    return nullptr;
  }
  for (auto &kv : state->trading_deals) {
    auto entry_it = kv.second.find("entry");
    const std::string entry = (entry_it != kv.second.end()) ? entry_it->second : "0";
    if (entry != "0") {
      continue;
    }
    auto sym_it = kv.second.find("symbol");
    const std::string row_symbol = (sym_it != kv.second.end()) ? sym_it->second : kv.first;
    if (row_symbol == symbol_selector || kv.first == symbol_selector) {
      return &kv.second;
    }
  }
  return nullptr;
}

const core::BacktestState::Dictionary *FindSelectedRowConst(
    const std::shared_ptr<core::BacktestState> &state,
    const std::string &symbol_selector) {
  if (!state || symbol_selector.empty()) {
    return nullptr;
  }
  for (const auto &kv : state->trading_deals) {
    auto entry_it = kv.second.find("entry");
    const std::string entry = (entry_it != kv.second.end()) ? entry_it->second : "0";
    if (entry != "0") {
      continue;
    }
    auto sym_it = kv.second.find("symbol");
    const std::string row_symbol = (sym_it != kv.second.end()) ? sym_it->second : kv.first;
    if (row_symbol == symbol_selector || kv.first == symbol_selector) {
      return &kv.second;
    }
  }
  return nullptr;
}

core::BacktestState::Dictionary &PositionInfo::EnsureRow() {
  auto &state = EnsureState();
  if (m_symbol.empty()) {
    m_symbol = "UNKNOWN";
  }
  core::BacktestState::Dictionary *row = FindSelectedRowMutable(m_state, m_symbol);
  if (row != nullptr) {
    return *row;
  }
  auto &created = state.trading_deals[m_symbol];
  created["symbol"] = m_symbol;
  created["entry"] = "0";
  return created;
}

bool PositionInfo::Select(const std::string &symbol) {
  if (!m_state)
    return false;
  for (const auto &kv : m_state->trading_deals) {
    auto entry_it = kv.second.find("entry");
    const std::string entry = (entry_it != kv.second.end()) ? entry_it->second : "0";
    if (entry != "0") {
      continue;
    }
    auto sym_it = kv.second.find("symbol");
    const std::string row_symbol = (sym_it != kv.second.end()) ? sym_it->second : kv.first;
    if (row_symbol == symbol || kv.first == symbol) {
      m_symbol = row_symbol;
      return true;
    }
  }
  return false;
}

bool PositionInfo::SelectByTicket(const long ticket) {
  if (!m_state)
    return false;
  std::string t_str = std::to_string(ticket);
  for (const auto &kv : m_state->trading_deals) {
    auto entry_it = kv.second.find("entry");
    const std::string entry = (entry_it != kv.second.end()) ? entry_it->second : "0";
    if (entry != "0") {
      continue;
    }
    auto it = kv.second.find("ticket");
    if (it != kv.second.end() && it->second == t_str) {
      auto sym_it = kv.second.find("symbol");
      m_symbol = (sym_it != kv.second.end()) ? sym_it->second : kv.first;
      return true;
    }
  }
  return false;
}

bool PositionInfo::SelectByIndex(const int index) {
  if (!m_state || index < 0)
    return false;

  int i = 0;
  for (const auto &kv : m_state->trading_deals) {
    auto entry_it = kv.second.find("entry");
    const std::string entry = (entry_it != kv.second.end()) ? entry_it->second : "0";
    if (entry != "0") {
      continue;
    }
    if (i == index) {
      auto sym_it = kv.second.find("symbol");
      m_symbol = (sym_it != kv.second.end()) ? sym_it->second : kv.first;
      return true;
    }
    i++;
  }
  return false;
}

long PositionInfo::GetInteger(const std::string &prop) const {
  if (!m_state || m_symbol.empty())
    return 0;

  const auto *row = FindSelectedRowConst(m_state, m_symbol);
  if (row != nullptr) {
    auto p_it = row->find(prop);
    if (p_it != row->end()) {
      try {
        return static_cast<long>(std::stoll(p_it->second));
      } catch (...) {
        return 0;
      }
    }
  }
  return 0;
}

double PositionInfo::GetDouble(const std::string &prop) const {
  if (!m_state || m_symbol.empty())
    return 0.0;

  const auto *row = FindSelectedRowConst(m_state, m_symbol);
  if (row != nullptr) {
    auto p_it = row->find(prop);
    if (p_it != row->end()) {
      try {
        return std::stod(p_it->second);
      } catch (...) {
        return 0.0;
      }
    }
  }
  return 0.0;
}

std::string PositionInfo::GetString(const std::string &prop) const {
  if (!m_state || m_symbol.empty())
    return "";

  const auto *row = FindSelectedRowConst(m_state, m_symbol);
  if (row != nullptr) {
    auto p_it = row->find(prop);
    if (p_it != row->end()) {
      return p_it->second;
    }
  }
  return "";
}

//--- Integer properties
long PositionInfo::Ticket() const { return GetInteger("ticket"); }
long PositionInfo::Time() const { return GetInteger("time"); }
long PositionInfo::TimeMsc() const { return GetInteger("time_msc"); }
long PositionInfo::TimeUpdate() const { return GetInteger("time_update"); }
long PositionInfo::TimeUpdateMsc() const {
  return GetInteger("time_update_msc");
}
long PositionInfo::Type() const { return GetInteger("type"); }
long PositionInfo::Magic() const { return GetInteger("magic"); }
long PositionInfo::Identifier() const { return GetInteger("identifier"); }
long PositionInfo::Reason() const { return GetInteger("reason"); }

//--- Double properties
double PositionInfo::Volume() const { return GetDouble("volume"); }
double PositionInfo::PriceOpen() const { return GetDouble("price_open"); }
double PositionInfo::Sl() const { return GetDouble("sl"); }
double PositionInfo::Tp() const { return GetDouble("tp"); }
double PositionInfo::PriceCurrent() const { return GetDouble("price_current"); }
double PositionInfo::Swap() const { return GetDouble("swap"); }
double PositionInfo::Profit() const { return GetDouble("profit"); }

//--- String properties
std::string PositionInfo::Symbol() const { return GetString("symbol"); }
std::string PositionInfo::Comment() const { return GetString("comment"); }
std::string PositionInfo::ExternalId() const {
  return GetString("external_id");
}

void PositionInfo::SetTicket(long value) {
  EnsureRow()["ticket"] = to_string_value(value);
}
void PositionInfo::SetTime(long value) {
  EnsureRow()["time"] = to_string_value(value);
}
void PositionInfo::SetTimeMsc(long value) {
  EnsureRow()["time_msc"] = to_string_value(value);
}
void PositionInfo::SetTimeUpdate(long value) {
  EnsureRow()["time_update"] = to_string_value(value);
}
void PositionInfo::SetTimeUpdateMsc(long value) {
  EnsureRow()["time_update_msc"] = to_string_value(value);
}
void PositionInfo::SetType(long value) {
  EnsureRow()["type"] = to_string_value(value);
}
void PositionInfo::SetMagic(long value) {
  EnsureRow()["magic"] = to_string_value(value);
}
void PositionInfo::SetIdentifier(long value) {
  EnsureRow()["identifier"] = to_string_value(value);
}
void PositionInfo::SetReason(long value) {
  EnsureRow()["reason"] = to_string_value(value);
}

void PositionInfo::SetVolume(double value) {
  EnsureRow()["volume"] = to_string_value(value);
}
void PositionInfo::SetPriceOpen(double value) {
  EnsureRow()["price_open"] = to_string_value(value);
}
void PositionInfo::SetSl(double value) {
  EnsureRow()["sl"] = to_string_value(value);
}
void PositionInfo::SetTp(double value) {
  EnsureRow()["tp"] = to_string_value(value);
}
void PositionInfo::SetPriceCurrent(double value) {
  EnsureRow()["price_current"] = to_string_value(value);
}
void PositionInfo::SetSwap(double value) {
  EnsureRow()["swap"] = to_string_value(value);
}
void PositionInfo::SetProfit(double value) {
  EnsureRow()["profit"] = to_string_value(value);
}

void PositionInfo::SetSymbol(const std::string &value) {
  m_symbol = value;
  EnsureRow()["symbol"] = value;
}
void PositionInfo::SetComment(const std::string &value) {
  EnsureRow()["comment"] = value;
}
void PositionInfo::SetExternalId(const std::string &value) {
  EnsureRow()["external_id"] = value;
}

} // namespace haruquant::trading
