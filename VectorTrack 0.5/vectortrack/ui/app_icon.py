"""Resolve VectorTrack application icons for dev and frozen builds."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

from PyQt6.QtCore import QPointF, Qt, QSize
from PyQt6.QtGui import QIcon, QPainter, QPixmap, QColor, QPolygonF
from PyQt6.QtWidgets import QStyle, QWidget

TrayStatus = Literal["inactive", "tracking", "paused", "idle"]

_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _assets_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).resolve().parents[2] / "assets"


def _base_icon_path() -> Path | None:
    for name in ("vectortrack.ico", "vectortrack.png"):
        path = _assets_dir() / name
        if path.exists():
            return path
    return None


def app_icon(parent: QWidget | None = None) -> QIcon:
    path = _base_icon_path()
    if path is not None:
        icon = QIcon(str(path))
        if not icon.isNull():
            return icon
    if getattr(sys, "frozen", False):
        icon = QIcon(sys.executable)
        if not icon.isNull():
            return icon
    if parent is not None:
        return parent.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        return app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
    return QIcon()


def _draw_status_badge(painter: QPainter, size: int, status: TrayStatus) -> None:
    if status == "inactive":
        return
    badge_size = max(8, size // 2)
    badge_x = size - badge_size
    badge_y = size - badge_size
    painter.setBrush(QColor(20, 24, 32, 220))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(badge_x, badge_y, badge_size, badge_size)

    painter.setBrush(QColor(255, 255, 255))
    inset = badge_size * 0.22
    inner_w = badge_size - (2 * inset)
    inner_h = badge_size - (2 * inset)
    inner_x = badge_x + inset
    inner_y = badge_y + inset
    if status == "tracking":
        triangle = QPolygonF(
            [
                QPointF(inner_x, inner_y),
                QPointF(inner_x, inner_y + inner_h),
                QPointF(inner_x + inner_w, inner_y + (inner_h / 2)),
            ]
        )
        painter.drawPolygon(triangle)
        return
    bar_w = max(1.0, inner_w * 0.28)
    gap = max(1.0, inner_w * 0.18)
    total = (2 * bar_w) + gap
    start_x = inner_x + ((inner_w - total) / 2)
    painter.drawRect(int(start_x), int(inner_y), int(bar_w), int(inner_h))
    painter.drawRect(int(start_x + bar_w + gap), int(inner_y), int(bar_w), int(inner_h))


def _compose_tray_pixmap(base: QPixmap, size: int, status: TrayStatus) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scaled_base = base.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = (size - scaled_base.width()) // 2
    y = (size - scaled_base.height()) // 2
    painter.drawPixmap(x, y, scaled_base)
    _draw_status_badge(painter, size, status)
    painter.end()
    return pixmap


def tray_icon(parent: QWidget | None = None, status: TrayStatus = "inactive") -> QIcon:
    base_path = _base_icon_path()
    if base_path is not None:
        base = QPixmap(str(base_path))
    else:
        base = app_icon(parent).pixmap(QSize(256, 256))
    if base.isNull():
        base = app_icon(parent).pixmap(QSize(256, 256))
    icon = QIcon()
    for size in _ICON_SIZES:
        icon.addPixmap(_compose_tray_pixmap(base, size, status))
    return icon
