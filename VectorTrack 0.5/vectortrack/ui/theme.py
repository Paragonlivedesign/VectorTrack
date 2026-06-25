"""Theme tokens and theme application helpers for VectorTrack 0.5."""

from __future__ import annotations

from typing import Dict

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

LIGHT_TOKENS: Dict[str, str] = {
    "bg": "#F3F5F8",
    "surface": "#FFFFFF",
    "surface_alt": "#EEF2F7",
    "text": "#1E293B",
    "muted_text": "#64748B",
    "accent": "#1D4ED8",
    "accent_text": "#FFFFFF",
    "border": "#CBD5E1",
    "success": "#15803D",
    "warning": "#B45309",
    "danger": "#B91C1C",
}

DARK_TOKENS: Dict[str, str] = {
    "bg": "#111827",
    "surface": "#1F2937",
    "surface_alt": "#0F172A",
    "text": "#E5E7EB",
    "muted_text": "#94A3B8",
    "accent": "#3B82F6",
    "accent_text": "#F8FAFC",
    "border": "#334155",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
}


def _table_qss(tokens: Dict[str, str]) -> str:
    return f"""
        QTableWidget {{
            background: {tokens["surface"]};
            border: 1px solid {tokens["border"]};
            gridline-color: {tokens["border"]};
            color: {tokens["text"]};
            selection-background-color: {tokens["accent"]};
            selection-color: {tokens["accent_text"]};
        }}
        QHeaderView::section {{
            background: {tokens["surface_alt"]};
            color: {tokens["muted_text"]};
            padding: 4px 6px;
            border: none;
            border-right: 1px solid {tokens["border"]};
            border-bottom: 1px solid {tokens["border"]};
            font-weight: 600;
        }}
    """


def apply_theme(app: QApplication, mode: str = "light") -> Dict[str, str]:
    """Apply the selected global theme and return the active token map."""
    normalized = (mode or "light").strip().lower()
    tokens = DARK_TOKENS if normalized == "dark" else LIGHT_TOKENS

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(tokens["bg"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(tokens["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(tokens["surface"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(tokens["surface_alt"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(tokens["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(tokens["surface"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(tokens["text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(tokens["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(tokens["accent_text"]))
    app.setPalette(palette)

    app.setStyleSheet(
        f"""
        QWidget {{
            color: {tokens["text"]};
            font-family: "Segoe UI", Arial, sans-serif;
        }}
        QMainWindow, QDialog {{
            background: {tokens["bg"]};
        }}
        QFrame#card {{
            background: {tokens["surface"]};
            border: 1px solid {tokens["border"]};
            border-radius: 8px;
        }}
        QLabel#muted {{
            color: {tokens["muted_text"]};
        }}
        QLabel#dashboardValue {{
            font-size: 16px;
            font-weight: 700;
        }}
        QTabWidget::pane {{
            border: 1px solid {tokens["border"]};
            border-radius: 6px;
            top: -1px;
        }}
        QTabBar::tab {{
            padding: 6px 12px;
            margin-right: 2px;
        }}
        QPushButton {{
            background: {tokens["surface"]};
            border: 1px solid {tokens["border"]};
            padding: 6px 10px;
            border-radius: 6px;
        }}
        QPushButton:hover {{
            border-color: {tokens["accent"]};
        }}
        QPushButton:checked {{
            background: {tokens["accent"]};
            color: {tokens["accent_text"]};
            border-color: {tokens["accent"]};
        }}
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateTimeEdit {{
            background: {tokens["surface"]};
            border: 1px solid {tokens["border"]};
            border-radius: 6px;
            padding: 4px 6px;
        }}
        QListWidget {{
            background: {tokens["surface"]};
            border: 1px solid {tokens["border"]};
            border-radius: 6px;
            color: {tokens["text"]};
        }}
        QListWidget::item {{
            padding: 4px 6px;
        }}
        QListWidget::item:selected {{
            background: {tokens["accent"]};
            color: {tokens["accent_text"]};
        }}
        { _table_qss(tokens) }
        """
    )
    return tokens

