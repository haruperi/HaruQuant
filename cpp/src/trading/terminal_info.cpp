#include "trading/terminal_info.hpp"
#include <sstream>
#include <string>

namespace haruquant::trading {

TerminalInfo::TerminalInfo() : m_state(std::make_shared<core::BacktestState>()) {}

TerminalInfo::TerminalInfo(std::shared_ptr<core::BacktestState> state)
    : m_state(std::move(state)) {
  EnsureState();
}

void TerminalInfo::SetState(std::shared_ptr<core::BacktestState> state) {
  m_state = std::move(state);
  EnsureState();
}

core::BacktestState &TerminalInfo::EnsureState() {
  if (!m_state) {
    m_state = std::make_shared<core::BacktestState>();
  }
  return *m_state;
}

long TerminalInfo::GetInteger(const std::string &prop) const {
  if (!m_state)
    return 0;
  auto it = m_state->terminal_info.find(prop);
  if (it != m_state->terminal_info.end()) {
    try {
      return static_cast<long>(std::stoll(it->second));
    } catch (...) {
      return 0;
    }
  }
  return 0;
}

double TerminalInfo::GetDouble(const std::string &prop) const {
  if (!m_state)
    return 0.0;
  auto it = m_state->terminal_info.find(prop);
  if (it != m_state->terminal_info.end()) {
    try {
      return std::stod(it->second);
    } catch (...) {
      return 0.0;
    }
  }
  return 0.0;
}

std::string TerminalInfo::GetString(const std::string &prop) const {
  if (!m_state)
    return "";
  auto it = m_state->terminal_info.find(prop);
  if (it != m_state->terminal_info.end()) {
    return it->second;
  }
  return "";
}

//--- Integer properties
long TerminalInfo::Build() const { return GetInteger("build"); }
long TerminalInfo::CommunityAccount() const {
  return GetInteger("community_account");
}
long TerminalInfo::CommunityConnection() const {
  return GetInteger("community_connection");
}
long TerminalInfo::Connected() const { return GetInteger("connected"); }
long TerminalInfo::DLLsAllowed() const { return GetInteger("dlls_allowed"); }
long TerminalInfo::TradeAllowed() const { return GetInteger("trade_allowed"); }
long TerminalInfo::EmailEnabled() const { return GetInteger("email_enabled"); }
long TerminalInfo::FtpEnabled() const { return GetInteger("ftp_enabled"); }
long TerminalInfo::NotificationsEnabled() const {
  return GetInteger("notifications_enabled");
}
long TerminalInfo::MaxBars() const { return GetInteger("maxbars"); }
long TerminalInfo::MQID() const { return GetInteger("mqid"); }
long TerminalInfo::CodePage() const { return GetInteger("codepage"); }
long TerminalInfo::CPUCores() const { return GetInteger("cpu_cores"); }
long TerminalInfo::DiskSpace() const { return GetInteger("disk_space"); }
long TerminalInfo::MemoryPhysical() const {
  return GetInteger("memory_physical");
}
long TerminalInfo::MemoryTotal() const { return GetInteger("memory_total"); }
long TerminalInfo::MemoryAvailable() const {
  return GetInteger("memory_available");
}
long TerminalInfo::MemoryUsed() const { return GetInteger("memory_used"); }
long TerminalInfo::X64() const { return GetInteger("x64"); }
long TerminalInfo::OpenCLSupport() const {
  return GetInteger("opencl_support");
}
long TerminalInfo::PingLast() const { return GetInteger("ping_last"); }

//--- String properties
std::string TerminalInfo::Language() const { return GetString("language"); }
std::string TerminalInfo::Company() const { return GetString("company"); }
std::string TerminalInfo::Name() const { return GetString("name"); }
std::string TerminalInfo::Path() const { return GetString("path"); }
std::string TerminalInfo::DataPath() const { return GetString("data_path"); }
std::string TerminalInfo::CommondataPath() const {
  return GetString("commondata_path");
}

namespace {
template <typename T>
std::string to_string_value(T value) {
  std::ostringstream oss;
  oss << value;
  return oss.str();
}
} // namespace

void TerminalInfo::SetBuild(long value) {
  EnsureState().terminal_info["build"] = to_string_value(value);
}
void TerminalInfo::SetCommunityAccount(long value) {
  EnsureState().terminal_info["community_account"] = to_string_value(value);
}
void TerminalInfo::SetCommunityConnection(long value) {
  EnsureState().terminal_info["community_connection"] = to_string_value(value);
}
void TerminalInfo::SetConnected(long value) {
  EnsureState().terminal_info["connected"] = to_string_value(value);
}
void TerminalInfo::SetDLLsAllowed(long value) {
  EnsureState().terminal_info["dlls_allowed"] = to_string_value(value);
}
void TerminalInfo::SetTradeAllowed(long value) {
  EnsureState().terminal_info["trade_allowed"] = to_string_value(value);
}
void TerminalInfo::SetEmailEnabled(long value) {
  EnsureState().terminal_info["email_enabled"] = to_string_value(value);
}
void TerminalInfo::SetFtpEnabled(long value) {
  EnsureState().terminal_info["ftp_enabled"] = to_string_value(value);
}
void TerminalInfo::SetNotificationsEnabled(long value) {
  EnsureState().terminal_info["notifications_enabled"] = to_string_value(value);
}
void TerminalInfo::SetMaxBars(long value) {
  EnsureState().terminal_info["maxbars"] = to_string_value(value);
}
void TerminalInfo::SetMQID(long value) {
  EnsureState().terminal_info["mqid"] = to_string_value(value);
}
void TerminalInfo::SetCodePage(long value) {
  EnsureState().terminal_info["codepage"] = to_string_value(value);
}
void TerminalInfo::SetCPUCores(long value) {
  EnsureState().terminal_info["cpu_cores"] = to_string_value(value);
}
void TerminalInfo::SetDiskSpace(long value) {
  EnsureState().terminal_info["disk_space"] = to_string_value(value);
}
void TerminalInfo::SetMemoryPhysical(long value) {
  EnsureState().terminal_info["memory_physical"] = to_string_value(value);
}
void TerminalInfo::SetMemoryTotal(long value) {
  EnsureState().terminal_info["memory_total"] = to_string_value(value);
}
void TerminalInfo::SetMemoryAvailable(long value) {
  EnsureState().terminal_info["memory_available"] = to_string_value(value);
}
void TerminalInfo::SetMemoryUsed(long value) {
  EnsureState().terminal_info["memory_used"] = to_string_value(value);
}
void TerminalInfo::SetX64(long value) {
  EnsureState().terminal_info["x64"] = to_string_value(value);
}
void TerminalInfo::SetOpenCLSupport(long value) {
  EnsureState().terminal_info["opencl_support"] = to_string_value(value);
}
void TerminalInfo::SetPingLast(long value) {
  EnsureState().terminal_info["ping_last"] = to_string_value(value);
}

void TerminalInfo::SetLanguage(const std::string &value) {
  EnsureState().terminal_info["language"] = value;
}
void TerminalInfo::SetCompany(const std::string &value) {
  EnsureState().terminal_info["company"] = value;
}
void TerminalInfo::SetName(const std::string &value) {
  EnsureState().terminal_info["name"] = value;
}
void TerminalInfo::SetPath(const std::string &value) {
  EnsureState().terminal_info["path"] = value;
}
void TerminalInfo::SetDataPath(const std::string &value) {
  EnsureState().terminal_info["data_path"] = value;
}
void TerminalInfo::SetCommondataPath(const std::string &value) {
  EnsureState().terminal_info["commondata_path"] = value;
}

} // namespace haruquant::trading
