#include "trading/position_info.hpp"
#include <sstream>
#include <string>

namespace haruquant::trading {

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

core::BacktestState::Dictionary &PositionInfo::EnsureRow() {
  auto &state = EnsureState();
  if (m_symbol.empty()) {
    m_symbol = "UNKNOWN";
  }
  return state.trading_positions[m_symbol];
}

bool PositionInfo::Select(const std::string &symbol) {
  if (!m_state)
    return false;
  auto it = m_state->trading_positions.find(symbol);
  if (it != m_state->trading_positions.end()) {
    m_symbol = symbol;
    return true;
  }
  return false;
}

bool PositionInfo::SelectByTicket(const long ticket) {
  if (!m_state)
    return false;
  std::string t_str = std::to_string(ticket);
  for (const auto &kv : m_state->trading_positions) {
    auto it = kv.second.find("ticket");
    if (it != kv.second.end() && it->second == t_str) {
      m_symbol =
          kv.first; // Dictionary key is typically symbol, but MT5 supports
                    // multiple positions per symbol in hedged mode. Assuming
                    // symbol as key for now based on context.
      return true;
    }
  }
  return false;
}

bool PositionInfo::SelectByIndex(const int index) {
  if (!m_state || index < 0)
    return false;

  int i = 0;
  for (const auto &kv : m_state->trading_positions) {
    if (i == index) {
      m_symbol = kv.first;
      return true;
    }
    i++;
  }
  return false;
}

long PositionInfo::GetInteger(const std::string &prop) const {
  if (!m_state || m_symbol.empty())
    return 0;

  auto t_it = m_state->trading_positions.find(m_symbol);
  if (t_it != m_state->trading_positions.end()) {
    auto p_it = t_it->second.find(prop);
    if (p_it != t_it->second.end()) {
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

  auto t_it = m_state->trading_positions.find(m_symbol);
  if (t_it != m_state->trading_positions.end()) {
    auto p_it = t_it->second.find(prop);
    if (p_it != t_it->second.end()) {
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

  auto t_it = m_state->trading_positions.find(m_symbol);
  if (t_it != m_state->trading_positions.end()) {
    auto p_it = t_it->second.find(prop);
    if (p_it != t_it->second.end()) {
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

namespace {
template <typename T>
std::string to_string_value(T value) {
  std::ostringstream oss;
  oss << value;
  return oss.str();
}
} // namespace

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
  std::string old_key = m_symbol;
  m_symbol = value;
  auto &state = EnsureState();
  if (!old_key.empty() && old_key != m_symbol) {
    auto it = state.trading_positions.find(old_key);
    if (it != state.trading_positions.end()) {
      state.trading_positions[m_symbol] = it->second;
      state.trading_positions.erase(it);
    }
  }
  EnsureRow()["symbol"] = value;
}
void PositionInfo::SetComment(const std::string &value) {
  EnsureRow()["comment"] = value;
}
void PositionInfo::SetExternalId(const std::string &value) {
  EnsureRow()["external_id"] = value;
}

} // namespace haruquant::trading
