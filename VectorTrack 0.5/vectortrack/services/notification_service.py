"""Windows notification helpers for VectorTrack events."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from loguru import logger


def hidden_subprocess_kwargs() -> dict[str, Any]:
    """Return subprocess kwargs that suppress console windows on Windows."""
    if sys.platform != "win32":
        return {}
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if not flags:
        return {}
    return {"creationflags": flags}


class NotificationService:
    """Dispatch notifications via the tray icon, with a hidden PowerShell fallback."""

    def __init__(self, enabled: bool = True, app_name: str = "VectorTrack") -> None:
        self.enabled = enabled
        self.app_name = app_name
        self._tray: Any = None

    def set_tray(self, tray: Any) -> None:
        self._tray = tray

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def notify_idle(self, file_name: str, idle_minutes: int) -> None:
        self.notify(
            "Idle detected",
            f"{file_name}: idle for {idle_minutes} minutes.",
        )

    def notify_budget_warning(self, project: str, used_percent: float) -> None:
        self.notify(
            "Budget warning",
            f"{project}: {used_percent:.0f}% of budget used.",
        )

    def notify_log_delta(self, file_name: str, delta_hours: float) -> None:
        self.notify(
            "Log delta detected",
            f"{file_name}: delta {delta_hours:+.2f}h.",
        )

    def notify_file_closed(self, file_name: str) -> None:
        self.notify(
            "File closed",
            f"{file_name} is no longer open in Vectorworks.",
        )

    def notify_eod(self, total_hours: float, amount: float) -> None:
        self.notify(
            "End of day summary",
            f"Tracked {total_hours:.2f}h today (${amount:.2f}).",
        )

    def notify(self, title: str, message: str) -> None:
        if not self.enabled:
            return
        if self._notify_tray(title, message):
            return
        self._notify_powershell(title, message)

    def _notify_tray(self, title: str, message: str) -> bool:
        tray = self._tray
        if tray is None:
            return False
        try:
            if hasattr(tray, "isVisible") and not tray.isVisible():
                return False
            # MessageIcon.Information == 1
            tray.showMessage(f"{self.app_name} - {title}", message, 1, 5000)
            return True
        except Exception as exc:
            logger.debug(f"Tray notification failed, using fallback: {exc}")
            return False

    def _notify_powershell(self, title: str, message: str) -> None:
        escaped_title = title.replace("'", "''")
        escaped_message = message.replace("'", "''")
        script = (
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
            "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null;"
            "$template = @\""
            "<toast><visual><binding template='ToastGeneric'>"
            f"<text>{self.app_name} - {escaped_title}</text><text>{escaped_message}</text>"
            "</binding></visual></toast>"
            "\"@;"
            "$xml = New-Object Windows.Data.Xml.Dom.XmlDocument;"
            "$xml.LoadXml($template);"
            "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml);"
            "$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('VectorTrack');"
            "$notifier.Show($toast);"
        )
        try:
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-WindowStyle",
                    "Hidden",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                check=False,
                capture_output=True,
                text=True,
                **hidden_subprocess_kwargs(),
            )
        except Exception as exc:  # pragma: no cover - best effort fallback
            logger.info(f"{self.app_name} notification [{title}]: {message}")
            logger.debug(f"PowerShell notification failed: {exc}")
