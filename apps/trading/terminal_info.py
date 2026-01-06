"""
TerminalInfo class for accessing terminal information.

This module provides a platform-agnostic implementation of terminal information
access, inspired by MT5's TerminalInfo.mqh but designed to work with any
trading platform through adapter patterns.

Copyright 2025, HaruQuant
"""

from typing import Any, Dict, Optional, Protocol


class TerminalDataProvider(Protocol):
    """
    Protocol for terminal data providers.

    Any trading platform adapter should implement this protocol
    to provide terminal information to the TerminalInfo class.
    """

    # Integer properties
    def get_build(self) -> int:
        """Get terminal build number."""
        ...

    def is_connected(self) -> bool:
        """Check if connected to trade server."""
        ...

    def is_dlls_allowed(self) -> bool:
        """Check if DLLs are allowed."""
        ...

    def is_trade_allowed(self) -> bool:
        """Check if trading is allowed."""
        ...

    def is_email_enabled(self) -> bool:
        """Check if email sending is enabled."""
        ...

    def is_ftp_enabled(self) -> bool:
        """Check if FTP is enabled."""
        ...

    def get_max_bars(self) -> int:
        """Get maximum bars in chart."""
        ...

    def get_code_page(self) -> int:
        """Get code page."""
        ...

    def get_cpu_cores(self) -> int:
        """Get number of CPU cores."""
        ...

    def get_memory_physical(self) -> int:
        """Get physical memory in MB."""
        ...

    def get_memory_total(self) -> int:
        """Get total memory in MB."""
        ...

    def get_memory_available(self) -> int:
        """Get available memory in MB."""
        ...

    def get_memory_used(self) -> int:
        """Get used memory in MB."""
        ...

    def is_x64(self) -> bool:
        """Check if terminal is 64-bit."""
        ...

    def get_opencl_support(self) -> int:
        """Get OpenCL support level."""
        ...

    def get_disk_space(self) -> int:
        """Get free disk space in MB."""
        ...

    # String properties
    def get_language(self) -> str:
        """Get terminal language."""
        ...

    def get_name(self) -> str:
        """Get terminal name."""
        ...

    def get_company(self) -> str:
        """Get company name."""
        ...

    def get_path(self) -> str:
        """Get terminal installation path."""
        ...

    def get_data_path(self) -> str:
        """Get terminal data folder path."""
        ...

    def get_common_data_path(self) -> str:
        """Get common data folder path."""
        ...

    # Direct API access
    def info_integer(self, prop_id: str) -> Optional[int]:
        """Get integer property by ID."""
        ...

    def info_string(self, prop_id: str) -> Optional[str]:
        """Get string property by ID."""
        ...


