"""VectorTrack 0.5 service layer."""

from .alias_resolver import AliasMatch, AliasResolver
from .backup_service import BackupService
from .billing_service import BillingContext, BillingService, BillingSummary
from .import_export import ImportExportService, ImportPreview
from .log_service import LogService, LogSummary
from .hotkey_service import HotkeyService
from .notification_service import NotificationService
from .report_data import ReportDataBuilder, ReportDataSet, ReportFilter, ReportRow
from .report_service import ReportService

try:
    from .tracking_service import TrackingService, TrackingState
except Exception:  # pragma: no cover - optional at import time in lightweight test envs
    TrackingService = None  # type: ignore[assignment]
    TrackingState = None  # type: ignore[assignment]

__all__ = [
    "AliasMatch",
    "AliasResolver",
    "BackupService",
    "BillingContext",
    "BillingService",
    "BillingSummary",
    "ImportExportService",
    "ImportPreview",
    "HotkeyService",
    "LogService",
    "LogSummary",
    "NotificationService",
    "ReportDataBuilder",
    "ReportDataSet",
    "ReportFilter",
    "ReportRow",
    "ReportService",
    "TrackingService",
    "TrackingState",
]
