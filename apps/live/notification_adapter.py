"""Notification Adapter for Live Trading.

Provides backward-compatible interface to the new comprehensive notifications module.
Supports loading credentials from database or direct configuration.
"""

from typing import Dict, List, Optional

from backend.common.logger import logger
from apps.notifications import (
    NotificationLevel,
    NotificationManager,
    NotificationManagerConfig,
)
from apps.notifications.config import NotificationConfig
from apps.sqlite import SQLiteDatabase


class LiveTradingNotifier:
    """Adapter for notification services in live trading.

    Provides backward-compatible interface matching the old EmailNotifier
    while using the new comprehensive notifications module.
    """

    manager: Optional[NotificationManager]

    def __init__(
        self,
        enabled: bool,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        recipients: List[str],
        max_retries: int = 3,
    ):
        """Initialize live trading notifier.

        Args:
            enabled: Whether email notifications are enabled
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            recipients: List of recipient email addresses
            max_retries: Maximum retry attempts for sending (not used, kept for compatibility)
        """
        self.enabled = enabled

        if self.enabled:
            # Create notification configuration
            notif_config = NotificationConfig()
            notif_config.email_enabled = True
            notif_config.email_smtp_server = smtp_host
            notif_config.email_smtp_port = smtp_port
            notif_config.email_username = smtp_user
            notif_config.email_password = smtp_password
            notif_config.email_use_tls = True
            notif_config.email_from_email = smtp_user
            notif_config.email_default_recipients = recipients

            # Create manager configuration
            manager_config = NotificationManagerConfig(
                email_config=notif_config.get_email_config(),
                default_levels=[
                    NotificationLevel.INFO,
                    NotificationLevel.WARNING,
                    NotificationLevel.ERROR,
                    NotificationLevel.CRITICAL,
                ],
            )

            # Initialize notification manager
            self.manager = NotificationManager(manager_config)

            logger.info(
                f"LiveTradingNotifier initialized (host={smtp_host}, port={smtp_port}, recipients={len(recipients)})"
            )
        else:
            self.manager = None
            logger.info("LiveTradingNotifier initialized (disabled)")

    def notify_startup(self, symbol: str, timeframe: str, volume: float):
        """Send startup notification.

        Args:
            symbol: Trading symbol (or strategy list for multi-strategy)
            timeframe: Timeframe
            volume: Trading volume
        """
        if not self.enabled or not self.manager:
            return

        self.manager.send_system_alert(
            level=NotificationLevel.INFO,
            message="Live Trading System Started",
            details=f"System initialized and ready\n\nConfiguration:\n- Symbol/Strategies: {symbol}\n- Timeframe: {timeframe}\n- Volume: {volume} lots",
            component="Live Trading Engine",
            status="Running",
        )

    def notify_shutdown(self, reason: str = "Normal shutdown"):
        """Send shutdown notification.

        Args:
            reason: Reason for shutdown
        """
        if not self.enabled or not self.manager:
            return

        self.manager.send_system_alert(
            level=NotificationLevel.INFO,
            message="Live Trading System Stopped",
            details=f"System shutdown: {reason}",
            component="Live Trading Engine",
            status="Stopped",
        )

    def notify_signal(self, signal: Dict, executed: bool, error: Optional[str] = None):
        """Send signal notification.

        Args:
            signal: Signal dictionary
            executed: Whether trade was executed
            error: Error message if execution failed
        """
        if not self.enabled or not self.manager:
            return

        signal_type = signal.get("signal", "UNKNOWN")
        reason = signal.get("reason", "")
        entry_price = signal.get("entry_price", 0.0)
        symbol = signal.get("symbol", "UNKNOWN")
        strategy_name = signal.get("strategy_name", "Auto")

        if executed:
            # Send trading alert for successful execution
            self.manager.send_trading_alert(
                symbol=symbol,
                action=str(signal_type).upper(),
                price=float(entry_price),
                reason=str(reason),
                account="Live",
                strategy=strategy_name,
                risk_level="Medium",
            )
        else:
            # Send error alert for failed execution
            self.manager.send_error_alert(
                error_type="Trade Execution Failed",
                message=f"Failed to execute {str(signal_type).upper()} signal on {symbol}",
                component=f"Trade Executor - {strategy_name}",
                stack_trace=error or "No error details available",
            )

    def notify_safety_violation(self, reason: str):
        """Send safety check violation notification.

        Args:
            reason: Reason for safety violation
        """
        if not self.enabled or not self.manager:
            return

        self.manager.send_system_alert(
            level=NotificationLevel.WARNING,
            message="Safety Check Failed",
            details=f"Trading action blocked: {reason}",
            component="Safety Checker",
            status="Blocked",
        )

    def notify_connection_error(self, error: str):
        """Send connection error notification.

        Args:
            error: Error message
        """
        if not self.enabled or not self.manager:
            return

        self.manager.send_system_alert(
            level=NotificationLevel.ERROR,
            message="MT5 Connection Error",
            details=f"Connection error detected: {error}\n\nThe system will attempt to reconnect automatically.",
            component="MT5 Client",
            status="Error - Reconnecting",
        )

    def notify_daily_summary(self, trades: int, profit: float, positions: int):
        """Send daily summary notification.

        Args:
            trades: Number of trades executed today
            profit: Total profit/loss today
            positions: Current open positions
        """
        if not self.enabled or not self.manager:
            return

        self.manager.send_custom_message(
            title="Daily Trading Summary",
            body=f"""Daily Trading Summary

Trades Executed: {trades}
Total P/L: {profit:+.2f}
Open Positions: {positions}

Report generated at end of trading day.""",
            level=NotificationLevel.INFO,
        )

    def test_connection(self) -> bool:
        """Test notification services.

        Returns:
            True if connection successful
        """
        if not self.enabled or not self.manager:
            logger.info("Notifications disabled, skipping test")
            return True

        try:
            results = self.manager.test_all_services()
            email_success = results.get("email", False)

            if email_success:
                logger.info("Notification connection test successful")
            else:
                logger.error("Notification connection test failed")

            return email_success

        except Exception as e:
            logger.error(f"Notification connection test failed: {e}")
            return False

    @classmethod
    def from_database(
        cls, user_id: int, db_path: str = "backend/data/database/haruquant.db"
    ) -> "LiveTradingNotifier":
        """
        Create LiveTradingNotifier from database credentials.

        Args:
            user_id (int): User ID to fetch credentials for
            db_path (str): Path to SQLite database

        Returns:
            LiveTradingNotifier: Configured notifier instance
        """
        db = SQLiteDatabase(db_path=db_path)

        # Get notification settings from database
        email_creds = db.get_email_credentials(user_id)
        telegram_creds = db.get_telegram_credentials(user_id)

        if not email_creds and not telegram_creds:
            logger.warning(
                f"No notification credentials found for user {user_id}, creating disabled notifier"
            )
            return cls(
                enabled=False,
                smtp_host="",
                smtp_port=587,
                smtp_user="",
                smtp_password="",
                recipients=[],
            )

        # Create notification configuration
        notif_config = NotificationConfig()

        # Configure email if available
        if email_creds:
            notif_config.email_enabled = True
            notif_config.email_smtp_server = email_creds["smtp_host"]
            notif_config.email_smtp_port = email_creds["smtp_port"]
            notif_config.email_username = email_creds["smtp_user"]
            notif_config.email_password = email_creds["smtp_password"]
            notif_config.email_use_tls = email_creds.get("use_tls", True)
            notif_config.email_from_email = email_creds["smtp_user"]
            notif_config.email_default_recipients = email_creds["recipients"]
            logger.info(f"Email notifications enabled for user {user_id}")

        # Configure Telegram if available
        if telegram_creds:
            notif_config.telegram_enabled = True
            notif_config.telegram_bot_token = telegram_creds["bot_token"]
            notif_config.telegram_chat_ids = telegram_creds["chat_ids"]
            notif_config.telegram_parse_mode = telegram_creds.get("parse_mode", "HTML")
            notif_config.telegram_disable_web_page_preview = telegram_creds.get(
                "disable_web_page_preview", True
            )
            notif_config.telegram_disable_notification = telegram_creds.get(
                "disable_notification", False
            )
            logger.info(f"Telegram notifications enabled for user {user_id}")

        # Create manager configuration
        manager_config = NotificationManagerConfig(
            email_config=notif_config.get_email_config(),
            telegram_config=notif_config.get_telegram_config(),
            sms_config=notif_config.get_sms_config(),
            default_levels=[
                NotificationLevel.INFO,
                NotificationLevel.WARNING,
                NotificationLevel.ERROR,
                NotificationLevel.CRITICAL,
            ],
        )

        # Create instance with manager
        instance = cls.__new__(cls)
        instance.enabled = email_creds is not None or telegram_creds is not None
        instance.manager = NotificationManager(manager_config)

        logger.info(
            f"LiveTradingNotifier created from database for user {user_id} "
            f"(Email: {email_creds is not None}, Telegram: {telegram_creds is not None})"
        )

        return instance

    def __repr__(self) -> str:
        """Return string representation of LiveTradingNotifier."""
        return f"LiveTradingNotifier(enabled={self.enabled})"

