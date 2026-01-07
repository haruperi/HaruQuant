"""Email Notifications.

Send email alerts for trading events via SMTP.
"""

import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

from apps.logger import logger


class EmailNotifier:
    """Send email notifications for trading events."""

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
        """Initialize email notifier.

        Args:
            enabled: Whether email notifications are enabled
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            recipients: List of recipient email addresses
            max_retries: Maximum retry attempts for sending
        """
        self.enabled = enabled
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.recipients = recipients
        self.max_retries = max_retries

        if self.enabled:
            logger.info(
                f"EmailNotifier initialized (host={smtp_host}, port={smtp_port}, recipients={len(recipients)})"
            )
        else:
            logger.info("EmailNotifier initialized (disabled)")

    def notify_startup(self, symbol: str, timeframe: str, volume: float):
        """Send startup notification.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            volume: Trading volume
        """
        if not self.enabled:
            return

        subject = "Live Trading System Started"
        body = f"""
Live Trading System Started

Symbol: {symbol}
Timeframe: {timeframe}
Volume: {volume} lots
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The system is now monitoring for signals.
"""

        self._send_email(subject, body)

    def notify_shutdown(self, reason: str = "Normal shutdown"):
        """Send shutdown notification.

        Args:
            reason: Reason for shutdown
        """
        if not self.enabled:
            return

        subject = "Live Trading System Stopped"
        body = f"""
Live Trading System Stopped

Reason: {reason}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The system has been shut down.
"""

        self._send_email(subject, body)

    def notify_signal(self, signal: Dict, executed: bool, error: Optional[str] = None):
        """Send signal notification.

        Args:
            signal: Signal dictionary
            executed: Whether trade was executed
            error: Error message if execution failed
        """
        if not self.enabled:
            return

        signal_type = signal.get("signal")
        signal_time = signal.get("time")
        reason = signal.get("reason")
        entry_price = signal.get("entry_price")

        signal_str = str(signal_type or "UNKNOWN")

        if executed:
            subject = f"Trade Executed: {signal_str.upper()}"
            status = "SUCCESS"
        else:
            subject = f"Trade Failed: {signal_str.upper()}"
            status = "FAILED"

        body = f"""
Signal Detected and Trade {status}

Signal: {signal_str.upper()}
Time: {signal_time}
Reason: {reason}
Entry Price: {entry_price:.5f}

Execution Status: {status}
"""

        if error:
            body += f"\nError: {error}"

        body += f"\n\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        self._send_email(subject, body)

    def notify_safety_violation(self, reason: str):
        """Send safety check violation notification.

        Args:
            reason: Reason for safety violation
        """
        if not self.enabled:
            return

        subject = "Safety Check Failed"
        body = f"""
Safety Check Violation

Reason: {reason}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Trading action was blocked due to safety check failure.
"""

        self._send_email(subject, body)

    def notify_connection_error(self, error: str):
        """Send connection error notification.

        Args:
            error: Error message
        """
        if not self.enabled:
            return

        subject = "MT5 Connection Error"
        body = f"""
MT5 Connection Error Detected

Error: {error}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The system will attempt to reconnect automatically.
"""

        self._send_email(subject, body)

    def notify_daily_summary(self, trades: int, profit: float, positions: int):
        """Send daily summary notification.

        Args:
            trades: Number of trades executed today
            profit: Total profit/loss today
            positions: Current open positions
        """
        if not self.enabled:
            return

        subject = "Daily Trading Summary"
        body = f"""
Daily Trading Summary

Date: {datetime.now().strftime('%Y-%m-%d')}

Trades Executed: {trades}
Total P/L: {profit:+.2f}
Open Positions: {positions}

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        self._send_email(subject, body)

    def _send_email(self, subject: str, body: str):
        """Send email with retry logic.

        Args:
            subject: Email subject
            body: Email body
        """
        if not self.enabled or not self.recipients:
            return

        for attempt in range(1, self.max_retries + 1):
            try:
                # Create message
                msg = MIMEMultipart()
                msg["From"] = self.smtp_user
                msg["To"] = ", ".join(self.recipients)
                msg["Subject"] = subject

                msg.attach(MIMEText(body, "plain"))

                # Connect and send
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)

                logger.info(f"Email sent: {subject}")
                return

            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"SMTP authentication failed: {e}")
                break  # Don't retry auth errors

            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(
                        f"Email send failed (attempt {attempt}/{self.max_retries}): {e}"
                    )
                    time.sleep(1)
                else:
                    logger.error(
                        f"Email send failed after {self.max_retries} attempts: {e}"
                    )

    def test_connection(self) -> bool:
        """Test SMTP connection.

        Returns:
            True if connection successful
        """
        if not self.enabled:
            logger.info("Email notifications disabled, skipping test")
            return True

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)

            logger.info("SMTP connection test successful")
            return True

        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False

    def __repr__(self) -> str:
        """Return string representation of EmailNotifier."""
        return (
            f"EmailNotifier(enabled={self.enabled}, recipients={len(self.recipients)})"
        )
