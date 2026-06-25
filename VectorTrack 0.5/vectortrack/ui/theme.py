"""Theme tokens and theme application helpers for VectorTrack 0.5."""

from __future__ import annotations

from typing import Dict, Tuple

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
    "accent_active": "#1D4ED8",
    "accent_active_text": "#FFFFFF",
    "border": "#CBD5E1",
    "success": "#15803D",
    "warning": "#B45309",
    "danger": "#B91C1C",
}

DARK_TOKENS: Dict[str, str] = {
    # Neutral charcoal palette aligned with Vectorworks dark UI.
    "bg": "#252525",
    "surface": "#2B2B2B",
    "surface_alt": "#1E1E1E",
    "text": "#E0E0E0",
    "muted_text": "#A0A0A0",
    "accent": "#505050",
    "accent_text": "#FFFFFF",
    "accent_active": "#787878",
    "accent_active_text": "#FFFFFF",
    "border": "#3F3F3F",
    "success": "#6EB86E",
    "warning": "#D4A72C",
    "danger": "#C45C5C",
}

# Table row/status fills keyed by semantic status, then theme mode.
TABLE_STATUS_COLORS: Dict[str, Dict[str, Tuple[str, str]]] = {
    "active": {
        "light": ("#E8F4FF", "#1A1A1A"),
        "dark": ("#454545", "#E0E0E0"),
    },
    "inactive": {
        "light": ("#F0F0F0", "#777777"),
        "dark": ("#333333", "#909090"),
    },
    "excluded": {
        "light": ("#E8E8E8", "#777777"),
        "dark": ("#2B2B2B", "#787878"),
    },
    "conflict": {
        "light": ("#F6DEB2", "#1E293B"),
        "dark": ("#78350F", "#FDE68A"),
    },
    "warning": {
        "light": ("#F6DEB2", "#1E293B"),
        "dark": ("#92400E", "#FDE68A"),
    },
    "danger": {
        "light": ("#F2B8B5", "#1E293B"),
        "dark": ("#7F1D1D", "#FCA5A5"),
    },
    "heatmap_empty": {
        "light": ("#EEF2F7", "#64748B"),
        "dark": ("#333333", "#A0A0A0"),
    },
}


def current_theme_mode() -> str:
    app = QApplication.instance()
    if app is not None:
        mode = app.property("vectortrack_theme_mode")
        if isinstance(mode, str) and mode in {"light", "dark"}:
            return mode
    return "light"


def current_tokens() -> Dict[str, str]:
    app = QApplication.instance()
    if app is not None:
        stored = app.property("vectortrack_theme_tokens")
        if isinstance(stored, dict):
            return stored
    return LIGHT_TOKENS


def table_status_colors(status: str) -> Tuple[QColor, QColor]:
    """Return background/foreground colors for a table row status."""
    mode = current_theme_mode()
    bg, fg = TABLE_STATUS_COLORS.get(status, TABLE_STATUS_COLORS["inactive"])[mode]
    return QColor(bg), QColor(fg)


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
            background: {tokens["surface_alt"]};
            color: {tokens["muted_text"]};
            border: 1px solid {tokens["border"]};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        QTabBar::tab:selected {{
            background: {tokens["surface"]};
            color: {tokens["text"]};
        }}
        QTabBar::tab:hover {{
            color: {tokens["text"]};
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
            background: {tokens["accent_active"]};
            color: {tokens["accent_active_text"]};
            border-color: {tokens["border"]};
            font-weight: 600;
        }}
        QToolButton {{
            background: transparent;
            color: {tokens["text"]};
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QToolButton:hover {{
            background: {tokens["border"]};
            border-color: {tokens["border"]};
        }}
        QToolButton:checked,
        QToolButton:pressed {{
            background: {tokens["accent_active"]};
            color: {tokens["accent_active_text"]};
            border: 1px solid {tokens["border"]};
            font-weight: 600;
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
        QMenuBar {{
            background: {tokens["surface"]};
            color: {tokens["text"]};
            border-bottom: 1px solid {tokens["border"]};
        }}
        QMenuBar::item:selected {{
            background: {tokens["surface_alt"]};
        }}
        QMenu {{
            background: {tokens["surface"]};
            color: {tokens["text"]};
            border: 1px solid {tokens["border"]};
        }}
        QMenu::item:selected {{
            background: {tokens["accent"]};
            color: {tokens["accent_text"]};
        }}
        QToolBar {{
            background: {tokens["surface"]};
            border-bottom: 1px solid {tokens["border"]};
            spacing: 4px;
        }}
        QStatusBar {{
            background: {tokens["surface"]};
            color: {tokens["muted_text"]};
            border-top: 1px solid {tokens["border"]};
        }}
        QCheckBox {{
            color: {tokens["text"]};
            spacing: 6px;
        }}
        QGroupBox {{
            color: {tokens["text"]};
            border: 1px solid {tokens["border"]};
            border-radius: 6px;
            margin-top: 8px;
            padding-top: 8px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
            color: {tokens["muted_text"]};
        }}
        QScrollBar:vertical {{
            background: {tokens["surface_alt"]};
            width: 10px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {tokens["border"]};
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar:horizontal {{
            background: {tokens["surface_alt"]};
            height: 10px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {tokens["border"]};
            min-width: 24px;
            border-radius: 4px;
        }}
        QSplitter::handle {{
            background: {tokens["border"]};
        }}
        QProgressBar {{
            background: {tokens["surface_alt"]};
            border: 1px solid {tokens["border"]};
            border-radius: 4px;
            color: {tokens["text"]};
            text-align: center;
        }}
        QProgressBar::chunk {{
            background: {tokens["accent"]};
            border-radius: 3px;
        }}
        QTextEdit, QPlainTextEdit {{
            background: {tokens["surface"]};
            color: {tokens["text"]};
            border: 1px solid {tokens["border"]};
            border-radius: 6px;
        }}
        { _table_qss(tokens) }
        """
    )
    app.setProperty("vectortrack_theme_tokens", tokens)
    app.setProperty("vectortrack_theme_mode", normalized)
    return tokens

