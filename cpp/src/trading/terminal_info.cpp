#include "trading/terminal_info.hpp"
#include <stdexcept>
#include <string>

namespace haruquant::trading {

TerminalInfo::TerminalInfo() : m_state(nullptr) {}

TerminalInfo::TerminalInfo(const core::BacktestState *state) : m_state(state) {}

void TerminalInfo::SetState(const core::BacktestState *state) {
  m_state = state;
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

} // namespace haruquant::trading
