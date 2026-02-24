#pragma once

#include "core/state.hpp"
#include <memory>
#include <string>

namespace haruquant::trading {

class TerminalInfo {
private:
  std::shared_ptr<core::BacktestState> m_state;
  core::BacktestState &EnsureState();

protected:
  long GetInteger(const std::string &prop) const;
  double GetDouble(const std::string &prop) const;
  std::string GetString(const std::string &prop) const;

public:
  TerminalInfo();
  explicit TerminalInfo(std::shared_ptr<core::BacktestState> state);
  virtual ~TerminalInfo() = default;

  void SetState(std::shared_ptr<core::BacktestState> state);
  const core::BacktestState *GetState() const { return m_state.get(); }
  const std::shared_ptr<core::BacktestState> &GetSharedState() const {
    return m_state;
  }

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

  //--- Setters for snapshot-style initialization from Python/bridge.
  void SetBuild(long value);
  void SetCommunityAccount(long value);
  void SetCommunityConnection(long value);
  void SetConnected(long value);
  void SetDLLsAllowed(long value);
  void SetTradeAllowed(long value);
  void SetEmailEnabled(long value);
  void SetFtpEnabled(long value);
  void SetNotificationsEnabled(long value);
  void SetMaxBars(long value);
  void SetMQID(long value);
  void SetCodePage(long value);
  void SetCPUCores(long value);
  void SetDiskSpace(long value);
  void SetMemoryPhysical(long value);
  void SetMemoryTotal(long value);
  void SetMemoryAvailable(long value);
  void SetMemoryUsed(long value);
  void SetX64(long value);
  void SetOpenCLSupport(long value);
  void SetPingLast(long value);

  void SetLanguage(const std::string &value);
  void SetCompany(const std::string &value);
  void SetName(const std::string &value);
  void SetPath(const std::string &value);
  void SetDataPath(const std::string &value);
  void SetCommondataPath(const std::string &value);
};

} // namespace haruquant::trading
