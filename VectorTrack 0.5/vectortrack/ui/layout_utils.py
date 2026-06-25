"""Shared layout helpers for DPI-aware, compact UI."""

from __future__ import annotations

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QHeaderView, QTableWidget


def ui_scale() -> float:
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return 1.0
    return max(1.0, screen.logicalDotsPerInchX() / 96.0)


def scale_px(value: int) -> int:
    return int(value * ui_scale())


def adaptive_window_size() -> tuple[tuple[int, int], tuple[int, int]]:
    """Return (minimum_size, default_size) sized to the primary monitor."""
    base_min = (960, 640)
    fallback_default = (1280, 800)
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return base_min, fallback_default

    geo = screen.availableGeometry()
    min_w = min(int(base_min[0] * ui_scale()), int(geo.width() * 0.55))
    min_h = min(int(base_min[1] * ui_scale()), int(geo.height() * 0.55))
    min_w = max(min_w, 800)
    min_h = max(min_h, 540)

    default_w = int(geo.width() * 0.72)
    default_h = int(geo.height() * 0.78)
    default_w = max(min_w, min(default_w, geo.width() - 24))
    default_h = max(min_h, min(default_h, geo.height() - 24))
    return (min_w, min_h), (default_w, default_h)


def adaptive_dialog_size(
    base_min: tuple[int, int] = (900, 560),
    base_default: tuple[int, int] = (980, 640),
    screen_fraction: tuple[float, float] = (0.65, 0.72),
) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return dialog minimum and default sizes relative to the active screen."""
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return base_min, base_default

    geo = screen.availableGeometry()
    min_w = min(scale_px(base_min[0]), int(geo.width() * 0.5))
    min_h = min(scale_px(base_min[1]), int(geo.height() * 0.45))
    min_w = max(min_w, 720)
    min_h = max(min_h, 480)

    default_w = int(geo.width() * screen_fraction[0])
    default_h = int(geo.height() * screen_fraction[1])
    default_w = max(min_w, min(default_w, geo.width() - 24))
    default_h = max(min_h, min(default_h, geo.height() - 24))
    return (min_w, min_h), (default_w, default_h)


def configure_compact_table(
    table: QTableWidget,
    *,
    stretch_column: int | None = None,
    fixed_columns: dict[int, int] | None = None,
    content_columns: list[int] | None = None,
) -> None:
    """Apply compact row height and predictable column sizing."""
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    row_height = scale_px(26)
    vheader = table.verticalHeader()
    vheader.setVisible(False)
    vheader.setDefaultSectionSize(row_height)
    vheader.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

    if content_columns:
        for col in content_columns:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
    if fixed_columns:
        for col, width in fixed_columns.items():
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(col, scale_px(width))
    if stretch_column is not None:
        header.setSectionResizeMode(stretch_column, QHeaderView.ResizeMode.Stretch)
