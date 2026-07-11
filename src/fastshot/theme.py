from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


class ThemeMode(str, Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class ThemeManager(QObject):
    changed = Signal(ThemeMode, ThemeMode)

    def __init__(self, app: QApplication, settings: QSettings | None = None) -> None:
        super().__init__(app)
        self.app = app
        self.settings = settings or QSettings()
        self.mode = self._stored_mode()
        self.app.styleHints().colorSchemeChanged.connect(self._system_scheme_changed)
        self.apply()

    @property
    def effective_mode(self) -> ThemeMode:
        if self.mode != ThemeMode.SYSTEM:
            return self.mode
        return (
            ThemeMode.DARK
            if self.app.styleHints().colorScheme() == Qt.ColorScheme.Dark
            else ThemeMode.LIGHT
        )

    def set_mode(self, mode: ThemeMode) -> None:
        if mode == self.mode:
            return
        self.mode = mode
        self.settings.setValue("appearance/theme", mode.value)
        self.apply()

    def apply(self) -> None:
        effective = self.effective_mode
        self.app.setPalette(_palette(effective))
        self.app.setStyleSheet(_stylesheet(effective))
        self.changed.emit(self.mode, effective)

    def _stored_mode(self) -> ThemeMode:
        value = self.settings.value("appearance/theme", ThemeMode.SYSTEM.value)
        try:
            return ThemeMode(str(value))
        except ValueError:
            return ThemeMode.SYSTEM

    def _system_scheme_changed(self, _scheme: Qt.ColorScheme) -> None:
        if self.mode == ThemeMode.SYSTEM:
            self.apply()


def _palette(mode: ThemeMode) -> QPalette:
    palette = QPalette()
    if mode == ThemeMode.DARK:
        colors = {
            QPalette.ColorRole.Window: "#202124",
            QPalette.ColorRole.WindowText: "#e8eaed",
            QPalette.ColorRole.Base: "#17181a",
            QPalette.ColorRole.AlternateBase: "#292b2f",
            QPalette.ColorRole.Text: "#e8eaed",
            QPalette.ColorRole.Button: "#292b2f",
            QPalette.ColorRole.ButtonText: "#e8eaed",
            QPalette.ColorRole.Highlight: "#3b82c4",
            QPalette.ColorRole.HighlightedText: "#ffffff",
            QPalette.ColorRole.PlaceholderText: "#9aa0a6",
        }
    else:
        colors = {
            QPalette.ColorRole.Window: "#f8f9fa",
            QPalette.ColorRole.WindowText: "#343a40",
            QPalette.ColorRole.Base: "#ffffff",
            QPalette.ColorRole.AlternateBase: "#f1f3f5",
            QPalette.ColorRole.Text: "#343a40",
            QPalette.ColorRole.Button: "#ffffff",
            QPalette.ColorRole.ButtonText: "#343a40",
            QPalette.ColorRole.Highlight: "#1971c2",
            QPalette.ColorRole.HighlightedText: "#ffffff",
            QPalette.ColorRole.PlaceholderText: "#868e96",
        }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#868e96"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#868e96"))
    return palette


def _stylesheet(mode: ThemeMode) -> str:
    if mode == ThemeMode.DARK:
        return """
            QMainWindow { background: #202124; }
            QToolBar { background: #252629; border: 0; border-bottom: 1px solid #3c4043; spacing: 4px; }
            QToolButton { padding: 6px; border-radius: 4px; border: 1px solid transparent; }
            QToolButton::menu-indicator { image: none; width: 0px; }
            QToolButton:hover, QToolButton:checked { background: #3c4043; border-color: transparent; }
            QTabWidget::pane { border: 0; }
            QTabWidget::tab-bar { alignment: left; }
            QTabBar::tab { padding: 7px 12px; background: #292b2f; border: 0; margin-right: 1px; }
            QTabBar::tab:selected { background: #202124; border-bottom: 2px solid #5da9e9; }
            QScrollArea { background: #111315; border: 0; }
            QMenu { background: #292b2f; border: 1px solid #4b4f54; }
            QMenu::item { padding: 6px 18px; }
            QMenu::item:selected { background: #3c4043; }
        """
    return """
        QMainWindow { background: #f8f9fa; }
        QToolBar { background: #ffffff; border: 0; border-bottom: 1px solid #dee2e6; spacing: 4px; }
        QToolButton { padding: 6px; border-radius: 4px; border: 1px solid transparent; }
        QToolButton::menu-indicator { image: none; width: 0px; }
        QToolButton:hover, QToolButton:checked { background: #e9ecef; border-color: transparent; }
        QTabWidget::pane { border: 0; }
        QTabWidget::tab-bar { alignment: left; }
        QTabBar::tab { padding: 7px 12px; background: #e9ecef; border: 0; margin-right: 1px; }
        QTabBar::tab:selected { background: #ffffff; border-bottom: 2px solid #1971c2; }
        QScrollArea { background: #ced4da; border: 0; }
        QMenu { background: #ffffff; border: 1px solid #ced4da; }
        QMenu::item { padding: 6px 18px; }
        QMenu::item:selected { background: #e7f5ff; }
    """
