"""
TerminalInfo class (MT5-specific).

This module mirrors the MQL5 Standard Library TerminalInfo interface and
order/grouping for MT5 usage.
Reference: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/cterminalinfo
"""

from __future__ import annotations

from typing import Any, Optional

from apps.mt5 import get_mt5_api

mt5 = get_mt5_api()


class TerminalInfo:
    """
    Class for handling terminal properties in MT5.

    This class is based on the MQL5 Standard Library TerminalInfo API.
    """

    def __init__(self, api: Optional[Any] = None) -> None:
        """Initialize."""
        self._api = api if api is not None else get_mt5_api()
        self._terminal_info: dict[str, Any] = {}

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _fetch_terminal_info(self) -> bool:
        info = self._api.terminal_info()
        if info is None:
            self._terminal_info = {}
            return False
        self._terminal_info = info._asdict()
        return True

    def _ensure_info(self) -> None:
        if not self._terminal_info:
            self._fetch_terminal_info()

    def _cached(self, default: Any, *keys: str) -> Any:
        self._ensure_info()
        for key in keys:
            if key in self._terminal_info and self._terminal_info[key] is not None:
                return self._terminal_info[key]
        return default

    def _info_integer(self, prop: Optional[int]) -> Optional[int]:
        if prop is None:
            return None
        if hasattr(self._api, "terminal_info_integer"):
            value = self._api.terminal_info_integer(prop)
        return int(value) if value is not None else None
        return None

    def _info_string(self, prop: Optional[int]) -> Optional[str]:
        if prop is None:
            return None
        if hasattr(self._api, "terminal_info_string"):
            value = self._api.terminal_info_string(prop)
        return str(value) if value is not None else None
        return None

    def _int_prop(self, const_name: str, default: int, *keys: str) -> int:
        prop = getattr(mt5, const_name, None)
        value = self._info_integer(prop)
        if value is not None:
            return int(value)
        return int(self._cached(default, *keys))

    def _string_prop(self, const_name: str, default: str, *keys: str) -> str:
        prop = getattr(mt5, const_name, None)
        value = self._info_string(prop)
        if value is not None:
            return str(value)
        return str(self._cached(default, *keys))

    # ---------------------------------------------------------------------
    # Terminal Identification
    # ---------------------------------------------------------------------
    def Build(self) -> int:
        """Get the build number of the client terminal."""
        return self._int_prop("TERMINAL_BUILD", 0, "build")

    def Language(self) -> str:
        """Get the language of the client terminal."""
        return self._string_prop("TERMINAL_LANGUAGE", "", "language")

    def Name(self) -> str:
        """Get the name of the client terminal."""
        return self._string_prop("TERMINAL_NAME", "", "name")

    def Company(self) -> str:
        """Get the company name of the client terminal."""
        return self._string_prop("TERMINAL_COMPANY", "", "company")

    def Path(self) -> str:
        """Get the folder of the client terminal."""
        return self._string_prop("TERMINAL_PATH", "", "path")

    def DataPath(self) -> str:
        """Get the data folder of the client terminal."""
        return self._string_prop("TERMINAL_DATA_PATH", "", "data_path")

    def CommonDataPath(self) -> str:
        """Get the common data folder of all client terminals."""
        return self._string_prop("TERMINAL_COMMONDATA_PATH", "", "common_data_path")

    # ---------------------------------------------------------------------
    # Terminal State and Permissions
    # ---------------------------------------------------------------------
    def IsConnected(self) -> bool:
        """Get the information about connection to trade server."""
        return bool(self._int_prop("TERMINAL_CONNECTED", 0, "connected"))

    def IsDLLsAllowed(self) -> bool:
        """Get the information about permission of DLL usage."""
        return bool(self._int_prop("TERMINAL_DLLS_ALLOWED", 0, "dlls_allowed"))

    def IsTradeAllowed(self) -> bool:
        """Get the information about permission to trade."""
        return bool(self._int_prop("TERMINAL_TRADE_ALLOWED", 0, "trade_allowed"))

    def IsEmailEnabled(self) -> bool:
        """Get the information about permission to send e-mails."""
        return bool(self._int_prop("TERMINAL_EMAIL_ENABLED", 0, "email_enabled"))

    def IsFtpEnabled(self) -> bool:
        """Get the information about permission to send trade reports to FTP."""
        return bool(self._int_prop("TERMINAL_FTP_ENABLED", 0, "ftp_enabled"))

    def GetConnectionInfo(self) -> dict[str, Any]:
        """Get a dictionary of connection information."""
        return {
            "connected": self.IsConnected(),
            "trade_allowed": self.IsTradeAllowed(),
            "dlls_allowed": self.IsDLLsAllowed(),
            "email_enabled": self.IsEmailEnabled(),
            "ftp_enabled": self.IsFtpEnabled(),
        }

    # ---------------------------------------------------------------------
    # System Resources
    # ---------------------------------------------------------------------
    def CPUCores(self) -> int:
        """Get the information about the CPU cores."""
        return self._int_prop("TERMINAL_CPU_CORES", 0, "cpu_cores")

    def MemoryPhysical(self) -> int:
        """Get the information about the physical memory (in Mb)."""
        return self._int_prop("TERMINAL_MEMORY_PHYSICAL", 0, "memory_physical")

    def MemoryTotal(self) -> int:
        """Get the information about the total memory (in Mb)."""
        return self._int_prop("TERMINAL_MEMORY_TOTAL", 0, "memory_total")

    def MemoryAvailable(self) -> int:
        """Get the information about the free memory (in Mb)."""
        return self._int_prop("TERMINAL_MEMORY_AVAILABLE", 0, "memory_available")

    def MemoryUsed(self) -> int:
        """Get the information about the memory used (in Mb)."""
        return self._int_prop("TERMINAL_MEMORY_USED", 0, "memory_used")

    def DiskSpace(self) -> int:
        """Get the information about free disk space (in Mb)."""
        return self._int_prop("TERMINAL_DISK_SPACE", 0, "disk_space")

    def MaxBars(self) -> int:
        """Get the information about maximum number of bars on chart."""
        return self._int_prop("TERMINAL_MAXBARS", 0, "maxbars", "max_bars")

    def CodePage(self) -> int:
        """Get the information about the code page of the language."""
        return self._int_prop("TERMINAL_CODEPAGE", 0, "codepage", "code_page")

    def IsX64(self) -> bool:
        """Get the information about the type of the client terminal."""
        return bool(self._int_prop("TERMINAL_X64", 0, "x64"))

    def OpenCLSupport(self) -> int:
        """Get the information about the version of OpenCL supported."""
        return self._int_prop("TERMINAL_OPENCL_SUPPORT", 0, "opencl_support")

    def GetSystemInfo(self) -> dict[str, Any]:
        """Get a dictionary of system information."""
        return {
            "cpu_cores": self.CPUCores(),
            "memory_physical": self.MemoryPhysical(),
            "memory_total": self.MemoryTotal(),
            "memory_available": self.MemoryAvailable(),
            "memory_used": self.MemoryUsed(),
            "disk_space": self.DiskSpace(),
            "opencl_support": self.OpenCLSupport(),
            "is_x64": self.IsX64(),
        }

    # ---------------------------------------------------------------------
    # Terminal Settings
    # ---------------------------------------------------------------------
    def InfoInteger(self, prop: Any) -> Optional[int]:
        """Get the value of the property of integer type."""
        if isinstance(prop, int) and hasattr(self._api, "terminal_info_integer"):
            value = self._api.terminal_info_integer(prop)
            return int(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return int(value) if value is not None else None
        return None

    def InfoString(self, prop: Any) -> Optional[str]:
        """Get the value of property of string type."""
        if isinstance(prop, int) and hasattr(self._api, "terminal_info_string"):
            value = self._api.terminal_info_string(prop)
            return str(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return str(value) if value is not None else None
        return None