class MT5TerminalProvider:
    """
    Implementation of TerminalDataProvider using MT5Client.

    This class adapts an MT5Client instance to the TerminalDataProvider protocol,
    providing access to terminal information from MT5.
    """

    def __init__(self, mt5_client):
        """
        Initialize MT5TerminalProvider.

        Args:
            mt5_client: Instance of MT5Client with active connection
        """
        self._client = mt5_client
        self._terminal_data: Dict[str, Any] = {}
        self._refresh_terminal_data()

    def _refresh_terminal_data(self) -> None:
        """Refresh terminal data from MT5."""
        data = self._client.fetch_terminal_info()
        if data:
            self._terminal_data = data
        else:
            self._terminal_data = {}

    def get_build(self) -> int:
        """Get build number."""
        return int(self._terminal_data.get("build", 0))

    def is_connected(self) -> bool:
        """Check if connected."""
        return bool(self._terminal_data.get("connected", False))

    def is_dlls_allowed(self) -> bool:
        """Check if DLLs allowed."""
        return bool(self._terminal_data.get("dlls_allowed", False))

    def is_trade_allowed(self) -> bool:
        """Check if trade allowed."""
        return bool(self._terminal_data.get("trade_allowed", False))

    def is_email_enabled(self) -> bool:
        """Check if email enabled."""
        return bool(self._terminal_data.get("email_enabled", False))

    def is_ftp_enabled(self) -> bool:
        """Check if FTP enabled."""
        return bool(self._terminal_data.get("ftp_enabled", False))

    def get_max_bars(self) -> int:
        """Get max bars."""
        return int(self._terminal_data.get("maxbars", 0))

    def get_code_page(self) -> int:
        """Get code page."""
        return int(self._terminal_data.get("codepage", 0))

    def get_cpu_cores(self) -> int:
        """Get CPU cores."""
        return int(self._terminal_data.get("cpu_cores", 1))

    def get_memory_physical(self) -> int:
        """Get physical memory."""
        return int(self._terminal_data.get("memory_physical", 0))

    def get_memory_total(self) -> int:
        """Get total memory."""
        return int(self._terminal_data.get("memory_total", 0))

    def get_memory_available(self) -> int:
        """Get available memory."""
        return int(self._terminal_data.get("memory_available", 0))

    def get_memory_used(self) -> int:
        """Get used memory."""
        return int(self._terminal_data.get("memory_used", 0))

    def is_x64(self) -> bool:
        """Check if x64."""
        return bool(self._terminal_data.get("x64", False))

    def get_opencl_support(self) -> int:
        """Get OpenCL support."""
        return int(self._terminal_data.get("opencl_support", 0))

    def get_disk_space(self) -> int:
        """Get disk space."""
        return int(self._terminal_data.get("disk_space", 0))

    def get_language(self) -> str:
        """Get language."""
        return str(self._terminal_data.get("language", ""))

    def get_name(self) -> str:
        """Get terminal name."""
        return str(self._terminal_data.get("name", ""))

    def get_company(self) -> str:
        """Get company."""
        return str(self._terminal_data.get("company", ""))

    def get_path(self) -> str:
        """Get path."""
        return str(self._terminal_data.get("path", ""))

    def get_data_path(self) -> str:
        """Get data path."""
        return str(self._terminal_data.get("data_path", ""))

    def get_common_data_path(self) -> str:
        """Get common data path."""
        return str(self._terminal_data.get("commondata_path", ""))

    def info_integer(self, prop_id: str) -> Optional[int]:
        """Get info integer."""
        return self._terminal_data.get(prop_id)

    def info_string(self, prop_id: str) -> Optional[str]:
        """Get info string."""
        return self._terminal_data.get(prop_id)


