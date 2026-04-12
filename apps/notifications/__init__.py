"""Notification Module.

Compatibility shim: re-exports from backend.services.notification.
"""

__version__ = "1.0.0"
__author__ = "HaruPyQuant Team"

__all__ = [
    "NotificationManager",
    "NotificationManagerConfig",
    "NotificationError",
    "NotificationLevel",
    "EmailNotifier",
    "TelegramNotifier",
    "SMSNotifier",
    "NotificationTemplate",
    "NotificationConfig",
]


def __getattr__(name: str):
    if name == "NotificationManager":
        from backend.services.notification.manager import NotificationManager
        return NotificationManager
    if name == "NotificationManagerConfig":
        from backend.services.notification.manager import NotificationManagerConfig
        return NotificationManagerConfig
    if name == "NotificationError":
        from backend.services.notification.base import NotificationError
        return NotificationError
    if name == "NotificationLevel":
        from backend.services.notification.base import NotificationLevel
        return NotificationLevel
    if name == "EmailNotifier":
        from backend.services.notification.email import EmailNotifier
        return EmailNotifier
    if name == "TelegramNotifier":
        from backend.services.notification.telegram import TelegramNotifier
        return TelegramNotifier
    if name == "SMSNotifier":
        from backend.services.notification.sms import SMSNotifier
        return SMSNotifier
    if name == "NotificationTemplate":
        from backend.services.notification.templates import NotificationTemplate
        return NotificationTemplate
    if name == "NotificationConfig":
        from backend.services.notification.config import NotificationConfig
        return NotificationConfig
    raise AttributeError(f"module 'apps.notifications' has no attribute '{name}'")
