#pragma once

#include "core/state.hpp"
#include <string>

namespace haruquant::trading {

class TerminalInfo {
private:
  const core::BacktestState *m_state;

protected:
  long GetInteger(const std::string &prop) const;
  double GetDouble(const std::string &prop) const;
  std::string GetString(const std::string &prop) const;

public:
  TerminalInfo();
  explicit TerminalInfo(const core::BacktestState *state);
  virtual ~TerminalInfo() = default;

  void SetState(const core::BacktestState *state);
  const core::BacktestState *GetState() const { return m_state; }

  //--- Integer properties
  long Build() const;
  long CommunityAccount() const;
  long CommunityConnection() const;
  long Connected() const;
  long DLLsAllowed() const;
  long TradeAllowed() const;
  long EmailEnabled() const;
  long FtpEnabled() const;
  long NotificationsEnabled() const;
  long MaxBars() const;
  long MQID() const;
  long CodePage() const;
  long CPUCores() const;
  long DiskSpace() const;
  long MemoryPhysical() const;
  long MemoryTotal() const;
  long MemoryAvailable() const;
  long MemoryUsed() const;
  long X64() const;
  long OpenCLSupport() const;
  long PingLast() const;

  //--- String properties
  std::string Language() const;
  std::string Company() const;
  std::string Name() const;
  std::string Path() const;
  std::string DataPath() const;
  std::string CommondataPath() const;
};

} // namespace haruquant::trading