class TerminalInfo:
    """
    Class for accessing terminal information.

    This class provides a clean interface to terminal information
    regardless of the underlying trading platform. It uses a data
    provider pattern to abstract platform-specific implementations.

    Usage:
        # With MT5 provider for live trading
        from apps.mt5 import MT5Client
        from apps.trade import TerminalInfo, MT5TerminalProvider

        client = MT5Client()
        client.initialize()
        provider = MT5TerminalProvider(client)
        terminal = TerminalInfo(provider)

        # Access terminal information
        print(f"Terminal: {terminal.name()}")
        print(f"Build: {terminal.build()}")
        print(f"Connected: {terminal.is_connected()}")
        print(f"Language: {terminal.language()}")
    """

    def __init__(self, data_provider: TerminalDataProvider):
        """
        Initialize TerminalInfo.

        Args:
            data_provider: Platform-specific data provider implementing
                          TerminalDataProvider protocol.
                          Use MT5TerminalProvider for live trading.
        """
        self._provider = data_provider

    # Fast access methods to integer terminal properties

    def build(self) -> int:
        """
        Get terminal build number.

        Returns:
            Terminal build number.
        """
        return self._provider.get_build()

    def is_connected(self) -> bool:
        """
        Check if terminal is connected to trade server.

        Returns:
            True if connected, False otherwise.
        """
        return self._provider.is_connected()

    def is_dlls_allowed(self) -> bool:
        """
        Check if DLLs are allowed to be loaded.

        Returns:
            True if DLLs are allowed, False otherwise.
        """
        return self._provider.is_dlls_allowed()

    def is_trade_allowed(self) -> bool:
        """
        Check if trading is allowed in the terminal.

        Returns:
            True if trading is allowed, False otherwise.
        """
        return self._provider.is_trade_allowed()

    def is_email_enabled(self) -> bool:
        """
        Check if email sending is enabled.

        Returns:
            True if email is enabled, False otherwise.
        """
        return self._provider.is_email_enabled()

    def is_ftp_enabled(self) -> bool:
        """
        Check if FTP is enabled.

        Returns:
            True if FTP is enabled, False otherwise.
        """
        return self._provider.is_ftp_enabled()

    def max_bars(self) -> int:
        """
        Get maximum bars in chart.

        Returns:
            Maximum number of bars in chart.
        """
        return self._provider.get_max_bars()

    def code_page(self) -> int:
        """
        Get code page of the language installed in the terminal.

        Returns:
            Code page number.
        """
        return self._provider.get_code_page()

    def cpu_cores(self) -> int:
        """
        Get number of physical CPU cores.

        Returns:
            Number of CPU cores.
        """
        return self._provider.get_cpu_cores()

    def memory_physical(self) -> int:
        """
        Get physical memory size in MB.

        Returns:
            Physical memory in megabytes.
        """
        return self._provider.get_memory_physical()

    def memory_total(self) -> int:
        """
        Get total memory size available for terminal in MB.

        Returns:
            Total memory in megabytes.
        """
        return self._provider.get_memory_total()

    def memory_available(self) -> int:
        """
        Get free memory available for terminal in MB.

        Returns:
            Available memory in megabytes.
        """
        return self._provider.get_memory_available()

    def memory_used(self) -> int:
        """
        Get memory used by terminal in MB.

        Returns:
            Used memory in megabytes.
        """
        return self._provider.get_memory_used()

    def is_x64(self) -> bool:
        """
        Check if terminal is 64-bit.

        Returns:
            True if 64-bit terminal, False if 32-bit.
        """
        return self._provider.is_x64()

    def opencl_support(self) -> int:
        """
        Get OpenCL support level.

        Returns:
            OpenCL support level (0 = not supported, 1+ = supported).
        """
        return self._provider.get_opencl_support()

    def disk_space(self) -> int:
        """
        Get free disk space in MB on the drive where terminal is installed.

        Returns:
            Free disk space in megabytes.
        """
        return self._provider.get_disk_space()

    # Fast access methods to string terminal properties

    def language(self) -> str:
        """
        Get language of the terminal.

        Returns:
            Language code (e.g., "English", "Russian", "Chinese").
        """
        return self._provider.get_language()

    def name(self) -> str:
        """
        Get terminal name.

        Returns:
            Terminal application name.
        """
        return self._provider.get_name()

    def company(self) -> str:
        """
        Get name of company owning the terminal.

        Returns:
            Company name.
        """
        return self._provider.get_company()

    def path(self) -> str:
        """
        Get folder where terminal is installed.

        Returns:
            Path to terminal installation directory.
        """
        return self._provider.get_path()

    def data_path(self) -> str:
        """
        Get folder where terminal data is stored.

        Returns:
            Path to terminal data directory.
        """
        return self._provider.get_data_path()

    def common_data_path(self) -> str:
        """
        Get common folder for all terminals installed on the computer.

        Returns:
            Path to common data directory.
        """
        return self._provider.get_common_data_path()

    # Direct API access methods

    def info_integer(self, prop_id: str) -> Optional[int]:
        """
        Get integer property by ID.

        Args:
            prop_id: Property identifier.

        Returns:
            Property value or None if not available.
        """
        return self._provider.info_integer(prop_id)

    def info_string(self, prop_id: str) -> Optional[str]:
        """
        Get string property by ID.

        Args:
            prop_id: Property identifier.

        Returns:
            Property value or None if not available.
        """
        return self._provider.info_string(prop_id)

    # Helper methods

    def get_system_info(self) -> dict:
        """
        Get system information summary.

        Returns:
            Dictionary with key system information.
        """
        return {
            "cpu_cores": self.cpu_cores(),
            "memory_physical": self.memory_physical(),
            "memory_total": self.memory_total(),
            "memory_available": self.memory_available(),
            "memory_used": self.memory_used(),
            "disk_space": self.disk_space(),
            "is_x64": self.is_x64(),
            "opencl_support": self.opencl_support(),
        }

    def get_connection_info(self) -> dict:
        """
        Get connection and permissions information.

        Returns:
            Dictionary with connection and permission settings.
        """
        return {
            "is_connected": self.is_connected(),
            "is_trade_allowed": self.is_trade_allowed(),
            "is_dlls_allowed": self.is_dlls_allowed(),
            "is_email_enabled": self.is_email_enabled(),
            "is_ftp_enabled": self.is_ftp_enabled(),
        }

    def format_memory_info(self) -> str:
        """
        Format memory information as a readable string.

        Returns:
            Formatted memory information.
        """
        return (
            f"Memory: {self.memory_used()}MB used / "
            f"{self.memory_available()}MB available / "
            f"{self.memory_total()}MB total "
            f"(Physical: {self.memory_physical()}MB)"
        )

    def __repr__(self) -> str:
        """Return string representation of TerminalInfo."""
        try:
            return (
                f"TerminalInfo(name={self.name()}, "
                f"build={self.build()}, "
                f"connected={self.is_connected()}, "
                f"language={self.language()})"
            )
        except Exception:
            return "TerminalInfo(no data available)"
